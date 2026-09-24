#!/usr/bin/env python3
"""Regenerate the cross-benchmark trajectory-value heatmap."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Rectangle
import numpy as np


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "fig_cross_benchmark_trajectory_value_source.csv"
OUTPUT = HERE / "fig_cross_benchmark_trajectory_value"

BENCHMARKS = ["Omni-MATH-2", "JEEBench", "SciBench", "LAB-Bench", "MaScQA"]
COLUMNS = [
    ("wrong", "OSS"),
    ("wrong", "Gemma"),
    ("correct", "OSS"),
    ("correct", "Gemma"),
]


def load_records() -> dict[tuple[str, str, str], dict[str, str]]:
    records: dict[tuple[str, str, str], dict[str, str]] = {}
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (row["benchmark"], row["proposal_correctness"], row["model"])
            records[key] = row
    return records


def main() -> None:
    global SOURCE, OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output-base", type=Path, default=OUTPUT)
    args = parser.parse_args()
    SOURCE = args.source
    OUTPUT = args.output_base

    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 8,
            "axes.linewidth": 0.8,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    records = load_records()
    mismatch_shares = np.zeros((len(BENCHMARKS), len(COLUMNS)))
    flip_rates = np.zeros_like(mismatch_shares)
    flip_counts = np.zeros_like(mismatch_shares, dtype=int)

    for row_index, benchmark in enumerate(BENCHMARKS):
        for column_index, (correctness, model) in enumerate(COLUMNS):
            row = records[(benchmark, correctness, model)]
            helpful_share = float(
                row["helpful_share_among_flips_pct"]
            )
            mismatch_shares[row_index, column_index] = (
                helpful_share if correctness == "wrong" else 100.0 - helpful_share
            )
            flip_rates[row_index, column_index] = float(
                row["correctness_flip_rate_pct"]
            )
            flip_counts[row_index, column_index] = int(
                row["correctness_flip_count"]
            )

    wrong_helpful_cmap = LinearSegmentedColormap.from_list(
        "wrong_helpful",
        ["#FCFBF8", "#2FB47C"],
    )
    correct_harmful_cmap = LinearSegmentedColormap.from_list(
        "correct_harmful",
        ["#FCFBF8", "#E86F9A"],
    )
    norm = Normalize(vmin=0, vmax=50, clip=True)

    fig, ax = plt.subplots(figsize=(6.45, 3.85))
    ax.set_xlim(-0.5, len(COLUMNS) - 0.5)
    ax.set_ylim(len(BENCHMARKS) - 0.5, -0.5)

    ax.set_xticks(range(len(COLUMNS)), ["OSS", "Gemma", "OSS", "Gemma"])
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=5)
    ax.set_yticks(range(len(BENCHMARKS)), BENCHMARKS)
    ax.tick_params(axis="y", length=0, pad=7)

    ax.text(
        0.5,
        -0.95,
        "Wrong proposal, helpful effect",
        ha="center",
        va="bottom",
        fontsize=9.5,
        fontweight="bold",
        color="#147A5B",
        transform=ax.transData,
    )
    ax.text(
        2.5,
        -0.95,
        "Correct proposal, harmful effect",
        ha="center",
        va="bottom",
        fontsize=9.5,
        fontweight="bold",
        color="#C84F78",
        transform=ax.transData,
    )

    for row_index in range(len(BENCHMARKS)):
        for column_index in range(len(COLUMNS)):
            cmap = (
                wrong_helpful_cmap
                if column_index < 2
                else correct_harmful_cmap
            )
            ax.add_patch(
                Rectangle(
                    (column_index - 0.5, row_index - 0.5),
                    1,
                    1,
                    facecolor=cmap(norm(mismatch_shares[row_index, column_index])),
                    edgecolor="white",
                    linewidth=1.3,
                )
            )

    ax.axvline(1.5, color="white", linewidth=4)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for row_index in range(len(BENCHMARKS)):
        for column_index in range(len(COLUMNS)):
            ax.text(
                column_index,
                row_index - 0.08,
                f"{mismatch_shares[row_index, column_index]:.1f}%",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                color="#202329",
            )
            ax.text(
                column_index,
                row_index + 0.27,
                (
                    f"flip {flip_rates[row_index, column_index]:.1f}%  "
                    f"n={flip_counts[row_index, column_index]:,}"
                ),
                ha="center",
                va="center",
                fontsize=6.5,
                color="#2B2E34",
            )

    fig.subplots_adjust(left=0.20, right=0.985, top=0.80, bottom=0.04)
    fig.savefig(f"{OUTPUT}.pdf", bbox_inches="tight")
    fig.savefig(f"{OUTPUT}.svg", bbox_inches="tight")
    fig.savefig(f"{OUTPUT}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
