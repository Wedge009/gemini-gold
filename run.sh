#!/bin/sh
# Run Gemini Gold on the Vega Strike engine built in the engine/ sub-module.
# Set VEGASTRIKE_ENGINE to use a different engine binary.
here=$(cd "$(dirname "$0")" && pwd)
engine=$VEGASTRIKE_ENGINE
if [ -z "$engine" ]; then
    # script/build is meant to copy the binary to engine/bin/, but the presets
    # build into engine/build/<preset>/ and the copy misses it. Use the most
    # recently built preset.
    engine=$here/engine/bin/vegastrike-engine
    [ -x "$engine" ] ||
        engine=$(ls -t "$here"/engine/build/*/vegastrike-engine 2>/dev/null | head -n 1)
fi
if [ ! -x "$engine" ]; then
    echo "run.sh: no engine binary found; build the engine/ sub-module or set VEGASTRIKE_ENGINE" >&2
    exit 1
fi
exec "$engine" -d"$here" "$@"
