import os
import subprocess
import json
import re
import time
from datetime import datetime
from math import ceil
from config import (
    BWTEST_SERVERS
)
# Bandwidth tiers in Mbps
TARGET_MBPS = [5, 10, 50, 100]

# Parameters
DURATION = 3  # seconds
PACKET_SIZE = 1000  # bytes

# Directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the base directory (../Data from the script)
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "Data"))
RESULT_DIR = os.path.join(BASE_DIR, "History", "Bandwidth")
LOG_DIR = os.path.join(BASE_DIR, "Logs", "Bandwidth")
os.makedirs(LOG_DIR, exist_ok=True)

def normalize_as(as_str):
    return as_str.replace(":", "_")

def parse_output(text):
    result = {
        "S->C results": {},
        "C->S results": {},
        "invalid_format": False
    }

    if "S->C results" not in text or "C->S results" not in text:
        result["invalid_format"] = True
        result["raw_output"] = text.strip()
        return result

    try:
        sections = text.split("C->S results")
        sc_block = sections[0].split("S->C results")[-1].strip()
        cs_block = sections[1].strip()
    except Exception as e:
        result["invalid_format"] = True
        result["raw_output"] = text.strip()
        result["error"] = f"Split failed: {e}"
        return result

    def extract_metrics(block):
        return {
            "attempted_bps": _match(r"Attempted bandwidth:\s+(.+)", block),
            "achieved_bps": _match(r"Achieved bandwidth:\s+(.+)", block),
            "loss_rate": _match(r"Loss rate:\s+(.+)", block),
            "interarrival time min/avg/max/mdev": _match(r"Interarrival time.*?=\s+(.+)", block)
        }

    def _match(pattern, text):
        match = re.search(pattern, text)
        return match.group(1) if match else None

    result["S->C results"] = extract_metrics(sc_block)
    result["C->S results"] = extract_metrics(cs_block)

    return result

def run_bwtest(ia, ip, folder, target_mbps):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
    tier_label = f"{target_mbps}Mbps"
    filename = f"BW_{timestamp}_AS_{normalize_as(ia)}_{tier_label}.json"
    log_filename = f"BW_AS_{normalize_as(ia)}.txt"
    log_path = os.path.join(LOG_DIR, log_filename)

    output_dir = os.path.join(RESULT_DIR, folder)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    bps_target = int(target_mbps * 1_000_000)
    packet_count = ceil(bps_target * DURATION / (PACKET_SIZE * 8))

    cmd = [
        "scion-bwtestclient",
        "-s", f"{ia},[{ip}]:30100",
        "-cs", f"{DURATION},{PACKET_SIZE},{packet_count},?",
        "-sc", f"{DURATION},{PACKET_SIZE},{packet_count},?"
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=30  
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        all_output = stdout + "\n" + stderr
        
        # Detect no-path case
        if "Fatal: no path to" in all_output:
            entry = {
                "timestamp": timestamp,
                "target": {
                    "tier_mbps": target_mbps,
                    "duration_sec": DURATION,
                    "packet_size_bytes": PACKET_SIZE,
                    "packet_count": packet_count
                },
                "target_server": {
                    "ia": ia,
                    "ip": ip
                },
                "command": " ".join(cmd),
                "error_type": "no_path_error",
                "raw_output": all_output,
                "return_code": result.returncode
            }

            with open(output_path, "w") as f:
                json.dump(entry, f, indent=2)

            with open(log_path, "a") as log_file:
                print(f"[NO PATH] {ia} at {tier_label}")
                log_file.write(f"[NO PATH] {timestamp} {tier_label} - No path to destination.\n")
            return

        # Parse valid results
        structured_output = parse_output(stdout)

        entry = {
            "timestamp": timestamp,
            "target": {
                "tier_mbps": target_mbps,
                "duration_sec": DURATION,
                "packet_size_bytes": PACKET_SIZE,
                "packet_count": packet_count
            },
            "target_server": {
                "ia": ia,
                "ip": ip
            },
            "command": " ".join(cmd),
            "result": structured_output,
            "stderr": stderr,
            "return_code": result.returncode
        }

        with open(output_path, "w") as f:
            json.dump(entry, f, indent=2)

        with open(log_path, "a") as log_file:
            if structured_output.get("invalid_format", False):
                print(f"[INVALID FORMAT] {ia} at {tier_label}")
                log_file.write(f"[INVALID FORMAT] {timestamp} {tier_label} - Unexpected output format.\n")
            elif result.returncode == 0:
                print(f"[OK] {ia} at {tier_label}")
                log_file.write(f"[SUCCESS] {timestamp} {tier_label}\n")
            else:
                print(f"[ERROR] Failed {ia} at {tier_label}")
                log_file.write(f"[ERROR] {timestamp} {tier_label}: {stderr}\n")

    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {ia} at {tier_label}")
        with open(log_path, "a") as log_file:
            log_file.write(f"[TIMEOUT] {timestamp} {tier_label} - Command timed out after 30s.\n")
    except Exception as e:
        print(f"[EXCEPTION] {ia} at {tier_label}: {e}")
        with open(log_path, "a") as log_file:
            log_file.write(f"[EXCEPTION] {timestamp} {tier_label}: {e}\n")

# Main execution
if __name__ == "__main__":
    global_start = time.time()

    for ia, (ip, folder) in BWTEST_SERVERS.items():
        for mbps in TARGET_MBPS:
            run_bwtest(ia, ip, folder, mbps)

    global_end = time.time()
    elapsed = global_end - global_start

    duration_log = os.path.join(LOG_DIR, "script_duration.log")
    with open(duration_log, "a") as f:
        f.write(f"{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')} - Total execution time: {elapsed:.2f} seconds\n")

    print(f"\n[LOG] Total execution time: {elapsed:.2f} seconds")
