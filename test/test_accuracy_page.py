import math

from traveltime_drive_time_comparisons.accuracy_page.aggregate import (
    aggregate,
    band_index,
    extract_rows,
    mean,
    parse_number,
    percentile,
    rmse_seconds,
)


def _record(origin, destination, dep, case, **cols):
    row = {
        "origin": origin,
        "destination": destination,
        "departure_time": dep,
        "case_category": case,
    }
    row.update(cols)
    return row


def test_parse_number():
    assert parse_number(None) is None
    assert parse_number("") is None
    assert parse_number("NaN") is None
    assert parse_number("abc") is None
    assert parse_number("0") == 0.0
    assert parse_number("12.5") == 12.5


def test_mean_and_rmse():
    assert math.isnan(mean([]))
    assert math.isnan(rmse_seconds([]))
    assert mean([90.0, 90.0]) == 90.0
    assert rmse_seconds([10.0, -20.0]) == math.sqrt(250)


def test_percentile_linear_interpolation():
    assert math.isnan(percentile([], 0.5))
    assert percentile([5.0], 0.5) == 5.0
    assert percentile([-10.0, 10.0], 0.5) == 0.0
    assert percentile([0.0, 30.0], 0.5) == 15.0


def test_band_index():
    assert band_index(99.0) == 0  # >=95
    assert band_index(95.0) == 0  # boundary -> >=95 bucket
    assert band_index(90.0) == 1  # 90-95
    assert band_index(74.0) == 5  # <75 catch-all


def test_extract_rows_clean_and_providers():
    records = [
        _record(
            "A",
            "B",
            "2026-01-01 05:00:00",
            "clean",
            google_travel_time="100",
            tt_travel_time="110",
        ),
        _record(
            "A",
            "C",
            "2026-01-01 13:00:00",
            "clean",
            google_travel_time="200",
            tt_travel_time="180",
        ),
    ]
    rows, scanned, od = extract_rows("Test", records)
    assert scanned == 2
    assert od == {"A|B", "A|C"}
    assert len(rows) == 2
    first = next(r for r in rows if r["hour"] == "05:00")
    assert first["google"] == 100.0
    assert first["provider_sec"] == {"TravelTime": 110.0}


def test_extract_rows_drops_non_clean_google():
    records = [
        _record(
            "A",
            "B",
            "2026-01-01 05:00:00",
            "bad_snap_origin",
            google_travel_time="100",
            tt_travel_time="110",
        ),
    ]
    rows, scanned, od = extract_rows("Test", records)
    assert rows == []
    assert scanned == 1
    assert od == {"A|B"}


def test_extract_rows_dedups_by_route_slot():
    records = [
        _record(
            "A",
            "B",
            "2026-01-01 05:00:00",
            "clean",
            google_travel_time="100",
            tt_travel_time="110",
        ),
        _record(
            "A",
            "B",
            "2026-01-09 05:00:00",
            "clean",
            google_travel_time="100",
            tt_travel_time="120",
        ),
    ]
    rows, scanned, od = extract_rows("Test", records)
    assert scanned == 1
    assert len(rows) == 1
    assert rows[0]["provider_sec"]["TravelTime"] == 120.0


def _sample_rows():
    return [
        {
            "state": "Test",
            "hour": "05:00",
            "google": 100.0,
            "provider_sec": {"TravelTime": 110.0, "TomTom": 100.0},
        },
        {
            "state": "Test",
            "hour": "13:00",
            "google": 200.0,
            "provider_sec": {"TravelTime": 180.0, "TomTom": 0.0},
        },
        {
            "state": "Test",
            "hour": "17:00",
            "google": 100.0,
            "provider_sec": {"TravelTime": None, "TomTom": 130.0},
        },
    ]


def test_aggregate_headline_and_no_result_rule():
    aggs = aggregate(_sample_rows(), "test", 3, 3, "GEN", "COL")
    assert [h["provider"] for h in aggs["headline"]] == ["TravelTime", "TomTom"]

    tt = aggs["headline"][0]
    assert tt["meanAccuracy"] == 90.0
    assert tt["rmseSeconds"] == math.sqrt(250)
    assert tt["medianBias"] == 0.0
    assert tt["shareOverPredicting"] == 0.5
    assert tt["cleanRoutesScored"] == 2

    # TomTom row2 == 0 -> no result; only row1 (acc 100) and row3 (acc 70) score.
    tomtom = aggs["headline"][1]
    assert tomtom["meanAccuracy"] == 85.0
    assert tomtom["cleanRoutesScored"] == 2


def test_aggregate_meta_is_data_only():
    meta = aggregate(_sample_rows(), "test", 3, 3, "GEN", "COL")["meta"]
    assert meta["slug"] == "test"
    assert "country" not in meta
    assert meta["providers"] == ["TravelTime", "TomTom"]
    assert meta["referenceProvider"] == "Google"
    assert meta["meanGoogleSeconds"] == (100 + 200 + 100) / 3
