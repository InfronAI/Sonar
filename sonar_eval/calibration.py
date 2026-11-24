"""Validate the production rubric judge on labeled public submissions."""
import importlib.util
import os
import tempfile
from pathlib import Path

from .common import ROOT, read_json, write_json
from .config import file_hash
from .providers import JUDGE_CONTEXT, judge_credential


def calibrate(state, repetitions):
    if repetitions < 1:
        raise ValueError("Calibration repetitions must be positive")
    spec = importlib.util.spec_from_file_location("sonar_calibration_judge", JUDGE_CONTEXT / "judge.py")
    judge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(judge)
    packet = read_json(ROOT / "validation/calibration/digitization.json")
    rubric_path = ROOT / packet["task"] / "tests/rubric.json"
    rubric = judge.read_rubric(rubric_path)
    key = judge_credential()
    root = state / "validation"
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="calibration-", dir=root))
    report = {"task": packet["task"], "judge": judge.MODEL, "rubric_sha256": file_hash(rubric_path),
              "judge_sha256": file_hash(JUDGE_CONTEXT / "judge.py"), "threshold": rubric["pass_threshold"],
              "repetitions": repetitions, "samples": []}
    write_json(directory / "packet.json", packet)
    write_json(directory / "rubric.json", rubric)
    previous_key = os.environ.get("SONAR_JUDGE_KEY")
    try:
        os.environ["SONAR_JUDGE_KEY"] = key
        for sample in packet["samples"]:
            levels = sample["levels"]
            expected = sum(c["weight"] * levels[c["id"]] for c in rubric["criteria"]) / 200
            obs = {"id": sample["id"], "expected_reward": expected, "levels": levels,
                   "unexpected_levels": 0, "unexpected_verdicts": 0, "errors": 0, "passed": 0, "graded": 0}
            report["samples"].append(obs)
            folder = directory / sample["id"]
            folder.mkdir()
            submission = folder / "submission.md"
            submission.write_text(sample["submission"], encoding="utf-8")
            for i in range(1, repetitions + 1):
                output = folder / str(i)
                if judge.grade(directory / "rubric.json", submission, output):
                    obs["errors"] += 1
                else:
                    evidence = read_json(output / "judge.json")
                    passed = evidence["reward"] >= rubric["pass_threshold"]
                    obs["graded"] += 1
                    obs["passed"] += int(passed)
                    obs["unexpected_verdicts"] += int(passed != (expected >= rubric["pass_threshold"]))
                    actual = {c["id"]: c["level"] for c in evidence.get("scores", [])}
                    obs["unexpected_levels"] += sum(actual.get(k) != v for k, v in levels.items())
                write_json(directory / "summary.json", report)
    finally:
        if previous_key is None:
            os.environ.pop("SONAR_JUDGE_KEY", None)
        else:
            os.environ["SONAR_JUDGE_KEY"] = previous_key
    return directory, report
