# Task and scoring revisions

## All tasks v5

Adds two multi-step tasks in agent-workflows. The SQL task records its initial and repaired submissions and grades the final query. The scanner scheduling task verifies the initial booking and the updated calendar, with equal weight for both steps. The v4 manifest keeps the original 100 tasks and remains the default evaluation suite.

## Quick 14 v1

Fixes one v4 task in each of 14 domains for routine comparisons. Eight have deterministic verifiers and six use the Infron rubric judge. Task selection is frozen in quick-14.json. It was drawn in domain round-robin order using the seed `sonar-v4-example`.

## Harbor reward interpretation

The grader now checks exceptions on individual steps and honors Harbor's explicit reward validity. A verifier timeout within a step can leave a numeric aggregate from preceding steps. This change records the timeout and withholds that aggregate. Legacy results and their grader digests stay in their frozen runs.

For changes to a task's inputs, verifier, rubric weights or threshold, add the version and reason here when publishing the new suite manifest. Preserve earlier manifests and the trial evidence for previously measured revisions.
