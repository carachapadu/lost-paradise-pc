#!/usr/bin/env bash
# Fist of the North Star: Lost Paradise launcher: game folder, graphics, Play.
exec python3 "$(dirname -- "$(readlink -f -- "$0")")/port/launcher/lostparadise_launcher.py" "$@"
