from datetime import datetime
from enum import Enum

import pytest
import pytz

from traveltime_drive_time_comparisons.config import Mode
from traveltime_drive_time_comparisons.api_requests.mapbox_handler import (
    format_depart_at,
    get_mapbox_specific_mode,
)


def test_local_departure_is_converted_to_utc():
    local = pytz.timezone("America/New_York").localize(datetime(2026, 4, 29, 17, 0))
    assert format_depart_at(local) == "2026-04-29T21:00:00Z"


def test_utc_departure_is_unchanged():
    utc = pytz.utc.localize(datetime(2026, 4, 29, 17, 0))
    assert format_depart_at(utc) == "2026-04-29T17:00:00Z"


def test_departure_crossing_the_date_boundary():
    local = pytz.timezone("Pacific/Auckland").localize(datetime(2026, 4, 29, 5, 0))
    assert format_depart_at(local) == "2026-04-28T17:00:00Z"


def test_get_mapbox_specific_mode_for_driving():
    assert get_mapbox_specific_mode(Mode.DRIVING) == "driving-traffic"


def test_get_mapbox_specific_mode_for_public_transport():
    with pytest.raises(ValueError, match=r"Public transport is not supported"):
        get_mapbox_specific_mode(Mode.PUBLIC_TRANSPORT)


def test_get_mapbox_specific_mode_for_unsupported_mode():
    class MockMode(Enum):
        WALKING = "WALKING"

    with pytest.raises(ValueError, match=r"Unsupported mode: `WALKING`"):
        get_mapbox_specific_mode(MockMode.WALKING)
