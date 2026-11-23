# Working in Sonar

Sonar evaluates a real agent CLI paired with a model on Harbor tasks. Any host agent can launch a run from the project root with `./sonar` or `python3 -m sonar_eval`. Harbor starts the CLI named in the plan inside each task container. Keep project documentation, task instructions and user-visible application text in English. [Setup and CLI examples](README.md)

## Running an experiment

1. **Resolve the requested combination.** Choose the exact provider and model ID, agent preset, suite and repetitions. Keep component IDs and family labels stable when studying upgrades. A one-off combination fits `--cli`. Put reusable matrices in `configs/`. The default collection has 100 tasks. The Ollama matrix schedules 100 attempts and the Infron matrix schedules 500. Each pair has 40 rubric evaluations through Infron. Use `--suite suites/all-tasks-v3.json` for the original 60 deterministic tasks.
2. **Prepare and preflight.** Start the required Docker context and model service. Load the archive or build the task images. Use `./sonar doctor` with the same selection and inference flags as the intended `run`. Check the number of pairs and trials, the in-image CLI release, and the fingerprint. Store the Infron key with `./sonar set-key infron`. Use environment variable names when specifying credentials in config.
3. **Run the requested evaluation.** Use `./sonar run` with that selection. Sonar freezes the plan and task snapshots before the first attempt. Track progress on demand with `./sonar runs --json` and `./sonar show RUN_ID --json`. Preserve the run ID when reporting progress, especially when several experiments are active.
4. **Recover from an interruption.** Use `./sonar resume RUN_ID` with the same state directory. It checks the saved task snapshots, grader, execution code, Harbor version, Docker platform and pinned images. Committed trials are reused, including scored failures and timeouts. Start a fresh run when the intended conditions change.
5. **Verify the result.** Reconcile the planned count with the four outcomes in `summary.json`. For a surprising score, follow the trial's `harbor_result` to the verifier output and agent trace. Check the model ID in the provider response when available. Report the exact combination, coverage, pass rate, error and timeout counts, and paths to the frozen plan, summary and run report. A completed run can contain failed or ungraded attempts.

## Preserving experiment integrity

- Start formal evaluations on request. Keep persisted formal history in `.sonar/runs/`. Use a separate `--state` for development fixtures and validation runs. The project-local Infron credential stays at `.sonar/credentials/infron-api-key`.
- Build the agent CLI, task software and public inputs into the images. Keep hidden verifier inputs and known-correct solutions outside the agent's build context. Use `solution/` to validate a task before publishing it.
- For rubric tasks, keep the case packet, grading anchors, numeric weights and pass threshold in sync with the assignment. Pin the separate verifier with its task-specific rubric and the Infron judge. Validate artifact handoff and scoring in an isolated state. Preserve per-criterion evidence and distinguish provider failure from a scored submission.
- Treat a saved plan, its task snapshots and committed results as experiment evidence. Apply changes to the source matrix, task or implementation. Regenerate derived pages with `./sonar report`. The report and catalog must remain usable offline.
- Compare one variable at a time when attributing a change to an agent or model. Preserve the exact model ID, provider endpoint, agent version, inference settings and time budgets. Check the frozen agent deadline separately from the whole-trial timeout. A `null` inference field means the client or provider chooses the value. Use Sonar's reported delta for matching conditions.

## Where changes belong

| Change | Source and verification |
| --- | --- |
| Matrix or inference option | Start with `configs/ollama.json` or `configs/infron.json`. Keep public validation shared by the catalog, `doctor` and `run` in `sonar_eval/config.py`. Provider routing and parameter support live in `providers.py` and `tuning.py` under `sonar_eval/`. |
| Agent release or preset | Update the npm package and lockfile in `docker/agents/`. Preset names and executables live in `sonar_eval/native.py`. Rebuild affected images, then use `doctor` to verify the version the container actually supplies. |
| Task or suite | Keep each task self-contained under `suites/datasets/<suite>/<task>/`. Register it in `suites/all-tasks.json` and its suite in `suites/domains.json`. Check the starting submission and the known-correct submission with the verifier. Rebuild changed environments and align the catalog counts with the manifest. |
| Run persistence or reporting | `runner.py` and `execution.py` under `sonar_eval/` own plans, attempts and resumption. `grading.py` interprets Harbor rewards. `history.py` derives family trends, `rankings.py` compares measured combinations, and `reporting.py` links these to the catalog and run evidence. Preserve the ability to read existing runs. |

Run `python3 -m unittest discover -s tests -v` after behavioral changes. For report changes, also rebuild a report with `./sonar report --state PATH` and check the affected navigation and evidence links. For documentation changes, verify the documented commands against `./sonar --help` and the relevant subcommand help.
