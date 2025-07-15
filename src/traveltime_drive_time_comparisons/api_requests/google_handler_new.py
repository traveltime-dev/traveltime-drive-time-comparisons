# This file is currently unused, as we use the Directions (legacy) API currently.
# This is here so we can easily swtich when ready

import logging
from datetime import datetime

from google.maps.routing_v2 import RoutesClient, ComputeRoutesRequest, Waypoint
from google.maps.routing_v2.types import (
    RouteTravelMode,
    RoutingPreference,
    Location,
    TrafficModel,
)
from google.type.latlng_pb2 import LatLng  # type: ignore
from google.protobuf.timestamp_pb2 import Timestamp

from traveltimepy.requests.common import Coordinates

from traveltime_drive_time_comparisons.config import Mode
from traveltime_drive_time_comparisons.api_requests.base_handler import (
    BaseRequestHandler,
    RequestResult,
    create_async_limiter,
)

logger = logging.getLogger(__name__)


class GoogleApiError(Exception):
    pass


class GoogleRequestHandler(BaseRequestHandler):
    def __init__(self, api_key, max_rpm, api_endpoint):
        self.api_key = api_key
        self._rate_limiter = create_async_limiter(max_rpm)

        from google.api_core.client_options import ClientOptions

        client_options = ClientOptions(api_key=self.api_key, api_endpoint=api_endpoint)
        self.client = RoutesClient(client_options=client_options)

    async def send_request(
        self,
        origin: Coordinates,
        destination: Coordinates,
        departure_time: datetime,
        mode: Mode,
    ) -> RequestResult:
        try:
            origin_location = Location(
                lat_lng=LatLng(latitude=origin.lat, longitude=origin.lng)
            )
            origin_waypoint = Waypoint(location=origin_location)

            destination_location = Location(
                lat_lng=LatLng(latitude=destination.lat, longitude=destination.lng)
            )
            destination_waypoint = Waypoint(location=destination_location)

            departure_timestamp = Timestamp()
            departure_timestamp.FromDatetime(departure_time)

            request = ComputeRoutesRequest(
                origin=origin_waypoint,
                destination=destination_waypoint,
                travel_mode=get_google_travel_mode(mode),
                routing_preference=RoutingPreference.TRAFFIC_AWARE_OPTIMAL,
                departure_time=departure_timestamp,
                traffic_model=TrafficModel.BEST_GUESS,
            )

            response = self.client.compute_routes(
                request=request, metadata=[("x-goog-fieldmask", "routes.duration")]
            )

            if response.routes:
                route = response.routes[0]
                travel_time = route.duration.seconds
                return RequestResult(travel_time=travel_time)
            else:
                logger.error("No routes returned from Google Maps Routing API")
                return RequestResult(None)

        except Exception as e:
            logger.error(f"Exception during requesting Google Maps Routing API: {e}")
            return RequestResult(None)


def get_google_travel_mode(mode: Mode) -> int:
    if mode == Mode.DRIVING:
        return RouteTravelMode.DRIVE
    elif mode == Mode.PUBLIC_TRANSPORT:
        return RouteTravelMode.TRANSIT
    else:
        raise ValueError(f"Unsupported mode: `{mode.value}`")
