# Cronjob Script

This directory contains the bash script used to run the entire measurement suite for long-term measurements.  
If the cronjob is set up as described in the root `README` of this repository, this script will be executed periodically.  
It handles executing the Python scripts in the correct order, writing logs, and moving files.

## General Usage

No direct interaction with this script is required, though it can be run manually to test the measurement suite.  

When adding or removing measurement scripts, this pipeline script must be modified accordingly.  
- New scripts can simply be pasted into the relevant section.  
- Scripts that are no longer necessary can be commented out or removed.  

The **execution order of scripts can be important** to avoid interference. For example, running the bandwidth tester before the prober may inadvertently affect latency measurements, as paths could still be recovering from the stress test.  

**Important:** The path discovery script must always remain the **first** script, as the others rely on its output.  

It is also crucial to run this script from the correct location (i.e., this directory). Running it elsewhere may cause unintended behavior.  

For debugging, you may need to temporarily disable `pipefail` and add additional output statements, since the pipeline script itself only provides rudimentary logging.  
