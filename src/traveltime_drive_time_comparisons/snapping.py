import math
import logging
from typing import List, Tuple

import pandas as pd
from pandas import DataFrame

from traveltime_drive_time_comparisons.common import Fields


logger = logging.getLogger(__name__)

EARTH_RADIUS_METERS = 6_371_000
BAD_SNAP_THRESHOLD_METERS = 200


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in meters between two coordinates using the Haversine formula."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return EARTH_RADIUS_METERS * c


def parse_coordinates(coord_string: str) -> Tuple[float, float]:
    parts = [c.strip() for c in coord_string.split(",")]
    return float(parts[0]), float(parts[1])


def detect_bad_snapping(
    df: DataFrame,
    provider_names: List[str],
    threshold: float = BAD_SNAP_THRESHOLD_METERS,
) -> DataFrame:
    """
    Add 'case_category' column to DataFrame based on snapping analysis.

    For each row, checks if any provider snapped origin or destination
    more than `threshold` meters from the requested coordinates.

    Values:
    - 'clean': No snapping issues detected
    - 'bad_snap_origin': Origin snapped >threshold from requested
    - 'bad_snap_destination': Destination snapped >threshold from requested
    - 'bad_snap_both': Both origin and destination have snapping issues
    """
    df = df.copy()
    categories = ["clean"] * len(df)

    for i, (idx, row) in enumerate(df.iterrows()):
        try:
            origin_lat, origin_lng = parse_coordinates(row[Fields.ORIGIN])
            dest_lat, dest_lng = parse_coordinates(row[Fields.DESTINATION])
        except (ValueError, TypeError):
            continue

        bad_origin = False
        bad_destination = False

        for provider in provider_names:
            snapped_origin_col = Fields.SNAPPED_ORIGIN.get(provider)
            snapped_dest_col = Fields.SNAPPED_DESTINATION.get(provider)

            if snapped_origin_col and snapped_origin_col in df.columns:
                snapped_origin = row.get(snapped_origin_col)
                if pd.notna(snapped_origin):
                    try:
                        snap_lat, snap_lng = parse_coordinates(str(snapped_origin))
                        distance = haversine_distance(
                            origin_lat, origin_lng, snap_lat, snap_lng
                        )
                        if distance > threshold:
                            bad_origin = True
                    except (ValueError, TypeError):
                        pass

            if snapped_dest_col and snapped_dest_col in df.columns:
                snapped_dest = row.get(snapped_dest_col)
                if pd.notna(snapped_dest):
                    try:
                        snap_lat, snap_lng = parse_coordinates(str(snapped_dest))
                        distance = haversine_distance(
                            dest_lat, dest_lng, snap_lat, snap_lng
                        )
                        if distance > threshold:
                            bad_destination = True
                    except (ValueError, TypeError):
                        pass

        if bad_origin and bad_destination:
            categories[i] = "bad_snap_both"
        elif bad_origin:
            categories[i] = "bad_snap_origin"
        elif bad_destination:
            categories[i] = "bad_snap_destination"

    df[Fields.CASE_CATEGORY] = categories
    return df


def log_snapping_summary(df: DataFrame) -> None:
    total = len(df)
    if total == 0:
        return

    clean_count = (df[Fields.CASE_CATEGORY] == "clean").sum()
    bad_snap_count = total - clean_count

    if bad_snap_count > 0:
        logger.info(f"Detected {bad_snap_count} routes with bad snapping issues")
        for category in ["bad_snap_origin", "bad_snap_destination", "bad_snap_both"]:
            count = (df[Fields.CASE_CATEGORY] == category).sum()
            if count > 0:
                logger.info(f"  - {category}: {count}")
