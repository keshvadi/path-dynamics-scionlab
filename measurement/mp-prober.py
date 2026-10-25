import os
import json
import subprocess
import random
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import AS_TARGETS

print("-----Starting MP-Prober-----")

# Setup directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "Data"))
CURRENTLY_DIR = os.path.join(BASE_DIR, "Currently")
BASE_PROBER_DIR = os.path.join(BASE_DIR, "History", "MP-Prober")
LOG_DIR = os.path.join(BASE_DIR, "Logs", "MP-Prober")

os.makedirs(BASE_PROBER_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def normalize_as(as_str):
    return as_str.replace(":", "_")

def load_current_paths(as_str):
    filename_base = normalize_as(as_str)
    for f in os.listdir(CURRENTLY_DIR):
        if f.endswith(f"_{filename_base}.json"):
            with open(os.path.join(CURRENTLY_DIR, f), "r") as file:
                try:
                    return json.load(file)
                except json.JSONDecodeError:
                    return {}
    return {}

def run_scion_ping(ia, ip_target, sequence):
    """Run one scion ping and timestamp its duration."""
    start = time.time()
    try:
        result = subprocess.run(
            ["scion", "ping", f"{ia},{ip_target}", "--format", "json", "-c", "15", "--sequence", sequence],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        end = time.time()
        if result.returncode != 0:
            return {
                "sequence": sequence,
                "error": f"ping failed: {result.stderr.strip()}",
                "duration": round(end - start, 2)
            }
        return {
            "sequence": sequence,
            "ping_result": json.loads(result.stdout),
            "duration": round(end - start, 2)
        }
    except Exception as e:
        return {"sequence": sequence, "error": str(e), "duration": round(time.time() - start, 2)}

def probe_mp_paths(ia, ip_target, as_folder):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
    filename_base = normalize_as(ia)

    output_dir = os.path.join(BASE_PROBER_DIR, as_folder)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"mp-prober_{timestamp}_{filename_base}.json")
    log_path = os.path.join(LOG_DIR, f"log_mp-prober_{filename_base}.txt")

    # Seed random for more true randomness
    random.seed(time.time())

    # Prepare logging
    with open(log_path, "a") as log_file:
        log_file.write(f"\n[{timestamp}] Starting multipath probe for {ia} ({as_folder})\n")

        path_data = load_current_paths(ia)
        all_paths = [p for p in path_data.get("paths", []) if p.get("status", "").lower() != "timeout"]

        if len(all_paths) < 2:
            print("Not enough paths found for mp probe")
            log_file.write("Not enough usable paths found. Skipping.\n")
            with open(output_path, "w") as f:
                json.dump({
                    "timestamp": timestamp,
                    "ia": ia,
                    "ip": ip_target,
                    "note": "Insufficient paths for multipath probing",
                    "probes": []
                }, f, indent=2)
            return

        num_paths = min(3, len(all_paths))
        selected_paths = random.sample(all_paths, num_paths)

        log_file.write(f"Selected {num_paths} paths for parallel probing.\n")
        for p in selected_paths:
            log_file.write(f"  -> {p.get('fingerprint')} | {p.get('sequence')}\n")

        # Parallel probing
        results = []
        with ThreadPoolExecutor(max_workers=num_paths) as executor:
            futures = {
                executor.submit(run_scion_ping, ia, ip_target, p["sequence"]): p
                for p in selected_paths
            }

            for future in as_completed(futures):
                path = futures[future]
                fingerprint = path.get("fingerprint")
                sequence = path.get("sequence")

                try:
                    result = future.result()
                    result["fingerprint"] = fingerprint
                    log_file.write(f"[RESULT] {fingerprint} | {sequence} | duration: {result.get('duration')}s\n")
                    results.append(result)
                except Exception as e:
                    printf("[ERROR] Failed to run thread for {sequence}")
                    log_file.write(f"[ERROR] Failed to run thread for {sequence}: {e}\n")
                    results.append({
                        "sequence": sequence,
                        "fingerprint": fingerprint,
                        "error": str(e)
                    })

    # Save output
    output_json = {
        "timestamp": timestamp,
        "ia": ia,
        "ip": ip_target,
        "probes": results
    }
    with open(output_path, "w") as f:
        json.dump(output_json, f, indent=2)

    print(f"[DONE] MP probe for {ia} complete. Results at {output_path}")

if __name__ == "__main__":
    for ia, (ip, folder) in AS_TARGETS.items():
        probe_mp_paths(ia, ip, folder)

print("-----MP-Probe Done-----")
