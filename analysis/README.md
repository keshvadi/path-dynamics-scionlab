# Analysis Scripts

This directory contains the analysis scripts used to process the raw data gathered via the `PythonTest` measurement suite.  

In their current form, the scripts calculate and visualize the statistics that were most relevant for our research. However, their modular design makes them easily adaptable to generate additional or alternative statistics depending on the user’s needs.

---

## General Usage

All scripts follow the same workflow:

1. **Input Data**  
   - Place all raw data files to be analyzed in a single directory.  
   - No further sorting or subfolder structure is required.  
   - Each script will automatically detect and parse the relevant files based on filename prefixes.
   - the prefix per data source are the following: (AS-* for the path data), (delta* for the comparer data), (BW_* for the Bandwidth data), (prober_* for the prober data), (BW_P* for the multipath Bandwidth data) and lastly (mp_prober* for the multipath prober data) 

2. **Execution**  
   - Run the desired script directly with Python (e.g., `python3 analyze_prober.py`).  
   - Each script is self-contained and can be run independently.  

3. **Output**  
   - **Console:** Analysis results are printed to the CLI for quick inspection.  
   - **Text Reports:** A `.txt` file containing the results is saved in the working directory.  
   - **Graphs:** Figures (e.g., time series, comparisons, boxplots) are generated and saved in dedicated subfolders for clarity.  

---

## Script Overview

- **Prober Analysis (`analyze_prober.py`)**  
  Processes latency, jitter, packet loss, and sequence issues from prober measurements. Produces both per-AS plots and combined comparison graphs.  

- **Bandwidth Analysis (`analyze_bw.py`)**  
  Evaluates achievable bandwidth, packet loss, and interarrival metrics for single-path and multipath runs.  

- **SP vs MP Comparison (`compare_sp_mp_bw.py` & `compare_sp_mp_prober.py`)**  
  Matches single-path (SP) and multipath (MP) runs within the same measurement intervals. Produces difference plots to quantify performance deltas.  

- **Delta Analysis (`analyze_delta.py`)**  
  Detects and visualizes path changes over time, including churn statistics, added/removed paths, and path lifetimes.  

---

## Extensibility

These scripts are designed with flexibility in mind.  
Users can:
- Modify metric calculations or add new ones.  
- Adjust time window matching for different synchronization tolerances.  
- Extend plotting functions for customized visualizations.  

---

## Requirements

- Python 3.8+  
- Libraries: `matplotlib`, `statistics`, `dateutil` (for timestamp parsing)  

