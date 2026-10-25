import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Shared by all analysis scripts: every figure has the same size and font sizes, and is saved as a vector PDF.
FIGSIZE = (6.5, 3.2)


def archive_dir():
    return os.environ.get("ARCHIVE_DIR", ".")


plt.rcParams.update({
    "figure.figsize": FIGSIZE,
    "savefig.format": "pdf",
    "pdf.fonttype": 42,
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "legend.title_fontsize": 8,
    "lines.linewidth": 1.0,
    "lines.markersize": 3,
})
