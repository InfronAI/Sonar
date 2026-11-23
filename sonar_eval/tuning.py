"""Resolve and freeze inference controls exposed by the pinned agent integrations."""
import json
import math
import os
import re

from .common import EvalError

FIELDS = ("reasoning_effort", "max_tokens", "temperature", "top_p", "max_turns", "max_thinking_tokens")
EFFORTS = {
    "codex": {"none", "minimal", "low", "medium", "high", "xhigh", "max"},
    "claude-code": {"low", "medium", "high", "xhigh", "max"},
    "pi": {"off", "minimal", "low", "medium", "high", "xhigh", "max"},
    "copilot-cli": {"low", "medium", "high", "xhigh", "max"},
    "opencode": None,  # Variants are named by the model/provider configuration.
}
ENV_FIELDS = {
    "claude-code": {"CLAUDE_CODE_EFFORT_LEVEL": "reasoning_effort", "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "max_tokens",
                    "CLAUDE_CODE_MAX_TURNS": "max_turns", "MAX_THINKING_TOKENS": "max_thinking_tokens"},
    "copilot-cli": {"COPILOT_CLI_EFFORT": "reasoning_effort", "COPILOT_PROVIDER_MAX_OUTPUT_TOKENS": "max_tokens"},
    "opencode": {"OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX": "max_tokens"},
}


def numeric_string(field, value):
    if field == "reasoning_effort" or not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError as exc:
        raise EvalError(f"{field} requires a number") from exc


def opencode_overlay(kwargs, model=None):
    config = json.loads(kwargs.get("opencode_config", "{}"))
    if not isinstance(config, dict):
        raise EvalError("opencode_config must be a JSON object")
    selected = config.get("default_agent", "build")
    agents = config.setdefault("agent", {})
    if not isinstance(selected, str) or not isinstance(agents, dict):
        raise EvalError("OpenCode needs a named default_agent and an agent configuration object")
    options = agents.setdefault(selected, {})
    if not isinstance(options, dict):
        raise EvalError(f"OpenCode agent {selected} needs a configuration object")
    if model and model.get("base_url") and "provider" in config:
        section = config
        for key in ("provider", "sonar-eval", "models", model.get("name", "")):
            section = section.get(key, {})
            if not isinstance(section, dict):
                raise EvalError(f"OpenCode {key} must be a configuration object")
    return config, options


def resolve(global_settings, model, agent, overrides, *, environ=None):
    name = agent.get("name")
    env = os.environ if environ is None else environ
    chosen = {field: numeric_string(field, env[key]) for key, field in ENV_FIELDS.get(name, {}).items()
              if env.get(key) and not (name == "copilot-cli" and field == "max_tokens" and not model.get("base_url"))}
    aliases = {"reasoning_effort": "reasoning_effort"}
    if name == "pi":
        aliases.update(thinking="reasoning_effort", max_output_tokens="max_tokens", max_turns="max_turns")
    elif name == "claude-code":
        aliases.update(max_turns="max_turns", max_thinking_tokens="max_thinking_tokens")
    elif name == "opencode":
        aliases["variant"] = "reasoning_effort"
    legacy = {aliases[k]: numeric_string(aliases[k], v) for k, v in agent.get("kwargs", {}).items() if k in aliases}
    if name == "opencode" and "opencode_config" in agent.get("kwargs", {}):
        _, options = opencode_overlay(agent["kwargs"], model)
        legacy.update(sampling(options))
    for layer in (global_settings, model.get("inference", {}), legacy, agent.get("inference", {}), overrides):
        if not isinstance(layer, dict) or any(key not in FIELDS for key in layer):
            raise EvalError(f"inference must be an object using {', '.join(FIELDS)}")
        chosen.update(layer)
    chosen = {key: value for key, value in chosen.items() if value is not None}
    supported = {"reasoning_effort"} if name in EFFORTS else set()
    if name == "claude-code":
        supported.update(("max_tokens", "max_turns", "max_thinking_tokens"))
    elif name == "pi":
        if model.get("base_url"):
            supported.add("max_tokens")
        supported.add("max_turns")
    elif name == "opencode":
        supported.update(("temperature", "top_p", "max_tokens"))
    elif name == "copilot-cli" and model.get("base_url"):
        supported.add("max_tokens")
    for field, value in chosen.items():
        if field not in supported:
            raise EvalError(f"{name or agent['id']} does not expose {field} for this driver/provider")
        if field == "reasoning_effort":
            if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value)
                    or EFFORTS[name] is not None and value not in EFFORTS[name]):
                raise EvalError(f"Unsupported reasoning_effort for {name}: {value!r}")
        elif field in {"temperature", "top_p"}:
            limit = 2 if field == "temperature" else 1
            if type(value) not in (int, float) or not 0 <= value <= limit or not math.isfinite(value):
                raise EvalError(f"{field} must be a finite number between 0 and {limit}")
            chosen[field] = float(value)
        elif type(value) is not int or value < (0 if field == "max_thinking_tokens" else 1):
            raise EvalError(f"Invalid token or turn count for {field}: {value!r}")
    return {field: chosen.get(field) for field in FIELDS}


def sampling(settings):
    return {k: settings[k] for k in ("temperature", "top_p") if settings.get(k) is not None}


def launch_env(name, env, settings):
    if name not in ENV_FIELDS:
        return env
    result = dict(os.environ if env is None else env)
    for key, field in ENV_FIELDS[name].items():
        result.pop(key, None)
        if settings.get(field) is not None:
            result[key] = str(settings[field])
    return result


def harbor_options(name, kwargs, settings, model=None):
    options = dict(kwargs)
    if name not in EFFORTS:
        return options
    options.pop("reasoning_effort", None)
    if name == "pi":
        for key in ("thinking", "max_output_tokens", "max_turns"):
            options.pop(key, None)
    if name == "opencode":
        options.pop("variant", None)
    if name == "claude-code":
        for key in ("max_turns", "max_thinking_tokens"):
            options.pop(key, None)
    for key in ("reasoning_effort", "max_turns", "max_thinking_tokens"):
        if settings.get(key) is not None:
            options[key] = str(settings[key])
    if name == "pi" and settings.get("max_tokens") is not None:
        options["max_output_tokens"] = str(settings["max_tokens"])
    if name == "opencode":
        config, selected = opencode_overlay(kwargs, model)
        # Harbor sets OPENCODE_FAKE_VCS=git. In a task without .git this makes
        # OpenCode try to snapshot the entire container filesystem.
        config.setdefault("snapshot", False)
        for key in ("temperature", "top_p"):
            selected.pop(key, None)
        selected.update(sampling(settings))
        config.setdefault("default_agent", "build")
        if model and model.get("base_url") and settings.get("temperature") is not None:
            provider = config.setdefault("provider", {}).setdefault("sonar-eval", {})
            provider.setdefault("models", {}).setdefault(model["name"], {})["temperature"] = True
        options["opencode_config"] = json.dumps(config)
    return options
