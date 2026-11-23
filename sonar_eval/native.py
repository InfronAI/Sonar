"""Pinned Agent CLIs and single-combination Harbor matrices."""
import os
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit

from .common import ROOT, EvalError, read_json
from .providers import HOST_DEFAULTS


class AgentCLI(NamedTuple):
    executable: str
    family: str
    package: str


PRESETS = {
    "codex": AgentCLI("codex", "Codex", "@openai/codex"),
    "claude-code": AgentCLI("claude", "Claude Code", "@anthropic-ai/claude-code"),
    "pi": AgentCLI("pi", "Pi", "@earendil-works/pi-coding-agent"),
    "opencode": AgentCLI("opencode", "OpenCode", "opencode-ai"),
    "copilot-cli": AgentCLI("copilot", "GitHub Copilot CLI", "@github/copilot"),
}


def agent_presets(root=ROOT):
    manifest = root / "docker/agents/package.json"
    packages = read_json(manifest)["dependencies"] if manifest.is_file() else {}
    return {name: {"id": name, "driver": "harbor", "name": name, "family": cli.family,
                   "version": packages.get(cli.package)} for name, cli in PRESETS.items()}


def default_provider(cli):
    if cli not in HOST_DEFAULTS:
        raise EvalError(f"{PRESETS[cli].family} requires --provider")
    if cli != "claude-code":
        return HOST_DEFAULTS[cli]
    for flag, provider in (("BEDROCK", "bedrock"), ("VERTEX", "vertex"), ("FOUNDRY", "foundry")):
        if os.environ.get("CLAUDE_CODE_USE_" + flag) == "1":
            return provider
    endpoint = os.environ.get("ANTHROPIC_BASE_URL")
    if endpoint:
        host = urlsplit(endpoint).hostname
        if host and host != "api.anthropic.com":
            return host
    return "anthropic"


def matrix(cli, model, provider, family, suite, endpoint=None, key_env=None, version=None):
    if not model:
        raise EvalError("--cli requires --model with the exact model ID")
    if provider is None:
        provider = default_provider(cli)
        if cli == "claude-code" and provider not in {"anthropic", "bedrock", "vertex", "foundry"} and not endpoint:
            endpoint = os.environ["ANTHROPIC_BASE_URL"]
            key_env = key_env or ("ANTHROPIC_AUTH_TOKEN" if not os.environ.get("ANTHROPIC_API_KEY")
                                  and os.environ.get("ANTHROPIC_AUTH_TOKEN") else "ANTHROPIC_API_KEY")
    agent = cli
    if version:
        agent = agent_presets()[cli]
        agent["version"] = version
    record = {"id": "model", "family": family or model, "name": model, "version": model, "provider": provider}
    if endpoint:
        record["base_url"] = endpoint
    if key_env:
        record["api_key_env"] = key_env
    config = {"schema": 1, "track": "agent-cli", "suite": str(suite), "timeout_seconds": 1200,
              "models": [record], "agents": [agent]}
    if Path(suite).resolve().is_relative_to(ROOT / "suites"):
        config["agent_timeout_seconds"] = 600
    return config
