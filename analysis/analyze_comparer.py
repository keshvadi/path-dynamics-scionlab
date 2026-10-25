import os
import json
from datetime import datetime
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
from plot_style import FIGSIZE, archive_dir

ARCHIVE_DIR = archive_dir()
COMPARER_PREFIX = "delta_"

def extract_path_features(sequence):
    segments = sequence.split()
    ases = [seg.split('#')[0] for seg in segments if '#' in seg]
    unique_ases = list(dict.fromkeys(ases))
    return {
        "ases": unique_ases,
        "length": len(unique_ases)
    }

def load_comparer_data(archive_dir):
    comparer_data = defaultdict(list)
    for fname in os.listdir(archive_dir):
        if not fname.startswith(COMPARER_PREFIX) or not fname.endswith(".json"):
            continue
        path = os.path.join(archive_dir, fname)
        try:
            with open(path) as f:
                data = json.load(f)
                destination = data.get("destination")
                if destination:
                    comparer_data[destination].append(data)
        except Exception as e:
            print(f"[WARN] Failed to read {fname}: {e}")
    return comparer_data

def analyze_comparer(data_by_ia):
    results = {}
    churn_by_as = defaultdict(int)
    churn_by_length = defaultdict(int)
    lifetime_data_by_ia = defaultdict(list)

    for ia, entries in data_by_ia.items():
        entries_sorted = sorted(entries, key=lambda x: x.get("timestamp", ""))
        total = len(entries_sorted)
        added_total, removed_total, change_events = 0, 0, 0
        path_lengths = []
        last_seen = {}

        for entry in entries_sorted:
            timestamp = entry.get("timestamp")
            ts = None
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M"):
                try:
                    ts = datetime.strptime(timestamp, fmt)
                    break
                except:
                    continue
            if ts is None:
                continue  # skip if no format matched

            if entry.get("change_status") == "change_detected":
                change_events += 1

            for change in entry.get("changes", []):
                change_type = change.get("change")
                if change_type not in {"added", "removed"}:
                    continue

                sequence = change.get("sequence", "")
                features = extract_path_features(sequence)
                path_id = sequence.strip()

                if change_type == "added":
                    added_total += 1
                    last_seen[path_id] = ts
                elif change_type == "removed":
                    removed_total += 1
                    if path_id in last_seen:
                        duration = (ts - last_seen[path_id]).total_seconds()
                        lifetime_data_by_ia[ia].append(duration)
                        del last_seen[path_id]

                path_lengths.append(features["length"])
                churn_by_length[features["length"]] += 1
                for ashop in features["ases"]:
                    churn_by_as[ashop] += 1

        avg_path_length = round(sum(path_lengths) / len(path_lengths), 2) if path_lengths else 0
        lifetimes = lifetime_data_by_ia[ia]
        avg_lifetime = round(sum(lifetimes) / len(lifetimes), 2) if lifetimes else None

        results[ia] = {
            "total_comparisons": total,
            "change_events": change_events,
            "added_paths": added_total,
            "removed_paths": removed_total,
            "avg_path_length_of_changes": avg_path_length,
            "avg_path_lifetime_sec": avg_lifetime
        }

    churn_insights = {
        "churn_by_path_length": dict(sorted(churn_by_length.items())),
        "top_unstable_ases": sorted(churn_by_as.items(), key=lambda x: -x[1])[:10]
    }

    return results, churn_insights

def write_output_to_file(output_lines, filename):
    with open(filename, "w") as f:
        for line in output_lines:
            f.write(line + "\n")

def generate_comparer_plots(data_by_ia):
    output_dir = "comparer_plots"
    os.makedirs(output_dir, exist_ok=True)
    hourly_changes = defaultdict(int)
    hourly_adds = defaultdict(int)
    hourly_removes = defaultdict(int)
    all_lifetimes = []

    for ia, entries in data_by_ia.items():
        entries_sorted = sorted(entries, key=lambda x: x.get("timestamp", ""))
        last_seen = {}

        for entry in entries_sorted:
            ts = None
            timestamp = entry.get("timestamp")
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M"):
                try:
                    ts = datetime.strptime(timestamp, fmt)
                    break
                except:
                    continue
            if not ts:
                continue
            ts_hour = ts.replace(minute=0, second=0)

            if entry.get("change_status") == "change_detected":
                hourly_changes[ts_hour] += 1

            for change in entry.get("changes", []):
                typ = change.get("change")
                seq = change.get("sequence", "").strip()

                if typ == "added":
                    hourly_adds[ts_hour] += 1
                    last_seen[seq] = ts
                elif typ == "removed":
                    hourly_removes[ts_hour] += 1
                    if seq in last_seen:
                        delta = (ts - last_seen[seq]).total_seconds()
                        all_lifetimes.append(delta)

    # Plot 1: Total change events per hour
    hours = sorted(hourly_changes)
    plt.figure(figsize=FIGSIZE)
    plt.plot(hours, [hourly_changes[h] for h in hours], marker='o', label='Total Changes')
    plt.xlabel("Time (Hourly)")
    plt.ylabel("Changes")
    plt.title("Total Path Changes Over Time")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, "plot_path_changes_over_time.pdf"))
    plt.close()

    # Plot 2: Additions vs Removals
    hours = sorted(set(hourly_adds) | set(hourly_removes))
    plt.figure(figsize=FIGSIZE)
    plt.plot(hours, [hourly_adds[h] for h in hours], label='Added Paths', marker='o')
    plt.plot(hours, [hourly_removes[h] for h in hours], label='Removed Paths', marker='x')
    plt.xlabel("Time (Hourly)")
    plt.ylabel("Count")
    plt.title("Added vs Removed Paths Over Time")
    plt.legend()
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir,"plot_add_remove_over_time.pdf"))
    plt.close()

    # Plot 3: Lifetime Histogram
    if all_lifetimes:
        plt.figure(figsize=FIGSIZE)
        plt.hist(all_lifetimes, bins=np.arange(0, max(all_lifetimes) + 3600, 3600), color='purple')  # 1-hour bins
        plt.xlabel("Lifetime (seconds)")
        plt.ylabel("Frequency")
        plt.title("Path Lifetimes Distribution")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "plot_path_lifetime_histogram.pdf"))
        plt.close()

def main():
    output_file = f"comparer_analysis.txt"
    output_lines = []

    def log(line=""):
        print(line)
        output_lines.append(line)

    log("=== SCION Path Comparer Analysis ===")
    comparer_data = load_comparer_data(ARCHIVE_DIR)
    comparer_results, churn_insights = analyze_comparer(comparer_data)

    log(f"\nComparer data summary:\n")
    for ia, stats in comparer_results.items():
        log(f"→ Destination AS: {ia}")
        for k, v in stats.items():
            log(f"   {k.replace('_', ' ').capitalize()}: {v}")
        log()

    log("=== Global Churn Insights ===")
    log("Top ASes in changing paths:")
    for ashop, count in churn_insights["top_unstable_ases"]:
        log(f"  {ashop:25} → {count} path changes")

    log("\nChurn by path length:")
    for length, count in churn_insights["churn_by_path_length"].items():
        log(f"  Length {length}: {count} changes")

    generate_comparer_plots(comparer_data)
    log("[Saved figures as .pdf files]")

    write_output_to_file(output_lines, output_file)
    log(f"\n[Saved output to {output_file}]")

if __name__ == "__main__":
    main()
