"""Build Harbor task environments ahead of time and pin the images used by each run."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .common import ROOT, EvalError, fingerprint
from .config import IGNORED, load_suite, task_hash
from .native import PRESETS
from .providers import JUDGE_CONTEXT, JUDGE_IMAGE, harbor_executable

BASE = "sonar-eval/agents:1"
BASE_CONTEXT = ROOT / "docker/agents"
LABEL = "io.sonar-eval.build-input"
ALL_TASKS = ROOT / "suites/all-tasks.json"
RUBRIC_IMAGE_PREFIX = "sonar-eval/rubric-verifier-"
RUBRIC_DOCKERFILE = f"FROM {JUDGE_IMAGE}\nCOPY rubric.json /tests/rubric.json\n"


def docker(*args, capture=False):
    cmd = ["docker", *map(str, args)]
    result = subprocess.run(cmd, stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None, text=True, check=False)
    if result.returncode:
        detail = (result.stderr or "").strip()
        raise EvalError(f"docker {args[0]} failed. {detail or 'See Docker output above.'}")
    return result.stdout


def docker_platform():
    daemon = docker("version", "--format", "{{.Server.Os}}/{{.Server.Arch}}", capture=True).strip()
    return {"daemon": daemon, "default": os.environ.get("DOCKER_DEFAULT_PLATFORM") or daemon}


def harbor_python():
    # Harbor's own environment includes a writer for the frozen TOML manifests.
    binary = Path(harbor_executable()).resolve()
    python = binary.with_name("python.exe" if sys.platform == "win32" else "python")
    return str(python) if python.is_file() else sys.executable


def read_manifest(path):
    try:
        import tomllib
    except ImportError:  # The project CLI also supports Python 3.10.
        result = subprocess.run([harbor_python(), "-c",
            "import tomllib,json,sys; print(json.dumps(tomllib.load(sys.stdin.buffer),default=str))"],
            input=path.read_bytes(), capture_output=True, check=True)
        return json.loads(result.stdout)
    with path.open("rb") as source:
        return tomllib.load(source)


def build_stamp(ref, context, base_hash):
    content = task_hash(context)
    if ref in (BASE, JUDGE_IMAGE):
        return content
    if ref and ref.startswith(RUBRIC_IMAGE_PREFIX):
        return fingerprint([task_hash(JUDGE_CONTEXT), content])
    return fingerprint([base_hash, content])


def image_specs(task, base_hash):
    config = read_manifest(task / "task.toml")
    envs = [("main", task / "environment", config.get("environment", {}))]
    verifier = config.get("verifier", {})
    mode = verifier.get("environment_mode", "separate" if "environment" in verifier else "shared")
    steps = config.get("steps", [])
    needs_task_verifier = not steps and mode == "separate"

    def has_image(section, directory):
        return section.get("environment", {}).get("docker_image") or any(
            (directory / name).is_file() for name in ("Dockerfile", "docker-compose.yaml"))

    for index, step in enumerate(steps):
        step_verifier = step.get("verifier", {})
        step_mode = step_verifier.get("environment_mode", "separate" if "environment" in step_verifier else mode)
        if step_mode == "separate":
            step_tests = task / "steps" / step["name"] / "tests"
            if has_image(step_verifier, step_tests):
                envs.append((str(index), step_tests, step_verifier.get("environment", {})))
            else:
                needs_task_verifier = True
    if needs_task_verifier and has_image(verifier, task / "tests"):
        envs.append(("verifier", task / "tests", verifier.get("environment", {})))
    specs = {}
    for role, context, env in envs:
        ref = env.get("docker_image")
        if (context / "Dockerfile").is_file():
            stamp = build_stamp(ref, context, base_hash)
            if not ref or not ref.startswith("sonar-eval/") or "@" in ref:
                ref = f"sonar-eval/task:{stamp}"
        elif ref:
            stamp = None
        else:
            raise EvalError(f"{context} needs a Dockerfile or a prebuilt docker_image in task.toml")
        specs[role] = (ref, context, stamp)
        compose = context / "docker-compose.yaml"
        if compose.is_file():
            relative = compose.relative_to(task).as_posix()
            for name, image in compose_images(compose).items():
                specs[f"service:{relative}:{name}"] = (image, context, None)
    return specs


def inspect_image(ref):
    # docker inspect can also contain arbitrary ENV values; request only the two public fields.
    fmt = '{{.Id}} {{if .Config.Labels}}{{index .Config.Labels "' + LABEL + '"}}{{end}}'
    output = docker("image", "inspect", "--format", fmt, ref, capture=True).strip()
    image_id, _, stamp = output.partition(" ")
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id):
        raise EvalError(f"Invalid Docker image ID for {ref}")
    return image_id, stamp


def archive_prefix(ref):
    path, slash, name = ref.partition("@")[0].rpartition("/")
    repository = path + slash + name.partition(":")[0]
    return f"{repository}:sonar-{fingerprint(ref)[:40]}-"


def inspect_prebuilt(ref):
    try:
        return inspect_image(ref)
    except EvalError:
        if "@" not in ref:
            raise
        # Some Docker stores restore only tags from an archive, losing repo digests.
        prefix = archive_prefix(ref)
        tags = docker("image", "ls", "--filter", "reference=" + prefix + "*", "--format",
                      "{{.Tag}}", capture=True).splitlines()
        matches = [prefix.rpartition(":")[0] + ":" + tag for tag in tags]
        if not matches:
            raise
        if len(matches) > 1:
            platform = docker("version", "--format", "{{.Server.Os}}/{{.Server.Arch}}", capture=True).strip()
            matches = [tag for tag in matches if docker("image", "inspect", "--format",
                       "{{.Os}}/{{.Architecture}}", tag, capture=True).strip() == platform]
        if len(matches) != 1:
            raise EvalError(f"No unique archived image for {ref} on this platform")
        image_id, stamp = inspect_image(matches[0])
        if matches[0] != prefix + image_id.removeprefix("sha256:"):
            raise EvalError(f"Archived Docker image differs for {ref}")
        return image_id, stamp


def archive_image(ref):
    if "@" not in ref:
        return ref
    image_id, _ = inspect_prebuilt(ref)
    alias = archive_prefix(ref) + image_id.removeprefix("sha256:")
    try:
        if inspect_image(alias)[0] == image_id:
            return alias
    except EvalError:
        pass
    docker("image", "tag", ref, alias)
    return alias


def compose_config(compose, *, interpolate=False):
    options = [] if interpolate else ["--no-interpolate"]
    return json.loads(docker("compose", "--profile", "*", "-f", compose, "config", *options,
                             "--no-consistency", "--no-env-resolution", "--no-path-resolution",
                             "--no-normalize", "--format", "json", capture=True))


def compose_images(compose):
    # Harbor merges this file after its prebuilt main service.
    services = compose_config(compose).get("services", {})
    resolved = None
    refs = {}
    for name, service in services.items():
        if "build" in service:
            raise EvalError(f"{compose}: prebuild service {name} and reference its image in the compose file")
        ref = service.get("image")
        if name == "main":
            if ref is not None and ref != "${PREBUILT_IMAGE_NAME}":
                raise EvalError(f"{compose}: declare the main image in task.toml so Harbor can pin it")
            continue
        if ref and "$" in ref:
            if resolved is None:
                resolved = compose_config(compose, interpolate=True)["services"]
            ref = resolved[name].get("image")
        if not ref:
            raise EvalError(f"{compose}: service {name} requires a prebuilt image")
        refs[name] = ref
    return refs


def build_images(suite, archive=None):
    _, origins = load_suite(suite.resolve())
    base_hash = task_hash(BASE_CONTEXT)
    recipes = {BASE: (BASE_CONTEXT, base_hash)}
    for task in origins.values():
        for ref, context, stamp in image_specs(task, base_hash).values():
            if ref.startswith(RUBRIC_IMAGE_PREFIX) and JUDGE_IMAGE not in recipes:
                recipes[JUDGE_IMAGE] = (JUDGE_CONTEXT, task_hash(JUDGE_CONTEXT))
            if ref in recipes and recipes[ref][1] and stamp and recipes[ref][1] != stamp:
                raise EvalError(f"Two different build contexts declare the same image {ref}")
            if ref not in recipes or stamp:
                recipes[ref] = context, stamp
    for ref, (context, stamp) in recipes.items():
        try:
            image_id, built_from = inspect_prebuilt(ref)
        except EvalError:
            image_id, built_from = None, None
        if image_id and (not stamp or built_from == stamp):
            print(f"{ref}  {image_id} (ready)", flush=True)
            continue
        if stamp:
            with tempfile.TemporaryDirectory() as temp:
                build_context = Path(temp) / "context"
                shutil.copytree(context, build_context, symlinks=True, ignore=shutil.ignore_patterns(*IGNORED))
                if build_stamp(ref, build_context, base_hash) != stamp:
                    raise EvalError(f"{context} changed while preparing the build. Run build-images again")
                docker("build", "--label", f"{LABEL}={stamp}", "-t", ref, build_context)
        else:
            docker("pull", ref)
        print(f"{ref}  {inspect_prebuilt(ref)[0]}", flush=True)
    if archive is not None:
        archive = archive.resolve()
        archive.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=archive.parent, prefix=".saving-", delete=False) as tmp:
            path = Path(tmp.name)
        try:
            docker("image", "save", "--output", path, *(archive_image(ref) for ref in recipes))
            os.replace(path, archive)
        finally:
            path.unlink(missing_ok=True)
        print(f"Saved {len(recipes)} image references to {archive}")


def resolve_images(plan, origins):
    """Read-only preflight, including the real CLI executable from each requested task image."""
    images = {}
    checked = {}
    base_hash = task_hash(BASE_CONTEXT)
    agents = [plan["agents"][a] for a in dict.fromkeys(a for _, a in plan["pairs"])]
    judged = {case["id"] for case in plan.get("suite", {}).get("cases", []) if case.get("judge")}
    for case_id, task in origins.items():
        images[case_id] = {}
        if case_id in judged:
            manifest = read_manifest(task / "task.toml")
            verifier = manifest.get("verifier", {})
            expected_env = {"SONAR_JUDGE_KEY": "${SONAR_JUDGE_KEY}"}
            tests = task / "tests"
            ref = verifier.get("environment", {}).get("docker_image", "")
            if (verifier.get("environment_mode") != "separate" or not ref.startswith(RUBRIC_IMAGE_PREFIX)
                    or verifier.get("env") != expected_env
                    or manifest.get("artifacts") != [{"source": "/app/submission.md", "destination": "submission.md"}]
                    or manifest.get("steps") or (tests / "docker-compose.yaml").exists()
                    or (tests / "Dockerfile").read_text() != RUBRIC_DOCKERFILE
                    or (tests / "test.sh").read_bytes() != (JUDGE_CONTEXT / "test.sh").read_bytes()):
                raise EvalError(f"{case_id} needs the isolated Sonar judge image, submission artifact and rubric launcher")
            verifier = {k: v for k, v in verifier.items() if k != "env"}
            if "SONAR_JUDGE_KEY" in json.dumps({**manifest, "verifier": verifier}):
                raise EvalError(f"{case_id} can request the judge credential only in the verifier environment")
        for role, (ref, context, stamp) in image_specs(task, base_hash).items():
            try:
                image_id, actual_stamp = inspect_prebuilt(ref)
                if stamp and stamp != actual_stamp:
                    raise EvalError(f"{ref} is stale")
            except EvalError as exc:
                raise EvalError(f"{exc}. Prepare the suite with './sonar build-images --suite {task}'") from exc
            record = {"image": ref, "id": image_id}
            compose = context / "docker-compose.yaml"
            if compose.is_file() and not role.startswith("service:"):
                record["compose_file"] = compose.relative_to(task).as_posix()
            if role == "main":
                versions = {}
                for agent in agents:
                    name = agent["name"]
                    if name not in PRESETS:
                        continue
                    key = image_id, name
                    if key not in checked:
                        output = docker("run", "--rm", "--pull=never", "--network", "none", "--entrypoint",
                                        PRESETS[name].executable, image_id, "--version", capture=True)
                        match = re.search(r"\b\d+\.\d+\.\d+(?:[-+][\w.+-]+)?", output)
                        checked[key] = match.group() if match else None
                    if checked[key] != agent["version"]:
                        raise EvalError(f"{ref} provides {name} {checked[key]}, matrix requires {agent['version']}")
                    versions[name] = checked[key]
                if versions:
                    record["cli_versions"] = versions
            images[case_id][role] = record
    return images


def pinned_tag(image_id):
    return "sonar-eval/frozen:" + image_id.removeprefix("sha256:")


def ensure_pinned(image_id):
    tag = pinned_tag(image_id)
    try:
        actual, _ = inspect_image(tag)
    except EvalError:
        # docker load restores the original tags. Recreate the run alias from its exact content.
        actual, _ = inspect_image(image_id)
        if actual == image_id:
            docker("image", "tag", image_id, tag)
    if actual != image_id:
        raise EvalError(f"Pinned Docker image differs from {image_id}")
    return tag


def pin_snapshot(task, images, agent_timeout=None):
    refs = {}
    services = {}
    for role, record in images.items():
        tag = ensure_pinned(record["id"])
        if role.startswith("service:"):
            relative, name = role.removeprefix("service:").rsplit(":", 1)
            services.setdefault(relative, {})[name] = tag
        else:
            refs[role] = tag
            if "compose_file" in record:
                services.setdefault(record["compose_file"], {})
    result = subprocess.run([harbor_python(), "-m", "sonar_eval.images", str(task / "task.toml"),
                             json.dumps(refs), json.dumps(services), json.dumps(agent_timeout)],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode:
        raise EvalError(f"Could not pin {task.name}/task.toml: {result.stderr.strip()}")


def write_pinned_manifest(path, refs, agent_timeout=None):
    import toml
    import tomllib

    config = read_manifest(path)
    if agent_timeout is not None:
        config.setdefault("agent", {})["timeout_sec"] = agent_timeout
        for step in config.get("steps", []):
            if "timeout_sec" in step.get("agent", {}):
                step["agent"]["timeout_sec"] = agent_timeout
    for role, ref in refs.items():
        section = config
        inherited = config.get("environment", {})
        if role == "verifier":
            section = config.setdefault("verifier", {})
            if "environment" not in section and section.get("environment_mode", "shared") == "shared":
                # A separate step inherits tests/ from the task. Pin it there so Harbor
                # keeps that directory and its Compose services when resolving the step.
                for step in config.get("steps", []):
                    step_verifier = step.setdefault("verifier", {})
                    if "environment" not in step_verifier:
                        step_verifier.setdefault("environment_mode", "shared")
                section["environment_mode"] = "separate"
        elif role != "main":
            section = config["steps"][int(role)].setdefault("verifier", {})
            inherited = config.get("verifier", {}).get("environment", inherited)
        section.setdefault("environment", dict(inherited))["docker_image"] = ref
    output = toml.dumps(config)
    if tomllib.loads(output) != config:
        raise EvalError("Harbor manifest changed during TOML serialization")
    path.write_text(output, encoding="utf-8")


def write_pinned_compose(path, tags):
    # Edit the source YAML nodes. Rendering through Compose would erase !reset/!override
    # before Harbor merges the task file with its own service and mount definitions.
    from copy import copy

    import yaml

    loader = yaml.SafeLoader(path.read_text(encoding="utf-8"))
    try:
        root = loader.get_single_node()

        def mapping(parent, name):
            loader.flatten_mapping(parent)
            for index in range(len(parent.value) - 1, -1, -1):
                key, value = parent.value[index]
                if key.value == name:
                    # Detach aliases so changing one service does not change another.
                    child = copy(value) if isinstance(value, yaml.MappingNode) else yaml.compose("{}")
                    child.value = list(child.value)
                    parent.value[index] = (key, child)
                    return child
            child = yaml.compose("{}")
            parent.value.append((yaml.ScalarNode("tag:yaml.org,2002:str", name), child))
            return child

        services = mapping(root, "services")
        for name, tag in {"main": None, **tags}.items():
            service = mapping(services, name)
            loader.flatten_mapping(service)
            updates = {"pull_policy": "never"}
            if tag is not None:
                updates["image"] = tag
            service.value = [(key, value) for key, value in service.value if key.value not in updates]
            service.value.extend(yaml.compose(json.dumps(updates)).value)
        path.write_text(yaml.serialize(root), encoding="utf-8")
    finally:
        loader.dispose()


if __name__ == "__main__":
    manifest = Path(sys.argv[1])
    write_pinned_manifest(manifest, json.loads(sys.argv[2]), json.loads(sys.argv[4]) if len(sys.argv) > 4 else None)
    for relative, services in json.loads(sys.argv[3]).items():
        write_pinned_compose(manifest.parent / relative, services)
