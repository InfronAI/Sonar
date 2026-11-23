# Triage duplicate receipts after a retry change

Write a release-owner memo on an application bug and the smallest credible repair validation.

## Case packet

A receipt service writes a receipt and then acknowledges a job. A retry patch went live at 09:00. Of 1,000 jobs, 18 timed out after a successful write. Logs show 17 duplicate receipts share a job ID and one has no matching trace. The worker fleet can roll back in ten minutes. Existing tests cover first-time delivery only.

## Submission

Write your response in English to `/app/submission.md` as plain UTF-8 Markdown (up to 16 KiB). Address the decision-maker, support your reasoning with the supplied facts and identify material uncertainty. Use only this fictional case packet. A rubric judge evaluates the content of the submitted file.
