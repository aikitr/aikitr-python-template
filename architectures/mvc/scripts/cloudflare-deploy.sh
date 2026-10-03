#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MVC_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
. "$SCRIPT_DIR/ensure-uv.sh"

cd "$MVC_ROOT"
uv run pywrangler d1 migrations apply aikitr-mvc-tasks --remote
uv run pywrangler deploy
