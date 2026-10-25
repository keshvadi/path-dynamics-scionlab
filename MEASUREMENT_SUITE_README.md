# SCION measurement for multipath delevopement
This project provides measurement scripts, analysis scripts as well as 4 weeks of raw data gathered from the 11th of July to the 11th of august. With the already gathered data or the use of the maesurement and analysis suite in a production environment such as SCIERA, crucial data can be gathered, the insights of which may prove integral in implementing Multipath Protocols such as MPQUIC on SCION.


## Motivation and initial Idea

With this project, we aim to provide a comprehensive and modular testing and analysis suite that can be used to gather, analyze, and interpret data collected over long timeframes within a SCION network—whether in the SCIONLab testbed or a full production deployment such as SCIERA.

The resulting data can help guide the implementation or migration of protocols into the SCION environment, ensuring that SCION’s novel attributes are fully leveraged. This is particularly relevant for multipath protocols such as MP-QUIC. Since SCION inherently supports multipath communication, protocols like MP-QUIC can utilize multiple available SCION paths—potentially diverse in capacity, latency, or reliability—to transmit data, rather than relying on a single path as is common in today’s Internet.


To gather the needed data, we have set up 4 ASes in the SCIONLab environment. These will run as 4 separate Google Cloud machines. The 4 chosen machines are the following:

- 19-ffaa:1:11de 	Lars Herschbach ScionLab 1 	EU 	Magdeburg AP 	VPN:50000
- 17-ffaa:1:11e4 	Lars Herschbach ScionLab 2 	Switzerland 	ETHZ-AP 	VPN:50001
- 18-ffaa:1:11e5 	Lars Herschbach ScionLab 3 	North America 	CMU AP 	VPN:50000
- 22-ffaa:1:11ee 	Lars Herschbach ScionLab 4 	Taiwan 	NTU 	VPN:50000

These were chosen based on the following criteria:
- Geographical diversity
- Accessibility (through the SCIONLab VPN option)
- Stability (or lack thereof in some cases giving us more representative data)
  
All of these machines follow the same setup and are created attached to their Access Points via VPN to avoid NAT issues. Their geographical diversity allows us to replicate results gathered by related work before us. The instability of some of these ASes allow us to gather more accurate data as opposed to a fully static sandbox environment, while the diversity of ASes should be sufficient enough, that at least one should always be able to measure.

After completing the measurement AS-4 in ISD-22 was excluded from the results as it experienced complete unaccesbility throughout the measurement period.

Each AS will run a suite of python scripts which will gather data to all 3 other ASes. This is done in the following way:

1. pathdiscover_scion.py discovers paths to the 3 other ASes. These are saved as timestamped json files for further use by the other scripts, analysis down the line and archival purposes.
2. comparer.py Compares the path availability of inter AS paths between two test instances providing us data on Path Churn as well as full connectivity breakdown (observed in ISD 17).
3. prober_scion.py will run the adapted “scion ping” command using SCMP to probe path latency as well as packet loss and (if possible) packet sequencing. This data will be saved per path per AS in timestamped json.
4. tr_collector_scion.py runs the adapted “scion traceroute” command using SCMP to probe the AS-level hops (hop count), RTT and path structure. The results are saved per path per AS in timestamped JSON files.
5. bw_collector_scion.py performs automated bandwidth testing from the local AS to 4 remote ASes over all available SCION paths, using predefined target rates (1–250 Mbps). For each direction (client-to-server and server-to-client), it collects detailed performance metrics including attempted and achieved throughput, packet loss percentage, and interarrival time (min/avg/max/mdev). Results are saved in timestamped JSON files for later analysis and benchmarking.
6. bw_alldiscover_path.py works like bw_collector_scion.py but iterates over a set number of available paths
7. bw_multipath.py runs two simultanious subprocesses over the same paths used in bw_alldiscover_path.py allowing us to compare single path and this simple multipath approach in terms of latency, loss etc.
8. mp-prober.py works like prober_scion.py and tests three random paths simultaniously allowing us to compare single path to multipath.
9. Custom Cron Job: will run the 4 scripts in a set interval and handle cleanup of the working directories and updates of the Archive directory from which data may be pulled during testing.

Some of these scripts were not used for the 4 weeks testing period as they are deprecated. Used were pathdiscovery, comparer, prober, mp-prober, bw_alldiscover, bw_mltipath and tr_collector.
   
This approach gives us both a compiled CSV (for some of the scripts) as well as all the raw data at the end. Through the structure of working and archive directories we are also able to access the already collected data at any point without interfering with the ongoing measurements. This may be used for backup needs.

For the analysis we provide one script each to compile and calculate the gathered statistics as well as to create representative graphs.
These scripts are found in the AnalysisScripts directory. By simply changing the variable for the directory it can be run on any subset of data. Resulting graphs are output into subdirs while raw numbers are printed to the CLI and written to files.
These scripts can be easily adapted to calculate other statistics or create other graphs, depending on what is most relevant to the research being conducted.
All scripts expect all raw data in one single directory so the data must be moved from the Dated directories where it was saved during measurement to a seperate directory for analysis. 


## Structure of this repo

This Repo contains the structure which would be found after running the measurement suite on a host. This includes the Data directory which is currently empty but would be used for the gathered data. The AnalysisResults directory only serves to present the raw and analyzed data from our testing period, it is not required when running the measurement suite.

## Cron Job Setup
1. To create the cronjob. Make sure that the repo is at /home/vagrant.

2. Run the command crontab -e and select you text editior

3. Paste the following entry:
```
SHELL=/bin/bash
PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin
# Edit this file to introduce tasks to be run by cron.
# 
# Each task to run has to be defined through a single line
# indicating with different fields when the task will be run
# and what command to run for the task
# 
# To define the time you can provide concrete values for
# minute (m), hour (h), day of month (dom), month (mon),
# and day of week (dow) or use '*' in these fields (for 'any').# 
# Notice that tasks will be started based on the cron's system
# daemon's notion of time and timezones.
# 
# Output of the crontab jobs (including errors) is sent through
# email to the user the crontab file belongs to (unless redirected).
# 
# For example, you can run a backup of all your user accounts
# at 5 a.m every week with:
# 0 5 * * 1 tar -zcf /var/backups/home.tgz /home/
# 
# For more information see the manual pages of crontab(5) and cron(8)
# 
# m h  dom mon dow   command
*/5 * * * * /home/vagrant/mpquic-on-scion-ipc/Scripts/pipeline.sh
```

Change number of bandwith tests at this time : Mon Jul 14 17:24:14 UTC 2025 on Scion Machine
Data as of Wednesday Jul 16 is fully operational and will be used for our final analysis
