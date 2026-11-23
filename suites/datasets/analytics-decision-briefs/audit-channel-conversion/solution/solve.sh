#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
A leads overall at 92/120 versus 34/120 because its mix contains far more returning users. Within strata B leads 95% to 90% and 15% to 10%. Equal weighting gives 55% for B and 50% for A. Pilot a stratified allocation next month before shifting all traffic, and report uncertainty alongside each stratum.
SONAR_EXAMPLE
