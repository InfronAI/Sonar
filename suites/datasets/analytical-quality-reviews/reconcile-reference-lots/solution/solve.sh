#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
The means exceed their assigned values by 0.5 and 0.4 units. Service and lot changed together, so the raw 1.9 shift cannot identify instrument drift. Interleave the three old units with repeated new units on the same day, recording lot and order. The supervisor should predefine an allowable adjusted difference and flag the boundary until the bridge and its uncertainty meet it.
SONAR_EXAMPLE
