"""Shared formatting and local evidence links for the static report."""
from html import escape

from .common import fingerprint


def h(value):
    return escape(str(value), quote=True)


def link(url, label):
    return f'<a href="{h(url)}">{h(label)}</a>'


def file_for(kind, key):
    if isinstance(key, str) and key.isascii() and key and all(c.isalnum() or c in "._-" for c in key):
        return f"{kind}-{key}.html"
    return f"{kind}-{fingerprint(key)}.html"


def anchor(member):
    return "pair-" + fingerprint([member["model"]["id"], member["agent"]["id"]])[:20]


def record_path(record):
    return file_for("run", record["point"]["run_id"]) + "#" + anchor(record["member"])


def settings(point):
    values = point.get("inference")
    if values is None:
        return "Not recorded"
    return " · ".join(f"{field}={value}" for field, value in values.items() if value is not None) or "Client defaults"


def agent_time_limit(record):
    explicit = record["point"].get("agent_timeout_seconds")
    if explicit is not None:
        return f"{explicit:g} s"
    limits = record.get("agent_limits") or []
    if len(limits) == 1:
        return f"{limits[0]:g} s (task setting)"
    if limits:
        return f"{limits[0]:g}–{limits[-1]:g} s (varies by task or step)"
    return "Defined in the frozen task manifests"
