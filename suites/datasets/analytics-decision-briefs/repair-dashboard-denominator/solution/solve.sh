#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
Keep opens and closes as throughput and reconcile backlog including reopen events. Of 130 closures, 85 belonged to week-12 opens. That does not establish seven-day durable resolution. Cohort by opening timestamp and count unique tickets resolved and still closed at day seven, after all have matured. Publish both metrics in parallel and ask operations to reconcile event histories, including the 15 reopens.
SONAR_EXAMPLE
