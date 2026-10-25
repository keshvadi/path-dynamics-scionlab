# Path Dynamics in a Deployed Path-Aware Network: SCIONLab Measurements

Four-week longitudinal measurement study of path dynamics in the operational SCIONLab testbed.

This repository contains the measurement suite, analysis scripts, and raw dataset that accompany the paper:

> **Path Dynamics in a Deployed Path-Aware Network: Operational Measurements and Management Implications from SCIONLab**  
> Lars Herschbach, Damien Rossi, Sina Keshvadi

---

## Measurement Campaign

- **Duration:** July 11 – August 11, 2025 (analysis uses July 16 – August 11)
- **Vantage points:** Three VMs co-located in GCP `us-central1-a`, attached to SCIONLab ISDs 17, 18, and 19
- **Measurement interval:** Every 30 minutes
- **Metrics collected:**
  - Path-set churn (availability, additions, removals, lifetimes)
  - Round-trip time (RTT), jitter, packet loss  
  - Directional bandwidth (achieved throughput, packet loss, interarrival times)
  - Single-path vs. multipath performance deltas

---

## Repository Structure

### `measurement/`
Python scripts used to collect control-plane and data-plane measurements from three vantage points.

**Key scripts:**
- `pathdiscovery_scion.py` — Discovers available paths and saves them as timestamped JSON
- `comparer.py` — Detects path churn by comparing consecutive path sets
- `prober_scion.py` — Measures RTT, jitter, and loss using SCMP probes
- `tr_collector_scion.py` — Collects hop-level info via traceroute
- `bw_alldiscover_path.py` — Single-path bandwidth testing across all available paths
- `mp-prober.py` — Multipath prober (concurrent probes on random paths)
- `bw_multipath.py` — Concurrent bandwidth tests on multiple paths

**Execution:** Normally orchestrated by the cronjob in `scripts/pipeline.sh`. Can be run manually for development or verification. See `measurement/README.md` for details.

### `analysis/`
Scripts to process raw measurement data and generate the figures and statistics in the paper.

**Key scripts:**
- `analyze_comparer.py` — Path churn statistics and visualizations
- `analyze_prober.py` — Per-path RTT, jitter, loss analysis
- `analyze_bw.py` — Bandwidth metrics across paths  
- `analyze_sp-mp-prober.py` — Single-path vs. multipath RTT comparison
- `analyze_sp-mp-bw.py` — Single-path vs. multipath bandwidth comparison

**Usage:**
```bash
cd analysis/
python3 analyze_prober.py       # Analyzes raw prober data (JSON files)
python3 analyze_bw.py           # Analyzes bandwidth data
python3 analyze_sp-mp-prober.py # SP vs MP comparison
```

All scripts expect raw data files in a single directory (see "Reproducing Results" below).

See `analysis/README.md` for detailed documentation.

### `data/`
Processed measurement data and pre-computed analysis results.

**Structure:**
```
data/
├── Lab1/          # Results from vantage point 1 (ISD 17)
│   ├── raw_data.zip           # Compressed archive of all raw JSON traces
│   ├── selected_paths.json     # Sample of discovered paths
│   └── Analysis/               # Pre-computed statistics and plots
│       ├── *_analysis.txt      # Text summaries
│       ├── comparer_plots/     # Path churn visualizations
│       ├── prober_plots/       # RTT/loss plots
│       ├── sp_mp_*_plots/      # Single vs multipath comparison plots
│       └── bw_plots/           # Bandwidth plots
├── Lab2/          # Results from vantage point 2 (ISD 18)
└── Lab3/          # Results from vantage point 3 (ISD 19)
```

**Data Caveat:** Raw measurement data collected between July 11–16 differs from data after July 16 due to updates to the measurement suite (file naming, path count, internal adjustments). Analysis was conducted only on the July 16–August 11 dataset. Earlier data is archived but not directly comparable.

### `paper/`
LaTeX source, final PDF, response letter, and all supporting files.

**Contents:**
- `main.tex` — Main paper manuscript
- `main.bib` — Bibliography  
- `main.pdf` — Final compiled PDF
- `response.txt` — Response to reviewer comments
- `figures/` — Paper figures (organized by analysis type)
  - `1_Comparer/` — Path churn figures
  - `2_Prober/` — RTT and loss figures
  - `3_Bandwidth/` — Bandwidth figures
  - `4_SP-MP-Prober/` — Single vs multipath latency comparison
  - `5_SP-MP-bw/` — Single vs multipath bandwidth comparison
- `*.bst`, `sn-jnl.cls` — Bibliography styles and document class

### `scripts/`
The cronjob pipeline orchestrator.

- `pipeline.sh` — Runs measurement scripts in the correct order, handles file organization
- `README.md` — Setup and usage instructions

### `MEASUREMENT_SUITE_README.md`
Original documentation from the ScionPathML repository describing the measurement suite's design, setup, and original objectives.

---

## Reproducing the Paper's Results

### Prerequisites
- Python 3.8+
- Required libraries: `matplotlib`, `statistics`, `dateutil`

```bash
pip install matplotlib statistics python-dateutil
```

### Step 1: Extract Raw Data
```bash
cd data/Lab1
unzip raw_data.zip
# Repeat for Lab2 and Lab3
```

### Step 2: Run Analysis Scripts
Analysis scripts expect all raw data in a single directory. Create a working directory and copy/symlink the data:

```bash
mkdir analysis_workspace
# Copy all extracted JSON files from all labs into this directory
# (Each lab's raw data should be merged together for aggregate analysis)

cd analysis_workspace
cp ../path-dynamics-scionlab/analysis/*.py .
python3 analyze_prober.py
python3 analyze_bw.py
python3 analyze_comparer.py
# ... etc. for other scripts
```

This will generate:
- `.txt` files with statistical summaries (printed to stdout and saved)
- Subdirectories with plots (PNG, PDF):
  - `prober_plots/`
  - `bw_plots/`
  - `comparer_plots/`
  - `sp_mp_*_plots/`

### Step 3: Compare with Paper Figures
Generated plots should match the figures in `paper/figures/`. 

The paper's figures are aggregates from the three vantage points. See the individual analysis script docstrings for details on metric definitions, time-window alignment, and filtering.

---

## File Organization Rationale

- **`measurement/`** — All data-collection tooling in one place, mirroring the original `PythonTests/` structure
- **`analysis/`** — Self-contained analysis suite; can be copied and run standalone  
- **`data/`** — Raw and processed results organized by vantage point (Lab1–3), easy to subset or extend
- **`paper/`** — Complete, self-contained LaTeX build with all dependencies (figures, bibliography styles, templates)
- **`scripts/`** — Operational infrastructure (pipeline, cronjob setup)

This separation ensures:
- The measurement suite can be deployed independently in a production network
- Analysis can be re-run on new or subset data without the paper build files
- The paper's LaTeX source remains self-contained and reproducible
- Clear boundaries between experimental workflow and publication artifacts

---

## Citation

If you use this dataset or the measurement tools, please cite:

```bibtex
@article{herschbach_path_dynamics_scionlab,
  title={Path Dynamics in a Deployed Path-Aware Network: 
         Operational Measurements and Management Implications from SCIONLab},
  author={Herschbach, Lars and Rossi, Damien and Keshvadi, Sina},
  year={2025}
}
```

---

## License

See `LICENSE` file for details.

---

## Support

For questions or issues related to the measurement suite, see `MEASUREMENT_SUITE_README.md` and individual `README.md` files in each directory (`measurement/`, `analysis/`, `scripts/`).

For questions related to the paper's methodology or interpretation, refer to the paper itself and the analysis script docstrings.
