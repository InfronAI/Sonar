import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "configs" / "ollama.json"
DEFAULT_STATE = ROOT / ".sonar"
STATUSES = ("pass", "fail", "error", "timeout")


class EvalError(ValueError):
    pass


class LockBusy(EvalError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path):
    with Path(path).open(encoding="utf-8") as source:
        return json.load(source, parse_constant=reject_constant)


def reject_constant(value):
    raise EvalError(f"Invalid JSON number: {value}")


def atomic_text(path, data):
    path = Path(path)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".writing-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def write_json(path, value):
    atomic_text(path, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


@contextmanager
def lock(path, *, wait=False):
    """Process-owned file lock. The OS releases it if the worker dies."""
    connection = sqlite3.connect(path, timeout=60 if wait else 0)
    try:
        try:
            connection.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            raise LockBusy(f"Another process holds {path}") from exc
        yield
    finally:
        connection.close()
