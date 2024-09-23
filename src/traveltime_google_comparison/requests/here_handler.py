import logging
from datetime import datetime

import aiohttp
from aiolimiter import AsyncLimiter
from traveltimepy import Coordinates

from traveltime_google_comparison.config import Mode
from traveltime_google_comparison.requests.base_handler import (
    BaseRequestHandler,
    RequestResult,
)

logger = logging.getLogger(__name__)


class HereApiError(Exception):
    pass


class HereRequestHandler(BaseRequestHandler):
    HERE_ROUTES_URL = "https://router.hereapi.com/v8/routes"

    default_timeout = aiohttp.ClientTimeout(total=60)

    def __init__(self, api_key, max_rpm):
        self.api_key = api_key
        self._rate_limiter = AsyncLimiter(max_rpm // 60, 1)

    async def send_request(
        self,
        origin: Coordinates,
        destination: Coordinates,
        departure_time: datetime,
        mode: Mode,
    ) -> RequestResult:
        params = {
            "transportMode": get_here_specific_mode(mode),
            "origin": f"{origin.lat},{origin.lng}",
            "destination": f"{destination.lat},{destination.lng}",
            "return": "summary",
            "departureTime": departure_time.strftime("%Y-%m-%dT%H:%M:%S"),
            "apikey": self.api_key,
        }
        try:
            async with aiohttp.ClientSession(
                timeout=self.default_timeout
            ) as session, session.get(self.HERE_ROUTES_URL, params=params) as response:
                data = await response.json()
                if response.status == 200:
                    first_route = data["routes"][0]

                    if not first_route:
                        raise HereApiError(
                            "No route found between origin and destination."
                        )

                    # I think for a simple routing request, there should only be one section. But just in case
                    # I'm taking the sum of all sections
                    total_duration = sum(
                        section["summary"]["duration"]
                        for section in first_route["sections"]
                    )

                    return RequestResult(travel_time=total_duration)
                else:
                    error_message = data.get("detailedError", "")
                    logger.error(
                        f"Error in HERE API response: {response.status} - {error_message}"
                    )
                    return RequestResult(None)
        except Exception as e:
            logger.error(f"Exception during requesting HERE API, {e}")
            return RequestResult(None)


def get_here_specific_mode(mode: Mode) -> str:
    if mode == Mode.DRIVING:
        return "car"
    elif mode == Mode.PUBLIC_TRANSPORT:
        return "bus"  # HERE doesn't have a general mode for transit / PT
        # TODO: figure out how to compare PT modes accorss different providers

    else:
        raise ValueError(f"Unsupported mode: `{mode.value}`")
