import os
import json
import statistics
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
from plot_style import FIGSIZE, archive_dir

ARCHIVE_DIR = archive_dir()
SP_PREFIX = "BW_"
MP_PREFIX = "BW-P"
TIME_WINDOW = timedelta(minutes=15)

def parse_timestamp_from_filename(fname):
    try:
        parts = fname.split("_")
        ts_str = parts[1]

        # Handle BW-P format (MP), e.g., BW-P_2025-07-15T22-14-53_...
        if "-" in ts_str and ":" not in ts_str:
            date, time = ts_str.split("T")
            time_parts = time.split("-")
            if len(time_parts) >= 2:
                time_fixed = f"{time_parts[0]}:{time_parts[1]}"
                ts_str = f"{date}T{time_fixed}"

        return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M")

    except Exception as e:
        print(f"[WARN] Timestamp parse error in {fname}: {e}")
        return None

def parse_bps_field(bps_str):
    try:
        return float(bps_str.split(" ")[0]) / 1e6  # Convert to Mbps
    except:
        return None

def parse_interarrival(inter_str):
    try:
        parts = inter_str.replace(" ms", "").split("/")
        return tuple(map(float, parts))  # min, avg, max, mdev
    except:
        return None, None, None, None

def extract_bw_stats(archive_dir, prefix):
    results = defaultdict(lambda: defaultdict(dict))  # ia -> timestamp -> fp -> metrics

    for fname in sorted(os.listdir(archive_dir)):
        if not fname.startswith(prefix) or not fname.endswith(".json"):
            continue
        ts = parse_timestamp_from_filename(fname)
        if not ts:
            continue

        fpath = os.path.join(archive_dir, fname)
        try:
            with open(fpath) as f:
                doc = json.load(f)
                ia = doc.get("target_server", {}).get("ia") or doc.get("as")
                paths = doc.get("paths", [doc])
                for path in paths:
                    fp = path.get("fingerprint")
                    if not fp:
                        continue
                    result = path.get("result", {})
                    if result.get("invalid_format"):
                        continue

                    stats = {}
                    for direction_key in ["S->C results", "C->S results"]:
                        d = result.get(direction_key)
                        if not d:
                            continue

                        bw = parse_bps_field(d.get("achieved_bps", ""))
                        loss = d.get("loss_rate", "").strip('%')
                        try:
                            loss = float(loss)
                        except:
                            loss = None
                        inter = d.get("interarrival time min/avg/max/mdev", "")
                        _, ia_avg, _, ia_mdev = parse_interarrival(inter)

                        dir_short = "sc" if direction_key.startswith("S->C") else "cs"
                        stats[dir_short] = {
                            "bw": bw,
                            "loss": loss,
                            "ia_avg": ia_avg,
                            "ia_mdev": ia_mdev
                        }

                    results[ia][ts][fp] = stats

        except Exception as e:
            print(f"[WARN] Failed to read {fname}: {e}")

    return results

def compare_metrics(sp_data, mp_data):
    differences = defaultdict(list)  # metric -> list of diffs
    matched_count = 0

    for ia in sp_data:
        for sp_time in sp_data[ia]:
            # Find the nearest mp_time within ±15 min
            mp_times = mp_data.get(ia, {})
            closest_time = None
            min_diff = TIME_WINDOW
            for mp_time in mp_times:
                delta = abs(mp_time - sp_time)
                if delta <= min_diff:
                    min_diff = delta
                    closest_time = mp_time

            if not closest_time:
                continue

            sp_paths = sp_data[ia][sp_time]
            mp_paths = mp_data[ia][closest_time]

            for fp, sp_path_data in sp_paths.items():
                if fp not in mp_paths:
                    continue

                mp_path_data = mp_paths[fp]
                matched_count += 1

                for dir_key in ["sc", "cs"]:
                    sp = sp_path_data.get(dir_key)
                    mp = mp_path_data.get(dir_key)
                    if not sp or not mp:
                        continue

                    for metric in ["bw", "loss", "ia_avg", "ia_mdev"]:
                        s = sp.get(metric)
                        m = mp.get(metric)
                        if s is not None and m is not None:
                            differences[f"{dir_key}_{metric}"].append(s - m)

    return differences, matched_count

def summarize_differences(differences):
    summary = {}
    for key, values in differences.items():
        summary[key] = round(statistics.mean(values), 3) if values else None
    return summary

def plot_bw_differences(differences):
    output_dir = "sp_mp_bw_plots"
    os.makedirs(output_dir, exist_ok=True)

    label_map = {
        "sc_bw": "S→C Bandwidth (Mbps)",
        "cs_bw": "C→S Bandwidth (Mbps)",
        "sc_loss": "S→C Loss (%)",
        "cs_loss": "C→S Loss (%)",
        "sc_ia_avg": "S→C Interarrival Avg (ms)",
        "cs_ia_avg": "C→S Interarrival Avg (ms)",
        "sc_ia_mdev": "S→C Interarrival Jitter (ms)",
        "cs_ia_mdev": "C→S Interarrival Jitter (ms)",
    }

    # Boxplots
    fig, ax = plt.subplots(figsize=FIGSIZE)
    keys = sorted([k for k in differences if differences[k]])
    values = [differences[k] for k in keys]
    labels = [label_map.get(k, k) for k in keys]

    ax.boxplot(values, patch_artist=True)
    ax.set_title("SP - MP Metric Differences (Boxplot)")
    ax.set_ylabel("Difference (SP minus MP)")
    ax.set_xticks(range(1, len(labels)+1))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "sp_mp_bw_diff_boxplot.pdf"))
    plt.close()

    # Optional: scatter plots for each metric
    for key in keys:
        diffs = differences[key]
        if not diffs:
            continue
        plt.figure(figsize=FIGSIZE)
        plt.scatter(range(len(diffs)), diffs, color="tab:blue", alpha=0.6)
        plt.axhline(0, color="red", linestyle="--")
        plt.title(f"{label_map.get(key, key)} Differences (SP - MP)")
        plt.xlabel("Matched Path Index")
        plt.ylabel("Difference")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{key}_diff_scatter.pdf"))
        plt.close()

    print(f"[Saved SP/MP bandwidth comparison plots to './{output_dir}/']")


def main():
    output_file = "sp_mp_bw_comparison.txt"
    output_lines = []

    def log(line=""):
        print(line)
        output_lines.append(line)

    log("=== SP vs MP Bandwidth Comparison ===\n")

    log("Loading SP bandwidth data...")
    sp_data = extract_bw_stats(ARCHIVE_DIR, SP_PREFIX)

    log("Loading MP bandwidth data...")
    mp_data = extract_bw_stats(ARCHIVE_DIR, MP_PREFIX)

    log("Comparing matched paths...\n")
    diffs, matched_count = compare_metrics(sp_data, mp_data)
    summary = summarize_differences(diffs)

    log(f"→ Matched paths: {matched_count}\n")

    for metric in sorted(summary):
        label = metric.replace("_", " ").upper()
        log(f"→ Avg diff {label}: {summary[metric]}")

    log(f"\n[Saved output to {output_file}]")
    with open(output_file, "w") as f:
        for line in output_lines:
            f.write(line + "\n")

    plot_bw_differences(diffs)

if __name__ == "__main__":
    main()
