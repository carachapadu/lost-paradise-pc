#!/usr/bin/env bash
# Runs inFAMOUS Second Son from a terminal with the launcher settings: ./run_infamous.sh [seconds]
exec python3 "$(dirname -- "$(readlink -f -- "$0")")/port/launcher/infamous_run.py" "$@"
