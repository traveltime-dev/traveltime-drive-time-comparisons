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


class OSRMApiError(Exception):
    pass


class OSRMRequestHandler(BaseRequestHandler):
    DEFAULT_API_ENDPOINT = "http://router.project-osrm.org"
    ROUTING_PATH = "/route/v1/"

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
        route = f"{origin.lng},{origin.lat};{destination.lng},{destination.lat}"  # for OSRM lat/lng are flipped!
        transport_mode = get_osrm_specific_mode(mode)

        params = {
            "overview": "false",
        }

        try:
            async with (
                aiohttp.ClientSession(timeout=self.default_timeout) as session,
                session.get(
                    f"{self.routing_url}{transport_mode}/{route}", params=params
                ) as response,
            ):
                data = await response.json()
                if response.status == 200:
                    first_route = data["routes"][0]

                    if not first_route:
                        raise OSRMApiError(
                            "No route found between origin and destination."
                        )

                    total_duration = sum(leg["duration"] for leg in first_route["legs"])

                    return RequestResult(travel_time=int(total_duration))
                else:
                    error_message = data.get("detailedError", "")
                    logger.error(
                        f"Error in OSRM API response: {response.status} - {error_message}"
                    )
                    return RequestResult(None)
        except Exception as e:
            logger.error(f"Exception during requesting OSRM API, {e}")
            return RequestResult(None)


def get_osrm_specific_mode(mode: Mode) -> str:
    if mode == Mode.DRIVING:
        return "driving"
    elif mode == Mode.PUBLIC_TRANSPORT:
        raise ValueError("Public transport is not supported for OSRM requests")
    else:
        raise ValueError(f"Unsupported mode: `{mode.value}`")
