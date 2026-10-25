# SCIONLab Path Dynamics

Four-week longitudinal measurement study of path dynamics in the operational SCIONLab testbed.

This repository contains the measurement suite, analysis scripts, and raw dataset that accompany the paper:

> **Path Dynamics in a Deployed Path-Aware Network: Operational Measurements and Management Implications from SCIONLab**  
> Lars Herschbach, Damien Rossi, Sina Keshvadi

## Contents

- `measurement/` — scripts used to collect control-plane path sets and data-plane performance (RTT, jitter, loss, bandwidth) from three vantage points
- `analysis/` — scripts that reproduce the figures and statistics reported in the paper
- `data/` — raw JSON traces and processed summaries (July–August 2025)
- `paper/` — LaTeX source of the paper

## Measurement Campaign

- Duration: 11 July – 11 August 2025 (analysis window: 16 July – 11 August)
- Vantage points: three VMs co-located in GCP `us-central1-a`, attached to SCIONLab ISD 17, 18, and 19
- Interval: 30 minutes
- Metrics: path-set churn, RTT, jitter, packet loss, directional bandwidth

## Citation

If you use this dataset or the measurement tools, please cite the paper.
