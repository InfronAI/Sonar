#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
Sales rose 10%, yet margin fell from 30% to 27%. The $30k volume contribution was outweighed by $22k of mix and $11k of freight, taking profit down $3k to $297k. Reversing only the identified disruption would add $6k, subject to invoice confirmation. Commercial finance should reconcile product volumes and procurement should trace the remaining $5k before revising the forecast.
SONAR_EXAMPLE
