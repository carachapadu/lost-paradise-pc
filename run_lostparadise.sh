#!/usr/bin/env bash
# Runs Lost Paradise from a terminal: TLG_GAME_DIR=/path/to/CUSA12781 ./run_lostparadise.sh
export TLG_SKIP_LINK_LIBC=1
exec "$(dirname -- "$(readlink -f -- "$0")")/port/run.sh" "$@"
