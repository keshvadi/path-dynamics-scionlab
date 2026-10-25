# analyze_prober.py

import os
import json
import statistics
from datetime import datetime
import matplotlib.pyplot as plt
from plot_style import FIGSIZE, archive_dir
import matplotlib.dates as mdates
from collections import defaultdict

ARCHIVE_DIR = archive_dir()
PROBER_PREFIX = "prober_"

def load_prober_data(archive_dir):
    from dateutil import parser  # Handles both Zulu and non-Zulu timestamps

    prober_data = defaultdict(lambda: {
        "rtts": [],
        "packet_losses": [],
        "sequence_issues": 0,
        "total_probes": 0
    })

    prober_data_by_time = defaultdict(lambda: defaultdict(list))
    # Structure: prober_data_by_time[ia][metric] = list of (timestamp, value)

    for fname in os.listdir(archive_dir):
        if not fname.startswith(PROBER_PREFIX) or not fname.endswith(".json"):
            continue
        path = os.path.join(archive_dir, fname)
        try:
            with open(path) as f:
                doc = json.load(f)
                ia = doc.get("ia")
                probes = doc.get("probes", [])
                timestamp_str = doc.get("timestamp")
                if not ia or not timestamp_str:
                    continue

                try:
                    ts = parser.parse(timestamp_str)
                    ts = ts.replace(minute=0, second=0, microsecond=0)  # Bucket into 1-hour intervals
                except Exception as e:
                    print(f"[WARN] Could not parse timestamp in {fname}: {e}")
                    continue

                total_rtts = []
                total_loss = []
                total_mdevs = []
                seq_issues = 0
                probe_count = 0

                for probe in probes:
                    result = probe.get("ping_result", {})
                    stats = result.get("statistics", {})
                    replies = result.get("replies", [])

                    avg_rtt = stats.get("avg_rtt")
                    mdev = stats.get("mdev_rtt")
                    packet_loss = stats.get("packet_loss")

                    if avg_rtt is not None:
                        prober_data[ia]["rtts"].append(avg_rtt)
                        total_rtts.append(avg_rtt)
                    if packet_loss is not None:
                        prober_data[ia]["packet_losses"].append(packet_loss)
                        total_loss.append(packet_loss)
                    if mdev is not None:
                        total_mdevs.append(mdev)

                    # Sequence analysis
                    seqs = [r.get("scmp_seq") for r in replies if "scmp_seq" in r]
                    expected = sorted(seqs)
                    if seqs and seqs != expected:
                        prober_data[ia]["sequence_issues"] += 1
                        seq_issues += 1

                    prober_data[ia]["total_probes"] += 1
                    probe_count += 1

                # Only store if we had probes this round
                if probe_count > 0:
                    if total_rtts:
                        prober_data_by_time[ia]["rtt"].append((ts, statistics.mean(total_rtts)))
                    if total_loss:
                        prober_data_by_time[ia]["loss"].append((ts, statistics.mean(total_loss)))
                    if total_mdevs:
                        prober_data_by_time[ia]["mdev"].append((ts, statistics.mean(total_mdevs)))
                    prober_data_by_time[ia]["seq_issue_ratio"].append((ts, seq_issues / probe_count))

        except Exception as e:
            print(f"[WARN] Failed to parse {fname}: {e}")
    return prober_data, prober_data_by_time

def compute_stats(values):
    if not values:
        return {"count": 0, "avg": None, "jitter": None}
    avg = round(statistics.mean(values), 2)
    jitter = round(statistics.stdev(values), 2) if len(values) > 1 else 0.0
    return {"count": len(values), "avg": avg, "jitter": jitter}

def write_output_to_file(output_lines, filename):
    with open(filename, "w") as f:
        for line in output_lines:
            f.write(line + "\n")

def main():
    output_file = f"prober_analysis.txt"
    output_lines = []

    def log(line=""):
        print(line)
        output_lines.append(line)

    log("=== SCION Prober Latency & Loss Analysis ===")
    prober_data, prober_data_by_time = load_prober_data(ARCHIVE_DIR)

    log(f"\n Summary:\n")
    for ia, data in prober_data.items():
        latency_stats = compute_stats(data["rtts"])
        loss_stats = compute_stats(data["packet_losses"])
        seq_issues = data["sequence_issues"]
        total = data["total_probes"]


        log(f"→ Destination IA: {ia}")
        log(f"   Probes:        {total}")
        log(f"   Avg RTT:       {latency_stats['avg']} ms")
        log(f"   Jitter:        {latency_stats['jitter']} ms")
        log(f"   Avg Loss:      {loss_stats['avg']}%")
        log(f"   Loss Jitter:   {loss_stats['jitter']}%")
        log(f"   Seq issues:    {seq_issues} of {total} probes\n")

    generate_prober_plots(prober_data_by_time)

    write_output_to_file(output_lines, output_file)
    log(f"\n[Saved output to {output_file}]")


def generate_prober_plots(prober_data_by_time):
    output_dir = "prober_plots"
    os.makedirs(output_dir, exist_ok=True)

    def hourly_average(series_by_time):
        buckets = defaultdict(list)
        for t, v in series_by_time:
            bucket_time = t.replace(minute=0, second=0, microsecond=0)
            buckets[bucket_time].append(v)
        return sorted((bt, sum(vs)/len(vs)) for bt, vs in buckets.items() if vs)

    all_metrics = {
        "rtt": {},
        "loss": {},
        "mdev": {},
        "seq_issue_ratio": {}
    }

    # Plot per-AS and store for combined plotting
    for ia, time_data in prober_data_by_time.items():
        rtt_series = time_data.get("rtt", [])
        loss_series = time_data.get("loss", [])
        mdev_series = time_data.get("mdev", [])
        seq_issue_series = time_data.get("seq_issue_ratio", [])

        rtt_avg = hourly_average(rtt_series)
        loss_avg = hourly_average(loss_series)
        mdev_avg = hourly_average(mdev_series)
        seq_issue_avg = hourly_average(seq_issue_series)

        all_metrics["rtt"][ia] = rtt_avg
        all_metrics["loss"][ia] = loss_avg
        all_metrics["mdev"][ia] = mdev_avg
        all_metrics["seq_issue_ratio"][ia] = seq_issue_avg

        def plot_metric(series, ylabel, title, filename):
            if not series:
                print(f"[INFO] Skipping {title}, no data.")
                return
            times, values = zip(*series)
            plt.figure(figsize=FIGSIZE)
            plt.plot(times, values, marker='o', linestyle='-')
            plt.title(title)
            plt.xlabel("Time")
            plt.ylabel(ylabel)
            plt.grid(True)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d\n%H:%M'))
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, filename))
            plt.close()
            print(f"[Saved plot to {output_dir}/{filename}]")

        plot_metric(rtt_avg, "Avg RTT (ms)", f"{ia} - Avg RTT Over Time", f"{ia}_rtt_plot.pdf")
        plot_metric(loss_avg, "Avg Loss (%)", f"{ia} - Packet Loss Over Time", f"{ia}_loss_plot.pdf")
        plot_metric(mdev_avg, "Avg Jitter (mdev, ms)", f"{ia} - Path Jitter Over Time", f"{ia}_jitter_plot.pdf")
        plot_metric(seq_issue_avg, "Seq Issue Ratio", f"{ia} - Seq Issues Over Time", f"{ia}_seq_plot.pdf")

    # Plot shared graphs: one for each metric, with both ASes on the same graph
    def plot_combined(metric_key, ylabel, title, filename):
        plt.figure(figsize=FIGSIZE)
        valid = False
        for ia, series in sorted(all_metrics[metric_key].items()):
            if not series:
                continue
            times, values = zip(*series)
            plt.plot(times, values, marker='o', linestyle='-', label=ia)
            valid = True
        if not valid:
            print(f"[INFO] Skipping combined plot {title}, no data.")
            plt.close()
            return
        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel(ylabel)
        plt.legend(title="IA")
        plt.grid(True)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d\n%H:%M'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, filename))
        plt.close()
        print(f"[Saved combined plot to {output_dir}/{filename}]")

    plot_combined("rtt", "Avg RTT (ms)", "RTT Comparison Between ASes", "combined_rtt_plot.pdf")
    plot_combined("loss", "Avg Loss (%)", "Loss Comparison Between ASes", "combined_loss_plot.pdf")
    plot_combined("mdev", "Avg Jitter (mdev, ms)", "Jitter Comparison Between ASes", "combined_jitter_plot.pdf")
    plot_combined("seq_issue_ratio", "Seq Issue Ratio", "Seq Issues Comparison Between ASes", "combined_seq_plot.pdf")


if __name__ == "__main__":
    main()
