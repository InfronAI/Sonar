#!/bin/sh
set -eu
cat > submission.md <<'SONAR_EXAMPLE'
A behaves like a constant offset, B like a 1.06 scale factor. Near 8 N their raw difference is about 0.28 N, larger than the allowed 0.15 N. Correct both against references, repeat independent points bracketing 8 N and estimate the spread of paired differences. Hold comparative measurements until residual disagreement and its uncertainty fit the tolerance.
SONAR_EXAMPLE
