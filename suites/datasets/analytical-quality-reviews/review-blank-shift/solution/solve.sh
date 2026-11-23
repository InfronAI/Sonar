#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
After matching blank subtraction A is 0.48 and B 0.45. B's blank exceeds 0.06. The close duplicates support short-term precision but do not validate the baseline. Hold the comparison pending review of B's blank identity and a repeat quality check. Record the corrected provisional values and remove the claim that B is higher.
SONAR_EXAMPLE
