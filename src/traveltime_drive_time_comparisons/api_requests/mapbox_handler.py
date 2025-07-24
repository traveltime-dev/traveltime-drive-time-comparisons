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


class MapboxApiError(Exception):
    pass


class MapboxRequestHandler(BaseRequestHandler):
    DEFAULT_API_ENDPOINT = "https://api.mapbox.com"
    ROUTING_PATH = "/directions/v5/mapbox"

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
        route = f"{origin.lng},{origin.lat};{destination.lng},{destination.lat}"  # for Mapbox lat/lng are flipped!
        transport_mode = get_mapbox_specific_mode(mode)
        params = {
            "depart_at": departure_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "access_token": self.api_key,
            "exclude": "ferry",  # by default I think it includes ferries, but for our API we use just driving, without ferries
        }
        try:
            async with (
                aiohttp.ClientSession(timeout=self.default_timeout) as session,
                session.get(
                    f"{self.routing_url}/{transport_mode}/{route}", params=params
                ) as response,
            ):
                data = await response.json()
                if response.status == 200:
                    duration = data["routes"][0]["duration"]
                    if not duration:
                        raise MapboxApiError(
                            "No route found between origin and destination."
                        )
                    return RequestResult(travel_time=int(duration))
                else:
                    error_message = data.get("detailedError", "")
                    logger.error(
                        f"Error in Mapbox API response: {response.status} - {error_message}"
                    )
                    return RequestResult(None)
        except Exception as e:
            logger.error(f"Exception during requesting Mapbox API, {e}")
            return RequestResult(None)


def get_mapbox_specific_mode(mode: Mode) -> str:
    if mode == Mode.DRIVING:
        return "driving-traffic"
    elif mode == Mode.PUBLIC_TRANSPORT:
        raise ValueError("Public transport is not supported for Mapbox requests")
    else:
        raise ValueError(f"Unsupported mode: `{mode.value}`")
