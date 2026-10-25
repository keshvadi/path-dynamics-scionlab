# compare_sp_mp_prober.py

import os
import json
import statistics
import numpy as np
from scipy.stats import wilcoxon, rankdata
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
from plot_style import FIGSIZE, archive_dir

ARCHIVE_DIR = archive_dir()
SP_PREFIX = "prober_"
MP_PREFIX = "mp-prober_"
TIME_WINDOW = timedelta(minutes=15)


def parse_filename_timestamp(fname):
    try:
        return datetime.strptime(fname.split("_")[1], "%Y-%m-%dT%H:%M")
    except Exception as e:
        print(f"[WARN] Could not parse timestamp from filename {fname}: {e}")
        return None


def load_prober_files(prefix):
    data = defaultdict(lambda: defaultdict(dict))  # ia -> timestamp -> fingerprint -> stats
    for fname in os.listdir(ARCHIVE_DIR):
        if not fname.startswith(prefix) or not fname.endswith(".json"):
            continue
        timestamp = parse_filename_timestamp(fname)
        if not timestamp:
            continue

        path = os.path.join(ARCHIVE_DIR, fname)
        try:
            with open(path) as f:
                doc = json.load(f)
                ia = doc.get("ia")
                if not ia or not doc.get("probes"):
                    continue

                for probe in doc["probes"]:
                    ping = probe.get("ping_result", {})
                    stats = ping.get("statistics", {})
                    fp = probe.get("fingerprint")
                    if not ping or not stats or not fp:
                        continue

                    data[ia][timestamp][fp] = {
                        "avg_rtt": stats.get("avg_rtt"),
                        "mdev": stats.get("mdev_rtt"),
                        "loss": stats.get("packet_loss"),
                    }
        except Exception as e:
            print(f"[WARN] Failed to load {fname}: {e}")
    return data


def match_and_compare(sp_data, mp_data):
    results = []
    for ia in sp_data:
        for sp_time in sp_data[ia]:
            for mp_time in mp_data.get(ia, {}):
                if abs(sp_time - mp_time) > TIME_WINDOW:
                    continue

                for fp, sp_stats in sp_data[ia][sp_time].items():
                    mp_stats = mp_data[ia][mp_time].get(fp)
                    if not mp_stats:
                        continue

                    try:
                        diff_rtt = mp_stats["avg_rtt"] - sp_stats["avg_rtt"]
                        diff_jitter = mp_stats["mdev"] - sp_stats["mdev"]
                        diff_loss = mp_stats["loss"] - sp_stats["loss"]
                        results.append({
                            "ia": ia,
                            "fp": fp,
                            "rtt_diff": diff_rtt,
                            "jitter_diff": diff_jitter,
                            "loss_diff": diff_loss
                        })
                    except:
                        continue
    return results


def summarize_differences(results):
    rtts = [x["rtt_diff"] for x in results if x["rtt_diff"] is not None]
    jitters = [x["jitter_diff"] for x in results if x["jitter_diff"] is not None]
    losses = [x["loss_diff"] for x in results if x["loss_diff"] is not None]

    summary = {
        "matched_paths": len(results),
        "avg_rtt_diff": round(statistics.mean(rtts), 2) if rtts else None,
        "avg_jitter_diff": round(statistics.mean(jitters), 2) if jitters else None,
        "avg_loss_diff": round(statistics.mean(losses), 2) if losses else None,
    }
    return summary

def paired_stats(diffs):
    d = np.asarray(diffs, dtype=float)
    nz = d[d != 0]
    out = {"n": len(d), "zeros": int((d == 0).sum()), "median": float(np.median(d)), "mean": float(d.mean()),
           "p5": float(np.percentile(d, 5)), "p25": float(np.percentile(d, 25)),
           "p75": float(np.percentile(d, 75)), "p95": float(np.percentile(d, 95)),
           "frac_pos": float((d > 0).mean()), "frac_neg": float((d < 0).mean())}
    if len(nz) == 0:
        out["p"] = None
        out["rank_biserial"] = None
    else:
        out["p"] = float(wilcoxon(d).pvalue)
        r = rankdata(np.abs(nz))
        out["rank_biserial"] = float((r[nz > 0].sum() - r[nz < 0].sum()) / r.sum())
    return out


def fmt_stats(name, st):
    p = "n/a (all differences zero)" if st["p"] is None else f"{st['p']:.3g}"
    rb = "n/a" if st["rank_biserial"] is None else f"{st['rank_biserial']:.3f}"
    return (f"{name}: n={st['n']} zeros={st['zeros']} median={st['median']:.3f} mean={st['mean']:.3f} "
            f"p5/p25/p75/p95={st['p5']:.2f}/{st['p25']:.2f}/{st['p75']:.2f}/{st['p95']:.2f} "
            f"frac>0={st['frac_pos']:.3f} frac<0={st['frac_neg']:.3f} Wilcoxon p={p} rank-biserial r={rb}")


def path_level(results, key):
    by = defaultdict(list)
    for r in results:
        if r[key] is not None:
            by[(r["ia"], r["fp"])].append(r[key])
    return [float(np.median(v)) for v in by.values()]


def plot_differences(results):
    output_dir = "sp_mp_prober_plots"
    os.makedirs(output_dir, exist_ok=True)

    # Extract values
    rtt_diffs = [r["rtt_diff"] for r in results if r["rtt_diff"] is not None]
    jitter_diffs = [r["jitter_diff"] for r in results if r["jitter_diff"] is not None]
    loss_diffs = [r["loss_diff"] for r in results if r["loss_diff"] is not None]

    # CDF of per-observation differences (MP - SP), one panel per metric
    fig, axes = plt.subplots(1, 3, figsize=FIGSIZE)
    for ax, (label, diffs, lim) in zip(axes, [("RTT difference (ms)", rtt_diffs, (-20, 20)),
                                              ("Jitter difference (ms)", jitter_diffs, (-20, 20)),
                                              ("Loss difference (pp)", loss_diffs, (-20, 20))]):
        x = np.sort(np.asarray(diffs, dtype=float))
        y = np.arange(1, len(x) + 1) / len(x)
        ax.step(x, y, where="post", color="steelblue")
        ax.axvline(0, linestyle="--", color="red", linewidth=0.8)
        ax.axvline(np.median(x), linestyle=":", color="black", linewidth=0.8)
        ax.set_xlim(*lim)
        ax.set_ylim(0, 1)
        ax.set_xlabel(label)
        ax.grid(True, linewidth=0.3)
    axes[0].set_ylabel("CDF")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "sp_mp_diff_cdf.pdf"))
    plt.close()

    # Scatter plot over index (optional, helps see trends)
    for name, diffs in [("rtt (ms)", rtt_diffs), ("jitter (ms)", jitter_diffs), ("loss (%)", loss_diffs)]:
        plt.figure(figsize=FIGSIZE)
        plt.scatter(range(len(diffs)), diffs, alpha=0.6, marker="o", color="steelblue")
        plt.axhline(0, linestyle="--", color="red")
        plt.title(f"{name.upper()} Difference per Matched Path")
        plt.xlabel("Matched Path Index")
        plt.ylabel(f"Difference (MP - SP) {name}") # was changed
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{name}_diff_scatter.pdf"))
        plt.close()

    print(f"[Saved SP/MP prober difference plots to ./{output_dir}/]")


def main():
    output_file = "sp_mp_prober_comparison.txt"
    output_lines = []

    def log(line=""):
        print(line)
        output_lines.append(line)

    log("=== SCION SP vs MP Prober Path Comparison ===\n")

    log("Loading SP data...")
    sp_data = load_prober_files(SP_PREFIX)

    log("Loading MP data...")
    mp_data = load_prober_files(MP_PREFIX)

    log("Matching and comparing paths...\n")
    comparison_results = match_and_compare(sp_data, mp_data)
    summary = summarize_differences(comparison_results)

    log(f"→ Matched Fingerprints: {summary['matched_paths']}")
    log(f"→ Avg RTT difference (MP - SP): {summary['avg_rtt_diff']} ms")
    log(f"→ Avg Jitter difference (MP - SP): {summary['avg_jitter_diff']} ms")
    log(f"→ Avg Loss difference (MP - SP): {summary['avg_loss_diff']} %\n")

    log("Paired Wilcoxon signed-rank tests on differences MP - SP (positive = worse under multipath)")
    log("Observation level (each matched SP/MP probe pair):")
    for key, name in (("rtt_diff", "RTT (ms)"), ("jitter_diff", "Jitter/mdev (ms)"), ("loss_diff", "Loss (pp)")):
        log("  " + fmt_stats(name, paired_stats([r[key] for r in comparison_results])))
    log("Path level (median over each (IA, fingerprint) path's matched pairs):")
    for key, name in (("rtt_diff", "RTT (ms)"), ("jitter_diff", "Jitter/mdev (ms)"), ("loss_diff", "Loss (pp)")):
        log("  " + fmt_stats(name, paired_stats(path_level(comparison_results, key))))
    log()

    log("[Saved comparison results to sp_mp_prober_comparison.txt]")
    with open(output_file, "w") as f:
        for line in output_lines:
            f.write(line + "\n")

    plot_differences(comparison_results)


if __name__ == "__main__":
    main()
