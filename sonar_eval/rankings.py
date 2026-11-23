"""Compare completed runs under matching benchmark and inference conditions."""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fractions import Fraction

from .common import canonical, fingerprint
from .report_html import agent_time_limit, file_for, h, link, record_path, settings


@dataclass(frozen=True, order=True)
class Agent:
    name: str
    version: str
    reported: tuple
    family: str = field(compare=False)

    def label(self):
        name = self.family if self.family.casefold() == self.name.replace("-", " ").casefold() else f"{self.family} ({self.name})"
        label = f"{name} {self.version}"
        if self.reported:
            label += " (reported " + ", ".join(self.reported) + ")"
        return label


@dataclass(frozen=True, order=True)
class Model:
    name: str
    provider: str
    version: str
    endpoint: str

    def revision(self):
        return self.version if self.version != self.name and not self.name.endswith(":" + self.version) else ""

    def label(self):
        name = self.name + (" @ " + self.revision() if self.revision() else "")
        return " · ".join(filter(None, (name, self.provider, self.endpoint)))


@dataclass(frozen=True)
class Score:
    started: datetime
    run_id: str
    passed: int
    attempts: int
    url: str

    @property
    def rate(self):
        return Fraction(self.passed, self.attempts)


def benchmark_key(point):
    return (point["track"], point["purpose"], point["suite"]["id"], point["suite"]["version"],
            point["signature"], point["repetitions"], point["timeout_seconds"],
            canonical(point.get("inference")), point.get("agent_options_sha256", ""))


def measured_series(records):
    """Combine aliases within a run, then retain every observation in time order."""
    groups = defaultdict(list)
    for record in records:
        agent, model = record["member"]["agent"], record["member"]["model"]
        versions = tuple(sorted(set(agent.get("reported_versions", ()))))
        a = Agent(record["agent"], agent["version"], () if versions == (agent["version"],) else versions, agent["family"])
        m = Model(record["model"][1], record["model"][0], model["version"], record["point"].get("base_url") or "")
        groups[(a, m), record["point"]["run_id"]].append(record)
    series = defaultdict(list)
    for (pair, run_id), members in groups.items():
        counts = [record["member"]["counts"] for record in members]
        attempts = sum(sum(c.values()) for c in counts)
        if attempts:
            point = members[0]["point"]
            date = datetime.fromisoformat(point["started_at"].replace("Z", "+00:00")).astimezone(timezone.utc)
            url = record_path(members[0]) if len(members) == 1 else file_for("run", run_id)
            series[pair].append(Score(date, run_id, sum(c["pass"] for c in counts), attempts, url))
    for observations in series.values():
        observations.sort(key=lambda s: (s.started, s.run_id))
    return series


def pair_label(pair, mode):
    agent, model = pair
    if mode == "agents":
        return agent.family
    if mode == "models":
        return model.name
    return f"{agent.family} × {model.name}"


def ordered_scores(series):
    ordered = sorted(series, key=lambda pair: (-series[pair][-1].rate, pair))
    previous, rank = None, 0
    for index, pair in enumerate(ordered, 1):
        score = series[pair][-1]
        if score.rate != previous:
            rank, previous = index, score.rate
        yield rank, pair, score


def rank_table(series, colors, mode):
    rows = []
    routes = defaultdict(set)
    for _, model in series:
        routes[model.name, model.provider, model.version].add(model.endpoint)
    for rank, pair, score in ordered_scores(series):
        agent, model = pair
        identities = []
        if mode != "models":
            details = [f"{agent.name} {agent.version}"]
            if agent.reported:
                details.append("Reported " + ", ".join(agent.reported))
            identities.append(f'<th class="rank-agent" scope="row">{link(file_for("agent", agent.name), agent.family)}'
                              f'<small>{h(" · ".join(details))}</small></th>')
        if mode != "agents":
            details = [model.provider or "Upstream configuration"]
            if model.revision():
                details.append("Model " + model.version)
            if len(routes[model.name, model.provider, model.version]) > 1:
                details.append(model.endpoint or "Provider default")
            model_link = link(file_for("model", (model.provider, model.name)), model.name)
            value = model_link + f'<small>{h(" · ".join(details))}</small>'
            identities.append(f'<td class="rank-model">{value}</td>' if mode == "pairs"
                              else f'<th class="rank-model" scope="row">{value}</th>')
        pct = float(score.rate) * 100
        rows.append(f'<tr class="series-{colors[pair]}"><td>{rank}</td>'
                    f'{"".join(identities)}<td class="rank-rate"><div class="rate-cell"><span class="rate-track" aria-hidden="true">'
                    f'<span style="width:{pct:.6f}%"></span></span><strong>{pct:.1f}%</strong></div></td>'
                    f'<td class="rank-count">{link(score.url, f"{score.passed} / {score.attempts}")}</td></tr>')
    entities = {"agents": ("Agent",), "models": ("Model",), "pairs": ("Agent", "Model")}[mode]
    headers = "".join(f'<th scope="col">{name}</th>' for name in ("Rank", *entities, "Pass rate", "Passed / total"))
    return f'<table class="rank-table rank-{mode}"><thead><tr>{headers}</tr></thead><tbody>' + "".join(rows) + '</tbody></table>'


def timeline(series, colors, mode, panel_id):
    ordered = sorted(series)
    labels = {pair: pair_label(pair, mode) for pair in ordered}
    duplicates = Counter(labels.values())
    for (agent, model), label in labels.items():
        if duplicates[label] > 1:
            if mode == "agents":
                labels[agent, model] = agent.label()
            elif mode == "models":
                labels[agent, model] = model.label()
            else:
                labels[agent, model] = f"{agent.label()} × {model.label()}"
    dates = [s.started for observations in series.values() for s in observations]
    start, end = min(dates), max(dates)
    span = (end - start).total_seconds()
    locations = defaultdict(list)
    paths, legend, latest = [], [], []
    for pair in ordered:
        entries = series[pair]
        coords = []
        for score in entries:
            x = 100 * (score.started - start).total_seconds() / span if span else 50
            y = 100 * (1 - float(score.rate))
            coords.append(f"{x:.6f},{y:.6f}")
            locations[score.started, score.rate].append((pair, score, x, y))
        if len(coords) > 1:
            paths.append(f'<polyline class="series-{colors[pair]}" points="{" ".join(coords)}"/>')
        latest.append((pair, x, y))
        legend.append(f'<li class="series-{colors[pair]}">{link(entries[-1].url, labels[pair])}</li>')

    dots, observations = [], []
    for index, ((date, rate), matches) in enumerate(sorted(locations.items())):
        pair, score, x, y = matches[0]
        row_id = f"{panel_id}-point-{index}"
        time = date.strftime("%Y-%m-%d %H:%M:%S")
        for offset, (entry, value, _, _) in enumerate(matches):
            marker = f' id="{row_id}"' if offset == 0 else ""
            observations.append(f'<tr{marker}><td>{h(time)}</td><td>{h(labels[entry])}</td>'
                                f'<td>{float(value.rate):.1%} · {value.passed} / {value.attempts}</td>'
                                f'<td>{link(value.url, value.run_id)}</td></tr>')
        if len(matches) == 1:
            color, url, count = f"series-{colors[pair]}", score.url, ""
            tooltip = f"{labels[pair]} · {score.passed} / {score.attempts}"
        else:
            color, url, count = "shared-point", "#" + row_id, str(len(matches))
            tooltip = f"{count} observations at this time and pass rate"
        title = h(f"{tooltip} · {float(rate):.1%} · {time} UTC")
        dots.append(f'<a class="time-point {color}" style="left:{x:.6f}%;top:{y:.6f}%" href="{h(url)}" '
                    f'title="{title}" aria-label="{title}">{count}</a>')

    tags = []
    for pair, x, y in latest:
        # If end labels would collide, the keyed legend still identifies every series.
        if len(latest) > 6 or any(other != pair and abs(y - oy) < 14 and abs(x - ox) < 60 for other, ox, oy in latest):
            continue
        short = pair[0].family if mode != "models" and sum(p[0].family == pair[0].family for p in ordered) == 1 else labels[pair]
        align = "at-right" if x >= 50 else "at-left"
        tags.append(f'<span aria-hidden="true" class="time-tag {align}" style="left:{x:.6f}%;top:{y:.6f}%">{h(short)}</span>')
    guides = "".join(f'<div class="time-guide" style="bottom:{tick}%"><span>{tick}%</span></div>'
                     for tick in (0, 25, 50, 75, 100))
    ticks = [start, end] if span else [start]
    axis = "".join(f'<time datetime="{t.isoformat()}">{t:%Y-%m-%d}<br>{t:%H:%M:%S}</time>' for t in ticks)
    observation_table = ('<details class="rank-observations"><summary>Run observations (' + str(len(observations))
                         + ')</summary><div class="scroll"><table><thead><tr><th scope="col">Run start (UTC)</th>'
                           '<th scope="col">Entry</th><th scope="col">Pass rate · passed / attempted</th>'
                           '<th scope="col">Run evidence</th></tr></thead><tbody>' + "".join(observations) + '</tbody></table></div></details>')
    return ('<div class="timeline" role="group" aria-label="Pass rate by run start time in UTC">'
            '<div class="time-field">' + guides + '<svg viewBox="0 0 100 100" preserveAspectRatio="none" '
            'aria-hidden="true" focusable="false">' + "".join(paths) + '</svg>' + "".join(tags + dots) + '</div>'
            '<div class="time-axis">' + axis + '</div></div><ul class="series-key">' + "".join(legend)
            + '</ul>' + observation_table)


def chooser(label, options):
    return f'<div class="tools rank-tools" hidden><label>{h(label)}<select>{options}</select></label></div>'


def charts(series, colors, mode, panel_id, context=""):
    title = {"agents": "Agent ranking", "models": "Model ranking", "pairs": "Combination ranking"}[mode]
    caption = f'<p class="chart-context">{h(context)}</p>' if context else ""
    if len(series) == 1:
        caption += '<p class="muted">One measured entry in this comparison.</p>'
    return (f'<section><h2>{title}</h2>{caption}' + rank_table(series, colors, mode)
            + '</section><section><h2>Pass rate over time</h2>'
              '<p class="chart-context">Run start in UTC. Each point opens its evidence.</p>'
            + timeline(series, colors, mode, panel_id) + '</section>')


def comparison_views(series, scope_id):
    colors = {pair: i % 8 for i, pair in enumerate(sorted(series))}
    modes = [("pairs", "Combination"), ("agents", "Agent"), ("models", "Model")]
    buttons = "".join(f'<label><input type="radio" name="{scope_id}-mode" value="{mode}"'
                      + (' checked' if mode == "pairs" else '') + f'><span>{title}</span></label>' for mode, title in modes)
    controls = f'<fieldset class="rank-tools rank-modes" hidden><legend>Rank by</legend><div>{buttons}</div></fieldset>'
    panels = ['<div data-rank-option="pairs">' + charts(series, colors, "pairs", scope_id + "-pairs") + '</div>']
    for mode, axis, fixed in (("agents", 1, "model"), ("models", 0, "agent")):
        groups = defaultdict(dict)
        for pair, observations in series.items():
            groups[pair[axis]][pair] = observations
        options, peers = [], []
        for i, (peer, selected) in enumerate(sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))):
            options.append(f'<option value="{i}">{h(peer.label())}</option>')
            content = charts(selected, colors, mode, f"{scope_id}-{mode}-{i}", f"Fixed {fixed} · {peer.label()}")
            peers.append(f'<div data-rank-option="{i}">{content}</div>')
        choose_peer = chooser("Fixed " + fixed, "".join(options)) if len(groups) > 1 else ""
        panels.append(f'<div data-rank-option="{mode}" data-rank-switch>{choose_peer}{"".join(peers)}</div>')
    return '<div data-rank-switch>' + controls + "".join(panels) + '</div>'


def ranking_content(records):
    grouped = defaultdict(list)
    for record in records:
        grouped[benchmark_key(record["point"])].append(record)
    scopes = []
    for key, members in grouped.items():
        series = measured_series(members)
        if series:
            newest = max(scores[-1].started for scores in series.values())
            scopes.append((newest, key, members[0], series))
    if not scopes:
        return '<section><h2>Measured combinations</h2><p class="empty">Rankings will appear after the first completed run.</p></section>'
    options, panels = [], []
    for i, (_, key, record, series) in enumerate(sorted(scopes, key=lambda s: (s[0], s[1]), reverse=True)):
        point = record["point"]
        suite_id = point["suite"]["id"]
        title = "All tasks" if suite_id == "all-tasks" else suite_id
        suite = f'{title} · Version {point["suite"]["version"]}'
        inference = settings(point)
        identity = fingerprint(key)[:10]
        label = f'{suite} · {point["track"]} · {inference} · Agent limit {agent_time_limit(record)} · {identity}'
        options.append(f'<option value="{i}">{h(label)}</option>')
        fields = [("Task collection ID", suite_id), ("Experiment track", point["track"]),
                  ("Attempts per task", point["repetitions"]), ("Agent execution limit", agent_time_limit(record)),
                  ("Whole trial limit", f'{point["timeout_seconds"]:g} s'), ("Inference settings", inference),
                  ("Agent options", point.get("agent_options_sha256") or "Client defaults"),
                  ("Benchmark fingerprint", point["signature"])]
        context = "".join(f'<div><dt>{h(name)}</dt><dd>{h(value)}</dd></div>' for name, value in fields)
        count = record.get("task_count")
        coverage = (f' · {count} ' + ("task" if count == 1 else "tasks")) if count else ""
        panels.append(f'<div data-rank-option="{i}"><p class="collection-label">Task collection <strong>{h(title)}</strong>'
                      f' · Version {h(point["suite"]["version"])}{coverage}</p><details class="rank-context">'
                      f'<summary>View comparison settings</summary><dl>{context}</dl></details>'
                      + comparison_views(series, f"scope-{i}") + '</div>')
    controls = chooser("Benchmark and settings", "".join(options)) if len(scopes) > 1 else ""
    return '<div data-rank-switch>' + controls + "".join(panels) + '</div>'
