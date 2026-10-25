import os
import json
import statistics
import matplotlib.pyplot as plt
from plot_style import FIGSIZE, archive_dir
from matplotlib.dates import DateFormatter
from datetime import datetime, timedelta
from datetime import datetime
from collections import defaultdict

ARCHIVE_DIR = archive_dir()
BW_PREFIX = "BW_"

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

def compute_full_stats(values):
    if not values:
        return {"count": 0, "avg": None, "jitter": None, "min": None, "max": None}
    return {
        "count": len(values),
        "avg": round(statistics.mean(values), 2),
        "jitter": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
        "min": round(min(values), 2),
        "max": round(max(values), 2)
    }

def load_bw_data(archive_dir):
    bw_data = defaultdict(lambda: defaultdict(lambda: {
        "sc_bandwidth": [],
        "cs_bandwidth": [],
        "sc_loss": [],
        "cs_loss": [],
        "sc_interarrival": [],
        "cs_interarrival": [],
        "sc_interarrival_minmax": [],
        "cs_interarrival_minmax": [],
        "sc_interarrival_mdev": [],
        "cs_interarrival_mdev": [],
        "files": 0,
    }))

    for fname in os.listdir(archive_dir):
        if not fname.startswith(BW_PREFIX) or not fname.endswith(".json"):
            continue

        path = os.path.join(archive_dir, fname)
        try:
            with open(path) as f:
                doc = json.load(f)
                ia = doc.get("target_server", {}).get("ia") or doc.get("as")
                mbps = doc.get("target", {}).get("tier_mbps") or doc.get("target_mbps")
                if not ia or not mbps:
                    continue

                bw_data[ia][mbps]["files"] += 1

                paths = doc.get("paths")

                for path_result in paths:
                    result = path_result.get("result", {})
                    if result.get("invalid_format"):
                        continue

                    for direction_key, prefix in [("S->C results", "sc"), ("C->S results", "cs")]:
                        dir_result = result.get(direction_key)
                        if not dir_result:
                            continue

                        bw = parse_bps_field(dir_result.get("achieved_bps", ""))
                        if bw is not None:
                            bw_data[ia][mbps][f"{prefix}_bandwidth"].append(bw)

                        loss_str = dir_result.get("loss_rate", "").strip('%')
                        try:
                            loss = float(loss_str)
                            bw_data[ia][mbps][f"{prefix}_loss"].append(loss)
                        except:
                            pass

                        inter_str = dir_result.get("interarrival time min/avg/max/mdev")
                        if inter_str:
                            min_i, avg_i, max_i, mdev = parse_interarrival(inter_str)
                            if avg_i is not None:
                                bw_data[ia][mbps][f"{prefix}_interarrival"].append(avg_i)
                                bw_data[ia][mbps][f"{prefix}_interarrival_minmax"].append((min_i, max_i))
                            if mdev is not None:
                                bw_data[ia][mbps][f"{prefix}_interarrival_mdev"].append(mdev)

        except Exception as e:
            print(f"[WARN] Failed to parse {fname}: {e}")

    return bw_data


def write_output_to_file(output_lines, filename):
    with open(filename, "w") as f:
        for line in output_lines:
            f.write(line + "\n")


def generate_bw_plots(archive_dir):
    TIME_RESOLUTION = timedelta(hours=1)
    BW_PREFIX = "BW_"
    os.makedirs("bw_plots", exist_ok=True)

    def parse_ts(fname):
        try:
            ts_part = fname.split("_")[1]
            return datetime.strptime(ts_part, "%Y-%m-%dT%H:%M")
        except:
            return None

    data_per_as = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    # structure: data[ia][mbps][timestamp][direction][(metric, value)]

    for fname in os.listdir(archive_dir):
        if not fname.startswith(BW_PREFIX) or not fname.endswith(".json"):
            continue
        ts = parse_ts(fname)
        if not ts:
            continue
        ts = ts.replace(minute=0, second=0, microsecond=0)  # round to hour
        fpath = os.path.join(archive_dir, fname)

        try:
            with open(fpath) as f:
                doc = json.load(f)
                ia = doc.get("target_server", {}).get("ia") or doc.get("as")
                mbps = doc.get("target", {}).get("tier_mbps") or doc.get("target_mbps")
                if not ia or not mbps:
                    continue
                paths = doc.get("paths", [doc])
                for p in paths:
                    if p.get("result", {}).get("invalid_format"):
                        continue
                    for dir_key, dir_label in [("S->C results", "sc"), ("C->S results", "cs")]:
                        res = p.get("result", {}).get(dir_key)
                        if not res:
                            continue
                        bw = parse_bps_field(res.get("achieved_bps", ""))
                        loss = res.get("loss_rate", "").strip('%')
                        try:
                            loss = float(loss)
                        except:
                            loss = None
                        _, ia_avg, _, ia_mdev = parse_interarrival(res.get("interarrival time min/avg/max/mdev", ""))

                        metrics = {
                            "bandwidth (mbps)": bw,
                            "loss (%)": loss,
                            "ia_avg (ms)": ia_avg,
                            "ia_mdev (ms)": ia_mdev
                        }

                        for key, val in metrics.items():
                            if val is not None:
                                data_per_as[ia][mbps][ts][dir_label].append((key, val))
        except Exception as e:
            print(f"[WARN] Failed to read {fname}: {e}")

    def average_per_hour(metric_data):
        out = defaultdict(list)
        for ts in sorted(metric_data):
            grouped = defaultdict(list)
            for metric, val in metric_data[ts]:
                grouped[metric].append(val)
            for metric, vals in grouped.items():
                out[metric].append((ts, sum(vals) / len(vals)))
        return out

    # 1. Per-AS, show all tiers in one plot per metric
    for ia in data_per_as:
        ia_dir = os.path.join("bw_plots", ia.replace(":", "_"))
        os.makedirs(ia_dir, exist_ok=True)

        for direction in ["sc", "cs"]:
            for metric in ["bandwidth (mbps)", "loss (%)", "ia_avg (m)s", "ia_mdev (ms)"]:
                plt.figure(figsize=FIGSIZE)
                found = False
                for mbps in sorted(data_per_as[ia]):
                    hourly_data = defaultdict(list)
                    for ts in sorted(data_per_as[ia][mbps]):
                        entries = data_per_as[ia][mbps][ts][direction]
                        for m, v in entries:
                            if m == metric:
                                hourly_data[ts].append(v)
                    if not hourly_data:
                        continue
                    avg_data = [(ts, sum(vs)/len(vs)) for ts, vs in sorted(hourly_data.items()) if vs]
                    if not avg_data:
                        continue
                    times, values = zip(*avg_data)
                    plt.plot(times, values, marker='o', label=f"{mbps} Mbps")
                    found = True

                if found:
                    plt.title(f"{ia} [{direction.upper()}] - {metric.upper()} across tiers")
                    plt.xlabel("Time")
                    plt.ylabel(metric)
                    plt.legend(title="Tier")
                    plt.grid(True)
                    plt.gca().xaxis.set_major_formatter(DateFormatter("%m-%d\n%H:%M"))
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    fname = f"{direction}_{metric.replace(' ', '_')}_all_tiers.pdf"
                    plt.savefig(os.path.join(ia_dir, fname))
                    print(f"[Saved] {ia} multi-tier → {fname}")
                plt.close()

    # 2. For each tier, show all ASes in one graph
    tier_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    # tier_data[tier][direction][metric][ia] = [(ts, val)]

    for ia in data_per_as:
        for mbps in data_per_as[ia]:
            for ts in data_per_as[ia][mbps]:
                for direction in data_per_as[ia][mbps][ts]:
                    for metric, value in data_per_as[ia][mbps][ts][direction]:
                        tier_data[mbps][direction][metric][ia].append((ts, value))

    for mbps in tier_data:
        for direction in ["sc", "cs"]:
            for metric in ["bandwidth (mbps)", "loss (%)", "ia_avg (m)s", "ia_mdev (ms)"]:
                plt.figure(figsize=FIGSIZE)
                found = False
                for ia in sorted(tier_data[mbps][direction][metric]):
                    data = tier_data[mbps][direction][metric][ia]
                    hourly = defaultdict(list)
                    for ts, val in data:
                        ts = ts.replace(minute=0, second=0, microsecond=0)
                        hourly[ts].append(val)
                    avg_data = [(ts, sum(vals)/len(vals)) for ts, vals in sorted(hourly.items()) if vals]
                    if not avg_data:
                        continue
                    times, values = zip(*avg_data)
                    plt.plot(times, values, marker='o', label=ia)
                    found = True

                if found:
                    plt.title(f"{metric.upper()} Comparison @ {mbps} Mbps ({direction.upper()})")
                    plt.xlabel("Time")
                    plt.ylabel(metric)
                    plt.legend(title="IA")
                    plt.grid(True)
                    plt.gca().xaxis.set_major_formatter(DateFormatter("%m-%d\n%H:%M"))
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    fname = f"tier_{mbps}_{direction}_{metric.replace(' ', '_')}_per_IA.pdf"
                    plt.savefig(os.path.join("bw_plots", fname))
                    print(f"[Saved] Cross-AS tier plot → {fname}")
                plt.close()


def print_bw_summary(bw_data):
    output_file = f"sp_bw_analysis.txt"
    output_lines = []

    def log(line=""):
        print(line)
        output_lines.append(line)

    log("=== SCION Bandwidth Test Summary ===")

    for ia in sorted(bw_data):
        print(f"→ Destination IA: {ia}")
        for mbps in sorted(bw_data[ia]):
            data = bw_data[ia][mbps]
            log(f"  - Tier:         {mbps} Mbps")
            log(f"    Files:        {data['files']}\n")

            for direction in ["sc", "cs"]:
                dir_label = "S→C" if direction == "sc" else "C→S"
                bw_stats = compute_full_stats(data[f"{direction}_bandwidth"])
                loss_stats = compute_full_stats(data[f"{direction}_loss"])
                inter_stats = compute_full_stats(data[f"{direction}_interarrival"])
                inter_mdev = compute_full_stats(data[f"{direction}_interarrival_mdev"])
                inter_minmax = data.get(f"{direction}_interarrival_minmax", [])
                min_vals = [x[0] for x in inter_minmax if x]
                max_vals = [x[1] for x in inter_minmax if x]
                inter_min = round(min(min_vals), 4) if min_vals else None
                inter_max = round(max(max_vals), 2) if max_vals else None

                log(f"    [{dir_label}]")
                log(f"      Count:           {bw_stats['count']}")
                log(f"      Avg BW:          {bw_stats['avg']} Mbps")
                log(f"      BW Jitter:       {bw_stats['jitter']} Mbps")
                log(f"      BW Min/Max:      {bw_stats['min']} / {bw_stats['max']} Mbps")
                log(f"      Avg Loss:        {loss_stats['avg']}%")
                log(f"      Loss Jitter:     {loss_stats['jitter']}%")
                log(f"      Interarrival:    {inter_stats['avg']} ms")
                log(f"      IA Jitter:       {inter_mdev['avg']} ms")
                log(f"      IA Min/Max:      {inter_min} / {inter_max} ms")
                log("")

    write_output_to_file(output_lines, output_file)
    log(f"\n[Saved output to {output_file}]")


def main():
    bw_data = load_bw_data(ARCHIVE_DIR)
    print_bw_summary(bw_data)
    generate_bw_plots(ARCHIVE_DIR)

if __name__ == "__main__":
    main()
