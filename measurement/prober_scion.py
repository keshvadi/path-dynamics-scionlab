import os
import json
import subprocess
import random
from datetime import datetime
from config import (
    AS_TARGETS
)

print("-----Starting Prober-----")
# Base directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "Data"))
CURRENTLY_DIR = os.path.join(BASE_DIR, "Currently")
BASE_PROBER_DIR = os.path.join(BASE_DIR, "History", "Prober")
LOG_DIR = os.path.join(BASE_DIR, "Logs", "Prober")

# Ensure directories exist
os.makedirs(BASE_PROBER_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def normalize_as(as_str):
    return as_str.replace(":", "_")

def load_current_paths(as_str):
    filename_base = normalize_as(as_str)
    for f in os.listdir(CURRENTLY_DIR):
        if f.endswith(f"_{filename_base}.json"):
            filepath = os.path.join(CURRENTLY_DIR, f)
            with open(filepath, "r") as file:
                try:
                    return json.load(file)
                except json.JSONDecodeError:
                    return {}
    return {}

def run_scion_ping(ia, ip_target, sequence):
    """Runs scion ping using a given path sequence"""
    try:
        result = subprocess.run(
            ["scion", "ping", f"{ia},{ip_target}", "--format", "json", "-c", "15", "--sequence", sequence],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        if result.returncode != 0:
            return None, f"ping failed: {result.stderr.strip()}"
        return json.loads(result.stdout), None
    except json.JSONDecodeError:
        return None, "invalid JSON in ping output"
    except Exception as e:
        return None, str(e)

def probe_all_paths(ia, ip_target, as_folder):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
    filename_base = normalize_as(ia)
    output_dir = os.path.join(BASE_PROBER_DIR, as_folder)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"prober_{timestamp}_{filename_base}.json")
    log_path = os.path.join(LOG_DIR, f"log_prober_{filename_base}.txt")

    path_data = load_current_paths(ia)
    all_paths = path_data.get("paths", [])

    with open(log_path, "a") as log_file:
        log_file.write(f"\n[{timestamp}] Starting probes for {ia} ({as_folder})\n")

        if not all_paths:
            log_file.write("No paths found in Currently/ directory.\n")
            print(f"[WARNING] No paths found for {ia}. Log created but no json written")
            return

        # Shuffle and select max 15 paths
        random.shuffle(all_paths)
        selected_paths = all_paths[:min(15, len(all_paths))]

        combined_results = {
            "timestamp": timestamp,
            "ia": ia,
            "ip": ip_target,
            "probes": []
        }

        for path in selected_paths:
            sequence = path.get("sequence")
            fingerprint = path.get("fingerprint")
            status = path.get("status")
            if not sequence or not fingerprint:
                log_file.write("Skipping path with missing sequence or fingerprint.\n")
                continue

            if status.lower() == "timeout":
                log_file.write(f"Skipping timed-out path: {fingerprint} | {sequence}\n")
                combined_results["probes"].append({
                    "fingerprint": fingerprint,
                    "sequence": sequence,
                    "status": "skipped",
                    "note": "Skipped probing: path previously timed out"
                })
                continue

            log_file.write(f"Probing path: {fingerprint} | {sequence}\n")
            result, error = run_scion_ping(ia, ip_target, sequence)
            if error:
                log_file.write(f"  [ERROR] {error}\n")
                combined_results["probes"].append({
                    "fingerprint": fingerprint,
                    "sequence": sequence,
                    "error": error
                })
            else:
                log_file.write(f"  [OK] Probe successful.\n")
                combined_results["probes"].append({
                    "fingerprint": fingerprint,
                    "sequence": sequence,
                    "ping_result": result
                })

    with open(output_path, "w") as f:
        json.dump(combined_results, f, indent=2)

    print(f"[DONE] Probing complete for {ia}. Results saved to {output_path}")

if __name__ == "__main__":
    for ia, (ip, folder) in AS_TARGETS.items():
        probe_all_paths(ia, ip, folder)

print("-----Prober Done-----")
