# Google Routes API handler (replaces legacy Directions API)

import logging
from datetime import datetime
from typing import List

import aiohttp
from traveltimepy.requests.common import Coordinates

from traveltime_drive_time_comparisons.config import Mode
from traveltime_drive_time_comparisons.api_requests.base_handler import (
    BaseRequestHandler,
    RequestResult,
    SnappedCoordinates,
    create_async_limiter,
)

logger = logging.getLogger(__name__)


class GoogleApiError(Exception):
    pass


class GoogleRequestHandler(BaseRequestHandler):
    DEFAULT_API_ENDPOINT = "https://routes.googleapis.com"
    ROUTING_PATH = "/directions/v2:computeRoutes"

    default_timeout = aiohttp.ClientTimeout(total=60)

    FIELD_MASK = ",".join(
        [
            "routes.duration",
            "routes.distanceMeters",
            "routes.warnings",
            "routes.legs.startLocation",
            "routes.legs.endLocation",
        ]
    )

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
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": self.FIELD_MASK,
        }

        body = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin.lat,
                        "longitude": origin.lng,
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": destination.lat,
                        "longitude": destination.lng,
                    }
                }
            },
            "travelMode": get_google_travel_mode(mode),
            "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
            "departureTime": departure_time.isoformat(),
            "trafficModel": "BEST_GUESS",
        }

        try:
            async with (
                aiohttp.ClientSession(timeout=self.default_timeout) as session,
                session.post(self.routing_url, json=body, headers=headers) as response,
            ):
                data = await response.json()

                if "error" in data:
                    error = data["error"]
                    logger.error(
                        f"Error in Google Routes API response: {error.get('status')} - {error.get('message')}"
                    )
                    return RequestResult(None)

                routes = data.get("routes", [])
                if not routes:
                    logger.error("No routes returned from Google Routes API")
                    return RequestResult(None)

                route = routes[0]

                duration_str = route.get("duration", "0s")
                travel_time = int(duration_str.rstrip("s"))

                distance = route.get("distanceMeters")

                warnings: List[str] = route.get("warnings", [])

                snapped = None
                legs = route.get("legs", [])
                if legs:
                    leg = legs[0]
                    start_loc = leg.get("startLocation", {}).get("latLng", {})
                    end_loc = leg.get("endLocation", {}).get("latLng", {})

                    if start_loc and end_loc:
                        snapped = SnappedCoordinates(
                            origin_lat=start_loc.get("latitude"),
                            origin_lng=start_loc.get("longitude"),
                            destination_lat=end_loc.get("latitude"),
                            destination_lng=end_loc.get("longitude"),
                        )

                return RequestResult(
                    travel_time=travel_time,
                    distance=distance,
                    snapped_coords=snapped,
                    warnings=warnings,
                )

        except Exception as e:
            logger.error(f"Exception during requesting Google Routes API: {e}")
            return RequestResult(None)


def get_google_travel_mode(mode: Mode) -> str:
    if mode == Mode.DRIVING:
        return "DRIVE"
    elif mode == Mode.PUBLIC_TRANSPORT:
        return "TRANSIT"
    else:
        raise ValueError(f"Unsupported mode: `{mode.value}`")
