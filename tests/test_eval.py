import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from sonar_eval import native, runner
from sonar_eval.catalog import experiments
from sonar_eval.cli import list_runs, main
from sonar_eval.common import ROOT, EvalError, LockBusy, lock, read_json, write_json
from sonar_eval.config import load_plan
from sonar_eval.grading import harbor_grade
from sonar_eval.history import points
from sonar_eval.reporting import file_for


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="sonar test ")
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.state = self.base / "state"
        self.config = self.base / "matrix.json"
        self.suite = self.base / "sql-analytics"
        shutil.copytree(ROOT / "suites/datasets/sql-analytics", self.suite)
        self.cfg = read_json(ROOT / "configs/ollama.json")
        self.cfg["suite"] = str(self.suite)
        write_json(self.config, self.cfg)
        # Exercise the production subprocess and result contract without a model account or a Docker daemon.
        binary = self.base / "harbor"
        binary.write_text("""#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
args = sys.argv[1:]
if '--version' in args:
    print('0.27.0')
    sys.exit()
name = args[args.index('-m')+1]
task = Path(args[args.index('-p')+1])
assert args[args.index('-a')+1] == 'pi'
assert 'skip_install=true' in args and 'version=1.6.0' in args
assert (task/'instruction.md').is_file()
if name.endswith('/slow'):
    time.sleep(5)
if name.endswith('/error'):
    sys.exit(7)
target = Path(args[args.index('-o')+1]) / args[args.index('--job-name')+1] / 'trials' / 'trial'
target.mkdir(parents=True)
value = int(name.endswith('/revision-2') or task.name == 'latest-readings')
if (task/'tests/rubric.json').exists():
    assert '--yes' in args and os.environ.get('SONAR_JUDGE_KEY') == 'fixture-judge-key'
    value = 0.75
    (target/'verifier').mkdir()
    (target/'verifier/judge.json').write_text(json.dumps({'status':'graded','reward':value}))
(target/'result.json').write_text(json.dumps({'agent_info': {'name': 'pi', 'version':'1.6.0'},
    'exception_info': None, 'verifier_result': {'rewards': {'reward': value}}}))
""")
        binary.chmod(0o755)
        runtime = patch.dict(os.environ, {"SONAR_EVAL_HARBOR_BIN": str(binary)})
        runtime.start()
        self.addCleanup(runtime.stop)
        self.image_id = "sha256:" + "a" * 64
        self.platform = {"daemon": "linux/arm64", "default": "linux/arm64"}
        def test_images(plan, origins):
            return {case: {"main": {"image": "test/task:1", "id": self.image_id}} for case in origins}
        for name, replacement in [("resolve_images", test_images), ("docker_platform", lambda: self.platform),
                                  ("pin_snapshot", lambda task, images, agent_timeout=None: None),
                                  ("ensure_pinned", lambda image_id: image_id)]:
            mock = patch.object(runner.images, name, replacement)
            mock.start()
            self.addCleanup(mock.stop)

    def cli(self, *args):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return main(list(map(str, args)))

    def run_matrix(self):
        write_json(self.config, self.cfg)
        return self.cli("run", "--state", self.state, "--config", self.config)

    def test_relocated_report_catalog_without_runtime(self):
        project = self.base / "new workspace"
        project.mkdir()
        for folder in ("sonar_eval", "configs", "suites"):
            shutil.copytree(ROOT / folder, project / folder, ignore=shutil.ignore_patterns("__pycache__"))
        (project / "docker/agents").mkdir(parents=True)
        shutil.copy2(ROOT / "docker/agents/package.json", project / "docker/agents/package.json")
        shutil.copy2(ROOT / "sonar", project / "sonar")
        env = {"PATH": os.environ["PATH"], "PYTHONNOUSERSITE": "1"}
        subprocess.run([sys.executable, project / "sonar", "report"], env=env, cwd=self.base,
                       capture_output=True, check=True)
        state = project / ".sonar"
        self.assertFalse(points(state))
        self.assertIn("100 tasks", (state / "report.html").read_text())
        self.assertIn('href="report/rankings.html"', (state / "report.html").read_text())
        self.assertIn("after the first completed run", (state / "report/rankings.html").read_text())
        self.assertEqual(len(list((state / "report").glob("dataset-*.html"))), 50)
        self.assertEqual(len(list((state / "report").glob("agent-*.html"))), 5)
        self.assertIn("No completed runs", (state / "report/agent-codex.html").read_text())
        catalog = (state / "report/experiments.html").read_text()
        self.assertIn("500 attempts", catalog)
        self.assertIn("example-matrix.json", catalog)
        rubric = (state / "report/dataset-archive-access-decisions.html").read_text()
        self.assertIn("infron/op-5.5", rubric)
        self.assertIn("Full credit (2)", rubric)
        self.assertIn("0.75", rubric)
        self.assertIn("12 staff-days", rubric)
        dataset = (state / "report/dataset-coding-bugfix.html").read_text()
        self.assertIn("Preserve its public function", dataset)
        self.assertIn("Verifier script", dataset)
        self.assertIn("--suite suites/datasets/coding-bugfix/repair-expiring-cache", dataset)

    def test_catalog_uses_run_validation_without_credentials(self):
        configs = self.base / "configs"
        configs.mkdir()
        (self.base / "suites/datasets").mkdir(parents=True)
        (self.base / "suites/datasets/notes").mkdir()
        write_json(self.base / "suites/domains.json", {})
        packages = self.base / "docker/agents"
        packages.mkdir(parents=True)
        shutil.copy2(ROOT / "docker/agents/package.json", packages)
        good = {**self.cfg, "models": [{**self.cfg["models"][0], "provider": "infron"}]}
        write_json(configs / "good.json", good)
        for key, value in (("schema", True), ("track", ""), ("timeout_seconds", 0), ("repetitions", 0),
                           ("agents", ["unknown"]), ("inference", {"temperature": .3})):
            cfg = {**good, key: value}
            write_json(configs / f"{key}.json", cfg)
            with self.subTest(key=key), self.assertRaises(EvalError):
                load_plan(cfg)
        with patch("sonar_eval.config.credential", side_effect=AssertionError("credential access")), \
                patch("sonar_eval.config.harbor_version", side_effect=AssertionError("runtime access")):
            _, entries = experiments(self.base)
        valid = [entry for entry in entries if not entry.get("unavailable")]
        self.assertEqual([entry["name"] for entry in valid], ["good.json"])
        self.assertEqual(valid[0]["pairs"][0][0], native.agent_presets()["pi"])
        self.assertTrue(all(" doctor " in e["command"] for e in entries if e.get("unavailable")))

    def test_image_identity_controls_comparisons_and_matches_doctor(self):
        self.assertEqual(self.run_matrix(), 0)
        original = points(self.state)[-1]
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["doctor", "--config", str(self.config)]), 0)
        self.assertIn(original["signature"], output.getvalue())
        self.image_id = "sha256:" + "b" * 64
        self.assertEqual(self.run_matrix(), 0)
        rebuilt = points(self.state)[-1]
        self.assertEqual(rebuilt["benchmark_sha256"], original["benchmark_sha256"])
        self.assertNotEqual(rebuilt["environment_sha256"], original["environment_sha256"])
        self.assertIsNone(rebuilt["delta_pp"])
        self.assertIsNone(rebuilt["previous_run"])
        self.image_id = "sha256:" + "a" * 64
        self.assertEqual(self.run_matrix(), 0)
        self.assertEqual(points(self.state)[-1]["previous_run"], original["run_id"])
        with patch.object(runner.images, "resolve_images", return_value={}), self.assertRaisesRegex(EvalError, "main image"):
            runner.create_run(self.state, self.config)
        self.assertEqual(len(list((self.state / "runs").iterdir())), 3)
        directory = runner.create_run(self.state, self.config)
        self.platform = {"daemon": "linux/amd64", "default": "linux/amd64"}
        with self.assertRaisesRegex(runner.SnapshotChanged, "platform"):
            runner.evaluate(directory)
        cross_platform, _ = runner.prepare_plan(self.config)
        self.assertNotEqual(cross_platform["environment_sha256"], original["environment_sha256"])

    def test_delta_members_suite_revisions_and_selective_pairs(self):
        self.assertEqual(self.run_matrix(), 0)
        model = self.cfg["models"][0]
        model.update(version="2", name="revision-2")
        self.assertEqual(self.run_matrix(), 0)
        first, second = points(self.state)
        self.assertEqual(second["delta_pp"], 50.0)
        self.assertEqual(second["previous_run"], first["run_id"])
        self.cfg["models"].append({**model, "id": "sibling", "name": "sibling", "version": "1"})
        self.assertEqual(self.run_matrix(), 0)
        third = points(self.state)[-1]
        self.assertEqual((third["total"], third["pass_rate"], third["delta_pp"]), (4, .75, None))
        pages = self.state / "report"
        for name, expected in [("revision-2", "2 / 2"), ("sibling", "1 / 2")]:
            page = pages / file_for("pair", ("pi", ("ollama", name)))
            self.assertIn(expected, page.read_text())
            self.assertNotIn("3 / 4", page.read_text())
        task = self.suite / "unpaid-invoices/instruction.md"
        task.write_text(task.read_text() + "\nClarification.\n")
        self.assertEqual(self.run_matrix(), 0)
        self.assertNotEqual(points(self.state)[-1]["signature"], third["signature"])
        self.assertIsNone(points(self.state)[-1]["previous_run"])
        self.cfg.update(pairs=[["sibling", "pi"]], repetitions=2)
        self.assertEqual(self.run_matrix(), 0)
        self.assertEqual(points(self.state)[-1]["total"], 4)

    def test_resume_committed_trials_and_reject_changed_snapshot(self):
        directory = runner.create_run(self.state, self.config)
        original = runner.run_trial
        def interrupt(*args):
            if args[3]["id"] == "unpaid-invoices":
                raise KeyboardInterrupt
            return original(*args)
        with patch.object(runner, "run_trial", side_effect=interrupt), redirect_stderr(io.StringIO()), \
                self.assertRaises(KeyboardInterrupt):
            runner.evaluate(directory)
        self.assertFalse(points(self.state))
        first = runner.trial_dir(directory, 1) / "result.json"
        mtime = first.stat().st_mtime_ns
        with lock(directory / ".worker.lock"), self.assertRaises(LockBusy):
            runner.evaluate(directory)
        for _ in range(2):
            self.assertEqual(self.cli("resume", directory.name, "--state", self.state), 0)
        self.assertEqual(first.stat().st_mtime_ns, mtime)
        self.assertEqual(len(points(self.state)), 1)
        new = runner.create_run(self.state, self.config)
        (new / "tasks/unpaid-invoices/instruction.md").write_text("Changed")
        with self.assertRaises(runner.SnapshotChanged):
            runner.evaluate(new)

    def test_error_timeout_missing_reward(self):
        self.cfg["models"] = [{**self.cfg["models"][0], "id": mode, "family": mode, "name": mode}
                              for mode in ("slow", "error")]
        self.cfg["timeout_seconds"] = .5
        self.assertEqual(self.run_matrix(), 1)
        results = {p["model_family"]: p for p in points(self.state)}
        for name, state in (("slow", "timeout"), ("error", "error")):
            self.assertEqual(results[name]["counts"][state], 2)
            self.assertIsNone(results[name]["mean_reward"])
        with self.assertRaises(EvalError):
            harbor_grade({"verifier_result": {"rewards": {}}}, {"reward_key": "reward", "pass_threshold": 1})
        self.assertEqual(harbor_grade({"exception_info": {"exception_type": "AgentTimeoutError"}}, {})["status"], "timeout")

    def test_rejects_invalid_matrix(self):
        for key, value in [("pairs", [["unknown", "pi"]]), ("purpose", "reference")]:
            with self.subTest(key=key), self.assertRaises(EvalError):
                load_plan({**self.cfg, key: value})
        with self.assertRaises(EvalError):
            load_plan({**self.cfg, "agents": [{**native.agent_presets()["pi"], "name": "oracle"}]})

    def test_rubric_pipeline_uses_the_task_threshold_and_verifier_credential(self):
        task = ROOT / "suites/datasets/archive-access-decisions/prioritize-digitization"
        self.cfg["suite"] = str(task)
        with patch.dict(os.environ, {"INFRON_API_KEY": "fixture-judge-key"}):
            self.assertEqual(self.run_matrix(), 0)
        run = next((self.state / "runs").iterdir())
        plan = read_json(run / "plan.json")
        case = plan["suite"]["cases"][0]
        self.assertEqual(case["pass_threshold"], .75)
        trial = read_json(run / "trials/000001/result.json")
        self.assertEqual((trial["status"], trial["reward"]), ("pass", .75))
        self.assertEqual(trial["metadata"]["judge"]["model"], "infron/op-5.5")
        self.assertEqual(trial["metadata"]["configured_provider"], "ollama")
        self.assertNotIn("fixture-judge-key", (run / "plan.json").read_text())
        self.assertNotIn("fixture-judge-key", (run / trial["evidence"] / "argv.json").read_text())
        page = (self.state / "report" / file_for("run", run.name)).read_text()
        self.assertIn("Rubric assessment", page)
        self.assertIn("Frozen rubric", page)

    def test_report_crosslinks_evidence_and_escaping(self):
        self.cfg["models"][0]["family"] = "<script>model</script>"
        self.assertEqual(self.run_matrix(), 0)
        record = points(self.state)[0]
        run_id = record["run_id"]
        pages = self.state / "report"
        key = ("ollama", "qwen3-vl:2b-instruct")
        pair = file_for("pair", ("pi", key))
        for name in ["agent-pi.html", file_for("model", key)]:
            self.assertIn(pair, (pages / name).read_text())
        run_page = file_for("run", run_id)
        self.assertIn(run_page + "#pair-", (pages / "rankings.html").read_text())
        self.assertIn(run_page + "#pair-", (pages / pair).read_text())
        dataset = (pages / "dataset-sql-analytics.html").read_text()
        self.assertIn(run_page + "#pair-", dataset)
        self.assertIn(run_page + "#trial-", dataset)
        for dimension in ("task", "agent", "model", "run", "provider", "status"):
            self.assertIn('select name="' + dimension + '"', dataset)
        detail = (pages / run_page).read_text()
        self.assertIn(f'../runs/{run_id}/plan.json', detail)
        self.assertIn("Client defaults", detail)
        self.assertIn("Harbor result", detail)
        self.assertIn('id="trial-', detail)
        self.assertIn("Frozen instruction", detail)
        for trial in runner.inspect_run(self.state / "runs" / run_id)["trials"]:
            self.assertIn(trial["harbor_result"], detail)
        overview = (self.state / "report.html").read_text()
        self.assertIn("&lt;script&gt;model&lt;/script&gt;", overview)
        self.assertNotIn("<script>model", overview)
        shutil.rmtree(self.state / "runs" / run_id)
        self.assertEqual(self.cli("report", "--state", self.state), 0)
        self.assertFalse((pages / run_page).exists())

    def test_replaced_run_links_preserve_the_new_plan_and_count_once(self):
        self.assertEqual(self.run_matrix(), 0)
        run = next((self.state / "runs").iterdir())
        previous_id = "previous-execution"
        (run.parent / previous_id).symlink_to(run.name, target_is_directory=True)
        counts = {"pass": 1, "fail": 1, "error": 0, "timeout": 0}
        trial = read_json(run / "trials/000001/result.json")
        write_json(run / "retest.json", {
            "previous": {"run_id": previous_id, "agent_timeout_seconds": 240, "counts": {**counts, "pass": 0, "timeout": 1}},
            "current": {"run_id": run.name, "agent_timeout_seconds": 600, "counts": counts},
            "tasks": [{**{k: trial[k] for k in ("agent", "model", "case", "attempt")},
                       "previous": {"status": "timeout", "agent_seconds": 240.1},
                       "current": {"status": "pass", "agent_seconds": 257.2}}],
        })
        self.assertEqual([r["run_id"] for r in list_runs(self.state)], [run.name])
        self.assertEqual([p["run_id"] for p in points(self.state)], [run.name])
        self.assertEqual(self.cli("report", "--state", self.state), 0)
        canonical = self.state / "report" / file_for("run", run.name)
        alias = self.state / "report" / file_for("run", previous_id)
        self.assertEqual(alias.read_bytes(), canonical.read_bytes())
        self.assertIn("Retest comparison", alias.read_text())
        self.assertIn('href="#trial-', alias.read_text())
        self.assertIn("257.2 s", alias.read_text())
        self.assertEqual(runner.inspect_run(run.parent / previous_id)["plan"]["run_id"], run.name)
