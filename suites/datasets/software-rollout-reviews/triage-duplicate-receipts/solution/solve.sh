#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
Roll back the retry change while preserving job and receipt evidence. A post-write timeout allows redelivery before acknowledgment and explains the 17 matched IDs. Use a unique job ID constraint with receipt creation in one transaction and make redelivery return the existing outcome. Test post-write crashes and concurrent retries. Monitor duplicate receipts per job in a canary and investigate the unmatched receipt separately.
SONAR_EXAMPLE
