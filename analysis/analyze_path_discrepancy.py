# analyze_path_discrepancy.py
#
# Compares the size of the forward (A->B) and reverse (B->A) path sets discovered by
# pathdiscover at the same 30-minute interval, between the vantage-point ASes.
#
# Usage: python analyze_path_discrepancy.py <lab1_dir> <lab2_dir> <lab3_dir>
# Each <labN_dir> is the extracted raw_data.zip of that lab (containing Archive/YYYY-MM-DD/AS-*.json).
# Both directions of a pair come from different labs (each lab only records paths it discovers itself).
#
# A path set is the set of paths with status != "timeout" (the same definition the comparer uses).
# Intervals in which a direction returned an empty set are reported separately and excluded from
# the difference statistics.

import glob
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime

WINDOW_START = datetime(2025, 7, 16, 0, 0)
WINDOW_END = datetime(2025, 8, 11, 23, 59)
NAMES = {"19-ffaa:1:11de": "AS-1", "17-ffaa:1:11e4": "AS-2", "18-ffaa:1:11e5": "AS-3"}
PAIRS = [("19-ffaa:1:11de", "17-ffaa:1:11e4"), ("19-ffaa:1:11de", "18-ffaa:1:11e5"),
         ("17-ffaa:1:11e4", "18-ffaa:1:11e5")]


def load(lab_dirs, viable_only):
    # (src, dst) -> timestamp -> number of paths
    sets = defaultdict(dict)
    for lab_dir in lab_dirs:
        for path in glob.glob(os.path.join(lab_dir, "Archive", "*", "AS-*.json")):
            try:
                ts = datetime.strptime(os.path.basename(path).split("_")[1], "%Y-%m-%dT%H:%M")
            except ValueError:
                continue
            if not (WINDOW_START <= ts <= WINDOW_END):
                continue
            with open(path) as f:
                doc = json.load(f)
            paths = doc.get("paths") or []
            if viable_only:
                paths = [p for p in paths if p.get("status") != "timeout"]
            sets[(doc["local_isd_as"], doc["destination"])][ts] = len(paths)
    return sets


def report(sets, label, log):
    log(f"--- {label} ---")
    all_d = []
    both_empty = one_empty = 0
    one_empty_abs = []
    n_total = 0
    for a, b in PAIRS:
        fwd, rev = sets[(a, b)], sets[(b, a)]
        common = sorted(set(fwd) & set(rev))
        n_total += len(common)
        usable = [t for t in common if fwd[t] > 0 and rev[t] > 0]
        be = sum(1 for t in common if fwd[t] == 0 and rev[t] == 0)
        oe = [abs(fwd[t] - rev[t]) for t in common if (fwd[t] == 0) != (rev[t] == 0)]
        both_empty += be
        one_empty += len(oe)
        one_empty_abs += oe
        d = [fwd[t] - rev[t] for t in usable]
        abs_d = [abs(x) for x in d]
        all_d += d
        n_diff = sum(1 for x in d if x)
        pos, neg = sum(1 for x in d if x > 0), sum(1 for x in d if x < 0)
        log(f"{NAMES[a]} <-> {NAMES[b]}: compared={len(common)} usable={len(usable)} (both empty={be}, one empty={len(oe)}) "
            f"differing={n_diff} ({100 * n_diff / len(usable):.1f}%) mean|d|={statistics.mean(abs_d):.2f} "
            f"median|d|={statistics.median(abs_d)} max|d|={max(abs_d)}; "
            f"{NAMES[a]}->{NAMES[b]} larger in {pos}, {NAMES[b]}->{NAMES[a]} larger in {neg}")
    abs_all = [abs(x) for x in all_d]
    n = len(abs_all)
    n_diff = sum(1 for x in abs_all if x)
    nz = [x for x in abs_all if x]
    log(f"TOTAL: pairwise comparisons={n_total}; usable={n}; both directions empty={both_empty}; "
        f"exactly one direction empty={one_empty} (max |d| there = {max(one_empty_abs)})")
    log(f"  differing={n_diff} ({100 * n_diff / n:.2f}% of usable; {100 * n_diff / n_total:.2f}% of all comparisons)")
    log(f"  mean|d|={statistics.mean(abs_all):.3f} median|d|={statistics.median(abs_all)} max|d|={max(abs_all)}")
    log(f"  among differing: mean|d|={statistics.mean(nz):.2f} median|d|={statistics.median(nz)}")
    log(f"  distribution of |d| (usable): {sorted(Counter(abs_all).items())}")
    log("")


def example(sets, log):
    a, b = "17-ffaa:1:11e4", "18-ffaa:1:11e5"
    ts = sorted(t for t in set(sets[(a, b)]) & set(sets[(b, a)])
                if sets[(a, b)][t] == 18 and sets[(b, a)][t] == 20)
    log(f"Intervals with {NAMES[a]}->{NAMES[b]} = 18 and {NAMES[b]}->{NAMES[a]} = 20: {len(ts)} "
        f"({ts[0]} .. {ts[-1]})")
    log("")


def main():
    lab_dirs = sys.argv[1:4]
    lines = []

    def log(s=""):
        print(s)
        lines.append(s)

    log(f"Window: {WINDOW_START} .. {WINDOW_END}")
    viable = load(lab_dirs, viable_only=True)
    report(viable, "Viable paths (status != timeout)", log)
    example(viable, log)
    report(load(lab_dirs, viable_only=False), "All discovered paths (including timeouts)", log)
    with open("path_discrepancy_analysis.txt", "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
