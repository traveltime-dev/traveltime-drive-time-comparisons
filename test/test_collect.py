import pytest
from datetime import datetime

import pytz
from traveltimepy.requests.common import Coordinates

from traveltime_drive_time_comparisons.collect import (
    generate_time_instants,
    parse_coordinates,
    localize_datetime,
)


def test_generate_time_instants_with_valid_times():
    timezone = pytz.UTC
    times = "12:00, 13:00"
    result = generate_time_instants(times, "2023-09-05", timezone)
    expected = [
        datetime(2023, 9, 5, 12, 0, tzinfo=timezone),
        datetime(2023, 9, 5, 13, 0, tzinfo=timezone),
    ]
    assert result == expected


def test_generate_time_instants_when_no_times_are_provided():
    timezone = pytz.UTC
    times = ""
    with pytest.raises(
        ValueError, match="At least one departure time must be provided."
    ):
        generate_time_instants(times, "2023-09-05", timezone)


def test_parse_coordinates_simple_case():
    coord_str = "51.4614,-0.1120"
    assert parse_coordinates(coord_str) == Coordinates(lat=51.4614, lng=-0.1120)


def test_parse_coordinates_with_spaces():
    assert parse_coordinates("51.4614, -0.1120") == Coordinates(
        lat=51.4614, lng=-0.1120
    )
    assert parse_coordinates("51.4614 , -0.1120") == Coordinates(
        lat=51.4614, lng=-0.1120
    )
    assert parse_coordinates(" 51.4614 , -0.1120") == Coordinates(
        lat=51.4614, lng=-0.1120
    )
    assert parse_coordinates(" 51.4614 , -0.1120 ") == Coordinates(
        lat=51.4614, lng=-0.1120
    )


def test_parse_coordinates_missing_coma():
    with pytest.raises(ValueError):
        coord_str = "51.4614 -0.1120"
        parse_coordinates(coord_str)


def test_parse_coordinates_wrong_format():
    with pytest.raises(ValueError):
        coord_str = "51.4614,-0.1120,-122.4194"
        parse_coordinates(coord_str)


def test_basic_localize_datetime_with_UTC():
    date = "2023-09-13"
    time = "15:00"
    timezone = pytz.UTC
    result = localize_datetime(date, time, timezone)
    assert result == datetime(2023, 9, 13, 15, 0, tzinfo=pytz.UTC)


def test_localize_datetime_with_different_timezone():
    date = "2023-09-13"
    time = "15:00"
    timezone = pytz.timezone("US/Pacific")
    result = localize_datetime(date, time, timezone)
    expected_result = timezone.localize(datetime(2023, 9, 13, 15, 0))
    assert result == expected_result


def test_localize_datetime_with_incorrect_format():
    with pytest.raises(ValueError):
        wrong_date = "13-09-2023"
        time = "3:00"
        timezone = pytz.timezone("US/Pacific")
        localize_datetime(wrong_date, time, timezone)

    with pytest.raises(ValueError):
        date = "2023-09-13"
        wrong_time = "3:00 PM"
        timezone = pytz.timezone("US/Pacific")
        localize_datetime(date, wrong_time, timezone)
