#!/usr/bin/env python3
"""Plot cross-evaluator agreement for the answer-only evaluation contract."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
_DEFAULT_SOURCE = HERE / "evaluator_agreement_source.csv"
_DEFAULT_OUTPUT = HERE / "fig_evaluator_agreement"

_parser = argparse.ArgumentParser(description=__doc__)
_parser.add_argument("--source", type=Path, default=_DEFAULT_SOURCE)
_parser.add_argument("--output-base", type=Path, default=_DEFAULT_OUTPUT)
_args, _ = _parser.parse_known_args()
SOURCE = _args.source
OUTPUT = _args.output_base

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 8,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.7,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
)

with SOURCE.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))

pairs = [row["evaluator_pair"] for row in rows]
agreement = [float(row["agreement_pct"]) for row in rows]
kappa = [float(row["cohen_kappa"]) for row in rows]

fig, ax = plt.subplots(figsize=(3.35, 2.15))
y = list(range(len(rows)))
bars = ax.barh(
    y,
    agreement,
    height=0.56,
    color=["#6E91D8", "#7AA6C2", "#6DB6A2"],
    edgecolor="white",
    linewidth=0.6,
)

ax.set_xlim(0, 100)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xlabel("Pairwise agreement on binary evaluator judgments (%)")
ax.set_yticks(y, labels=pairs)
ax.invert_yaxis()
ax.grid(axis="x", color="#D9DEE7", linewidth=0.55, alpha=0.9)
ax.set_axisbelow(True)

for bar, value, kappa_value in zip(bars, agreement, kappa):
    cy = bar.get_y() + bar.get_height() / 2
    ax.text(
        value - 1.5,
        cy,
        f"{value:.1f}%",
        ha="right",
        va="center",
        color="white",
        fontsize=8.2,
        fontweight="bold",
    )
    ax.text(
        2.0,
        cy,
        rf"$\kappa={kappa_value:.3f}$",
        ha="left",
        va="center",
        color="#243447",
        fontsize=7.2,
    )

fig.tight_layout(pad=0.35)
for suffix in ("pdf", "svg", "png"):
    kwargs = {"dpi": 600} if suffix == "png" else {}
    fig.savefig(OUTPUT.with_suffix(f".{suffix}"), bbox_inches="tight", **kwargs)
plt.close(fig)
