import logging
from datetime import datetime

import aiohttp
from traveltimepy.requests.common import Coordinates

from traveltime_drive_time_comparisons.config import Mode
from traveltime_drive_time_comparisons.api_requests.base_handler import (
    BaseRequestHandler,
    RequestResult,
    create_async_limiter,
)

logger = logging.getLogger(__name__)


class ValhallaApiError(Exception):
    pass


class ValhallaRequestHandler(BaseRequestHandler):
    DEFAULT_API_ENDPOINT = "https://valhalla1.openstreetmap.de"
    ROUTING_PATH = "/route"

    default_timeout = aiohttp.ClientTimeout(total=60)

    def __init__(self, api_key, max_rpm, api_endpoint):
        self.api_key = api_key
        self._rate_limiter = create_async_limiter(max_rpm)

        base_url = api_endpoint or self.DEFAULT_API_ENDPOINT
        self.routing_url = base_url + self.ROUTING_PATH

    async def send_request(
        self,
        origin: Coordinates,
        destination: Coordinates,
        departure_time: datetime,
        mode: Mode,
    ) -> RequestResult:
        transport_mode = get_valhalla_specific_mode(mode)

        request_body = {
            "locations": [
                {"lat": origin.lat, "lon": origin.lng, "type": "break"},
                {"lat": destination.lat, "lon": destination.lng, "type": "break"},
            ],
            "costing": transport_mode,
            "date_time": {
                "type": 1,  # 1 means departure time
                "value": departure_time.strftime("%Y-%m-%dT%H:%M"),
            },
        }

        try:
            async with (
                aiohttp.ClientSession(timeout=self.default_timeout) as session,
                session.post(self.routing_url, json=request_body) as response,
            ):
                data = await response.json()

                if response.status == 200:
                    trip = data.get("trip")

                    if not trip or trip.get("status") != 0:
                        raise ValhallaApiError(
                            trip.get(
                                "status_message",
                                "No route found between origin and destination.",
                            )
                        )

                    total_duration = trip["summary"]["time"]

                    return RequestResult(travel_time=int(total_duration))
                else:
                    error_message = data.get("error", "Unknown error")
                    logger.error(
                        f"Error in Valhalla API response: {response.status} - {error_message}"
                    )
                    return RequestResult(None)
        except Exception as e:
            logger.error(f"Exception during requesting Valhalla API, {e}")
            return RequestResult(None)


def get_valhalla_specific_mode(mode: Mode) -> str:
    if mode == Mode.DRIVING:
        return "auto"
    elif mode == Mode.PUBLIC_TRANSPORT:
        raise ValueError("Public transport is not supported for Valhalla requests")
    else:
        raise ValueError(f"Unsupported mode: `{mode.value}`")
