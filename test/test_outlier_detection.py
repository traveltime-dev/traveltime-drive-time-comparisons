"""
Comprehensive tests for outlier detection.

Tests cover various scenarios including:
- Different numbers of providers (2, 3, 5, 7)
- Different magnitudes of outliers (2x, 3x, 5x, 10x)
- Edge cases (zeros, NaN, identical values, small values)
- Configuration options
"""

import numpy as np
import pandas as pd

from traveltime_drive_time_comparisons.common import (
    Fields,
    GOOGLE_API,
    TRAVELTIME_API,
    TOMTOM_API,
    HERE_API,
    OSRM_API,
    MAPBOX_API,
    VALHALLA_API,
)
from traveltime_drive_time_comparisons.outlier_detection import (
    OutlierConfig,
    detect_outliers,
    filter_outliers,
)


class TestOutlierDetectionBasics:
    """Test basic outlier detection functionality."""

    def test_detect_obvious_high_outlier_with_7_providers(self):
        """5x outlier should be detected with 7 providers."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 1000, 1000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 5000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000, 1000],
                Fields.TRAVEL_TIME[MAPBOX_API]: [1000, 1000, 1000, 1000],
                Fields.TRAVEL_TIME[VALHALLA_API]: [1000, 1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1
        assert outliers.iloc[0]["row_index"] == 1
        assert outliers.iloc[0]["outlier_provider"] == "TomTom"
        assert outliers.iloc[0]["outlier_value"] == 5000
        assert outliers.iloc[0]["median_value"] == 1000
        assert outliers.iloc[0]["ratio"] == 5.0

    def test_detect_obvious_low_outlier_with_7_providers(self):
        """10x low outlier should be detected with 7 providers."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [500, 500, 500, 50],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [500, 500, 500, 500],
                Fields.TRAVEL_TIME[TOMTOM_API]: [500, 500, 500, 500],
                Fields.TRAVEL_TIME[HERE_API]: [500, 500, 500, 500],
                Fields.TRAVEL_TIME[OSRM_API]: [500, 500, 500, 500],
                Fields.TRAVEL_TIME[MAPBOX_API]: [500, 500, 500, 500],
                Fields.TRAVEL_TIME[VALHALLA_API]: [500, 500, 500, 500],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1
        assert outliers.iloc[0]["row_index"] == 3
        assert outliers.iloc[0]["outlier_value"] == 50
        assert outliers.iloc[0]["ratio"] == 10.0

    def test_no_outlier_with_natural_variance(self):
        """Natural variance (±10%) should not be flagged."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [950, 980, 1000, 1020, 1050],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [960, 990, 1010, 1030, 1040],
                Fields.TRAVEL_TIME[TOMTOM_API]: [940, 970, 1000, 1010, 1060],
                Fields.TRAVEL_TIME[HERE_API]: [970, 1000, 990, 1040, 1030],
                Fields.TRAVEL_TIME[OSRM_API]: [980, 980, 1020, 1020, 1050],
                Fields.TRAVEL_TIME[MAPBOX_API]: [990, 1010, 1000, 1000, 1040],
                Fields.TRAVEL_TIME[VALHALLA_API]: [1000, 990, 1010, 1030, 1020],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 0


class TestDifferentProviderCounts:
    """Test outlier detection with varying numbers of providers."""

    def test_with_2_providers_big_difference_outlier_detected(self):
        """With 2 providers and large difference, median falls in middle so one will be flagged."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 5000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1

    def test_with_2_providers_small_difference_no_outlier(self):
        """With 2 providers and small difference, no outliers flagged."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 2000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 0

    def test_with_3_providers_detects_egregious_outlier(self):
        """With 3 providers, 5x outlier should still be detected."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 5000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1
        assert outliers.iloc[0]["row_index"] == 1
        assert outliers.iloc[0]["outlier_value"] == 5000

    def test_with_5_providers_detects_outlier(self):
        """With 5 providers, outlier detection works well."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 5000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1
        assert outliers.iloc[0]["row_index"] == 1


class TestDifferentOutlierMagnitudes:
    """Test detection of outliers of different magnitudes."""

    def test_2x_outlier_not_detected_with_threshold_3(self):
        """2x difference should not be flagged with threshold=3.0."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 2000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 0

    def test_2x_outlier_detected_with_threshold_2(self):
        """2x difference should be flagged with threshold=2.0."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 2000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=2.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1
        assert outliers.iloc[0]["outlier_value"] == 2000

    def test_3x_outlier_detected_with_threshold_3(self):
        """Exactly 3x difference should be flagged with threshold=3.0."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 3000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1

    def test_3point1x_outlier_detected_with_threshold_3(self):
        """Slightly above 3x should be flagged with threshold=3.0."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 3100, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1

    def test_10x_outlier_detected(self):
        """Extreme 10x outlier should definitely be detected."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 10000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1
        assert outliers.iloc[0]["ratio"] == 10.0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_identical_values_no_outliers(self):
        """When all providers agree, no outliers."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 0

    def test_small_values_with_huge_outlier(self):
        """Outlier detection should work with small base values."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [3, 1500, 5],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [5, 3, 3],
                Fields.TRAVEL_TIME[TOMTOM_API]: [4, 5, 4],
                Fields.TRAVEL_TIME[HERE_API]: [3, 4, 3],
                Fields.TRAVEL_TIME[OSRM_API]: [5, 3, 5],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1
        assert outliers.iloc[0]["row_index"] == 1
        assert outliers.iloc[0]["outlier_value"] == 1500

    def test_nan_values_ignored(self):
        """NaN values should be ignored in outlier detection."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 5000, np.nan],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [np.nan, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        # Row 1 should still be detected despite NaN in row 2
        assert len(outliers) == 1
        assert outliers.iloc[0]["row_index"] == 1

    def test_zero_values_ignored(self):
        """Zero values should be ignored (likely means no data)."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 5000, 0],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [0, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 1
        assert outliers.iloc[0]["row_index"] == 1

    def test_single_provider_no_outliers(self):
        """With only 1 provider, can't detect outliers."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 5000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 0

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty outliers."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 0


class TestFilterOutliers:
    """Test filtering functionality."""

    def test_filter_removes_outlier_rows(self):
        """filter_outliers should remove flagged rows."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 5000, 1000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)
        filtered = filter_outliers(data, outliers)

        assert len(data) == 4
        assert len(filtered) == 3
        assert 5000 not in filtered[Fields.TRAVEL_TIME[GOOGLE_API]].values

    def test_filter_with_no_outliers_returns_original(self):
        """If no outliers detected, filtered data should equal original."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)
        filtered = filter_outliers(data, outliers)

        assert len(filtered) == len(data)
        pd.testing.assert_frame_equal(filtered, data.reset_index(drop=True))

    def test_filter_resets_index(self):
        """Filtered DataFrame should have reset index."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 5000, 1000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000, 1000],
            }
        )

        config = OutlierConfig(ratio_threshold=3.0)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)
        filtered = filter_outliers(data, outliers)

        # Index should be [0, 1, 2] not [0, 2, 3]
        assert list(filtered.index) == [0, 1, 2]


class TestConfiguration:
    """Test configuration options."""

    def test_default_config(self):
        """Test that default configuration works."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 5000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000],
            }
        )

        # Using None should apply defaults
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config=None)

        assert len(outliers) == 1

    def test_disabled_outlier_detection(self):
        """Test that outlier detection can be disabled."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 5000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        # With detection disabled
        config = OutlierConfig(enabled=False)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 0

        # Verify filtering does nothing when no outliers detected
        filtered = filter_outliers(data, outliers)
        assert len(filtered) == len(data)

    def test_custom_ratio_threshold(self):
        """Test custom ratio threshold."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 2500, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[TOMTOM_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[HERE_API]: [1000, 1000, 1000],
                Fields.TRAVEL_TIME[OSRM_API]: [1000, 1000, 1000],
            }
        )

        # 2.5x outlier should not be caught with threshold=3.0
        config_lenient = OutlierConfig(ratio_threshold=3.0)
        outliers_lenient = detect_outliers(data, Fields.TRAVEL_TIME, config_lenient)
        assert len(outliers_lenient) == 0

        # But should be caught with threshold=2.0
        config_strict = OutlierConfig(ratio_threshold=2.0)
        outliers_strict = detect_outliers(data, Fields.TRAVEL_TIME, config_strict)
        assert len(outliers_strict) == 1

    def test_min_providers_setting(self):
        """Test minimum providers setting."""
        data = pd.DataFrame(
            {
                Fields.TRAVEL_TIME[GOOGLE_API]: [1000, 5000, 1000],
                Fields.TRAVEL_TIME[TRAVELTIME_API]: [1000, 1000, 1000],
            }
        )

        # With min_providers=3, no outliers should be detected
        config = OutlierConfig(ratio_threshold=3.0, min_providers=3)
        outliers = detect_outliers(data, Fields.TRAVEL_TIME, config)

        assert len(outliers) == 0
