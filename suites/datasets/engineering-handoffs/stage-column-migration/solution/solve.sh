#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
Add nullable preferred_name, deploy compatibility writes and read the new field with a legacy fallback. Backfill only unset destinations from nonnull legacy values in restartable batches and retain deliberate nulls. Observe mismatches and client versions throughout the seven days. Keep the legacy field writable for rollback until old traffic and verified mismatches reach the agreed gate.
SONAR_EXAMPLE
