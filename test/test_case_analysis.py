import pandas as pd
import pytest
from traveltime_drive_time_comparisons.case_analysis import (
    detect_bad_snapping,
    detect_restricted_roads,
    has_restricted_road_warning,
    haversine_distance,
    parse_coordinates,
)
from traveltime_drive_time_comparisons.common import (
    CaseCategory,
    Fields,
    GOOGLE_API,
    TRAVELTIME_API,
)


class TestHaversineDistance:
    def test_same_point_returns_zero(self):
        distance = haversine_distance(51.5074, -0.1278, 51.5074, -0.1278)
        assert distance == 0

    def test_known_distance_london_to_paris(self):
        # London to Paris is approximately 344 km
        london_lat, london_lng = 51.5074, -0.1278
        paris_lat, paris_lng = 48.8566, 2.3522
        distance = haversine_distance(london_lat, london_lng, paris_lat, paris_lng)
        assert 340_000 < distance < 350_000

    def test_short_distance_within_city(self):
        # Two points ~100m apart in London
        lat1, lng1 = 51.5074, -0.1278
        lat2, lng2 = 51.5083, -0.1278
        distance = haversine_distance(lat1, lng1, lat2, lng2)
        assert 90 < distance < 110

    def test_antipodal_points(self):
        # Points on opposite sides of Earth should be ~20,000 km
        distance = haversine_distance(0, 0, 0, 180)
        assert 20_000_000 < distance < 20_050_000


class TestParseCoordinates:
    def test_standard_format(self):
        lat, lng = parse_coordinates("51.5074, -0.1278")
        assert lat == 51.5074
        assert lng == -0.1278

    def test_no_spaces(self):
        lat, lng = parse_coordinates("51.5074,-0.1278")
        assert lat == 51.5074
        assert lng == -0.1278

    def test_extra_spaces(self):
        lat, lng = parse_coordinates("  51.5074  ,  -0.1278  ")
        assert lat == 51.5074
        assert lng == -0.1278

    def test_invalid_format_raises_error(self):
        with pytest.raises((ValueError, IndexError)):
            parse_coordinates("invalid")

    def test_non_numeric_raises_error(self):
        with pytest.raises(ValueError):
            parse_coordinates("abc, def")


class TestDetectBadSnapping:
    def test_clean_case_when_snap_within_threshold(self):
        # Snapped coordinates very close to original (within 200m threshold)
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.SNAPPED_ORIGIN[GOOGLE_API]: ["51.5074, -0.1278"],
                Fields.SNAPPED_DESTINATION[GOOGLE_API]: ["48.8566, 2.3522"],
            }
        )
        result = detect_bad_snapping(df, [GOOGLE_API])
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.CLEAN

    def test_bad_snap_origin_when_origin_exceeds_threshold(self):
        # Origin snapped >200m away
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.SNAPPED_ORIGIN[GOOGLE_API]: ["51.5100, -0.1278"],
                Fields.SNAPPED_DESTINATION[GOOGLE_API]: ["48.8566, 2.3522"],
            }
        )
        result = detect_bad_snapping(df, [GOOGLE_API])
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.BAD_SNAP_ORIGIN

    def test_bad_snap_destination_when_destination_exceeds_threshold(self):
        # Destination snapped >200m away
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.SNAPPED_ORIGIN[GOOGLE_API]: ["51.5074, -0.1278"],
                Fields.SNAPPED_DESTINATION[GOOGLE_API]: ["48.8600, 2.3522"],
            }
        )
        result = detect_bad_snapping(df, [GOOGLE_API])
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.BAD_SNAP_DESTINATION

    def test_bad_snap_both_when_both_exceed_threshold(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.SNAPPED_ORIGIN[GOOGLE_API]: ["51.5100, -0.1278"],
                Fields.SNAPPED_DESTINATION[GOOGLE_API]: ["48.8600, 2.3522"],
            }
        )
        result = detect_bad_snapping(df, [GOOGLE_API])
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.BAD_SNAP_BOTH

    def test_multiple_providers_any_bad_triggers_flag(self):
        # TravelTime snaps fine, but Google snaps badly
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.SNAPPED_ORIGIN[GOOGLE_API]: ["51.5100, -0.1278"],
                Fields.SNAPPED_DESTINATION[GOOGLE_API]: ["48.8566, 2.3522"],
                Fields.SNAPPED_ORIGIN[TRAVELTIME_API]: ["51.5074, -0.1278"],
                Fields.SNAPPED_DESTINATION[TRAVELTIME_API]: ["48.8566, 2.3522"],
            }
        )
        result = detect_bad_snapping(df, [GOOGLE_API, TRAVELTIME_API])
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.BAD_SNAP_ORIGIN

    def test_missing_snapped_columns_treated_as_clean(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
            }
        )
        result = detect_bad_snapping(df, [GOOGLE_API])
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.CLEAN

    def test_nan_snapped_values_treated_as_clean(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.SNAPPED_ORIGIN[GOOGLE_API]: [None],
                Fields.SNAPPED_DESTINATION[GOOGLE_API]: [None],
            }
        )
        result = detect_bad_snapping(df, [GOOGLE_API])
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.CLEAN

    def test_invalid_origin_coordinates_skipped(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["invalid"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.SNAPPED_ORIGIN[GOOGLE_API]: ["51.5100, -0.1278"],
                Fields.SNAPPED_DESTINATION[GOOGLE_API]: ["48.8566, 2.3522"],
            }
        )
        result = detect_bad_snapping(df, [GOOGLE_API])
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.CLEAN

    def test_invalid_snapped_coordinates_skipped(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.SNAPPED_ORIGIN[GOOGLE_API]: ["invalid"],
                Fields.SNAPPED_DESTINATION[GOOGLE_API]: ["48.8566, 2.3522"],
            }
        )
        result = detect_bad_snapping(df, [GOOGLE_API])
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.CLEAN

    def test_multiple_rows(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278", "52.0, 0.0", "53.0, 1.0"],
                Fields.DESTINATION: ["48.8566, 2.3522", "49.0, 3.0", "50.0, 4.0"],
                Fields.SNAPPED_ORIGIN[GOOGLE_API]: [
                    "51.5074, -0.1278",
                    "52.0030, 0.0",
                    "53.0, 1.0",
                ],
                Fields.SNAPPED_DESTINATION[GOOGLE_API]: [
                    "48.8566, 2.3522",
                    "49.0, 3.0",
                    "50.0030, 4.0",
                ],
            }
        )
        result = detect_bad_snapping(df, [GOOGLE_API])
        assert result[Fields.CASE_CATEGORY].tolist() == [
            CaseCategory.CLEAN,
            CaseCategory.BAD_SNAP_ORIGIN,
            CaseCategory.BAD_SNAP_DESTINATION,
        ]


class TestHasRestrictedRoadWarning:
    def test_returns_false_for_none(self):
        assert has_restricted_road_warning(None) is False

    def test_returns_false_for_nan(self):
        assert has_restricted_road_warning(float("nan")) is False

    def test_returns_false_for_empty_string(self):
        assert has_restricted_road_warning("") is False

    def test_returns_false_for_unrelated_warning(self):
        assert has_restricted_road_warning("Traffic delay expected") is False

    def test_returns_true_for_restricted_keyword(self):
        assert has_restricted_road_warning("This route uses restricted roads") is True

    def test_returns_true_for_private_keyword(self):
        assert (
            has_restricted_road_warning("Route passes through private property") is True
        )

    def test_case_insensitive_restricted(self):
        assert has_restricted_road_warning("RESTRICTED access road") is True

    def test_case_insensitive_private(self):
        assert has_restricted_road_warning("PRIVATE road ahead") is True


class TestDetectRestrictedRoads:
    def test_marks_clean_row_as_restricted_when_warning_present(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.CASE_CATEGORY: [CaseCategory.CLEAN],
                Fields.WARNINGS[GOOGLE_API]: ["This route uses restricted roads"],
            }
        )
        result = detect_restricted_roads(df)
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.RESTRICTED_ROAD

    def test_does_not_modify_bad_snap_rows(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.CASE_CATEGORY: [CaseCategory.BAD_SNAP_ORIGIN],
                Fields.WARNINGS[GOOGLE_API]: ["This route uses restricted roads"],
            }
        )
        result = detect_restricted_roads(df)
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.BAD_SNAP_ORIGIN

    def test_leaves_clean_row_clean_when_no_warning(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.CASE_CATEGORY: [CaseCategory.CLEAN],
                Fields.WARNINGS[GOOGLE_API]: ["Traffic is normal"],
            }
        )
        result = detect_restricted_roads(df)
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.CLEAN

    def test_handles_missing_warnings_column(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.CASE_CATEGORY: [CaseCategory.CLEAN],
            }
        )
        result = detect_restricted_roads(df)
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.CLEAN

    def test_handles_nan_warning_value(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278"],
                Fields.DESTINATION: ["48.8566, 2.3522"],
                Fields.CASE_CATEGORY: [CaseCategory.CLEAN],
                Fields.WARNINGS[GOOGLE_API]: [None],
            }
        )
        result = detect_restricted_roads(df)
        assert result[Fields.CASE_CATEGORY].iloc[0] == CaseCategory.CLEAN

    def test_multiple_rows_mixed_cases(self):
        df = pd.DataFrame(
            {
                Fields.ORIGIN: ["51.5074, -0.1278", "52.0, 0.0", "53.0, 1.0"],
                Fields.DESTINATION: ["48.8566, 2.3522", "49.0, 3.0", "50.0, 4.0"],
                Fields.CASE_CATEGORY: [
                    CaseCategory.CLEAN,
                    CaseCategory.CLEAN,
                    CaseCategory.BAD_SNAP_ORIGIN,
                ],
                Fields.WARNINGS[GOOGLE_API]: [
                    "Route uses private roads",
                    "Normal route",
                    "Route uses restricted roads",
                ],
            }
        )
        result = detect_restricted_roads(df)
        assert result[Fields.CASE_CATEGORY].tolist() == [
            CaseCategory.RESTRICTED_ROAD,
            CaseCategory.CLEAN,
            CaseCategory.BAD_SNAP_ORIGIN,
        ]
