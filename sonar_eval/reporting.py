"""Generate linked local HTML pages from the public catalog and committed results."""
from collections import defaultdict
from pathlib import Path
from shlex import join as shell_join
from string import Template

from .catalog import experiments
from .common import ROOT, STATUSES, atomic_text, fingerprint, lock
from .history import delta, points, report_evidence, series_key
from .measurements import PHASES, USAGE, aligned_outcomes, repeatability, summarize_measurements
from .native import agent_presets
from .rankings import ranking_content
from .report_html import (
    agent_time_limit,
    anchor,
    file_for,
    h,
    link,
    record_path,
    settings,
)

ASSETS = ROOT / "sonar_eval/report"
NAV = {"home": ("Overview", "report.html"), "experiments": ("Experiment catalog", "experiments.html"),
       "rankings": ("Rankings", "rankings.html"),
       "agents": ("Agents", "agents.html"), "models": ("Models", "models.html"),
       "runs": ("Run history", "runs.html")}
STATUS_LABELS = dict(zip(STATUSES, ("Passed", "Failed", "Error", "Timeout")))


def note(value):
    return f'<small class="cell-note">{h(value)}</small>'


def section(title, body, attrs=""):
    return f'<section{attrs}><h2>{h(title)}</h2>{body}</section>'


def empty(message="No completed runs yet."):
    return f'<p class="empty">{h(message)}</p>'


def metrics(items):
    return '<div class="metrics">' + "".join(
        f'<div class="metric"><span>{h(label)}</span><strong>{h(value)}</strong></div>'
        for label, value in items) + '</div>'


def row(cells, *, element_id=None, **attributes):
    attrs = f' id="{h(element_id)}"' if element_id else ""
    attrs += "".join(f' data-{key}="{h(value)}"' for key, value in attributes.items())
    return '<tr' + attrs + '>' + "".join(f'<td>{cell}</td>' for cell in cells) + '</tr>'


def table(headers, rows):
    return ('<div class="scroll"><table><thead><tr>' + "".join(f'<th scope="col">{h(x)}</th>' for x in headers)
            + '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>')


def task_definition(case):
    rubric = case.get("rubric")
    if rubric:
        criteria = [row([h(c["id"]), h(f'{c["weight"]}%'), h(c["full"]), h(c["partial"])])
                    for c in rubric["criteria"]]
        verification = (
            f'<p>Infron <code>{h(rubric["model"])}</code> grades the submitted document in a separate '
            f'Harbor verifier. The passing reward is {h(case["pass_threshold"])} or higher.</p>'
            '<p>Each criterion earns 2 for full credit, 1 for partial credit, or 0 for missing, '
            'contradicted or unsupported work. Reward is the weighted sum of the levels divided by 2, '
            'with weights expressed as fractions. The judge records a justification for each level.</p>'
            + table(["Criterion", "Weight", "Full credit (2)", "Partial credit (1)"], criteria))
    else:
        count = case.get("fixture_count")
        verification = (f'<p>The verifier checks the submitted work against {h(count)} test cases. '
                        'Passing every check earns 1. A failed check earns 0.</p>' if count is not None else
                        '<p>Harbor runs the task verifier and reads its reward.</p>')
    if case.get("verifier_script"):
        verification += ('<details><summary>Verifier script · tests/test.sh</summary>'
                         f'<pre class="source"><code>{h(case["verifier_script"])}</code></pre></details>')
    for path, script in case.get("step_verifiers", []):
        verification += (f'<details><summary>{h(path)}</summary>'
                         f'<pre class="source"><code>{h(script)}</code></pre></details>')
    command = shell_join(["./sonar", "run", "--suite", case["path"]])
    instructions = "".join('<details><summary>' + h(name) + '</summary><pre class="task-prompt">'
                           + h(text.rstrip()) + '</pre></details>' for name, text in case.get("step_instructions", []))
    return (f'<article class="task-definition" id="task-{h(case["id"])}"><h3>{h(case["title"])}</h3>'
            '<h4>Agent instruction and required submission</h4>'
            f'<pre class="task-prompt">{h(case["instruction"].rstrip())}</pre>{instructions}<h4>Verification</h4>{verification}'
            '<details><summary>Run this task</summary>'
            f'<code class="command">{h(command)}</code></details></article>')


def searchable(title, headers, rows, filters=(), hint="Run ID, agent, or model", no_data="No completed runs yet."):
    if not rows:
        return section(title, empty(no_data))
    controls = f'<label>Search<input type="search" placeholder="{h(hint)}"></label>'
    for key, label, options in filters:
        choices = "".join(f'<option value="{h(value)}">{h(name)}</option>' for value, name in options)
        controls += f'<label>{h(label)}<select name="{key}"><option value="">All</option>{choices}</select></label>'
    tools = '<div class="tools" hidden>' + controls + '</div>'
    pager = ('<div class="pager" hidden><button type="button" data-prev>Previous</button><output aria-live="polite"></output>'
             '<button type="button" data-next>Next</button></div>')
    return section(title, tools + table(headers, rows) + pager, ' data-list')


def model_key(model):
    return model.get("provider", ""), model.get("name") or model["id"]


def trial_anchor(trial):
    return "trial-" + fingerprint([trial["agent"], trial["model"], trial["case"], trial["attempt"]])[:20]


def totals(observations):
    counts = {k: sum(o["member"]["counts"][k] for o in observations) for k in STATUSES}
    return len({o["point"]["run_id"] for o in observations}), counts


def rate(counts):
    total = sum(counts.values())
    return f"{counts['pass'] / total:.1%}" if total else "—"


def result_metrics(observations):
    runs, counts = totals(observations)
    return metrics([("Completed runs", runs), ("Task attempts", sum(counts.values())),
                    ("Pass rate", rate(counts)), ("Errors / timeouts", f"{counts['error']} / {counts['timeout']}")])


def measurement_tables(trials, k):
    measured = summarize_measurements(trials)
    rows = []
    for key, label in (USAGE | PHASES).items():
        metric = h(label + (" (s)" if key in PHASES else ""))
        stats = measured.get(key)
        if stats is None:
            rows.append(row([metric, "—", "—", f"0 / {len(trials)}"]))
            continue
        fmt = ".6f" if key == "cost_usd" else ",.2f"
        rows.append(row([metric, format(stats["median"], fmt),
                         format(stats["sum"], fmt), f'{stats["observed"]} / {len(trials)}']))
    body = table(["Measurement", "Median per attempt", "Observed total", "Coverage"], rows)
    repairs = []
    for trial in trials:
        steps = {name: reward for name, reward, error in trial.get("steps", []) if not error and reward in (0, 1)}
        if trial["status"] in {"pass", "fail"} and steps.keys() >= {"draft", "repair"}:
            repairs.append(steps)
    if repairs:
        missed = [s for s in repairs if s["draft"] == 0]
        recovered = sum(s["repair"] == 1 for s in missed)
        body += table(["Self-repair", "Attempts"], [
            row(["Passed on first submission", f'{len(repairs) - len(missed)} / {len(repairs)}']),
            row(["Recovered after a failed first submission", f'{recovered} / {len(missed)}' if missed else "No failed first submissions"])])
    if k > 1:
        r = repeatability(trials, k)
        body += table(["Reliability", "Numerator / denominator"], [
            row(["Passed / graded attempts", f'{r["passed"]} / {r["graded"]}']),
            row([f"Tasks with {k} graded attempts", f'{r["complete"]} / {r["tasks"]}']),
            row([f"Passed at least once (pass@{k})", f'{r["any"]} / {r["complete"]}']),
            row([f"Passed every time (pass^{k})", f'{r["all"]} / {r["complete"]}']),
            row(["Tasks with mixed results", f'{r["mixed"]} / {r["complete"]}'])])
    return body


class Report:
    def __init__(self, history, evidence, catalog):
        self.history, self.evidence = history, evidence
        self.datasets, self.matrices = catalog
        self.agents = agent_presets()
        self.models, self.combinations = {}, defaultdict(list)
        self.records, self.by_run, self.by_pair = [], defaultdict(list), defaultdict(list)
        self.task_names = {c["task_sha256"]: (dataset, c["id"]) for dataset, spec in self.datasets.items() for c in spec["cases"]}
        self.by_dataset = defaultdict(list)
        for matrix in self.matrices:
            for agent, model in matrix["pairs"]:
                pair = self.index_pair(agent, model)
                self.combinations[pair].append(matrix)
        trials = defaultdict(list)
        for run_id, bundle in evidence.items():
            for trial in bundle["trials"]:
                trials[run_id, trial["model"], trial["agent"]].append(trial)
        for point in reversed(history):
            run_id = point["run_id"]
            bundle = evidence.get(run_id, {})
            task_hashes = bundle.get("tasks", {})
            for member in point["members"]:
                agent, model = self.index_pair(member["agent"], member["model"])
                self.combinations.setdefault((agent, model), [])
                attempts = trials[run_id, member["model"]["id"], member["agent"]["id"]]
                record = {"point": point, "member": member, "agent": agent, "model": model, "trials": attempts,
                          "task_count": len(task_hashes), "agent_limits": bundle.get("agent_limits", [])}
                self.records.append(record)
                self.by_run[run_id].append(record)
                self.by_pair[agent, model].append(record)
                for trial in attempts:
                    current = self.task_names.get(task_hashes.get(trial["case"]))
                    if current:
                        self.by_dataset[current[0]].append((record, trial, current[1]))
        self.template = Template((ASSETS / "template.html").read_text(encoding="utf-8"))
        self.pages = {}

    def index_pair(self, agent, model):
        name = agent.get("name") or agent["id"]
        key = model_key(model)
        self.agents.setdefault(name, agent)
        self.models.setdefault(key, model)
        return name, key

    def page(self, file, tab, title, body, subtitle="", parent=None):
        root = tab == "home"
        assets, home = ("report/", "report.html") if root else ("", "../report.html")
        nav = ""
        for name, (label, dest) in NAV.items():
            path = home if name == "home" else assets + dest
            active = ' aria-current="page"' if tab == name else ""
            nav += f'<a href="{path}"{active}>{label}</a>'
        crumb = f'<a class="crumb" href="{parent[1]}">‹ {h(parent[0])}</a>' if parent else ""
        self.pages["report.html" if root else "report/" + file] = self.template.substitute(
            assets=assets, home=home, nav=nav, title=h(title), crumb=crumb, content=body,
            subtitle=f'<p class="sub">{h(subtitle)}</p>' if subtitle else "")

    def agent_link(self, key):
        return link(file_for("agent", key), self.agents[key]["family"])

    def model_link(self, key):
        return link(file_for("model", key), key[1]) + note(key[0] or "Upstream configuration")

    def pair_link(self, pair):
        return link(file_for("pair", pair), "View combination")

    def record_link(self, record, label):
        return link(record_path(record), label)

    def records_table(self, records, title="Run history"):
        rows = []
        facets = {"suite": set(), "provider": set(), "agent": set(), "model": set()}
        for record in records:
            p, m = record["point"], record["member"]
            count = m["counts"]
            suite = p["suite"]["id"]
            provider = record["model"][0]
            selection = {"suite": suite, "provider": provider, "agent": p["agent_family"], "model": p["model_family"]}
            for key, value in selection.items():
                if value:
                    facets[key].add(value)
            timestamp = p["started_at"][:19].replace("T", " ")
            rows.append(row([self.record_link(record, timestamp) + note(p["run_id"]),
                             self.agent_link(record["agent"]) + note(m["agent"]["version"]),
                             self.model_link(record["model"]), h(suite), f'{count["pass"]} / {sum(count.values())}',
                             f'{count["error"]} / {count["timeout"]}', self.record_link(record, "Trial results")],
                            **selection))
        labels = {"suite": "Suite", "provider": "Provider", "agent": "Agent family", "model": "Model family"}
        filters = [(key, labels[key], [(x, x) for x in sorted(vals)]) for key, vals in facets.items()]
        return searchable(title, ["Time (UTC)", "Agent", "Model", "Suite", "Passed / attempted", "Errors / timeouts", "Details"], rows, filters)

    def pair_rows(self, pairs):
        rows = []
        for agent, model in sorted(pairs):
            records = self.by_pair[agent, model]
            runs, counts = totals(records)
            rows.append(row([self.agent_link(agent), self.model_link(model), str(runs),
                             f'{counts["pass"]} / {sum(counts.values())}', rate(counts), self.pair_link((agent, model))]))
        return table(["Agent", "Model / provider", "Runs", "Passed / attempted", "Pass rate", "Details"], rows)

    def browse(self, kind):
        is_agent = kind == "agents"
        entries = self.agents if is_agent else self.models
        singular = "agent" if is_agent else "model"
        cards = []
        for key, item in sorted(entries.items()):
            title = item["family"] if is_agent else key[1]
            desc = ("CLI " + (item["version"] or "version unavailable")) if is_agent else (key[0] + " · " + item["family"])
            pairs = [p for p in self.combinations if p[0 if is_agent else 1] == key]
            records = [r for r in self.records if r[singular] == key]
            runs, _ = totals(records)
            target = file_for(singular, key)
            cards.append(f'<article class="card"><h2>{link(target, title)}</h2><small>{h(desc)}</small>'
                         f'<small>{len(pairs)} combinations · {runs} completed runs</small></article>')
            body = result_metrics(records) + section("Model combinations" if is_agent else "Agent combinations", self.pair_rows(pairs))
            self.page(target, kind, title, body + self.records_table(records), desc, NAV[kind])
        self.page(NAV[kind][1], kind, NAV[kind][0],
                  '<div class="cards">' + "".join(cards) + '</div>',
                  "Choose an agent to inspect its models and runs." if is_agent else "Choose a model to inspect its agents and runs.")

    def pair_pages(self):
        for (agent, model), matrices in self.combinations.items():
            records = self.by_pair[agent, model]
            links = '<div class="links">' + self.agent_link(agent) + " " + link(file_for("model", model), model[1]) + '</div>'
            body = result_metrics(records)
            if matrices:
                commands = []
                for matrix in matrices:
                    attempts = len(matrix["pairs"]) * matrix["tasks"] * matrix["repetitions"]
                    commands.append(f'<p>{h(matrix["name"])} · {attempts} scheduled attempts</p>'
                                    f'<code class="command">{h(matrix["command"])}</code>')
                body += section("Run configuration", "".join(commands))
            body += self.records_table(records)
            self.page(file_for("pair", (agent, model)), "runs", self.agents[agent]["family"] + " × " + model[1],
                      links + body, model[0], NAV["runs"])

    def evaluation_guide(self):
        examples, files = defaultdict(list), []
        for matrix in self.matrices:
            commands = h(matrix["check"])
            if not matrix.get("unavailable"):
                commands += "\n" + h(matrix["command"])
            commands = f'<pre class="command"><code>{commands}</code></pre>'
            if matrix.get("unavailable"):
                description = '<p class="muted">Configuration unavailable. Check the selection with doctor.</p>'
            else:
                count = len(matrix["pairs"]) * matrix["tasks"] * matrix["repetitions"]
                description = f'<p class="muted">{h(matrix["suite"])} · {count} attempts per run</p>'
            if "scenario" in matrix:
                if matrix["pairs"]:
                    agent, model = matrix["pairs"][0]
                    identity = link(file_for("pair", (agent["name"], model_key(model))), agent["family"] + " × " + model["name"])
                    identity += note(model.get("provider") or "Upstream configuration")
                else:
                    identity = h(matrix["name"])
                examples[matrix["scenario"]].append(f'<div class="example-choice">{identity}{description}'
                                                     f'<details><summary>Show commands</summary>{commands}</details></div>')
            else:
                files.append(f'<div class="saved-matrix"><h3><code>{h(matrix["path"])}</code></h3>{description}{commands}</div>')
        cards = "".join(f'<article><h3>{h(title)}</h3>{"".join(items)}</article>' for title, items in examples.items())
        saved = ('<details class="guide-part"><summary>Saved project matrices (' + str(len(files))
                 + ')</summary>' + "".join(files) + '</details>') if files else ""
        guide = Template((ASSETS / "evaluation-guide.html").read_text(encoding="utf-8")).substitute(
            matrix=h((ASSETS / "example-matrix.json").read_text(encoding="utf-8").strip()), files=saved)
        return (section("Example evaluations", '<div class="example-grid">' + cards + '</div>', ' id="examples"')
                + section("Customize an evaluation", guide, ' id="custom-evaluation"'))

    def catalog_pages(self):
        rows = []
        domains = sorted({spec["domain"] for spec in self.datasets.values()})
        for dataset, spec in self.datasets.items():
            found = self.by_dataset[dataset]
            target = file_for("dataset", dataset)
            rows.append(row([link(target, dataset), h(spec["domain"]), "<br>".join(h(c["title"]) for c in spec["cases"]),
                             str(len(found))], domain=spec["domain"]))
            case_rows = []
            for c in spec["cases"]:
                trials = [trial for _, trial, case_id in found if case_id == c["id"]]
                method = "Rubric · Infron" if c.get("judge") else "Programmatic verifier"
                case_rows.append(row([link("#task-" + c["id"], c["title"]) + note(c["id"]), h(method),
                                      str(len(trials)), str(sum(t["status"] == "pass" for t in trials))]))
            body = section("Tasks", table(["Task", "Verification", "Attempts", "Passed"], case_rows))
            body += section("Run this suite", '<code class="command">' + h(shell_join(["./sonar", "run", "--suite", spec["path"]])) + '</code>')
            body += section("Task instructions and verification", "".join(task_definition(c) for c in spec["cases"]))
            body += self.trial_table([(r, t) for r, t, _ in found], "Results for these task revisions", include_run=True)
            self.page(target, "experiments", dataset, body, spec["path"], NAV["experiments"])
        suites = searchable("Available suites", ["Suite", "Domain", "Tasks", "Recorded attempts"], rows,
                             [("domain", "Domain", [(d, d) for d in domains])], "Suite, domain, or task")
        jumps = '<div class="links catalog-jumps" role="navigation" aria-label="Catalog sections">' + " ".join(
            link("#" + target, name) for target, name in (("examples", "Examples"), ("custom-evaluation", "Custom setup"),
                                                         ("suites", "Available suites"))) + '</div>'
        content = jumps + self.evaluation_guide() + '<div id="suites">' + suites + '</div>'
        self.page("experiments.html", "experiments", "Experiment catalog", content)

    def trial_table(self, items, title="Trial results", include_run=False):
        rows = []
        facets = defaultdict(dict)
        for record, trial in items:
            state = trial["status"]
            run_id = record["point"]["run_id"]
            agent_key, model_key = record["agent"], record["model"]
            agent_name = self.agents[agent_key]["family"]
            provider, model = model_key
            values = {"task": trial["case"], "attempt": str(trial["attempt"]), "status": state}
            if include_run:
                values.update(agent=agent_key, model=model, provider=provider or "Upstream configuration", run=run_id)
            for key, value in values.items():
                facets[key][value] = agent_name if key == "agent" else value
            trial_id = trial_anchor(trial)
            links = [link("../" + trial[k], label) for k, label in (("result", "result.json"), ("harbor", "Harbor result"))
                     if trial.get(k)]
            for key, label in (("assessment", "Rubric assessment"), ("submission", "Submitted document"),
                               ("verifier_log", "Verifier output")):
                if trial.get(key):
                    links.append(link("../" + trial[key], label))
            log = trial.get("trial_log") or trial.get("launcher_log")
            if log:
                links.append(link("../" + log, "Harbor log" if trial.get("trial_log") else "Launcher log"))
            links.extend(link("../" + url, label) for label, url in trial.get("definition", []))
            traces = [link("../" + trial["trajectory"], "Trajectory JSON")] if trial.get("trajectory") else []
            traces.extend(link("../" + url, name) for name, url in trial.get("transcripts", []))
            links.extend(link("../" + url, label) for label, url in trial.get("step_evidence", []))
            runtime = h(trial.get("cli_version") or "—")
            if trial.get("docker_image_id"):
                runtime += note(trial["docker_image_id"])
            cells = [h(trial["case"]) + note("Attempt " + str(trial["attempt"])),
                     f'<span class="badge {h(state)}">{h(STATUS_LABELS.get(state, state))}</span>' + note(trial.get("reason") or ""),
                     h(trial["reward"] if trial["reward"] is not None else "—"),
                     (h(f'{trial["elapsed_seconds"]:.2f} s') if trial["elapsed_seconds"] is not None else "—") +
                     "".join(note(f'{label} · {value:g}' + (" s" if key in PHASES else "")) for key, label in (USAGE | PHASES).items()
                             if (value := trial.get("measurements", {}).get(key)) is not None),
                     runtime, '<div class="links">' + "".join(traces) + '</div>' if traces else note("No agent trace recorded"),
                     '<div class="links">' + "".join(links) + '</div>']
            for step, reward, error in trial.get("steps", []):
                cells[2] += note(f"{step} · " + ("error" if error else str(reward) if reward is not None else "ungraded"))
            if include_run:
                target = file_for("run", run_id) + "#" + trial_id
                cells[0] = link(target, trial["case"]) + note("Attempt " + str(trial["attempt"]))
                cells[:0] = [self.record_link(record, run_id), self.agent_link(agent_key), self.model_link(model_key)]
            rows.append(row(cells, element_id=None if include_run else trial_id, **values))
        headers = (["Run", "Agent", "Model / provider"] if include_run else []) + [
            "Task / attempt", "Status", "Reward", "Duration", "Runtime", "Trajectory", "Evidence"]
        filters = [("status", "Outcome", STATUS_LABELS.items())]
        for key, label in (("task", "Task"), ("agent", "Agent"), ("model", "Model"), ("provider", "Provider"),
                           ("run", "Run"), ("attempt", "Attempt")):
            if facets[key] and (key != "attempt" or len(facets[key]) > 1):
                filters.append((key, label, sorted(facets[key].items(), key=lambda item: item[1].casefold())))
        return searchable(title, headers, rows, filters, "Task, run, model, or outcome",
                          "No trial results yet.")

    def run_pages(self):
        for run_id, records in self.by_run.items():
            p = records[0]["point"]
            bundle = self.evidence.get(run_id, {})
            body = result_metrics(records)
            if bundle.get("plan"):
                files = [link("../" + bundle["plan"], "Open plan.json")]
                if bundle.get("handbook"):
                    files.append(link("../" + bundle["handbook"], "Open the operating guide"))
                body += section("Frozen run plan", " · ".join(files))
            if comparison := bundle.get("retest"):
                comparison_rows = []
                for label, phase in (("Previous run", comparison["previous"]), ("Retest", comparison["current"])):
                    comparison_rows.append(row([h(label), h(phase["run_id"]), h(f'{phase["agent_timeout_seconds"]:g} s'),
                                                *(h(phase["counts"][status]) for status in STATUSES)]))
                summary = table(["Execution", "Run ID", "Agent limit", *STATUS_LABELS.values()], comparison_rows)
                timeout_rows = []
                for trial in comparison.get("tasks", []):
                    before, after = trial["previous"], trial["current"]
                    if before["status"] != after["status"] or "timeout" in (before["status"], after["status"]):
                        times = [f'{phase["agent_seconds"]:.1f} s' if phase.get("agent_seconds") is not None else "—"
                                 for phase in (before, after)]
                        timeout_rows.append(row([link("#" + trial_anchor(trial), trial["case"]),
                                                 h(STATUS_LABELS[before["status"]]), h(times[0]),
                                                 h(STATUS_LABELS[after["status"]]), h(times[1])]))
                if timeout_rows:
                    summary += '<h3>Changed outcomes and timeouts</h3>' + table(
                        ["Task", "Previous outcome", "Previous agent time", "Retest outcome", "Retest agent time"], timeout_rows)
                summary += link("../" + bundle["retest_url"], "Compare task outcomes and elapsed time")
                body += section("Retest comparison", summary)
            for record in records:
                m, point = record["member"], record["point"]
                agent, model = m["agent"], m["model"]
                c = m["counts"]
                protocols = sorted({t["api_format"] for t in record["trials"] if t.get("api_format")})
                data = [
                    ("Agent", self.agent_link(record["agent"]) + note(agent["id"] + " · " + agent["version"])),
                    ("Model", self.model_link(record["model"]) + note(model["id"] + " · " + model["version"])),
                    ("Configured provider", h(point["provider"] or "Upstream configuration")),
                    ("Provider endpoint", h(point["base_url"] or "Provider default")),
                    ("Requested inference settings", h(settings(point))), ("Concurrent trial limit", str(point.get("workers", 1))),
                    ("Concurrent trials per endpoint", str(point.get("endpoint_workers", 1))),
                    ("Concurrent rubric trials", str(point.get("judge_workers", 1))),
                    ("Operating guide SHA-256", h(point.get("handbook_sha256") or "None")), ("Agent execution limit", h(agent_time_limit(record))),
                    ("Whole trial limit", f'{h(point["timeout_seconds"])} s'), ("Attempts per task", h(point["repetitions"])),
                    ("Passed / attempted", f'{c["pass"]} / {sum(c.values())}'), ("Mean reward", "—" if not c["pass"]+c["fail"] else
                     f'{m["reward_sum"] / (c["pass"]+c["fail"]):.3f}'),
                    ("Comparison fingerprint", f'<code>{h(point["signature"])}</code>')]
                if protocols:
                    data.insert(4, ("Harbor API protocol", h(", ".join(protocols))))
                if "environment_sha256" in point:
                    data.append(("Image fingerprint", f'<code>{h(point["environment_sha256"])}</code>'))
                detail = table(["Setting", "Recorded value"], [row([h(k), val]) for k, val in data])
                detail += measurement_tables(record["trials"], point["repetitions"])
                prior = point.get("previous_run")
                if prior:
                    old = self.evidence.get(prior, {})
                    old_trials = [t for t in old.get("trials", []) if t["model"] == model["id"] and t["agent"] == agent["id"]]
                    changes, counts = aligned_outcomes(old_trials, record["trials"], old.get("tasks", {}), bundle.get("tasks", {}))
                    detail += '<h3>Task outcomes since ' + link(file_for("run", prior), prior) + '</h3>'
                    detail += table(["Previous", "Current", "Attempts"], [
                        row([h(x["before"]), h(x["after"]), str(x["count"])]) for x in counts])
                    changed = [row([link("#" + trial_anchor({**x, "model": model["id"], "agent": agent["id"]}), x["case"]),
                                    str(x["attempt"]), h(x["before"]), h(x["after"])])
                               for x in changes if x["same_revision"] and x["before"] != x["after"] and x["after"]]
                    if changed:
                        detail += table(["Changed task", "Attempt", "Previous", "Current"], changed)
                label = agent["family"] + " × " + record["model"][1]
                body += section(label, detail, f' id="{anchor(m)}"')
                body += self.trial_table([(record, trial) for trial in record["trials"]], "Trial results · " + label)
            self.page(file_for("run", run_id), "runs", run_id, body,
                      f'{p["started_at"]} · {p["track"]} · {p["suite"]["id"]}@{p["suite"]["version"]}', NAV["runs"])
        self.page("runs.html", "runs", "Run history", result_metrics(self.records) + self.records_table(self.records, "Results by run and combination"))

    def trend(self):
        if not self.history:
            return section("Family pass-rate history", empty("Family pass rates will appear after the first completed run."))
        series = defaultdict(list)
        for point in self.history:
            series[series_key(point, across_images=True)].append(point)
        options, charts = [], []
        for index, observations in enumerate(sorted(series.values(), key=lambda group: group[-1]["started_at"], reverse=True)):
            last = observations[-1]
            name = f'{last["agent_family"]} × {last["model_family"]} · {last["provider"]} · {last["suite"]["id"]}'
            options.append(f'<option value="{index}">{h(name)} · {h(settings(last))} · {fingerprint(series_key(last, across_images=True))[:8]}</option>')
            coords = [(35 + i * 590 / max(1, len(observations) - 1), 99 - 88 * p["pass_rate"])
                      for i, p in enumerate(observations)]
            segments = []
            for i, (x, y) in enumerate(coords):
                same_images = i > 0 and observations[i - 1]["signature"] == observations[i]["signature"]
                segments.append(f"{'L' if same_images else 'M'} {x:.2f} {y:.2f}")
            line = " ".join(segments)
            markers = []
            for (x, y), p in zip(coords, observations):
                path = "report/" + file_for("run", p["run_id"]) + "#" + anchor(p["members"][0])
                label = h(p["started_at"] + " · " + f'{p["pass_rate"]:.1%}')
                markers.append(f'<a href="{path}" aria-label="{label}"><title>{label}</title>'
                               f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5"/></a>')
            chart = (f'<svg class="chart" viewBox="0 0 660 112" aria-label="{h(name)}">'
                     '<line x1="34" y1="11" x2="634" y2="11"/><line x1="34" y1="99" x2="634" y2="99"/>'
                     '<text x="0" y="14" font-size="9">100%</text><text x="8" y="102" font-size="9">0%</text>'
                     f'<path d="{line}"/>{"".join(markers)}</svg>')
            latest = link("report/" + file_for("run", last["run_id"]), "Latest run")
            charts.append(f'<div data-trend="{index}"><h3>{h(name)}</h3>{chart}<p>{latest} · {len(observations)} runs · '
                          f'Passed {last["counts"]["pass"]}/{last["total"]} · Change {h(delta(last))}</p></div>')
        picker = '<div class="tools" data-trend-picker hidden><label>Comparable series<select>' + "".join(options) + '</select></label></div>'
        return section("Family pass-rate history", picker + "".join(charts))

    def generate(self):
        self.catalog_pages()
        self.browse("agents")
        self.browse("models")
        self.pair_pages()
        self.run_pages()
        self.page("rankings.html", "rankings", "Rankings", ranking_content(self.records),
                  "Pass rate counts all attempts in each combination’s latest completed run, including errors and timeouts. Equal rates share a rank.")
        cards = []
        detail = {"experiments": f'{len(self.datasets)} suites · {len(self.task_names)} tasks',
                  "rankings": f'{sum(bool(r) for r in self.by_pair.values())} measured combinations',
                  "agents": f'{len(self.agents)} agents', "models": f'{len(self.models)} models',
                  "runs": f'{len(self.by_run)} completed runs'}
        for tab, count in detail.items():
            label, path = NAV[tab]
            cards.append(f'<article class="card"><h2>{link("report/"+path, label)}</h2><small>{h(count)}</small></article>')
        body = result_metrics(self.records) + '<div class="cards">' + "".join(cards) + '</div>' + self.trend()
        self.page("report.html", "home", "Evaluation overview", body)
        return self.pages


def write_report(state):
    state = Path(state)
    state.mkdir(parents=True, exist_ok=True)
    with lock(state / ".report.lock", wait=True):
        history = points(state, member_metrics=True)
        report = Report(history, report_evidence(state, history), experiments())
        directory = state / "report"
        directory.mkdir(exist_ok=True)
        pages = report.generate()
        runs = state / "runs"
        for alias in runs.iterdir() if runs.is_dir() else ():
            if alias.is_symlink():
                target = alias.resolve()
                canonical = "report/" + file_for("run", target.name)
                if target.parent == runs.resolve() and canonical in pages:
                    pages["report/" + file_for("run", alias.name)] = pages[canonical]
        for name in ("report.js", "style.css", "example-matrix.json"):
            atomic_text(directory / name, (ASSETS / name).read_text(encoding="utf-8"))
        for path, html in pages.items():
            atomic_text(state / path, html)
        for kind in ("agent", "model", "dataset", "pair", "run"):
            for file in directory.glob(kind + "-*.html"):
                if "report/" + file.name not in pages and not file.is_symlink():
                    with file.open("rb") as source:
                        generated = b"<!-- Generated by Sonar. -->" in source.read(100)
                    if generated:
                        file.unlink()
    return history
