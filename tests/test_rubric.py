import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sonar_eval import images
from sonar_eval.common import ROOT, read_json
from sonar_eval.config import load_suite

spec = importlib.util.spec_from_file_location("sonar_rubric_judge", images.JUDGE_CONTEXT / "judge.py")
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)


class RubricTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.source = ROOT / "suites/datasets/archive-access-decisions/prioritize-digitization/tests/rubric.json"
        self.rubric = judge.read_rubric(self.source)
        self.submission = self.folder / "submission.md"
        self.submission.write_text("Use four days for two fragile maps.")
        self.out = self.folder / "verifier"

    def response(self, levels=(2, 2, 1, 0), fenced=False):
        scores = [{"id": c["id"], "level": level, "reason": "Cites the case packet."}
                  for c, level in zip(self.rubric["criteria"], levels)]
        content = json.dumps({"scores": scores})
        if fenced:
            content = "```json\n" + content + "\n```"
        return {"id": "fixture", "model": judge.MODEL, "usage": {"total_tokens": 100},
                "choices": [{"finish_reason": "stop", "message": {"content": content}}]}

    def test_all_rubrics_match_their_submitted_assignment_and_verifier_image(self):
        _, tasks = load_suite(ROOT / "suites/rubric-tasks.json")
        images_seen = set()
        for name, task in tasks.items():
            with self.subTest(task=name):
                rubric = judge.read_rubric(task / "tests/rubric.json")
                self.assertEqual([c["weight"] for c in rubric["criteria"]], [30, 30, 25, 15])
                instruction = (task / "instruction.md").read_text()
                self.assertIn(rubric["source"], instruction)
                self.assertIn(rubric["assignment"], instruction)
                self.assertIn("/app/submission.md", instruction)
                self.assertEqual((task / "tests/test.sh").read_bytes(), (images.JUDGE_CONTEXT / "test.sh").read_bytes())
                self.assertEqual((task / "tests/Dockerfile").read_text(), images.RUBRIC_DOCKERFILE)
                config = images.read_manifest(task / "task.toml")
                self.assertEqual(config["verifier"]["environment_mode"], "separate")
                self.assertEqual(config["verifier"]["env"], {"SONAR_JUDGE_KEY": "${SONAR_JUDGE_KEY}"})
                actual = images.image_specs(task, "base")
                self.assertEqual(actual["main"][0], "sonar-eval/rubric-workspace:1")
                images_seen.add(actual["verifier"][0])
        self.assertEqual(len(images_seen), 40)

    def test_weighted_and_fenced_scores(self):
        for levels, expected in (((2, 2, 1, 0), .725), ((1, 2, 2, 2), .85), ((0, 0, 0, 0), 0), ((2, 2, 2, 2), 1)):
            for fenced in (True, False):
                result = self.response(levels, fenced)
                score, details = judge.score_response(self.rubric["criteria"], result)
                self.assertEqual(score, expected)
                self.assertEqual([item["level"] for item in details], list(levels))
                self.assertTrue(all(item["reason"] for item in details))

    def test_incomplete_or_invalid_provider_results_are_ungraded(self):
        response = self.response()
        scores = json.loads(response["choices"][0]["message"]["content"])["scores"]
        for invalid in [scores[:-1], [*scores[:-1], scores[0]], [{**scores[0], "level": True}, *scores[1:]],
                        [{**scores[0], "reason": ""}, *scores[1:]]]:
            response["choices"][0]["message"]["content"] = json.dumps({"scores": invalid})
            with self.assertRaises(ValueError):
                judge.score_response(self.rubric["criteria"], response)
        for result in [{**self.response(), "model": "wrong/model"}, {}, self.response()]:
            if "choices" in result and result.get("model") == judge.MODEL:
                result["choices"][0]["finish_reason"] = "length"
            with self.assertRaises(ValueError):
                judge.score_response(self.rubric["criteria"], result)

    def test_evidence_reward_and_failure_on_an_existing_output_directory(self):
        with patch.dict(os.environ, {"SONAR_JUDGE_KEY": "test-credential"}, clear=True):
            with patch.object(judge, "request_judgment", return_value=self.response(fenced=True)) as call:
                self.assertEqual(judge.grade(self.source, self.submission, self.out), 0)
                call.assert_called_once()
            evidence = read_json(self.out / "judge.json")
            self.assertEqual((evidence["reported_model"], evidence["reward"], len(evidence["scores"])), (judge.MODEL, .725, 4))
            self.assertEqual((self.out / "reward.txt").read_text().strip(), "0.725")
            self.assertNotIn("test-credential", (self.out / "judge.json").read_text())
            with patch.object(judge, "request_judgment", side_effect=ValueError("Infron returned HTTP 503")):
                self.assertEqual(judge.grade(self.source, self.submission, self.out), 1)
            self.assertEqual(read_json(self.out / "judge.json")["status"], "judge_error")
            self.assertFalse((self.out / "reward.txt").exists())
        with patch.dict(os.environ, {}, clear=True), patch.object(judge, "request_judgment") as call:
            self.assertEqual(judge.grade(self.source, self.submission, self.out), 1)
            self.assertFalse((self.out / "reward.txt").exists())
            self.submission.unlink()
            for value in (None, b" ", b"\xff", b"x" * (judge.MAX_BYTES + 1)):
                if value is not None:
                    self.submission.write_bytes(value)
                self.assertEqual(judge.grade(self.source, self.submission, self.out), 0)
                self.assertEqual(read_json(self.out / "judge.json")["status"], "invalid_submission")
                self.assertEqual((self.out / "reward.txt").read_text().strip(), "0")
            call.assert_not_called()
