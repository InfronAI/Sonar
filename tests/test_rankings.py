import unittest
from collections import Counter
from fractions import Fraction
from html.parser import HTMLParser

from sonar_eval.rankings import (
    benchmark_key,
    measured_series,
    ordered_scores,
    ranking_content,
)


def record(run, hour, agent="pi", model="m1", counts=(1, 0, 0, 0), endpoint="local", version="1", **point_fields):
    point = {"track": "comparison", "purpose": "evaluation", "suite": {"id": "tasks", "version": "1"},
             "started_at": f"2026-01-01T{hour:02}:00:00Z", "signature": "a" * 64, "run_id": run,
             "repetitions": 1, "timeout_seconds": 60, "inference": {"temperature": None}, "base_url": endpoint,
             **point_fields}
    member = {"agent": {"id": agent, "family": agent.capitalize(), "name": agent, "version": version},
              "model": {"id": model, "name": model, "version": model, "provider": "test"},
              "counts": dict(zip(("pass", "fail", "error", "timeout"), counts))}
    return {"point": point, "member": member, "model": ("test", model), "agent": agent}


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def matching(self, tag, attribute):
        return [attrs for name, attrs in self.tags if name == tag and attribute in attrs]


class RankingTests(unittest.TestCase):
    def test_latest_run_exact_ties_and_ungraded_attempts(self):
        runs = [record("prior", 1, counts=(12, 0, 0, 0)),
                record("latest", 3, counts=(1, 1, 1, 1)),
                record("tied", 2, agent="codex", counts=(2, 1, 4, 1)),
                record("zero", 3, agent="claude", counts=(0, 0, 1, 0)),
                record("unmeasured", 3, agent="unused", counts=(0, 0, 0, 0))]
        series = measured_series(runs[::-1])
        scored = list(ordered_scores(series))
        self.assertEqual([(rank, score.run_id, score.rate) for rank, _, score in scored],
                         [(1, "tied", Fraction(1, 4)), (1, "latest", Fraction(1, 4)), (3, "zero", 0)])
        self.assertEqual(sum(map(len, series.values())), 4)
        html = ranking_content(runs)
        self.assertIn("0.0%", html)
        self.assertNotIn("unused", html)
        self.assertIn("after the first completed run", ranking_content([runs[-1]]))

    def test_benchmark_and_fixed_peer_identity(self):
        base = record("one", 1)
        for change in ({"track": "other"}, {"signature": "b" * 64}, {"inference": None},
                       {"inference": {"temperature": .2}}, {"agent_options_sha256": "other"},
                       {"repetitions": 2}, {"timeout_seconds": 120}):
            with self.subTest(change=change):
                variant = record("two", 2, **change)
                self.assertNotEqual(benchmark_key(base["point"]), benchmark_key(variant["point"]))
                self.assertIn("Benchmark and settings<select>", ranking_content([base, variant]))
        runs = [base, record("two", 2, agent="codex"), record("three", 3, endpoint="alternate"),
                record("four", 4, version="2")]
        variants = measured_series(runs)
        self.assertEqual(len(variants), 4)
        self.assertEqual(sorted(Counter(model for _, model in variants).values()), [1, 3])
        self.assertEqual(sorted(Counter(agent for agent, _ in variants).values()), [1, 1, 2])
        html = ranking_content(runs)
        self.assertIn("Fixed model<select>", html)
        self.assertIn("Fixed agent<select>", html)
        self.assertNotIn("Benchmark and settings<select>", html)

    def test_aliases_are_pooled_within_the_same_run(self):
        first = record("same-run", 1, counts=(2, 0, 0, 0))
        alias = record("same-run", 1, counts=(0, 4, 1, 1))
        alias["member"]["agent"]["id"] = "other-id"
        scores, = measured_series([first, alias]).values()
        self.assertEqual([(s.rate, s.passed, s.attempts, s.url) for s in scores],
                         [(Fraction(1, 4), 2, 8, "run-same-run.html")])

    def test_timeline_time_scale_shared_points_and_escaping(self):
        unsafe = '<img src=x onerror="bad">'
        runs = [record("first", 0), record("middle", 1, counts=(1, 1, 0, 0)),
                record("last", 4, counts=(0, 1, 0, 0)), record("same-time", 1, model=unsafe, counts=(2, 2, 0, 0))]
        html = ranking_content(runs)
        tags = Tags(html)
        paths = tags.matching("polyline", "points")
        self.assertTrue(paths)
        self.assertTrue(all(path["points"] == "0.000000,0.000000 25.000000,50.000000 100.000000,100.000000" for path in paths))
        self.assertIn("&lt;img", html)
        self.assertNotIn("<img", html)
        links = tags.matching("a", "href")
        ids = [attrs["id"] for _, attrs in tags.tags if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        shared = [a for a in links if "shared-point" in a.get("class", "")]
        self.assertTrue(shared)
        for a in shared:
            self.assertIn(a["href"][1:], ids)
            self.assertIn("2 observations", a["aria-label"])
        for run in runs:
            self.assertTrue(any(a["href"].startswith("run-" + run["point"]["run_id"] + ".html#pair-") for a in links))
        self.assertFalse(Tags(ranking_content([runs[0]])).matching("polyline", "points"))
