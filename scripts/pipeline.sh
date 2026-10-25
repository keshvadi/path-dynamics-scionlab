#!/bin/bash
set -euo pipefail

# Set working paths relative to repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
PY_DIR="$REPO_ROOT/PythonTests"
DATA_DIR="$REPO_ROOT/Data"
CURRENTLY="$DATA_DIR/Currently"
HISTORY="$DATA_DIR/History"
ARCHIVE="$DATA_DIR/Archive"
LOG="$DATA_DIR/Logs/pipeline.log"

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
archive_day=$(date +"%Y-%m-%d")
ARCHIVE_DAY_DIR="$ARCHIVE/$archive_day"

mkdir -p "$ARCHIVE_DAY_DIR"

echo "[$timestamp] Starting pipeline..." >> "$LOG"

# Step 1: Run scripts, add more here in correct order
/usr/bin/python3 "$PY_DIR/pathdiscovery_scion.py" >> "$LOG"
/usr/bin/python3 "$PY_DIR/comparer.py" >> "$LOG"
/usr/bin/python3 "$PY_DIR/prober_scion.py" >> "$LOG"
/usr/bin/python3 "$PY_DIR/mp-prober.py" >> "$LOG"
/usr/bin/python3 "$PY_DIR/tr_collector_scion.py" >> "$LOG"
#/usr/bin/python3 "$PY_DIR/bw_collector_scion.py" >> "$LOG"
/usr/bin/python3 "$PY_DIR/bw_alldiscover_path.py" >> "$LOG"
/usr/bin/python3 "$PY_DIR/bw_multipath.py" >> "$LOG"
#/usr/bin/python3 "$PY_DIR/transform_csv.py" >> "$LOG"

# Step 2: Move files from all History/<Tool>/AS-* into Archive/<date>/
for tool_dir in "$HISTORY"/*/; do
  find "$tool_dir" -type f -name '*.json' -print -exec mv {} "$ARCHIVE_DAY_DIR"/ \;
done

# Step 3: Move current path files to the appropriate History subdirs
if compgen -G "$CURRENTLY/*.json" > /dev/null; then
  for pathfile in "$CURRENTLY"/*.json; do
    # Extract IA/AS identifier from filename (assuming name format e.g. "AS-1*.json")
    filename=$(basename "$pathfile")
    as_dir="${filename%%_*.json}"  # e.g., "AS-1"

    # Choose a destination (e.g., for pathdiscovery, change as needed)
    dest_dir="$HISTORY/Showpaths/$as_dir"
    mkdir -p "$dest_dir"
    mv "$pathfile" "$dest_dir/"
    echo "Moved $filename to $dest_dir" >> "$LOG"
  done
else
  echo "No current path files found in $CURRENTLY" >> "$LOG"
fi

end_ts=$(date +"%Y-%m-%d %H:%M:%S")
echo "[$end_ts] Pipeline complete." >> "$LOG"
echo "" >> "$LOG"

