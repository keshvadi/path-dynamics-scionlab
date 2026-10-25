# config.py
import os

# AS list adjust with your own AS
AS_FOLDER_MAP = {
    "19-ffaa:1:11de": "AS-1",
    "17-ffaa:1:11e4": "AS-2",
    "18-ffaa:1:11e5": "AS-3",
    "22-ffaa:1:11ee": "AS-4",
}

# Define AS targets and their folder name with IP address
AS_TARGETS = {
    "19-ffaa:1:11de": ("127.0.0.1", "AS-1"),
    "17-ffaa:1:11e4": ("127.0.0.1", "AS-2"),
    "18-ffaa:1:11e5": ("127.0.0.1", "AS-3"),
    "22-ffaa:1:11ee": ("127.0.0.1", "AS-4"),
}

BWTEST_SERVERS = {
    #"16-ffaa:0:1001": ("172.31.0.23", "Server-1"),
    #"17-ffaa:0:1102": ("192.33.93.177", "Server-2"),
    "19-ffaa:0:1303": ("141.44.25.144", "Server-3"),
    #"20-ffaa:0:1401": ("134.75.250.114", "Server-4"),
    "18-ffaa:0:1201": ("128.2.24.126", "Server-5"),
}