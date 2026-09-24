#!/usr/bin/env python3
"""Regenerate Figure 3 as the direction of non-neutral LOO effects."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7.2,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.75,
        "legend.frameon": False,
        "xtick.major.width": 0.65,
        "ytick.major.width": 0,
    }
)


HELPFUL = "#6F91E5"
HARMFUL = "#E985A7"
HELPFUL_TEXT = "#365FAE"
HARMFUL_TEXT = "#B4446C"
GRID = "#E8E8E8"
TEXT = "#1A1A1A"
MODEL_ORDER = ["OSS", "Gemma"]
PROPOSAL_ORDER = ["wrong", "correct"]


def load_rows(source: Path) -> dict[str, dict[str, dict[str, float | int]]]:
    rows: dict[str, dict[str, dict[str, float | int]]] = {}
    with source.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["metric"] != "In-pool LOO":
                continue
            eligible = int(row["eligible_count"])
            helpful_count = int(row["helpful_count"])
            harmful_count = int(row["harmful_count"])
            rows.setdefault(row["model"], {})[row["proposal_correctness"]] = {
                "eligible": eligible,
                "helpful_count": helpful_count,
                "harmful_count": harmful_count,
                "helpful_share": 100 * helpful_count / (helpful_count + harmful_count),
                "harmful_share": 100 * harmful_count / (helpful_count + harmful_count),
                "flip_rate": 100 * (helpful_count + harmful_count) / eligible,
            }
    return rows


def annotate_rate(
    ax: plt.Axes,
    *,
    value: float,
    count: int,
    side: str,
    y: float,
) -> None:
    """Place each conditional share and event count outside its bar."""
    if side == "helpful":
        x = value + 3.0
        horizontal_alignment = "left"
    else:
        x = -value - 3.0
        horizontal_alignment = "right"

    ax.text(
        x,
        y,
        f"{value:.1f}%\n$n$={count:,}",
        ha=horizontal_alignment,
        va="center",
        color=TEXT,
        fontsize=6.15,
        fontweight="semibold",
        linespacing=0.95,
        clip_on=False,
    )


def plot(source: Path, output_base: Path) -> None:
    rows = load_rows(source)
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(3.25, 3.42),
        sharex=True,
        gridspec_kw={"hspace": 0.82},
    )

    for panel_index, (ax, model) in enumerate(zip(axes, MODEL_ORDER)):
        y_positions = [1, 0]
        for y, proposal_correctness in zip(y_positions, PROPOSAL_ORDER):
            row = rows[model][proposal_correctness]
            helpful_share = float(row["helpful_share"])
            harmful_share = float(row["harmful_share"])
            ax.barh(
                y,
                -harmful_share,
                height=0.42,
                color=HARMFUL,
                edgecolor="white",
                linewidth=0.35,
            )
            ax.barh(
                y,
                helpful_share,
                height=0.42,
                color=HELPFUL,
                edgecolor="white",
                linewidth=0.35,
            )
            annotate_rate(
                ax,
                value=harmful_share,
                count=int(row["harmful_count"]),
                side="harmful",
                y=y,
            )
            annotate_rate(
                ax,
                value=helpful_share,
                count=int(row["helpful_count"]),
                side="helpful",
                y=y,
            )

        wrong_flip = float(rows[model]["wrong"]["flip_rate"])
        correct_flip = float(rows[model]["correct"]["flip_rate"])
        ax.set_yticks(
            y_positions,
            [
                f"Wrong answer\nFlip rate: {wrong_flip:.1f}%\n(all eligible)",
                f"Correct answer\nFlip rate: {correct_flip:.1f}%\n(all eligible)",
            ],
        )
        ax.tick_params(axis="y", pad=4)
        ax.axvline(0, color="#5B5B5B", linewidth=0.8, zorder=0)
        for x in (-100, -50, 50, 100):
            ax.axvline(x, color=GRID, linewidth=0.6, zorder=0)
        ax.set_xlim(-108, 108)
        ax.set_ylim(-0.45, 1.55)
        ax.set_title(
            f"{chr(65 + panel_index)}  {model}",
            loc="left",
            pad=3,
            fontsize=8.5,
            fontweight="bold",
        )
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color("#4C4C4C")

    for ax in axes:
        ax.text(
            -50,
            1.34,
            "Harmful",
            ha="center",
            va="center",
            color=HARMFUL_TEXT,
            fontsize=7.5,
            fontweight="bold",
        )
        ax.text(
            50,
            1.34,
            "Helpful",
            ha="center",
            va="center",
            color=HELPFUL_TEXT,
            fontsize=7.5,
            fontweight="bold",
        )

    for ax in axes:
        ax.set_xticks([-100, -50, 0, 50, 100])
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{abs(x):g}"))
        ax.tick_params(axis="x", bottom=True, labelbottom=True)
        ax.set_xlabel("Share among correctness flips (%)", labelpad=4)

    fig.subplots_adjust(left=0.31, right=0.985, top=0.96, bottom=0.115)

    output_base.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(output_base.with_suffix(".png"), dpi=600, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("figures/fig_correctness_flip_direction_source.csv"),
    )
    parser.add_argument(
        "--output-base",
        type=Path,
        default=Path("figures/fig_correctness_flip_direction"),
    )
    args = parser.parse_args()
    plot(args.source, args.output_base)


if __name__ == "__main__":
    main()
