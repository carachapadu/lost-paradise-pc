#!/usr/bin/env bash
# inFAMOUS Second Son launcher (pt_BR/en_US): game folder, languages, video, Play.
exec python3 "$(dirname -- "$(readlink -f -- "$0")")/port/launcher/infamous_launcher.py" "$@"
