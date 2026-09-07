#!/bin/sh
set -eu

if [ "$#" -eq 0 ]; then
  echo "entrypoint: no command configured" >&2
  exit 64
fi

if [ "${ORES_ENTRYPOINT_LOG_COMMAND:-0}" = "1" ]; then
  printf 'entrypoint: exec %s\n' "$1" >&2
fi

exec "$@"
