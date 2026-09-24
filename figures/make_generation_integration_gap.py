#!/usr/bin/env python3
"""Regenerate the candidate-availability and integration-gap figure."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent

COLORS = {
    "independent": "#6F7A86",
    "full": "#2F786B",
    "candidate": "#CB8A25",
    "connector": "#D7DCE2",
    "text": "#17191C",
}


def load_rows(source: Path) -> list[dict[str, str]]:
    with source.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def plot(source: Path, output_base: Path, panel_title: str | None) -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 7.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    rows = load_rows(source)
    labels = [row["benchmark"] for row in rows]
    independent = [float(row["independent_k0_accuracy_pct"]) for row in rows]
    full = [float(row["full_k5_accuracy_pct"]) for row in rows]
    candidate = [
        float(row["at_least_one_correct_proposal_pct"]) for row in rows
    ]
    y_positions = list(range(len(rows) - 1, -1, -1))

    fig, ax = plt.subplots(figsize=(3.10, 3.10))
    for y, values in zip(y_positions, zip(independent, full, candidate)):
        ax.plot(
            [min(values), max(values)],
            [y, y],
            color=COLORS["connector"],
            linewidth=2.2,
            solid_capstyle="round",
            zorder=1,
        )

    ax.scatter(
        independent,
        y_positions,
        s=30,
        marker="o",
        color=COLORS["independent"],
        label=r"Independent $K=0$",
        zorder=3,
    )
    ax.scatter(
        full,
        y_positions,
        s=34,
        marker="s",
        color=COLORS["full"],
        label=r"Full pool $K=5$",
        zorder=3,
    )
    ax.scatter(
        candidate,
        y_positions,
        s=40,
        marker="D",
        color=COLORS["candidate"],
        label="Candidate available",
        zorder=3,
    )

    for index, y in enumerate(y_positions):
        ax.annotate(
            f"{independent[index]:.1f}",
            (independent[index], y),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=6.8,
            color=COLORS["text"],
        )
        ax.annotate(
            f"{full[index]:.1f}",
            (full[index], y),
            xytext=(0, -10),
            textcoords="offset points",
            ha="center",
            va="top",
            fontsize=6.8,
            color=COLORS["text"],
        )
        ax.annotate(
            f"{candidate[index]:.1f}",
            (candidate[index], y),
            xytext=(6, -1),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=6.8,
            color=COLORS["text"],
        )

    ax.set_yticks(y_positions, labels)
    ax.set_xlim(36, 101)
    ax.set_xticks([40, 60, 80, 100])
    ax.set_xlabel("Share of problems (%)")
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    if panel_title:
        ax.set_title(panel_title, loc="left", fontsize=8.5, fontweight="bold")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.17),
        ncol=3,
        frameon=False,
        fontsize=6.2,
        handletextpad=0.35,
        columnspacing=0.75,
        borderaxespad=0,
    )

    fig.subplots_adjust(left=0.28, right=0.95, top=0.97, bottom=0.24)
    output_base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=HERE / "fig_generation_integration_gap_source.csv",
    )
    parser.add_argument(
        "--output-base",
        type=Path,
        default=HERE / "fig_generation_integration_gap",
    )
    parser.add_argument("--panel-title")
    args = parser.parse_args()
    plot(args.source, args.output_base, args.panel_title)


if __name__ == "__main__":
    main()
