from enum import Enum

import pytest

from traveltime_drive_time_comparisons.config import Mode
from traveltime_drive_time_comparisons.api_requests.google_handler import (
    get_google_travel_mode,
)


def test_get_google_specific_mode_for_driving():
    result = get_google_travel_mode(Mode.DRIVING)
    assert result == "driving"


def test_get_google_specific_mode_for_public_transport():
    result = get_google_travel_mode(Mode.PUBLIC_TRANSPORT)
    assert result == "transit"


def test_get_google_specific_mode_for_unsupported_mode():
    class MockMode(Enum):
        WALKING = "WALKING"

    with pytest.raises(ValueError, match=r"Unsupported mode: `WALKING`"):
        get_google_travel_mode(MockMode.WALKING)
