# analyze_path_replacements.py
#
# Decomposes the path-churn events behind Figure 2 (comparer output) into their causes.
#
# Usage: python analyze_path_replacements.py <lab1_dir> <lab2_dir> <lab3_dir>
# Each <labN_dir> is the extracted raw_data.zip of that lab (containing Archive/YYYY-MM-DD/AS-*.json
# and delta_*.json). Output is also written to path_replacement_analysis.txt in the cwd.
#
# Path set A_t = paths with status != "timeout" (the comparer's definition); L_t = all listed paths.
# An event is an interval in which A_t != A_(t-1) for a directed pair (src, dst).

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


def load(lab_dirs):
    series = defaultdict(dict)  # (src, dst) -> ts -> {fp: (status, sequence)}
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
            if doc["destination"] not in NAMES:
                continue
            series[(doc["local_isd_as"], doc["destination"])][ts] = {
                p["fingerprint"]: (p.get("status"), p["sequence"]) for p in (doc.get("paths") or [])}
    return series


def delta_totals(lab_dirs):
    tot = defaultdict(lambda: [0, 0, 0])  # (src, dst) -> events, added, removed
    for lab_dir in lab_dirs:
        for path in glob.glob(os.path.join(lab_dir, "Archive", "*", "delta_*.json")):
            with open(path) as f:
                d = json.load(f)
            ts = datetime.strptime(d["timestamp"], "%Y-%m-%dT%H:%M")
            if not (WINDOW_START <= ts <= WINDOW_END) or d["change_status"] != "change_detected":
                continue
            t = tot[(d["source"], d["destination"])]
            t[0] += 1
            t[1] += sum(1 for c in d["changes"] if c["change"] == "added")
            t[2] += sum(1 for c in d["changes"] if c["change"] == "removed")
    return tot


def asn(h):
    return h.split("#")[0]


def alive(cur):
    return {fp for fp, (s, _) in cur.items() if s != "timeout"}


def classify(series):
    # returns (src,dst) -> list of event dicts
    out = {}
    for key, v in series.items():
        evs = []
        ts = sorted(v)
        for prev_t, t in zip(ts, ts[1:]):
            pa, ca = alive(v[prev_t]), alive(v[t])
            if pa == ca:
                continue
            add, rem = ca - pa, pa - ca
            if not ca:
                kind = "set_lost_listing_empty" if not v[t] else "set_lost_all_timeout"
            elif not pa:
                kind = "set_restored_from_empty" if not v[prev_t] else "set_restored_from_all_timeout"
            elif set(v[t]) != set(v[prev_t]):
                kind = "listing_change"
            else:
                kind = "status_flip"
            evs.append(dict(t=t, kind=kind, add=add, rem=rem, key=key))
        out[key] = evs
    return out


def short(label):
    return "->".join(NAMES[x] for x in label)


def main():
    lab_dirs = sys.argv[1:4]
    lines = []

    def log(s=""):
        print(s)
        lines.append(s)

    series = load(lab_dirs)
    dt = delta_totals(lab_dirs)
    events = classify(series)
    log(f"Window: {WINDOW_START} .. {WINDOW_END}; path set = status != timeout\n")

    for key in sorted(events):
        evs = events[key]
        v = series[key]
        n_add = sum(len(e["add"]) for e in evs)
        n_rem = sum(len(e["rem"]) for e in evs)
        both = [e for e in evs if e["add"] and e["rem"]]
        log(f"=== {short(key)} ===")
        d = dt.get(key, [0, 0, 0])
        log(f"events={len(evs)} added={n_add} removed={n_rem}   (delta_ files: events={d[0]} added={d[1]} removed={d[2]})")
        kinds = Counter(e["kind"] for e in evs)
        for kind in ("status_flip", "set_lost_all_timeout", "set_restored_from_all_timeout",
                     "set_lost_listing_empty", "set_restored_from_empty", "listing_change"):
            sel = [e for e in evs if e["kind"] == kind]
            if sel:
                log(f"  {kind:32s} events={len(sel):4d} paths_added={sum(len(e['add']) for e in sel):5d} "
                    f"paths_removed={sum(len(e['rem']) for e in sel):5d}")
        log(f"  same-interval add+remove events: {len(both)} of {len(evs)} ({100 * len(both) / len(evs):.1f}%)")
        all_fps = set()
        for c in v.values():
            all_fps |= set(c)
        seen, readd, tot_add = set(), 0, 0
        for e in evs:
            for fp in e["add"]:
                tot_add += 1
                readd += fp in seen
            seen |= e["add"] | e["rem"]
        # fingerprints that were alive at the very first non-empty interval count as seen
        first = next(t for t in sorted(v) if v[t])
        log(f"  distinct fingerprints listed in window: {len(all_fps)}; distinct AS-level routes: "
            f"{len({tuple(asn(h) for h in q.split()) for c in v.values() for _, q in c.values()})}")
        ever_listed_before = 0
        hist = set(alive(v[first]))
        for e in evs:
            ever_listed_before += len(e["add"] & hist)
            hist |= e["add"]
        log(f"  added paths that had already been alive earlier in the window: {ever_listed_before} of {tot_add}")
        listing_changes = [e for e in evs if e["kind"] == "listing_change"]
        for e in listing_changes:
            log(f"  listing change at {e['t']}: +{len(e['add'])} -{len(e['rem'])}")
        n_ints = len(v)
        n_empty = sum(1 for c in v.values() if not c)
        n_allto = sum(1 for c in v.values() if c and not alive(c))
        log(f"  intervals={n_ints}; empty listing={n_empty}; all listed paths timed out={n_allto}")
        # duration of status-flip down periods (in 30-min intervals)
        ts = sorted(v)
        runs = []
        for fp in all_fps:
            run = 0
            for t in ts:
                c = v[t]
                if fp in c and c[fp][0] == "timeout":
                    run += 1
                else:
                    if run:
                        runs.append(run)
                    run = 0
        if runs:
            log(f"  per-path timeout runs: n={len(runs)} median={statistics.median(runs)} intervals; "
                f"single-interval runs={sum(1 for r in runs if r == 1)} ({100 * sum(1 for r in runs if r == 1) / len(runs):.0f}%)")
        log("")

    # cross-lab coincidence of set-wide outages and of any change events
    log("=== cross-vantage-point coincidence (timestamps are interval ids) ===")
    keys = sorted(events)
    by_dst = defaultdict(list)
    for k in keys:
        by_dst[k[1]].append(k)
    for dst, ks in sorted(by_dst.items()):
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                a, b = ks[i], ks[j]
                for kinds, label in ((("set_lost_listing_empty", "set_lost_all_timeout"), "set-wide loss"),
                                     (("status_flip",), "single-path flips")):
                    ta = {e["t"] for e in events[a] if e["kind"] in kinds}
                    tb = {e["t"] for e in events[b] if e["kind"] in kinds}
                    common = ta & tb
                    n = len(set(series[a]) & set(series[b]))
                    exp = len(ta) * len(tb) / n if n else 0
                    log(f"  to {NAMES[dst]}: {short(a)} vs {short(b)} {label}: {len(ta)} / {len(tb)} events, "
                        f"{len(common)} at the same interval (expected by chance {exp:.1f})")
    log("")
    log("=== unavailable periods ===")
    for k in keys:
        v = series[k]
        ts = sorted(v)
        blocks = []
        run = []
        for t in ts:
            if not alive(v[t]):
                run.append(t)
            else:
                if run:
                    blocks.append(run)
                run = []
        if run:
            blocks.append(run)
        big = [b for b in blocks if len(b) >= 8]
        log(f"  {short(k)}: {len(blocks)} blocks with no viable path; blocks >= 4h: "
            + "; ".join(f"{b[0]:%m-%d %H:%M}..{b[-1]:%m-%d %H:%M} ({len(b)})" for b in big))
    with open("path_replacement_analysis.txt", "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
