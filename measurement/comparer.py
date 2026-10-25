import os
import json
from datetime import datetime
from config import (
    AS_FOLDER_MAP
)


print("-----Starting Comparer-----")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the base directory (../Data from the script)
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "Data"))
CURRENTLY_DIR = os.path.join(BASE_DIR, "Currently")
HISTORY_SHOWPATHS_DIR = os.path.join(BASE_DIR, "History", "Showpaths")
COMPARER_DIR = os.path.join(BASE_DIR, "History", "Comparer")
LOG_DIR = os.path.join(BASE_DIR, "Logs", "Comparer")

os.makedirs(CURRENTLY_DIR, exist_ok=True)
os.makedirs(COMPARER_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def normalize_as(as_str):
    return as_str.replace(":", "_")

def load_json(filepath):
    if not os.path.isfile(filepath):
        return {}
    with open(filepath, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def extract_valid_paths(path_data):
    if not path_data or "paths" not in path_data:
        return []
    return [p for p in path_data["paths"] if p.get("status") != "timeout"]

def extract_fingerprint_map(paths):
    return {
        p["fingerprint"]: p.get("sequence", "unknown_sequence")
        for p in paths
    }

def compare_paths(ia):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
    filename_base = normalize_as(ia)
    delta_filename = f"delta_{timestamp}_{filename_base}.json"

    #Load latest file from Currently/
    current_files = [f for f in os.listdir(CURRENTLY_DIR) if f.endswith(f"_{filename_base}.json")]
    if not current_files:
        print(f"[ERROR] No current file found for {ia}")
        return
    latest_file = os.path.join(CURRENTLY_DIR, current_files[0])
    latest_data = load_json(latest_file)

    #Load history file from Showpaths/AS-X/
    as_folder = AS_FOLDER_MAP.get(ia, "UNKNOWN_AS")
    history_dir = os.path.join(HISTORY_SHOWPATHS_DIR, as_folder)
    os.makedirs(history_dir, exist_ok=True)

    history_files = [f for f in os.listdir(history_dir) if f.endswith(f"_{filename_base}.json")]
    history_file = os.path.join(history_dir, history_files[0]) if history_files else None
    history_data = load_json(history_file) if history_file else {}

    #Extract paths and fingerprint maps (ignoring timeouts)
    valid_latest_paths = extract_valid_paths(latest_data)
    valid_history_paths = extract_valid_paths(history_data)

    latest_fps_map = extract_fingerprint_map(valid_latest_paths)
    history_fps_map = extract_fingerprint_map(valid_history_paths)

    latest_fps = set(latest_fps_map.keys())
    history_fps = set(history_fps_map.keys())

    #Compare sets
    added = sorted(latest_fps - history_fps)
    removed = sorted(history_fps - latest_fps)

    changes = []
    for fp in added:
        changes.append({
            "fingerprint": fp,
            "sequence": latest_fps_map.get(fp, "unknown"),
            "change": "added"
        })

    for fp in removed:
        changes.append({
            "fingerprint": fp,
            "sequence": history_fps_map.get(fp, "unknown"),
            "change": "removed"
        })

    #Change status
    if added or removed:
        change_status = "change_detected"
    elif not latest_fps and not history_fps:
        change_status = "no_paths_present"
    elif not latest_fps:
        change_status = "all_paths_lost"
    elif not history_fps:
        change_status = "all_paths_new"
    else:
        change_status = "no_change"

    output = {
        "timestamp": timestamp,
        "source": latest_data.get("local_isd_as", "unknown"),
        "destination": latest_data.get("destination", ia),
        "change_status": change_status,
        "changes": changes
    }

    #Save delta file
    comparer_sub_dir = os.path.join(COMPARER_DIR, as_folder)
    os.makedirs(comparer_sub_dir, exist_ok=True)
    delta_path = os.path.join(comparer_sub_dir, delta_filename)
    with open(delta_path, "w") as f:
        json.dump(output, f, indent=2)

    #Logging
    log_file = os.path.join(LOG_DIR, f"log_compare_{filename_base}.txt")
    with open(log_file, "a") as log:
        log.write(f"\n[{timestamp}] Compare run for AS {ia}:\n")
        log.write(f"Status: {change_status}\n")
        if not changes:
            log.write("No changes detected.\n")
        else:
            for change in changes:
                log.write(f"- {change['change'].upper()}: {change['fingerprint']} | {change['sequence']}\n")

    #Console output
    print(f"[COMPARE] {ia}: {change_status} ({len(added)} added, {len(removed)} removed)")
    for change in changes:
        print(f"    {change['change'].upper()}: {change['fingerprint']} | {change['sequence']}")

    return delta_path

if __name__ == "__main__":
    for ia in AS_FOLDER_MAP:
        compare_paths(ia)

print("-----Comparer Done-----")
