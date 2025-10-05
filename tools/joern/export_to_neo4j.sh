#!/usr/bin/env bash
set -euo pipefail

# Export Joern CPG to Neo4j-compatible CSVs
# Usage:
#   tools/joern/export_to_neo4j.sh /path/to/repo.cpg.bin [OUT_DIR]

CPG_PATH=${1:-}
OUT_DIR=${2:-"$(dirname "$0")/out/neo4j_csvs"}

if [[ -z "$CPG_PATH" ]]; then
  echo "ERROR: Missing CPG path. Usage: $0 /path/to/repo.cpg.bin [OUT_DIR]" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"

# Detect joern-export
if command -v joern-export >/dev/null 2>&1; then
  JOERN_EXPORT=joern-export
elif [[ -x "${JOERN_HOME:-}/joern-export" ]]; then
  JOERN_EXPORT="${JOERN_HOME}/joern-export"
else
  echo "ERROR: joern-export not found. Install Joern and ensure it is on PATH or set JOERN_HOME." >&2
  exit 3
fi

echo "[joern] Exporting $CPG_PATH → $OUT_DIR (neo4jcsv)"
set +e
"$JOERN_EXPORT" "$CPG_PATH" --out "$OUT_DIR" --format neo4jcsv --repr all
STATUS=$?
set -e

if [[ $STATUS -ne 0 ]]; then
  echo "[joern] neo4jcsv export failed with status $STATUS. Trying legacy flags..." >&2
  # Some versions expect: --outdir and --format=neo4j-csv
  set +e
  "$JOERN_EXPORT" "$CPG_PATH" --outdir "$OUT_DIR" --format neo4j-csv --repr all
  STATUS=$?
  set -e
  if [[ $STATUS -ne 0 ]]; then
    echo "ERROR: joern-export failed. Check Joern version and flags. See https://joern.io/docs/" >&2
    exit 4
  fi
fi

echo "[joern] Export complete. Files in $OUT_DIR"



