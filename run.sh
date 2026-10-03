#!/bin/sh
# Run Gemini Gold on the Vega Strike engine built in the engine/ sub-module.
# Set VEGASTRIKE_ENGINE to use a different engine binary.
here=$(cd "$(dirname "$0")" && pwd)
engine=${VEGASTRIKE_ENGINE:-$here/engine/bin/vegastrike-engine}
exec "$engine" -d"$here" "$@"
