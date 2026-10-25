import os
import json
import statistics
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ARCHIVE_DIR = "/home/lars/Desktop/Scion_Project_Canada/NewTestData/biggertest"
TR_PREFIX = "TR_"

def parse_filename_timestamp(fname):
    try:
        ts_str = fname.split("_")[1]
        return datetime.strptime(ts_str, "%Y-%m-%dT%H:%M")
    except Exception as e:
        print(f"[WARN] Timestamp parse error in {fname}: {e}")
        return None

def load_traceroute_data(archive_dir):
    traces = []
    for fname in os.listdir(archive_dir):
        if not fname.startswith(TR_PREFIX) or not fname.endswith(".json"):
            continue
        timestamp = parse_filename_timestamp(fname)
        if not timestamp:
            continue

        path = os.path.join(archive_dir, fname)
        try:
            with open(path) as f:
                doc = json.load(f)
                hops = doc.get("hops", [])
                if not hops:
                    continue

                rtts = []
                as_rtt_map = defaultdict(list)
                as_hop_count = defaultdict(int)
                missing_rtts = 0

                for hop in hops:
                    isd_as = hop.get("isd_as")
                    times = hop.get("round_trip_times", [])
                    if not times:
                        missing_rtts += 1
                        continue
                    avg_rtt = statistics.mean(times)
                    rtts.append(avg_rtt)
                    if isd_as:
                        as_rtt_map[isd_as].append(avg_rtt)
                        as_hop_count[isd_as] += 1

                traces.append({
                    "timestamp": timestamp,
                    "hop_count": len(hops),
                    "missing_rtts": missing_rtts,
                    "avg_rtt": statistics.mean(rtts) if rtts else None,
                    "as_rtt_map": dict(as_rtt_map),
                    "as_hop_count": dict(as_hop_count)
                })

        except Exception as e:
            print(f"[WARN] Failed to load {fname}: {e}")

    return traces

def plot_time_series(traces):
    timestamps = [t["timestamp"] for t in traces]
    avg_rtts = [t["avg_rtt"] for t in traces]
    hop_counts = [t["hop_count"] for t in traces]
    missing_rtts = [t["missing_rtts"] for t in traces]

    fig, axs = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    axs[0].plot(timestamps, avg_rtts, label="Avg RTT", color="blue")
    axs[0].set_ylabel("RTT (ms)")
    axs[0].set_title("Average RTT Over Time")
    axs[0].grid(True)

    axs[1].plot(timestamps, hop_counts, label="Hop Count", color="green")
    axs[1].set_ylabel("Hop Count")
    axs[1].set_title("Hop Count Over Time")
    axs[1].grid(True)

    axs[2].plot(timestamps, missing_rtts, label="Missing RTTs", color="red")
    axs[2].set_ylabel("Missing Hops")
    axs[2].set_title("Missing RTTs Over Time")
    axs[2].set_xlabel("Time")
    axs[2].grid(True)

    for ax in axs:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax.legend()

    plt.tight_layout()
    plt.savefig("traceroute_time_series.png")
    plt.close()

def plot_as_rtt_bar(traces):
    as_rtt_totals = defaultdict(list)

    for trace in traces:
        for ia, rtts in trace["as_rtt_map"].items():
            as_rtt_totals[ia].extend(rtts)

    as_avg_rtt = {
        ia: round(statistics.mean(rtts), 2)
        for ia, rtts in as_rtt_totals.items() if rtts
    }

    # Top 10 ASes with highest RTT
    top_ases = sorted(as_avg_rtt.items(), key=lambda x: x[1], reverse=True)[:10]
    labels = [x[0] for x in top_ases]
    values = [x[1] for x in top_ases]

    plt.figure(figsize=(12, 6))
    plt.barh(labels, values, color="purple")
    plt.xlabel("Avg RTT (ms)")
    plt.title("Top 10 ASes by Average RTT")
    plt.gca().invert_yaxis()
    plt.grid(axis='x')
    plt.tight_layout()
    plt.savefig("top_as_rtt.png")
    plt.close()

def summarize(traces):
    all_rtts = [t["avg_rtt"] for t in traces if t["avg_rtt"] is not None]
    all_hops = [t["hop_count"] for t in traces]
    all_missing = [t["missing_rtts"] for t in traces]

    output_lines = []

    def log(line=""):
        print(line)
        output_lines.append(line)

    log("=== SCION Traceroute Summary ===\n")
    log(f"→ Number of traces: {len(traces)}")
    log(f"→ Avg RTT: {round(statistics.mean(all_rtts), 2)} ms")
    log(f"→ Avg Hop Count: {round(statistics.mean(all_hops), 2)}")
    log(f"→ Avg Missing RTTs: {round(statistics.mean(all_missing), 2)}")

    with open("traceroute_summary.txt", "w") as f:
        for line in output_lines:
            f.write(line + "\n")

def main():
    traces = load_traceroute_data(ARCHIVE_DIR)
    summarize(traces)
    plot_time_series(traces)
    plot_as_rtt_bar(traces)

if __name__ == "__main__":
    main()
