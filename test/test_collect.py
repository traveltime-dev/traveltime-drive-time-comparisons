import asyncio
import pytest
from datetime import datetime

import pandas as pd
import pytz
from traveltimepy.requests.common import Coordinates

from traveltime_drive_time_comparisons.api_requests.base_handler import (
    BaseRequestHandler,
    RequestResult,
    create_async_limiter,
)
from traveltime_drive_time_comparisons.collect import (
    generate_tasks,
    generate_time_instants,
    parse_coordinates,
    localize_datetime,
    time_instants_for_origin,
)
from traveltime_drive_time_comparisons.common import Fields
from traveltime_drive_time_comparisons.config import Mode

TIJUANA = "32.52,-117.03"
MEXICO_CITY = "19.43,-99.13"


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


def _local_time(origin, time_zone_id):
    instants = time_instants_for_origin(origin, "17:00", "2026-09-30", time_zone_id)
    return instants[0].strftime("%H:%M%z")


def test_time_instants_for_origin_uses_the_given_zone_for_every_route():
    assert _local_time(TIJUANA, "America/Mexico_City") == "17:00-0600"
    assert _local_time(MEXICO_CITY, "America/Mexico_City") == "17:00-0600"


def test_time_instants_for_origin_uses_each_origins_zone_without_one():
    assert _local_time(TIJUANA, None) == "17:00-0700"
    assert _local_time(MEXICO_CITY, None) == "17:00-0600"


class _ConstantHandler(BaseRequestHandler):
    def __init__(self):
        self._rate_limiter = create_async_limiter(6000)

    async def send_request(self, origin, destination, departure_time, mode):
        return RequestResult(travel_time=60)


async def _run(tasks):
    return await asyncio.gather(*tasks)


def test_generate_tasks_departs_at_the_origins_local_time():
    data = pd.DataFrame({Fields.ORIGIN: [TIJUANA], Fields.DESTINATION: [MEXICO_CITY]})
    tasks = generate_tasks(
        data, "17:00", "2026-09-30", None, {"google": _ConstantHandler()}, Mode.DRIVING
    )

    results = asyncio.run(_run(tasks))

    assert [r[Fields.DEPARTURE_TIME] for r in results] == ["2026-09-30 17:00:00-0700"]
