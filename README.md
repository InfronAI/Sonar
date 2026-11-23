# Sonar

Sonar measures how a command-line agent and a model perform together on reproducible tasks. The agent gets a working directory, tools and a task. The verifier grades the artifact the agent leaves behind. For example, on a SQL task it executes the submitted query against fresh databases and checks the returned rows. [Example SQL task](suites/datasets/sql-analytics/unpaid-invoices/instruction.md)

Use Sonar to compare several agents on one model, compare model releases through one agent, or track a combination over time. Each run starts manually and exits after publishing its results and report in the project workspace.

## What an experiment measures

| Term | Meaning in Sonar |
| --- | --- |
| Agent | A real CLI such as Pi, Claude Code or Codex. Harbor launches the selected CLI in a fresh task environment for each attempt. |
| Model | The exact model identifier served by a provider, such as local Ollama or remote Infron. A family label groups releases for reporting. |
| Task and suite | A task has instructions, an environment and a verifier. The collection contains 100 tasks in 50 two-task suites across 14 domains. |
| Trial and run | A trial is one agent–model pair attempting one task once. A run freezes a matrix and executes **selected pairs × tasks × repetitions** trials. |

Sonar owns the experiment plan, history and report. Upstream Harbor runs each task and its verifier in Docker. [Task manifest](suites/all-tasks.json) · [Domain index](suites/domains.json) · [Upstream Harbor](https://github.com/harbor-framework/harbor)

### Evaluation principles

- **Control the comparison.** To measure a model change, keep the agent, tasks, verifier and inference settings fixed. When both the agent and model change, the result describes the new combination.
- **Freeze conditions before execution.** The plan captures task revisions, image IDs, Docker platform, versions, deadlines and requested inference settings before the first trial.
- **Keep the evidence for every outcome.** A verifier reward, an agent timeout and a launcher error answer different questions. Each attempt has a result record that points to its evidence.

## Run a local evaluation

From the project root, use Python 3.10 or newer for Sonar. Start Docker with Compose and Buildx available. With Colima, start the VM and select it in the current shell with `export DOCKER_CONTEXT=colima`. Install the pinned Harbor runtime in its own environment on a fresh checkout.

```sh
python3.12 -m venv .venv-harbor
.venv-harbor/bin/python -m pip install -r requirements-harbor.txt
```

Prepare the bundled images with `./sonar build-images`. If the Linux arm64 archive came with your workspace, restore it on a compatible Docker host with `docker image load -i .sonar/images/sonar-linux-arm64.tar`. It contains the agent CLIs, task workspaces and separate rubric verifier images. The 40 rubric tasks share one agent workspace image. Each verifier layers its task's criteria on the same judge image. [Pinned Harbor dependency](requirements-harbor.txt) · [Agent image recipe](docker/agents/Dockerfile)

Start Ollama on the host. Prepare the default model and run the two-task SQL suite with Pi.

```sh
ollama pull qwen3-vl:2b-instruct
./sonar doctor --suite suites/datasets/sql-analytics
./sonar run --suite suites/datasets/sql-analytics
```

For an evaluation that runs entirely locally, select the original 60 deterministic tasks with `./sonar doctor --suite suites/all-tasks-v3.json`, then `./sonar run --suite suites/all-tasks-v3.json`. The default suite now also includes 40 remote-judged tasks and requires an Infron key. `doctor` checks the plan, configured credentials, local images and CLI releases. Model inference begins with `run`. The default Ollama URL inside Docker is `http://host.docker.internal:11434/v1`. Set `SONAR_EVAL_OLLAMA_URL` to use another reachable address. [Local matrix](configs/ollama.json) · [Ollama API compatibility](https://docs.ollama.com/api/openai-compatibility)

`./sonar` and `python3 -m sonar_eval` expose the same commands. An explicit `SONAR_EVAL_HARBOR_BIN` selects the upstream executable. The default search checks `.venv-harbor` before the system path.

## Choose the agent and model

| Selection | What runs with the full bundled collection |
| --- | --- |
| `./sonar run --config configs/ollama.json` | Pi × local Qwen, 100 attempts including 40 rubric evaluations through Infron |
| `./sonar run --config configs/infron.json` | Codex, Claude Code, Pi, OpenCode and GitHub Copilot CLI × Infron `z-ai/glm-5.2`, 500 attempts including 200 rubric evaluations |
| Single combination using `--cli`, `--provider` and `--model` | One specified agent and model, 100 attempts including 40 rubric evaluations |

Use `--suite` on either `doctor` or `run` to select a task directory, a suite directory or a manifest. For a single combination, the CLI accepts `codex`, `claude-code`, `pi`, `opencode` and `copilot-cli`. The image, presets and report share the same package versions. Optional host installations for interactive use live at `.sonar/tools/pi/node_modules/.bin/pi`, `.sonar/tools/opencode/node_modules/.bin/opencode` and `.sonar/tools/copilot/node_modules/.bin/copilot`. [Agent package versions](docker/agents/package.json)

### Infron and custom endpoints

Run `./sonar set-key infron` to save the key through a hidden prompt. The command writes `.sonar/credentials/infron-api-key` with mode `0600`. Later runs read that file. An explicit `INFRON_API_KEY` in the launch environment takes precedence. The plan records the variable name and endpoint. The key value travels in the child process environment.

For example, to run Claude Code with ERNIE on the full collection through Infron, use the same selection for preflight and execution.

```sh
./sonar doctor --cli claude-code --provider infron --model baidu/ernie-5.5-flash-preview --model-family ERNIE
./sonar run --cli claude-code --provider infron --model baidu/ernie-5.5-flash-preview --model-family ERNIE
```

Infron uses `https://llm.onerouter.pro/v1`. Sonar selects Anthropic Messages for Claude Code, OpenAI Responses for Codex and Chat Completions for Pi, OpenCode and Copilot CLI. In a trial’s `result.json`, `metadata.configured_provider` identifies the selected service. Harbor’s `metadata.harbor_model_info.provider` describes its model connection. For Claude Code using Infron, those values are `infron` and `anthropic`. The evidence directory’s `argv.json` records the exact model selector, API format and endpoint. [Infron setup](https://infron.ai/docs) · [Infron matrix](configs/infron.json)

```sh
./sonar run --cli codex --provider openai --model gpt-6.2-astra --model-family Astra
./sonar run --cli claude-code --provider infron --model anthropic/claude-opus-5.5 --model-family Opus
./sonar run --cli claude-code --provider infron --model qwen/qwen4-max --model-family Qwen4 --suite suites/all-tasks-v3.json
./sonar run --cli pi --provider team-gateway --model team/model-v2 --model-family team-model \
  --base-url https://gateway.example.com/v1 --api-key-env TEAM_MODEL_KEY
```

Codex can use `OPENAI_API_KEY` or an existing Codex login. Direct Claude Code access supports `--provider anthropic --model claude-opus-5-5` with `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`. Subscription users can obtain the latter with `claude setup-token`. [Harbor agent authentication](https://docs.harborframework.com/agents/agent-auth-resolution)

### Matrices and inference settings

Use a JSON matrix for a recurring experiment. Each model has a stable `id`, a `family`, an exact `name` and a `version`. Specify the `provider` and, for a custom route, `base_url` and `api_key_env`. The `agents` list accepts preset names or full records with `id`, `family`, `name`, `driver` and `version`. Full records also accept `inference` and string-valued Harbor `kwargs`. By default Sonar pairs every configured agent with every model. An explicit `pairs` entry such as `[["glm", "pi"]]` selects just those model and agent IDs.

Set `inference` on the matrix, model or agent. Each narrower scope takes precedence, and CLI flags take precedence over all three. The resolved values appear in `plan.json` under `inference[model_id][agent_id]`, in each trial result and in the pair summary. A `null` value delegates the decision to the client or provider.

| Control | Support in the pinned integrations |
| --- | --- |
| `--thinking` or `--reasoning-effort` | All five agents. Accepted values depend on the CLI and model. OpenCode uses a named variant. |
| `--max-tokens` | Claude Code, OpenCode, Pi with an explicit endpoint, and Copilot with a custom endpoint. Limits one response. |
| `--temperature` and `--top-p` | OpenCode's selected primary agent. |
| `--max-turns` | Claude Code and Pi. |
| `--max-thinking-tokens` | Claude Code with models that support a thinking-token budget. |

For example, `./sonar doctor --cli pi --provider infron --model z-ai/glm-5.2 --thinking high --max-tokens 2048` validates both controls before starting an experiment.

The bundled matrices and single-pair CLI runs on this collection allow **600 seconds for agent execution** and **1,200 seconds for the whole trial**, including setup and verification. Deterministic verifiers have 30 seconds. Rubric verifiers have 240 seconds. Set `agent_timeout_seconds` and `timeout_seconds` in a matrix, or pass `--agent-timeout 900 --trial-timeout 1500` to both `doctor` and `run`. Sonar applies the agent budget to the frozen task copy, including each step of a multi-step task, and includes the override in the comparison fingerprint. A custom matrix that omits the agent budget uses the Harbor task limits in its manifest.

## Evidence, recovery and comparison

Each formal run has a directory under `.sonar/runs/<RUN_ID>/`. Use `./sonar runs --json` to find its ID and see how many planned trials have committed results. Substitute that ID for `RUN_ID` in the commands below.

When an explicitly requested retest replaces a recorded experiment, its new run keeps the actual execution ID and timestamps. The previous ID can be retained as a local link to that run. History counts the new execution once. The run page displays the previous and current counts when a `retest.json` comparison accompanies the result.

| Inside the run directory | What it records |
| --- | --- |
| `plan.json` and `tasks/` | The frozen matrix, versions, provider route, inference settings, fingerprints and task snapshots |
| `trials/000001/result.json` | One attempt's status, reward, elapsed time, evidence directory and, when available, its `harbor_result` path |
| `trials/000001/execution-*/` | Launch arguments and logs, including the upstream Harbor job, agent output and verifier evidence |
| `summary.json` | Final counts and rewards per pair. Its publication marks the run complete. |

```sh
./sonar show RUN_ID --json
./sonar resume RUN_ID
./sonar history --json
./sonar report
```

`show` includes committed trials from unfinished runs. `resume` checks the frozen environment and reuses committed results. `history` and the HTML report use completed runs. Open `.sonar/report.html` to browse the experiment catalog, rankings, agents, models and run history. The catalog includes example commands, a downloadable matrix and a page for every suite with its instructions, submission requirements and verifier. Filter suite results by task, agent, model, provider, run or outcome. Select a task attempt to open its row in the frozen run. **Trajectory** opens the recorded steps and CLI transcript. **Evidence** links to the results, verifier, task snapshot and any rubric assessment. The report rebuilds offline. Copy `report.html`, `report/` and `runs/` together to move it. Use `--state PATH` or `SONAR_EVAL_STATE` for a separate results directory.

In **Rankings**, choose **Combination** to see every measured pair in a benchmark, **Agent** to hold the model and provider endpoint fixed, or **Model** to hold the agent release fixed. The chart ranks each exact combination by its most recently started completed run. Equal pass rates share a rank. The time plot shows every completed observation at its UTC start time. Each point links to run evidence. Coincident points show a count and open their underlying observations.

Rankings group runs by track, benchmark fingerprint, repetitions, time limit, recorded inference settings and agent options. The fingerprint covers the tasks, scoring and Docker environment. Release and endpoint labels distinguish entries within a group. When multiple tracking IDs select the same exact combination in one run, their pass and attempt counts are added together.

**All tasks v3** selects the original 60 tasks. Their verifiers run fixed test cases. Passing every check earns 1 and a failed check earns 0. **All tasks v4** includes these same revisions plus 40 rubric-judged tasks. Select `--suite suites/rubric-tasks.json` to run the 40 on their own. [Original 60](suites/all-tasks-v3.json) · [Rubric tasks](suites/rubric-tasks.json) · [All 100](suites/all-tasks.json)

On a rubric task, the agent writes an English Markdown document to `/app/submission.md`. Harbor transfers it into a separate verifier container. That verifier sends the assignment, case packet, four criteria and submission to Infron’s `infron/op-5.5`. Each criterion earns a level of 0, 1 or 2. Its contribution is its percentage weight times the level divided by 2. The four weights are 30%, 30%, 25% and 15%. A reward of **0.75 or higher** passes. An absent or invalid submission earns zero locally. A judge or provider failure leaves the attempt ungraded. Each graded assessment saves the reported model ID, response ID, usage when available, scores, reasons and evidence hashes in `verifier/judge.json`. Judge scores can vary between calls. [Example rubric](suites/datasets/archive-access-decisions/prioritize-digitization/tests/rubric.json) · [Judge implementation](docker/rubric-judge/judge.py)

Pass rate counts every attempt. Mean reward uses graded attempts. On a binary suite, six passes, two failures and two timeouts give a 60% pass rate and a mean reward of 0.75. `run` and `resume` exit with `0` when every attempt receives a score, `1` when any attempt errors or times out, `2` for command or configuration errors, and `130` after a manual interruption.

Family history uses stable model and agent IDs across releases. When moving a `--cli` experiment into a reusable matrix, copy its track, component IDs and family labels from `plan.json` to continue the series. A change in percentage points compares against the previous run with matching task and scoring fingerprints, image identities, Docker platform, track, repetitions, timeouts, endpoint, inference settings, agent options and family membership. A run with changed conditions still has its own results and evidence.

## Maintaining the task collection

The bundled work includes software repair, finance, law, biology, healthcare, physics and chemistry. The coding bugfix suite checks repaired Python interfaces. The legal suites apply supplied fictional rules, and healthcare tasks use synthetic operational records. Browse the full list by domain in the report or the domain index. [Task collection](suites/datasets) · [Domain index](suites/domains.json)

A bundled Harbor task carries `instruction.md`, `task.toml`, an `environment/` build context and `tests/test.sh` with its verifier inputs. The Dockerfile supplies task tools and public starter data. Harbor supplies the tests at verification time. The bundled verifiers write `/logs/verifier/reward.txt`. `solution/` contains a known-correct submission for developing and checking the verifier. Custom manifests can set their own `reward_key` and `pass_threshold`. [Harbor task format](https://docs.harborframework.com/tasks/overview) · [Verifier conventions](https://docs.harborframework.com/tasks/verifier)

Use `./sonar build-images --suite PATH` for an imported suite. Declare the main image in `task.toml` for multi-service Compose tasks and reference prebuilt auxiliary service images. Sonar can also freeze separate verifier images. Rebuild after changing a task environment or the agent package lock. Use `./sonar build-images --archive .sonar/images/sonar-linux-arm64.tar` on Linux arm64 Docker to export the bundled images. Run `python3 -m unittest discover -s tests -v` for regression checks. [Workspace instructions](AGENTS.md)
