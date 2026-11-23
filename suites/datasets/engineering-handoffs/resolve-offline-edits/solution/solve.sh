#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
Version edits at the server and retain per-field changes. Apply the rename and priority independently. For concurrent titles preserve both versions and ask the user to choose, showing the conflict source. Keep a tombstone that rejects older edits until an explicit restore. Test reordered and duplicate deliveries so neither priority loss nor silent resurrection can recur.
SONAR_EXAMPLE
