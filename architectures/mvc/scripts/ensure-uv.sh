#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MVC_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
CLOUDFLARE_UV_DIR="$MVC_ROOT/.cloudflare-tools"
CLOUDFLARE_UV_BIN="$CLOUDFLARE_UV_DIR/uv"

if [ ! -x "$CLOUDFLARE_UV_BIN" ]; then
    mkdir -p "$CLOUDFLARE_UV_DIR"
    curl -LsSf https://astral.sh/uv/0.12.6/install.sh \
        | env UV_INSTALL_DIR="$CLOUDFLARE_UV_DIR" UV_NO_MODIFY_PATH=1 sh
fi

CLOUDFLARE_UV_VERSION=$("$CLOUDFLARE_UV_BIN" --version)
case "$CLOUDFLARE_UV_VERSION" in
    "uv 0.12.6"*) ;;
    *)
        echo "Expected uv 0.12.6 in $CLOUDFLARE_UV_DIR, found: $CLOUDFLARE_UV_VERSION" >&2
        exit 1
        ;;
esac

PATH="$CLOUDFLARE_UV_DIR:$PATH"
export PATH
