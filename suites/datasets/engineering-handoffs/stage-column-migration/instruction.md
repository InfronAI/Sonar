# Plan a compatible column migration

Write an implementation handoff for a database field transition during a rolling client release.

## Case packet

Old clients read and write display_name. New clients need preferred_name. Fleet rollout takes seven days. Historical rows contain 8% null display names. Rollback restores old clients. The team can add nullable columns without downtime and run a resumable backfill.

## Submission

Write your response in English to `/app/submission.md` as plain UTF-8 Markdown (up to 16 KiB). Address the decision-maker, support your reasoning with the supplied facts and identify material uncertainty. Use only this fictional case packet. A rubric judge evaluates the content of the submitted file.
