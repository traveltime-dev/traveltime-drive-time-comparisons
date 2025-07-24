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


class OpenRoutesError(Exception):
    pass


class OpenRoutesRequestHandler(BaseRequestHandler):
    DEFAULT_API_ENDPOINT = "https://api.openrouteservice.org"
    ROUTING_PATH = "/v2/directions"

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
        mode: Mode = Mode.DRIVING,
    ) -> RequestResult:
        transport_mode = get_open_routes_specific_mode(mode)
        params = {
            "api_key": self.api_key,
            "start": f"{origin.lng},{origin.lat}",
            "end": f"{destination.lng},{destination.lat}",
        }
        try:
            async with (
                aiohttp.ClientSession(timeout=self.default_timeout) as session,
                session.get(
                    f"{self.routing_url}/{transport_mode}", params=params
                ) as response,
            ):
                data = await response.json()
                if response.status == 200:
                    duration = data["features"][0]["properties"]["segments"][0][
                        "duration"
                    ]
                    if not duration:
                        raise OpenRoutesError(
                            "No route found between origin and destination."
                        )
                    return RequestResult(travel_time=int(duration))
                else:
                    error_message = data.get("detailedError", "")
                    logger.error(
                        f"Error in OpenRoutes API response: {response.status} - {error_message}"
                    )
                    return RequestResult(None)
        except Exception as e:
            logger.error(f"Exception during requesting OpenRoutes API, {e}")
            return RequestResult(None)


def get_open_routes_specific_mode(mode: Mode) -> str:
    if mode == Mode.DRIVING:
        return "driving-car"
    elif mode == Mode.PUBLIC_TRANSPORT:
        raise ValueError("Public transport is not supported for OpenRoutes requests")
    else:
        raise ValueError(f"Unsupported mode: `{mode.value}`")
