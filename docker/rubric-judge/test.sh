#!/bin/sh
set -eu
exec python3 -I /opt/sonar/judge.py "$(dirname "$0")/rubric.json"
