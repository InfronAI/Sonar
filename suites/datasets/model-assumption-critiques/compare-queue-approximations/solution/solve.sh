#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
The formula gives 0.5 hours in system, not an observed queue wait. Fifteen arrivals in the last hour and a break reduce the relevance of average capacity. Record timestamps, service durations and break coverage. Pilot relief during the busy hour and compare tail waits with a piecewise model before fixing the roster.
SONAR_EXAMPLE
