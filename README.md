# Path Dynamics in a Deployed Path-Aware Network: SCIONLab Measurements

Measurement suite, analysis scripts, and dataset from a four-week SCIONLab study.

## Campaign

- **When:** July 11 – August 11, 2025, every 30 minutes. Published analysis uses July 16 – August 11. Earlier traces remain in the archives; file names, path count, and suite internals changed before July 16, so the two windows stay separate.
- **Where:** Three VMs in GCP `us-central1-a`, attached to SCIONLab ISDs 17, 18, and 19.
- **What:** Path-set churn, RTT, jitter, packet loss, directional bandwidth, and single-path versus multipath performance.

## Repository

### `measurement/`

Collection scripts. See `measurement/README.md`.

- `pathdiscovery_scion.py` — available paths, saved as timestamped JSON
- `comparer.py` — path-set changes between consecutive discoveries
- `prober_scion.py` — RTT, jitter, and loss (SCMP)
- `tr_collector_scion.py` — hop-level traceroute
- `bw_alldiscover_path.py` — single-path bandwidth on each available path
- `mp-prober.py` — concurrent probes on several paths
- `bw_multipath.py` — concurrent bandwidth tests

### `analysis/`

Scripts for the measurements above. See `analysis/README.md`.

- `analyze_comparer.py`
- `analyze_prober.py`
- `analyze_bw.py`
- `analyze_sp-mp-prober.py`
- `analyze_sp-mp-bw.py`

### `data/`

One directory per vantage point: `Lab1` (ISD 17), `Lab2` (ISD 18), `Lab3` (ISD 19). Each has `raw_data.zip`, `selected_paths.json`, and `Analysis/` with the precomputed summaries and plots.

### `scripts/`

`pipeline.sh` runs the measurement scripts and organizes their output. See `scripts/README.md`.

### `paper/`

Manuscript.

`MEASUREMENT_SUITE_README.md` describes how the suite is set up.

## Reproducing the analysis

Python 3.8+, plus `matplotlib` and `python-dateutil`. `statistics` is in the standard library.

```bash
pip install matplotlib python-dateutil
```

Each analysis script reads the JSON files in one directory (`ARCHIVE_DIR`, defaulting to the working directory). Inside a zip those files sit under `Archive/YYYY-MM-DD/`. Flatten one lab, then run the scripts:

```bash
mkdir -p work && cd work
unzip -q ../data/Lab1/raw_data.zip
find Archive -name '*.json' -exec cp -t . {} +
python3 ../analysis/analyze_prober.py
python3 ../analysis/analyze_bw.py
python3 ../analysis/analyze_comparer.py
```

Repeat for `Lab2` and `Lab3` in their own directories. Each script prints a summary, writes a `.txt` report, and saves plots beside it.

## Citation

```bibtex
@article{herschbach2025path,
  title={Path dynamics in a deployed path-aware network: A measurement study of scionlab},
  author={Herschbach, Lars and Rossi, Damien and Keshvadi, Sina},
  journal={arXiv preprint arXiv:2509.04695},
  year={2025}
}
```

## License

See `LICENSE`.
