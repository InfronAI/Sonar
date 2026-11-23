import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from sonar_eval import images, native, tuning
from sonar_eval.common import ROOT, EvalError, write_json
from sonar_eval.config import load_plan, load_suite, snapshot_tasks, task_hash
from sonar_eval.execution import execute
from sonar_eval.history import points
from sonar_eval.providers import configure, credential, harbor_model, save_infron_key


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.suite = ROOT / "suites/datasets/sql-analytics"
        self.key_file = self.base / ".sonar/credentials/infron-api-key"
        key_file = patch("sonar_eval.providers.INFRON_KEY_FILE", self.key_file)
        key_file.start()
        self.addCleanup(key_file.stop)

    def test_harbor_directory_dataset_and_single_task(self):
        suite, origins = load_suite(self.suite)
        ids = ["latest-readings", "unpaid-invoices"]
        self.assertEqual([c["id"] for c in suite["cases"]], ids)
        snapshot_tasks(origins, self.base / "snapshot")
        single, _ = load_suite(self.base / "snapshot" / ids[0])
        self.assertEqual(single["cases"][0], suite["cases"][0])
        task = self.base / "snapshot" / ids[0]
        self.assertEqual(task_hash(task), suite["cases"][0]["task_sha256"])
        state_names = (".sonar", ".harbor-eval", ".harbo")
        for state_name in state_names:
            private = task / state_name / "credentials"
            private.mkdir(parents=True)
            (private / "infron-api-key").write_text("fixture-secret")
        self.assertEqual(task_hash(task), suite["cases"][0]["task_sha256"])
        snapshot_tasks({ids[0]: task}, self.base / "copy")
        for state_name in state_names:
            self.assertFalse((self.base / "copy" / ids[0] / state_name).exists())
        (task / "instruction.md").write_text("Changed")
        self.assertNotEqual(task_hash(task), suite["cases"][0]["task_sha256"])

    def test_all_bundled_tasks_score_empty_and_reference_submissions(self):
        if not shutil.which("sh"):
            self.skipTest("POSIX shell required")
        complete, tasks = load_suite(images.ALL_TASKS)
        original, binary_tasks = load_suite(ROOT / "suites/all-tasks-v3.json")
        rubrics, judged_tasks = load_suite(ROOT / "suites/rubric-tasks.json")
        self.assertEqual((complete["version"], original["version"]), ("4", "3"))
        self.assertEqual((len(tasks), len(binary_tasks), len(judged_tasks)), (100, 60, 40))
        self.assertFalse(binary_tasks.keys() & judged_tasks.keys())
        self.assertEqual(tasks, {**binary_tasks, **judged_tasks})
        self.assertTrue(all("judge" not in c for c in original["cases"]))
        self.assertTrue(all(c["judge"]["model"] == "infron/op-5.5" and c["pass_threshold"] == .75
                            for c in rubrics["cases"]))
        groups = {task.parent for task in tasks.values()}
        self.assertEqual(len(groups), 50)
        self.assertTrue(all(len(load_suite(group)[1]) == 2 for group in groups))
        domains = json.loads((ROOT / "suites/domains.json").read_text())
        self.assertEqual(len(domains), 14)
        self.assertCountEqual((name for names in domains.values() for name in names), (g.name for g in groups))
        self.assertEqual(set(tasks.values()), {p.parent for p in (ROOT / "suites/datasets").glob("*/*/task.toml")})
        for task in binary_tasks.values():
            work = self.base / task.name
            shutil.copytree(task / "environment", work)
            env = {**os.environ, "SONAR_EVAL_REWARD_DIR": str(work / "grade")}
            for solve, expected in [(False, "0"), (True, "1")]:
                if solve:
                    subprocess.run(["sh", str(task / "solution/solve.sh")], cwd=work, env=env, check=True)
                subprocess.run(["sh", str(task / "tests/test.sh")], cwd=work, env=env,
                               check=True, capture_output=True)
                self.assertEqual((work / "grade/reward.txt").read_text().strip(), expected, task.name)

    def test_prebuilt_inputs_and_versions_are_checked_before_a_trial(self):
        task = self.base / "imported"
        shutil.copytree(self.suite / "unpaid-invoices", task)
        (task / "task.toml").write_text('[environment]\ncpus = 1\n')
        base_hash = task_hash(images.BASE_CONTEXT)
        initial = images.image_specs(task, base_hash)["main"]
        (task / "environment/example.json").write_text("[]")
        ref, _, stamp = images.image_specs(task, base_hash)["main"]
        self.assertNotEqual(initial[0], ref)
        cfg = {"agents": {"pi": {"name": "pi", "version": "1.6.0"}}, "pairs": [["m", "pi"]]}
        with patch.object(images, "inspect_image", return_value=("sha256:fake", "old")), \
                self.assertRaisesRegex(EvalError, "stale"):
            images.resolve_images(cfg, {"case": task})
        with patch.object(images, "inspect_image", return_value=("sha256:fake", stamp)), \
                patch.object(images, "docker", return_value="1.5.0") as command, \
                self.assertRaisesRegex(EvalError, "1.5.0"):
            images.resolve_images(cfg, {"case": task})
        self.assertIn("--pull=never", command.call_args.args)
        self.assertIn("none", command.call_args.args)
        image_id = "sha256:" + "a" * 64
        with patch.object(images, "inspect_image", side_effect=[EvalError("missing alias"), (image_id, "")]), \
                patch.object(images, "docker") as tag:
            alias = images.ensure_pinned(image_id)
        tag.assert_called_once_with("image", "tag", image_id, alias)

    def test_inference_precedence_transport_and_incompatible_controls(self):
        model = {"inference": {"reasoning_effort": "medium"}, "base_url": "http://provider.test/v1"}
        pi = {"name": "pi", "driver": "harbor", "inference": {"max_tokens": 800}}
        settings = tuning.resolve({"reasoning_effort": "low"}, model, pi, {"reasoning_effort": "high"})
        self.assertEqual(tuning.harbor_options("pi", {}, settings), {"reasoning_effort": "high", "max_output_tokens": "800"})
        for agent, bad in [("codex", {"max_tokens": 100}), ("pi", {"temperature": .2}),
                           ("opencode", {"top_p": 1.1}), ("claude-code", {"max_tokens": True})]:
            with self.subTest(agent=agent), self.assertRaises(EvalError):
                tuning.resolve({}, model, {"name": agent, "driver": "harbor"}, bad)
        with patch.dict(os.environ, {"CLAUDE_CODE_MAX_OUTPUT_TOKENS": "456"}, clear=True):
            settings = tuning.resolve({}, model, {"name": "claude-code", "driver": "harbor"}, {})
            self.assertEqual(settings["max_tokens"], 456)
            self.assertEqual(tuning.launch_env("claude-code", {}, settings)["CLAUDE_CODE_MAX_OUTPUT_TOKENS"], "456")
        cfg = {"name": "opencode", "driver": "harbor", "kwargs": {"opencode_config": json.dumps(
            {"default_agent": "bench", "agent": {"bench": {"top_p": .9, "description": "fixture"}}})}}
        settings = tuning.resolve({}, model, cfg, {"temperature": 0})
        actual = json.loads(tuning.harbor_options("opencode", cfg["kwargs"], settings)["opencode_config"])
        self.assertEqual(actual["agent"]["bench"], {"top_p": .9, "description": "fixture", "temperature": 0})
        with self.assertRaisesRegex(EvalError, "provider"):
            tuning.resolve({}, model, {**cfg, "kwargs": {"opencode_config": '{"provider": []}'}}, {"temperature": 0})
        for name, var in (("opencode", "OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX"),
                          ("copilot-cli", "COPILOT_PROVIDER_MAX_OUTPUT_TOKENS")):
            settings = tuning.resolve({}, model, {"name": name, "driver": "harbor"}, {"max_tokens": 1536})
            self.assertEqual(tuning.launch_env(name, {}, settings)[var], "1536")

    def test_compose_images_are_prepared_archived_and_recorded(self):
        task = self.base / "composed-task"
        env = task / "environment"
        env.mkdir(parents=True)
        (task / "instruction.md").write_text("Read the local dataset.")
        (task / "task.toml").write_text('[environment]\ndocker_image = "example/main:1"\n')
        (env / "docker-compose.yaml").touch()
        sidecar = "example/db:2"
        cfg = {"services": {"main": {}, "db": {"image": sidecar}, "cache": {"image": "example/main:1"}}}
        refs = {ref: "sha256:" + c * 64 for ref, c in ((images.BASE, "a"), ("example/main:1", "b"), (sidecar, "c"))}
        installed = {images.BASE, "example/main:1"}
        def lookup(ref):
            if ref not in installed:
                raise EvalError("Missing local image")
            return refs[ref], task_hash(images.BASE_CONTEXT) if ref == images.BASE else ""
        def docker(*args, **kwargs):
            if args[0] == "pull":
                installed.add(args[1])
            elif args[0] == "run":
                return "1.6.0"
        with patch.object(images, "compose_config", return_value=cfg), \
                patch.object(images, "inspect_image", side_effect=lookup), patch.object(images, "docker", side_effect=docker) as cmd:
            with redirect_stdout(StringIO()):
                images.build_images(task, self.base / "images.tar")
            saved = next(c.args for c in cmd.call_args_list if c.args[:2] == ("image", "save"))
            self.assertCountEqual(saved[4:], refs)
            self.assertIn(sidecar, installed)
            selected = {"agents": {"pi": native.agent_presets()["pi"]}, "pairs": [["local", "pi"]]}
            records = images.resolve_images(selected, {task.name: task})[task.name]
        self.assertEqual(records["service:environment/docker-compose.yaml:db"]["id"], refs[sidecar])
        self.assertEqual(records["main"]["compose_file"], "environment/docker-compose.yaml")
        self.assertEqual(records["main"]["cli_versions"], {"pi": "1.6.0"})

    def test_digest_archives_restore_verified_local_ids(self):
        ref = "registry.test:5000/team/db:2@sha256:" + "1" * 64
        image_id = "sha256:" + "2" * 64
        alias = images.archive_prefix(ref) + image_id.removeprefix("sha256:")
        self.assertTrue(alias.startswith("registry.test:5000/team/db:sonar-"))
        with patch.object(images, "inspect_image", side_effect=[(image_id, ""), EvalError("no tag")]), \
                patch.object(images, "docker") as docker:
            self.assertEqual(images.archive_image(ref), alias)
            docker.assert_called_once_with("image", "tag", ref, alias)
        with patch.object(images, "docker", return_value=alias.rpartition(":")[2]), \
                patch.object(images, "inspect_image", side_effect=[EvalError("no digest"), (image_id, "")]):
            self.assertEqual(images.inspect_prebuilt(ref)[0], image_id)
        with patch.object(images, "docker", return_value=alias.rpartition(":")[2]), \
                patch.object(images, "inspect_image", side_effect=[EvalError("no digest"), ("sha256:" + "3" * 64, "")]), \
                self.assertRaisesRegex(EvalError, "differs"):
            images.inspect_prebuilt(ref)

    def test_inherited_verifier_keeps_task_tests_and_shared_steps(self):
        task = self.base / "multi-step"
        tests = task / "tests"
        tests.mkdir(parents=True)
        (tests / "Dockerfile").write_text("FROM image:1\n")
        manifest = task / "task.toml"
        manifest.write_text('[agent]\ntimeout_sec=240\n[environment]\ndocker_image="example/task:1"\n'
                            '[verifier]\nenvironment_mode="shared"\ntimeout_sec=30\n'
                            '[[steps]]\nname="first"\n[steps.agent]\ntimeout_sec=45\n'
                            '[[steps]]\nname="second"\n[steps.verifier]\nenvironment_mode="separate"\n')
        specs = images.image_specs(task, "base")
        self.assertEqual(set(specs), {"main", "verifier"})
        self.assertEqual(specs["verifier"][1], tests)
        try:
            python = images.harbor_python()
        except EvalError as exc:
            self.skipTest(str(exc))
        refs = {"main": "frozen/task:1", "verifier": "frozen/check:1"}
        subprocess.run([python, "-m", "sonar_eval.images", str(manifest), json.dumps(refs), "{}", "600"],
                       cwd=ROOT, check=True, capture_output=True)
        cfg = images.read_manifest(manifest)
        self.assertEqual(cfg["agent"]["timeout_sec"], 600)
        self.assertEqual(cfg["steps"][0]["agent"]["timeout_sec"], 600)
        self.assertNotIn("agent", cfg["steps"][1])
        self.assertEqual(cfg["verifier"]["timeout_sec"], 30)
        self.assertEqual([s["verifier"]["environment_mode"] for s in cfg["steps"]], ["shared", "separate"])
        self.assertNotIn("environment", cfg["steps"][1]["verifier"])
        self.assertEqual(cfg["verifier"]["environment"]["docker_image"], "frozen/check:1")

    @unittest.skipUnless(os.name == "posix", "POSIX signals required")
    def test_trial_deadline_allows_process_cleanup(self):
        import sys
        code = ("import signal, time\nfrom pathlib import Path\n"
                "def cleanup(*args):\n    Path('cleaned').touch()\n    raise SystemExit()\n"
                "signal.signal(signal.SIGTERM, cleanup)\ntime.sleep(12)\n")
        with self.assertRaises(subprocess.TimeoutExpired):
            execute([sys.executable, "-c", code], self.base, self.base, 1)
        self.assertTrue((self.base / "cleaned").is_file())

    def test_gateway_protocols_and_secrets(self):
        with patch.dict(os.environ, {"INFRON_API_KEY": "secret-for-tests"}, clear=True), \
                patch("sonar_eval.config.harbor_version", return_value="0.27.0"):
            for name in native.PRESETS:
                with self.subTest(name=name):
                    cfg = native.matrix(name, "z-ai/glm-5.2", "infron", "GLM", self.suite)
                    plan, _ = load_plan(cfg)
                    self.assertEqual(plan["agents"][name]["driver"], "harbor")
                    self.assertEqual(plan["harbor_version"], "0.27.0")
                    options, env = harbor_model(name, plan["models"]["model"])
                    wire = options[options.index("--api-format") + 1]
                    expected = {"codex": "openai_responses", "claude-code": "anthropic_messages"}
                    self.assertEqual(wire, expected.get(name, "openai_chat_completions"))
                    endpoint = options[options.index("--base-url") + 1]
                    self.assertEqual(endpoint, "https://llm.onerouter.pro" + ("" if name == "claude-code" else "/v1"))
                    self.assertEqual(options[1].partition("/")[2], "z-ai/glm-5.2")
                    if name == "opencode":
                        self.assertEqual(options[1], "sonar-eval/z-ai/glm-5.2")
                    self.assertEqual(env["INFRON_API_KEY"], "secret-for-tests")
                    self.assertNotIn("secret-for-tests", json.dumps([options, plan]))
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(EvalError, "INFRON_API_KEY"):
            load_plan(cfg)

    def test_local_and_custom_providers(self):
        with patch.dict(os.environ, {}, clear=True):
            guest = {"provider": "ollama"}
            configure(guest)
            self.assertIn("host.docker.internal", guest["base_url"])
            self.assertEqual(credential(guest), "ollama")
        with self.assertRaises(EvalError):
            configure({"provider": "custom", "base_url": "https://user:secret@host/v1", "api_key_env": "TEAM_KEY"})
        with self.assertRaises(EvalError):
            configure({"provider": "infron", "base_url": "https://elsewhere.test"})
        with self.assertRaises(EvalError):
            configure({"provider": "team", "base_url": "http://service:invalid/v1", "api_key_env": "TEAM_KEY"})
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://gateway.test:8443/team",
                                     "ANTHROPIC_AUTH_TOKEN": "test-token"}, clear=True):
            model = native.matrix("claude-code", "opus", None, "Opus", self.suite)["models"][0]
            self.assertEqual(model["base_url"], "https://gateway.test:8443/team")
            self.assertEqual(model["api_key_env"], "ANTHROPIC_AUTH_TOKEN")
            self.assertNotIn("test-token", str(model))
        with patch.dict(os.environ, {"TEAM_KEY": "synthetic-secret"}, clear=True):
            model = {"provider": "custom", "name": "my/model", "api_key_env": "TEAM_KEY",
                     "base_url": "http://service.test:8080/v1"}
            configure(model)
            argv, env = harbor_model("pi", model)
            self.assertIn("openai/my/model", argv)
            self.assertIn("TEAM_KEY", argv)
            self.assertNotIn("synthetic-secret", str(argv))
            self.assertEqual(env["TEAM_KEY"], "synthetic-secret")

    def test_project_infron_key(self):
        model = {"name": "anthropic/claude-opus-5.5", "provider": "infron"}
        configure(model)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(save_infron_key("fixture-first"), self.key_file)
            save_infron_key("fixture-second")
            with self.assertRaises(EvalError):
                save_infron_key(" ")
            if os.name == "posix":
                self.assertEqual(self.key_file.stat().st_mode & 0o777, 0o600)
                self.assertEqual(self.key_file.parent.stat().st_mode & 0o777, 0o700)
            options, guest_env = harbor_model("claude-code", model)
            self.assertEqual(guest_env["INFRON_API_KEY"], "fixture-second")
            self.assertNotIn("fixture-second", json.dumps([model, options]))
            with self.assertRaises(EvalError):
                credential({**model, "provider": "other"})
            os.environ["INFRON_API_KEY"] = "fixture-override"
            self.assertEqual(credential(model), "fixture-override")

    def test_history_separates_model_endpoints(self):
        for i, (provider, url) in enumerate([("a", "http://a"), ("b", "http://b"), ("a", "http://a"),
                                              ("a", "http://different")]):
            directory = self.base / "runs" / str(i)
            directory.mkdir(parents=True)
            model = {"id": "m", "family": "Model", "version": str(i), "provider": provider, "base_url": url}
            agent = {"id": "a", "family": "Pi", "version": "1"}
            pair = {"model": model, "agent": agent, "seconds": 1, "reward_sum": 1,
                    "counts": {"pass": 1, "fail": 0, "error": 0, "timeout": 0}}
            write_json(directory / "summary.json", {"run_id": str(i), "started_at": str(i), "finished_at": str(i),
                       "track": "test", "signature": "same", "suite": {"id": "suite", "version": "1"},
                       "repetitions": 1, "timeout_seconds": 2, "pairs": [pair]})
        self.assertEqual([p["previous_run"] for p in points(self.base)], [None, None, "0", None])

    def test_history_separates_inference_settings_and_unrecorded_history(self):
        for i, value in enumerate([None, {"reasoning_effort": "low"}, {"reasoning_effort": "high"},
                                   {"reasoning_effort": "low"}]):
            directory = self.base / "runs" / str(i)
            directory.mkdir(parents=True)
            pair = {"model": {"id": "m", "family": "Model", "version": "1"}, "agent": {"id": "a", "family": "Pi", "version": "1"},
                    "counts": {"pass": 1, "fail": 0, "error": 0, "timeout": 0}, "reward_sum": 1, "seconds": 1}
            if value is not None:
                pair["inference"] = value
            write_json(directory / "summary.json", {"run_id": str(i), "started_at": str(i), "finished_at": str(i),
                       "track": "test", "signature": "same", "suite": {"id": "suite", "version": "1"},
                       "repetitions": 1, "timeout_seconds": 2, "pairs": [pair]})
        self.assertEqual([p["previous_run"] for p in points(self.base)], [None, None, None, "1"])
