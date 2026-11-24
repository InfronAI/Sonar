import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

from sonar_eval.common import ROOT, read_json
from sonar_eval.config import load_suite
from sonar_eval.grading import harbor_grade
from sonar_eval.measurements import aligned_outcomes, harbor_measurements, repeatability, summarize_measurements
from sonar_eval.scripted_endpoint import scripted_reply
from sonar_eval.smoke import check_pair

RULES = {"reward_key": "reward", "pass_threshold": 1}


class DiagnosticsTests(unittest.TestCase):
    def test_nested_exception_and_invalid_reward_override_positive_aggregate(self):
        full = {"schema_version": 1, "verifier_result": {"rewards": {"reward": 1}}}
        self.assertEqual(harbor_grade(full, RULES)["status"], "pass")
        self.assertEqual(harbor_grade({**full, "reward_valid": False}, RULES)["status"], "error")
        bad = {"step_name": "revise", "exception_info": {"exception_type": "VerifierTimeoutError"}}
        result = harbor_grade({**full, "step_results": [full, bad], "reward_valid": False}, RULES)
        self.assertEqual((result["status"], result["reward"]), ("timeout", None))
        self.assertIn("revise", result["reason"])

    def test_multistep_measurements_preserve_partial_coverage(self):
        timing = {"started_at": "2026-11-01T00:00:00Z", "finished_at": "2026-11-01T00:00:01Z"}
        steps = [{"agent_result": {"n_output_tokens": 12, "cost_usd": 0}, "agent_execution": timing},
                 {"agent_result": {"n_output_tokens": 0}, "agent_execution": timing}]
        measurement = harbor_measurements({"agent_result": {"n_output_tokens": 99}, "step_results": steps})
        self.assertEqual(measurement, {"n_output_tokens": 12, "agent_execution": 2})
        self.assertEqual(summarize_measurements([{"measurements": measurement}, {}])["n_output_tokens"]["observed"], 1)
        self.assertEqual(harbor_measurements({"agent_result": {"cost_usd": 0}}), {"cost_usd": 0})

    def test_repeatability_uses_only_complete_tasks_for_any_and_all(self):
        trials = [{"case": c, "attempt": i, "status": v}
                  for c, outcomes in {"a": ["pass", "pass"], "b": ["pass", "fail"], "c": ["pass", "timeout"]}.items()
                  for i, v in enumerate(outcomes, 1)]
        r = repeatability(trials, 2)
        self.assertEqual((r["passed"], r["graded"], r["any"], r["all"], r["mixed"], r["complete"], r["tasks"]),
                         (4, 5, 2, 1, 1, 2, 3))

    def test_changed_task_versions_are_listed_apart_from_transitions(self):
        trial = {"case": "a", "attempt": 1, "status": "pass", "reward": 1}
        newer = {**trial, "status": "fail", "reward": 0}
        rows, counts = aligned_outcomes([trial], [newer], {"a": "old"}, {"a": "new"})
        self.assertEqual(counts, [])
        self.assertFalse(rows[0]["same_revision"])
        rows, counts = aligned_outcomes([trial], [newer], {"a": "old"}, {"a": "old"})
        self.assertEqual(counts, [{"before": "pass", "after": "fail", "count": 1}])

    def test_frozen_quick_suite_covers_domains_and_both_grading_paths(self):
        suite = ROOT / "suites"
        _, full = load_suite(suite / "all-tasks-v4.json")
        quick, selected = load_suite(suite / "quick-14.json")
        domains = {name: k for k, names in read_json(suite / "domains.json").items() for name in names}
        self.assertEqual(len(selected), 14)
        self.assertEqual(len({domains[p.parent.name] for p in selected.values()}), 14)
        self.assertEqual(sum("judge" in c for c in quick["cases"]), 6)
        self.assertTrue(all(path == full[k] for k, path in selected.items()))

    def test_scripted_tool_value_must_arrive_via_a_tool_result(self):
        tools = [{"type": "function", "function": {"name": "bash", "parameters": {"properties": {"command": {}}}}}]
        token = "SNR-12345678"
        msgs = [{"role": "user", "content": "SONAR_TOOL_TASK"}, {"role": "assistant", "content": token}]
        self.assertEqual(scripted_reply({"messages": msgs, "tools": tools}, token)[1], "read")
        msgs.append({"role": "tool", "content": token})
        self.assertEqual(scripted_reply({"messages": msgs, "tools": tools}, token)[1], "write")

    def test_diagnostic_verifies_inference_and_tool_round_trip_on_the_selected_route(self):
        pair = {"model": {"name": "test", "id": "route-1"}, "agent": {"name": "pi"}, "counts": {"pass": 2},
                "inference": {"max_tokens": 256, "top_p": 0.5, "max_turns": 3}}
        request = {"model": "test", "path": "/pi/route-1/v1/responses",
                   "fields": {"max_output_tokens": 256, "top_p": 0.5}}
        calls = [{**request, "case": case, "action": action}
                 for case, action in (("direct", "write"), ("tool", "read"), ("tool", "write"))]
        other = {**calls[0], "path": "/pi/route-2/v1/responses", "fields": {}}
        title = {**calls[0], "action": "no shell tool", "fields": {"temperature": 0.5}}
        report = check_pair(pair, calls + [other, title])
        self.assertTrue(report["passed"])
        self.assertEqual(report["other_requests"], 1)
        self.assertEqual(report["observed_inference"], {"max_tokens": [256] * 3, "top_p": [0.5] * 3})
        self.assertFalse(check_pair(pair, calls[::-1])["passed"])
        self.assertFalse(check_pair(pair, [*calls, {**calls[-1], "fields": {}}])["passed"])

    def test_workflows_grade_the_first_submission_and_preserve_state_for_the_revision(self):
        workflows = ROOT / "suites/datasets/agent-workflows"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            def run(task, script):
                subprocess.run(["sh", str(workflows / task / script)], cwd=workspace, check=True,
                               env={**os.environ, "SONAR_EVAL_REWARD_DIR": tmp})
            def reward(task, script):
                run(task, script)
                return int((workspace / "reward.txt").read_text())

            task = "repair-inventory-query"
            (workspace / "query.sql").write_text("SELECT sku, MAX(units) FROM readings GROUP BY sku")
            self.assertEqual(reward(task, "tests/test.sh"), 0)
            run(task, "steps/repair/workdir/setup.sh")
            feedback = (workspace / "feedback.txt").read_text()
            self.assertIn("Expected rows: [('A', 0), ('B', 12)]", feedback)
            self.assertIn("Your rows (up to ten): [('A', 2), ('B', 12)]", feedback)
            run(task, "solution/solve.sh")
            self.assertEqual(reward(task, "tests/test.sh"), 1)

            task = "reschedule-scanner"
            run(task, "steps/book/workdir/setup.sh")
            self.assertEqual(reward(task, "steps/book/tests/test.sh"), 0)
            run(task, "steps/book/solution/solve.sh")
            self.assertEqual(reward(task, "steps/book/tests/test.sh"), 1)
            self.assertEqual(reward(task, "steps/reschedule/tests/test.sh"), 0)
            run(task, "steps/reschedule/solution/solve.sh")
            self.assertEqual(reward(task, "steps/reschedule/tests/test.sh"), 1)
            with sqlite3.connect(workspace / "calendar.db") as db:
                db.execute("DELETE FROM bookings WHERE job='atlas'")
            self.assertEqual(reward(task, "steps/reschedule/tests/test.sh"), 0)
