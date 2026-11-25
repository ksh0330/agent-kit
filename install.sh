#!/bin/sh
# agent-kit installer (POSIX). Preview by default; pass --apply to write.
# Usage: ./install.sh [--target DIR] [--skills-dir PATH] [--docs-dir PATH] [--no-guard] [--apply]
set -eu
KIT_HOME=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for runtime in python3 python; do
  if command -v "$runtime" >/dev/null 2>&1 &&
     "$runtime" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    PYTHONPATH="$KIT_HOME"
    export PYTHONPATH
    exec "$runtime" -m agentkit install "$@"
  fi
done
echo "agent-kit: Python 3.10+ not found on PATH; nothing was installed." >&2
exit 2
