"""
Outlier detection for travel time comparisons.

This module provides outlier detection to identify and filter out rows where one provider
returns a drastically different travel time compared to others, indicating potential
data quality issues (e.g., routing errors, API failures).
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd
from pandas import DataFrame

from traveltime_drive_time_comparisons.common import get_capitalized_provider_name


@dataclass
class OutlierConfig:
    """Configuration for outlier detection."""

    enabled: bool = True
    """
    Whether outlier detection is enabled.
    If False, no outliers will be detected and all rows will be kept.
    """

    ratio_threshold: float = 3.0
    """
    Threshold for flagging outliers as a ratio of difference from median.
    Values are flagged if their ratio is greater than or equal to this threshold.

    Examples with ratio_threshold=3.0:
    - Value of 3000 when median is 1000 → ratio = 3.0 → flagged as outlier (exactly at threshold)
    - Value of 5000 when median is 1000 → ratio = 5.0 → flagged as outlier
    - Value of 1500 when median is 1000 → ratio = 1.5 → NOT flagged
    - Value of 300 when median is 1000 → ratio = 3.33 → flagged as outlier
    - Value of 2999 when median is 1000 → ratio = 2.999 → NOT flagged (just below threshold)

    Recommended values:
    - 3.0: Catches egregious errors (default, recommended)
    - 2.0: More strict, catches moderate differences
    - 5.0: Very lenient, only extreme cases

    Note: With only 2 providers, a value needs to be ~5x different from the other
    to be flagged with threshold=3.0 (e.g., [5000, 1000] will flag the 1000).
    """

    min_providers: int = 2
    """
    Minimum number of providers required to perform outlier detection.
    With fewer providers, no outliers will be detected.

    Default is 2, but note that with only 2 providers, outlier detection
    is less meaningful as there's no consensus to compare against.
    """


def detect_outliers(
    data: DataFrame,
    columns: Dict[str, str],
    config: Optional[OutlierConfig] = None,
) -> DataFrame:
    """
    Detect rows where one provider's value differs dramatically from the median.

    For each row, calculates the median of all provider values. If any provider's
    value is greater than or equal to ratio_threshold times different from the
    median (either larger or smaller), that row is flagged as containing an outlier.

    Args:
        data: DataFrame with provider travel times
        columns: Dictionary mapping provider names to column names
        config: Configuration for outlier detection (uses defaults if None)

    Returns:
        DataFrame with one row per detected outlier, containing:
        - All original row data
        - outlier_provider: Name of the provider with outlier value
        - outlier_value: The outlier value
        - median_value: Median of all providers in that row
        - ratio: How many times different from median
        - row_index: Original row index

    Examples:
        >>> config = OutlierConfig(ratio_threshold=3.0)
        >>> outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)
        >>> print(f"Found {len(outliers)} outlier rows")

        >>> # With threshold=3.0, values exactly 3x different are flagged
        >>> # [1000, 1000, 3000, 1000, 1000] → 3000 flagged (ratio=3.0)
        >>> # [1000, 1000, 2999, 1000, 1000] → 2999 not flagged (ratio=2.999)
    """

    if config is None:
        config = OutlierConfig()

    if not config.enabled:
        return pd.DataFrame()

    existing_fields = {k: v for k, v in columns.items() if v in data.columns}
    outliers = []

    for idx, row in data.iterrows():
        # Get all valid provider values for this row
        values = [
            row[col]
            for col in existing_fields.values()
            if pd.notna(row[col]) and row[col] > 0
        ]

        # Skip if not enough providers
        if len(values) < config.min_providers:
            continue

        median_val = np.median(values)

        # Skip if median is zero (shouldn't happen with travel times, but be safe)
        if median_val == 0:
            continue

        # Check each provider for egregious differences
        for provider_key, provider_col in existing_fields.items():
            provider_val = row[provider_col]

            if pd.isna(provider_val) or provider_val == 0:
                continue

            # Calculate how many times larger/smaller than median
            if provider_val > median_val:
                ratio = provider_val / median_val
            else:
                ratio = median_val / provider_val

            if ratio >= config.ratio_threshold:
                outlier_info = row.to_dict()
                outlier_info["outlier_provider"] = get_capitalized_provider_name(
                    provider_key
                )
                outlier_info["outlier_value"] = provider_val
                outlier_info["median_value"] = median_val
                outlier_info["ratio"] = round(ratio, 2)
                outlier_info["row_index"] = idx
                outliers.append(outlier_info)
                break  # Only report once per row

    return pd.DataFrame(outliers) if outliers else pd.DataFrame()


def filter_outliers(
    data: DataFrame,
    outliers_df: DataFrame,
) -> DataFrame:
    """
    Remove rows that were identified as outliers.

    Args:
        data: Original DataFrame
        outliers_df: DataFrame returned by detect_outliers()

    Returns:
        Filtered DataFrame with outlier rows removed, index reset

    Examples:
        >>> outliers = detect_outliers(data, Fields.TRAVEL_TIME)
        >>> clean_data = filter_outliers(data, outliers)
        >>> print(f"Removed {len(data) - len(clean_data)} rows")
    """
    if outliers_df.empty:
        return data

    outlier_indices = outliers_df["row_index"].tolist()
    return data[~data.index.isin(outlier_indices)].reset_index(drop=True)


def log_outliers(outliers_df: DataFrame, data_description: str = "dataset") -> None:
    """
    Log detected outliers in a human-readable format.

    Args:
        outliers_df: DataFrame returned by detect_outliers()
        data_description: Description of the dataset being analyzed

    Examples:
        >>> outliers = detect_outliers(data, Fields.TRAVEL_TIME)
        >>> log_outliers(outliers, "NYC to Boston routes")
    """
    if outliers_df.empty:
        logging.info(f"No outliers detected in {data_description}")
        return

    logging.info(f"Detected {len(outliers_df)} outlier rows in {data_description}:")
    for _, outlier in outliers_df.iterrows():
        csv_line = outlier["row_index"] + 1  # Rows start from 0
        logging.info(
            f"  Row {csv_line} (not counting header): {outlier['outlier_provider']} = "
            f"{outlier['outlier_value']:.0f}s (median: {outlier['median_value']:.0f}s, "
            f"ratio: {outlier['ratio']:.1f}x)"
        )
