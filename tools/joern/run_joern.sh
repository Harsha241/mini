#!/usr/bin/env bash
set -euo pipefail

# Joern CPG generation script
# Usage:
#   tools/joern/run_joern.sh /path/to/repo [OUT_DIR]
# Outputs:
#   - CPG file under OUT_DIR (default: tools/joern/out)
#   - Neo4j CSV export under OUT_DIR/neo4j_csvs when used with export script

REPO_PATH=${1:-}
OUT_DIR=${2:-"$(dirname "$0")/out"}

if [[ -z "$REPO_PATH" ]]; then
  echo "ERROR: Missing repo path. Usage: $0 /path/to/repo [OUT_DIR]" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"

# Detect joern
if command -v joern-parse >/dev/null 2>&1; then
  JOERN_PARSE=joern-parse
elif [[ -x "${JOERN_HOME:-}/joern-parse" ]]; then
  JOERN_PARSE="${JOERN_HOME}/joern-parse"
else
  echo "ERROR: joern-parse not found. Install Joern and ensure it is on PATH or set JOERN_HOME." >&2
  echo "See: https://joern.io/ (requires Java)." >&2
  exit 3
fi

CPG_PATH="$OUT_DIR/repo.cpg.bin"

echo "[joern] Parsing repo at $REPO_PATH → $CPG_PATH"
"$JOERN_PARSE" "$REPO_PATH" --output "$CPG_PATH" || {
  echo "ERROR: joern-parse failed. Check Joern version and repo size/memory." >&2
  exit 4
}

echo "[joern] Done. CPG at: $CPG_PATH"
echo "$CPG_PATH" > "$OUT_DIR/.latest_cpg_path"



