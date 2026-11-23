"""Resolve model endpoints and construct Harbor's per-trial authentication options."""
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from .common import DEFAULT_STATE, ROOT, EvalError, atomic_text

INFRON = "https://llm.onerouter.pro/v1"
JUDGE_MODEL = "infron/op-5.5"
JUDGE_IMAGE = "sonar-eval/rubric-judge:1"
JUDGE_CONTEXT = ROOT / "docker/rubric-judge"
INFRON_KEY_FILE = DEFAULT_STATE / "credentials" / "infron-api-key"
FORMATS = {"codex": "openai_responses", "claude-code": "anthropic_messages"}
HOST_DEFAULTS = {"codex": "openai", "claude-code": "anthropic", "copilot-cli": "github-copilot"}
KEY_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def harbor_executable():
    override = os.environ.get("SONAR_EVAL_HARBOR_BIN")
    if override:
        binary = shutil.which(override)
        if not binary or Path(binary).resolve() == ROOT / "sonar":
            raise EvalError("SONAR_EVAL_HARBOR_BIN must point to the upstream Harbor CLI")
        return binary
    local = ROOT / ".venv-harbor" / ("Scripts/harbor.exe" if os.name == "nt" else "bin/harbor")
    if local.is_file():
        return str(local)
    for directory in os.get_exec_path():
        binary = shutil.which("harbor", path=directory)
        if binary and Path(binary).resolve() != ROOT / "sonar":
            return binary
    raise EvalError("Install Harbor with the pinned requirements-harbor.txt (see README)")


def harbor_version():
    try:
        probe = subprocess.run([harbor_executable(), "--version"], env=harbor_env(), capture_output=True,
                               text=True, timeout=30, check=False)
    except subprocess.TimeoutExpired as exc:
        raise EvalError("Harbor --version timed out") from exc
    version = re.search(r"\b\d+\.\d+\.\d+(?:[-+][\w.+-]+)?", probe.stdout)
    if probe.returncode or not version:
        raise EvalError("Could not determine the Harbor CLI version")
    return version.group()


def harbor_env(env=None):
    return {"HARBOR_TELEMETRY": "0", **(os.environ if env is None else env)}


def base_url(value):
    if not isinstance(value, str) or any(char.isspace() for char in value):
        raise EvalError("Model base_url must be an HTTP(S) URL without whitespace")
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme in {"http", "https"} and parsed.hostname and parsed.port != 0
                 and parsed.username is None and parsed.password is None and not parsed.query and not parsed.fragment)
    except ValueError:
        valid = False
    if not valid:
        raise EvalError("Model base_url must be an HTTP(S) URL without credentials, query or fragment")
    return value.rstrip("/")


def configure(model, *, environ=None):
    """Freeze the actual route into the plan. Credentials stay in the child environment."""
    provider = model.get("provider")
    endpoint, key = model.get("base_url"), model.get("api_key_env")
    if provider == "infron":
        if endpoint not in (None, INFRON) or key not in (None, "INFRON_API_KEY"):
            raise EvalError("The infron profile uses its documented endpoint and INFRON_API_KEY")
        endpoint, key = INFRON, "INFRON_API_KEY"
    elif provider == "ollama":
        if not endpoint:
            env = os.environ if environ is None else environ
            endpoint = env.get("SONAR_EVAL_OLLAMA_URL", "http://host.docker.internal:11434/v1")
        key = key or "SONAR_EVAL_OLLAMA_KEY"
    if endpoint is not None or key is not None:
        if not isinstance(key, str) or not KEY_NAME.fullmatch(key):
            raise EvalError("A custom endpoint requires api_key_env naming an environment variable")
        model.update(base_url=base_url(endpoint), api_key_env=key)


def save_infron_key(value):
    value = value.strip()
    if not value or any(char.isspace() for char in value):
        raise EvalError("Enter a single Infron API key")
    directory = INFRON_KEY_FILE.parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_text(INFRON_KEY_FILE, value + "\n")
    return INFRON_KEY_FILE


def credential(model):
    name = model.get("api_key_env")
    if not name:
        return None
    value = os.environ.get(name)
    if (not value and name == "INFRON_API_KEY" and model.get("provider") == "infron"
            and model.get("base_url") == INFRON):
        try:
            value = INFRON_KEY_FILE.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            pass
        if not value:
            raise EvalError("Run './sonar set-key infron' or set INFRON_API_KEY")
    if not value and model.get("provider") == "ollama" and name == "SONAR_EVAL_OLLAMA_KEY":
        return "ollama"
    if not value:
        raise EvalError(f"Set {name} to run the {model.get('provider')} model")
    return value


def messages_root(url):
    return url.rstrip("/").removesuffix("/v1")


def judge_credential():
    return credential({"provider": "infron", "base_url": INFRON, "api_key_env": "INFRON_API_KEY"})


def harbor_model(agent, model):
    """Harbor strips the transport prefix and passes the remaining exact ID to the CLI."""
    name, provider = model["name"], model.get("provider")
    if not provider:
        return ["-m", name], None  # Explicit upstream selector from an existing matrix.
    if "base_url" in model:
        wire = FORMATS.get(agent, "openai_chat_completions")
        transport = "anthropic" if wire == "anthropic_messages" else "openai"
        url = messages_root(model["base_url"]) if wire == "anthropic_messages" else model["base_url"]
        if agent == "opencode":
            # Its built-in "openai" provider forces Responses even for a Chat Completions SDK.
            transport = "sonar-eval"
        key = model["api_key_env"]
        env = {**os.environ, key: credential(model)}
        # An inherited first-party login can take precedence over an explicit endpoint.
        for flag in ("CODEX_FORCE_AUTH_JSON", "CODEX_AUTH_JSON_PATH", "CLAUDE_FORCE_OAUTH",
                     "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
                     "CLAUDE_CODE_USE_FOUNDRY"):
            if flag != key:
                env.pop(flag, None)
        return ["-m", f"{transport}/{name}", "--base-url", url, "--api-key-name", key,
                "--api-format", wire], env
    env = None
    if agent == "codex" and provider == "openai" and not any(
            os.environ.get(k) for k in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_AUTH_JSON_PATH")):
        login = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json"
        if login.is_file():
            env = {**os.environ, "CODEX_AUTH_JSON_PATH": str(login)}
    return ["-m", f"{provider}/{name}"], env
