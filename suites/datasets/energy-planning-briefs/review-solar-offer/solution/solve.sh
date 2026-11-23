#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
The base estimate saves $1,675 annually. At 45 MWh self-use, export credit rises to $1,925 but import savings fall to $5,850, leaving a $225 loss. Condition approval on interval-meter evidence of overlap and clear allocation of curtailment and escalation. Negotiate a volume or price protection if the lower-use scenario is credible.
SONAR_EXAMPLE
