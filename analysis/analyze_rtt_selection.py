# analyze_rtt_selection.py
# Quantifies how much RTT a latency-aware endpoint could gain over the random path sampling used by the prober.

import os
import json
import numpy as np
from collections import defaultdict
from plot_style import archive_dir

ARCHIVE_DIR = archive_dir()
SP_PREFIX = "prober_"


def load():
    probe_gap = []  # per probe: avg RTT - min RTT over the 15 pings (ms)
    by_interval = defaultdict(list)  # (ia, file timestamp) -> avg RTT of each sampled path
    for fname in sorted(os.listdir(ARCHIVE_DIR)):
        if not fname.startswith(SP_PREFIX) or not fname.endswith(".json"):
            continue
        with open(os.path.join(ARCHIVE_DIR, fname)) as f:
            doc = json.load(f)
        ia = doc.get("ia")
        ts = fname.split("_")[1]
        for probe in doc.get("probes") or []:
            st = (probe.get("ping_result") or {}).get("statistics") or {}
            avg, mn = st.get("avg_rtt"), st.get("min_rtt")
            if not avg or mn is None or st.get("received", 0) == 0:
                continue
            probe_gap.append(avg - mn)
            by_interval[(ia, ts)].append(avg)
    return np.array(probe_gap), by_interval


def main():
    out = []

    def log(line=""):
        print(line)
        out.append(line)

    probe_gap, by_interval = load()
    log("=== Average vs minimum RTT in the single-path prober data ===")
    log(f"Within-probe (15 pings): n={len(probe_gap)} probes, avg-min RTT gap: median={np.median(probe_gap):.2f} ms "
        f"mean={probe_gap.mean():.2f} ms")

    for ia in sorted({k[0] for k in by_interval}) + [None]:
        gaps, ratios, means, mins, ns = [], [], [], [], []
        for (i, _), v in by_interval.items():
            if (ia is not None and i != ia) or len(v) < 2:
                continue
            gaps.append(np.mean(v) - np.min(v))
            ratios.append(np.min(v) / np.mean(v))
            means.append(np.mean(v))
            mins.append(np.min(v))
            ns.append(len(v))
        gaps, ratios, means, mins = map(np.array, (gaps, ratios, means, mins))
        name = ia if ia else "all destinations"
        log(f"Across sampled paths per interval, {name}: n_intervals={len(gaps)} median paths/interval={int(np.median(ns))} "
            f"mean-of-paths RTT median={np.median(means):.1f} ms, min-of-paths RTT median={np.median(mins):.1f} ms, "
            f"(mean - min) median={np.median(gaps):.1f} ms mean={gaps.mean():.1f} ms, "
            f"min/mean median={np.median(ratios):.3f}")

    with open("rtt_selection_summary.txt", "w") as f:
        f.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
