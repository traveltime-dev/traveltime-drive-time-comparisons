import matplotlib.pyplot as plt
import pandas as pd
from traveltime_drive_time_comparisons.common import (
    PROVIDER_COLUMN,
    ACCURARY_SCORE_COLUMN,
    RELATIVE_TIME_COLUMN,
)


def get_bar_colors(providers):
    """Return colors for bars - lime for TravelTime, canary for others"""
    colors = []
    for provider in providers:
        if provider == "TravelTime":
            colors.append("#74f171")  # lime
        else:
            colors.append("#fffeeb")  # canary-50
    return colors


def plot_accuracy_comparison(
    accuracy_df: pd.DataFrame, title: str = "Provider Accuracy Comparison"
):
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = get_bar_colors(accuracy_df[PROVIDER_COLUMN])

    bars = ax.bar(
        accuracy_df[PROVIDER_COLUMN],
        accuracy_df[ACCURARY_SCORE_COLUMN],
        color=colors,
        alpha=0.7,
        edgecolor="black",
        linewidth=0.5,
    )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.set_xlabel(PROVIDER_COLUMN, fontsize=12)
    ax.set_ylabel(ACCURARY_SCORE_COLUMN, fontsize=12)

    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 1,  # Increased padding for better visibility
            f"{height:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.xticks(rotation=45, ha="right")

    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    # Dynamic y-axis range
    min_val = min(accuracy_df[ACCURARY_SCORE_COLUMN])
    max_val = max(accuracy_df[ACCURARY_SCORE_COLUMN])
    range_size = max_val - min_val

    # Add 10% padding above and below the data range
    padding = max(range_size * 0.1, 5)  # At least 5% padding
    ax.set_ylim(max(0, min_val - padding), max_val + padding)

    plt.tight_layout()
    return fig


def plot_relative_time_comparison(
    accuracy_df: pd.DataFrame, title: str = "Provider Relative Time Comparison"
):
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = get_bar_colors(accuracy_df[PROVIDER_COLUMN])

    bars = ax.bar(
        accuracy_df[PROVIDER_COLUMN],
        accuracy_df[RELATIVE_TIME_COLUMN],
        color=colors,
        alpha=0.7,
        edgecolor="black",
        linewidth=0.5,
    )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.set_xlabel(PROVIDER_COLUMN, fontsize=12)
    ax.set_ylabel(f"{RELATIVE_TIME_COLUMN}", fontsize=12)

    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 2,  # Increased padding for better visibility
            f"{height:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    plt.xticks(rotation=45, ha="right")

    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    # Dynamic y-axis range
    min_val = min(accuracy_df[RELATIVE_TIME_COLUMN])
    max_val = max(accuracy_df[RELATIVE_TIME_COLUMN])
    range_size = max_val - min_val

    # Add 10% padding above and below the data range
    padding = max(range_size * 0.1, 8)  # At least 8% padding for relative time

    # Ensure 100% baseline is visible if it's close to the data range
    y_min = max(0, min_val - padding)
    y_max = max_val + padding
    if min_val > 95 and y_min > 95:  # If all values are close to 100%, include 100%
        y_min = 95

    ax.set_ylim(y_min, y_max)

    plt.tight_layout()
    return fig
