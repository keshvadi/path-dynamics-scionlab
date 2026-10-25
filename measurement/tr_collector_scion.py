import os
import json
import subprocess
import time
import random
from datetime import datetime
from config import (
    AS_TARGETS
)

# Base directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "Data"))
BASE_TRACEROUTE_DIR = os.path.join(BASE_DIR, "History", "Traceroute")
LOG_DIR = os.path.join(BASE_DIR, "Logs", "Traceroute")
os.makedirs(LOG_DIR, exist_ok=True)

def normalize_as(as_str):
    return as_str.replace(":", "_")

def run_all_traceroutes(ia, ip_target, as_folder):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
    log_filename = f"TR_AS_{normalize_as(ia)}.log"
    log_path = os.path.join(LOG_DIR, log_filename)

    output_dir = os.path.join(BASE_TRACEROUTE_DIR, as_folder)
    os.makedirs(output_dir, exist_ok=True)

    # Get all available paths via scion showpaths
    showpaths_result = subprocess.run(
        ["scion", "showpaths", ia, "--format", "json", "-m", "40"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if showpaths_result.returncode != 0:
        print(f"[ERROR] Failed to get paths for {ia}: {showpaths_result.stderr}")
        with open(log_path, "a") as log_file:
            log_file.write(f"[ERROR] {timestamp} Failed to get paths for {ia}: {showpaths_result.stderr}\n")
        return

    try:
        path_data = json.loads(showpaths_result.stdout)
        paths = path_data.get("paths", [])
    except json.JSONDecodeError:
        print(f"[ERROR] Failed to parse showpaths JSON for {ia}")
        with open(log_path, "a") as log_file:
            log_file.write(f"[ERROR] {timestamp} Invalid JSON from showpaths for {ia}\n")
        return

    if not paths:
        print(f"[WARNING] No paths found for {ia}")
        with open(log_path, "a") as log_file:
            log_file.write(f"[WARNING] No paths found for {ia} at {timestamp}\n")
        return

    original_path_count = len(paths)

    # Select up to 10 random path indexes
    if original_path_count > 10:
        selected_indexes = sorted(random.sample(range(original_path_count), 10))
    else:
        selected_indexes = list(range(original_path_count))

    selected_paths = [paths[i] for i in selected_indexes]

    # Log which full-list indexes were selected
    selected_indexes_str = ", ".join(str(i) for i in selected_indexes)
    print(f"[INFO] {timestamp} - AS {ia}: Selected path indexes from full list: [{selected_indexes_str}]")
    with open(log_path, "a") as log_file:
        log_file.write(f"[INFO] {timestamp} - AS {ia}: Selected path indexes from full list: [{selected_indexes_str}]\n")

    # Run traceroute on each selected path
    for idx_in_list, real_index in enumerate(selected_indexes):
        path = paths[real_index]
        sequence = path.get("sequence")
        if not sequence:
            continue

        hop_count = len(sequence.split())

        traceroute_result = subprocess.run(
            ["scion", "traceroute", f"{ia},{ip_target}", "--format", "json", "--sequence", sequence],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if traceroute_result.returncode != 0:
            print(f"[ERROR] Traceroute failed on path {real_index} for {ia}: {traceroute_result.stderr}")
            with open(log_path, "a") as log_file:
                log_file.write(f"[ERROR] {timestamp} Traceroute failed on path {real_index} for {ia}: {traceroute_result.stderr}\n")
            continue

        try:
            traceroute_data = json.loads(traceroute_result.stdout)
        except json.JSONDecodeError:
            print(f"[ERROR] Failed to parse traceroute JSON for path {real_index} of {ia}")
            with open(log_path, "a") as log_file:
                log_file.write(f"[ERROR] {timestamp} Invalid traceroute JSON for path {real_index} of {ia}\n")
            continue

        traceroute_data["hop_count"] = hop_count
        filename = f"TR_{timestamp}_AS_{normalize_as(ia)}_p_{real_index}.json"
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w") as f:
            json.dump(traceroute_data, f, indent=2)

        print(f"[OK] {timestamp} - AS {ia} TR path {real_index} (hops: {hop_count})")
        with open(log_path, "a") as log_file:
            log_file.write(f"[OK] {timestamp} - AS {ia} TR path {real_index} (hops: {hop_count})\n")


if __name__ == "__main__":
    global_start = time.time()
    global_timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    print("==== START TRACEROUTE TESTING ====")

    for ia, (ip, folder) in AS_TARGETS.items():
        run_all_traceroutes(ia, ip, folder)

    global_end = time.time()
    duration = global_end - global_start
    print("==== END TRACEROUTE TESTING ====")
    print(f"[LOG] Total execution time: {duration:.2f} seconds")

    duration_log_path = os.path.join(LOG_DIR, "script_duration.log")
    with open(duration_log_path, "a") as f:
        f.write(f"{global_timestamp} - Total traceroute script duration: {duration:.2f} seconds\n")
