#!/usr/bin/env python3
"""Regenerate the per-benchmark leave-one-out rates figure from its source CSV."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.75,
        "legend.frameon": False,
        "xtick.major.width": 0.65,
        "ytick.major.width": 0.65,
    }
)


BENCHMARK_ORDER = [
    "Omni-MATH-2",
    "JEEBench",
    "SciBench",
    "LAB-Bench",
    "MaScQA",
]

# Distinct hues preserve the correctness-value distinction without relying on
# a red-versus-green encoding.
SERIES = [
    ("wrong_help", "Wrong helpful", "#2FB47C"),
    ("wrong_harm", "Wrong harmful", "#4E88E5"),
    ("correct_help", "Correct helpful", "#C1843F"),
    ("correct_harm", "Correct harmful", "#E86F9A"),
]


def load_rates(source: Path) -> dict[str, dict[int, dict[str, float]]]:
    rates: dict[str, dict[int, dict[str, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    with source.open(newline="") as handle:
        for row in csv.DictReader(handle):
            rates[row["benchmark"]][int(row["k"])][row["signal_category"]] = float(
                row["eligible_signal_rate_pct"]
            )
    return rates


def plot(source: Path, output_base: Path) -> None:
    rates = load_rates(source)
    fig, axes = plt.subplots(3, 2, figsize=(6.8, 5.25))
    axes = axes.ravel()

    for panel_index, (ax, benchmark) in enumerate(zip(axes, BENCHMARK_ORDER)):
        ks = sorted(rates[benchmark])
        x = np.arange(len(ks))
        width = 0.18
        for series_index, (key, label, color) in enumerate(SERIES):
            values = [rates[benchmark][k][key] for k in ks]
            offset = (series_index - 1.5) * width
            ax.bar(x + offset, values, width, color=color, label=label)

        largest = max(
            rates[benchmark][k][key]
            for k in ks
            for key, _, _ in SERIES
        )
        ax.set_title(benchmark, loc="left", pad=4)
        ax.set_xticks(x, [str(k) for k in ks])
        ax.set_ylim(0, max(5, largest * 1.18))
        ax.grid(axis="y", color="#E8E8E8", linewidth=0.6)
        ax.set_axisbelow(True)
        if panel_index >= 4:
            ax.set_xlabel("Pool size $K$")
        if panel_index % 2 == 0:
            ax.set_ylabel("Eligible LOO signals (%)")

    legend_ax = axes[-1]
    legend_ax.axis("off")
    legend_ax.set_xlim(0, 1)
    legend_ax.set_ylim(0, 1)
    legend_ax.text(
        0.5,
        0.76,
        "LOO signal category",
        ha="center",
        va="center",
        fontsize=9.2,
        fontweight="bold",
    )
    legend_positions = [
        (0.05, 0.51),
        (0.53, 0.51),
        (0.05, 0.29),
        (0.53, 0.29),
    ]
    for (_, label, color), (x_pos, y_pos) in zip(SERIES, legend_positions):
        legend_ax.add_patch(
            plt.Rectangle(
                (x_pos, y_pos - 0.055),
                0.105,
                0.11,
                transform=legend_ax.transAxes,
                facecolor=color,
                edgecolor="none",
            )
        )
        legend_ax.text(
            x_pos + 0.135,
            y_pos,
            label,
            transform=legend_ax.transAxes,
            ha="left",
            va="center",
            fontsize=8.4,
        )

    fig.tight_layout(rect=[0.005, 0.005, 0.995, 0.995], h_pad=0.65, w_pad=0.75)
    output_base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".png"), dpi=450, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("figures/fig_loo_by_k_appendix_source.csv"),
    )
    parser.add_argument(
        "--output-base",
        type=Path,
        default=Path("figures/fig_loo_by_k_appendix"),
    )
    args = parser.parse_args()
    plot(args.source, args.output_base)


if __name__ == "__main__":
    main()
