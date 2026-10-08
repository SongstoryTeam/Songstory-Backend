#!/usr/bin/env bash
set -o errexit -o nounset -o pipefail

LUCIDE_VERSION="0.383.0"
ESBUILD_VERSION="0.25.0"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

pascal() {
    awk -F- '{ out = ""; for (i = 1; i <= NF; i++) out = out toupper(substr($i, 1, 1)) substr($i, 2); print out }'
}

names=$(grep -v '^\s*$' "$ROOT/tools/icons.txt" | pascal | paste -sd, -)

cat > "$WORKDIR/entry.js" <<JS
import { createIcons, ${names//,/, } } from 'lucide';

const icons = { ${names//,/, } };

window.lucide = {
    createIcons: (options = {}) => createIcons({ icons, ...options }),
};
JS

cd "$WORKDIR"
npm init -y >/dev/null
npm install --silent --no-audit --no-fund "lucide@${LUCIDE_VERSION}" "esbuild@${ESBUILD_VERSION}"
npx esbuild entry.js --bundle --minify --format=iife --target=es2019 --outfile="$ROOT/static/vendor/lucide.min.js"
