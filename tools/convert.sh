#!/usr/bin/env bash
# Regenerate the engine's JSON config files from the legacy vegastrike.config.
#
# Usage: tools/convert.sh UPSTREAM_ASSETS_DIR [ENGINE_SOURCE_DIR]
#   UPSTREAM_ASSETS_DIR  vegastrike/Assets-Production checkout, for the base
#                        vegastrike.config and starting JSON files
#   ENGINE_SOURCE_DIR    engine checkout the game targets (default: engine/)
set -euo pipefail

if [ $# -lt 1 ] || [ $# -gt 2 ]; then
    sed -n '2,7p' "$0"
    exit 1
fi
here=$(cd "$(dirname "$0")" && pwd)
game=$(dirname "$here")
assets=$1
engine=${2:-$game/engine}

python3 "$here/config_to_json.py" \
    "$assets/vegastrike.config" "$game/vegastrike.config" \
    "$engine/engine/src/configuration/configuration.cpp" \
    "$assets/config.json" "$game/config.json" "$here/config_report.txt"

python3 - "$game/config.json" "$here/overrides.json" <<'PY'
import json, sys

def merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            merge(dst[k], v)
        else:
            dst[k] = v

path, overrides = sys.argv[1:]
with open(path) as f:
    config = json.load(f)
with open(overrides) as f:
    merge(config, json.load(f))
with open(path, 'w') as f:
    json.dump(config, f, indent=4)
    f.write('\n')
PY

python3 "$here/bindings_to_json.py" "$game/vegastrike.config" "$assets/bindings.json" "$game/bindings.json"
python3 "$here/theme_to_json.py" "$game/vegastrike.config" "$assets/theme.json" "$game/theme.json"
cp "$assets/engine.json" "$assets/controls.json" "$game/"
echo "Wrote config.json, bindings.json, theme.json; copied engine.json, controls.json"
