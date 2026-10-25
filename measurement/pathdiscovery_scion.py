import os
import json
import subprocess
from datetime import datetime
from config import (
    AS_FOLDER_MAP
)


print("-----Starting Pathdiscovery-----")
# Directory structure
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the base directory (../Data from the script)
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "Data"))
HISTORY_BASE = os.path.join(BASE_DIR, "History", "Showpaths")
CURRENTLY_DIR = os.path.join(BASE_DIR, "Currently")
LOG_DIR = os.path.join(BASE_DIR, "Logs", "Showpaths")

# Ensure required directories exist
os.makedirs(HISTORY_BASE, exist_ok=True)
os.makedirs(CURRENTLY_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Normalize AS for filenames
def normalize_as(as_str):
    return as_str.replace(":", "_")

# Execute scion showpaths and save outputs
def discover_paths(ia):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
    filename_base = normalize_as(ia)
    as_folder = AS_FOLDER_MAP.get(ia, "UNKNOWN_AS")

    # Paths
    history_dir = os.path.join(HISTORY_BASE, as_folder)
    os.makedirs(history_dir, exist_ok=True)

    history_file = os.path.join(history_dir, f"{as_folder}_{timestamp}_{filename_base}.json")
    latest_file = os.path.join(CURRENTLY_DIR, f"{as_folder}_{timestamp}_{filename_base}.json")
    log_file = os.path.join(LOG_DIR, f"SP_AS_{filename_base}.log")

    # Run scion command
    result = subprocess.run(
        ["scion", "showpaths", ia, "--format", "json", "-m", "40", "-e"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if result.returncode != 0:
        print(f"[ERROR] Failed for {ia}: {result.stderr}")
        with open(log_file, "a") as f:
            f.write(f"[ERROR] {timestamp} - AS {ia} : {result.stderr}\n")
        return

    try:
        json_data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"[ERROR] Invalid JSON output for {ia}")
        with open(log_file, "a") as f:
            f.write(f"[ERROR] Invalid JSON output for {ia} at {timestamp}\n")
        return


    # Save to "currently"
    with open(latest_file, "w") as f:
        json.dump(json_data, f, indent=2)

    print(f"[OK] Saved paths to {latest_file}")
    with open(log_file, "a") as f:
        f.write(f"[SUCCESS] {timestamp} - AS {ia}\n")

if __name__ == "__main__":
    for ia in AS_FOLDER_MAP:
        discover_paths(ia)


print("-----Pathdiscovery Done-----")
