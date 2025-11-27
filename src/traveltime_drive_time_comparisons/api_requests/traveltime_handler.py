from datetime import datetime
from typing import Union
import logging

from traveltimepy import AsyncClient
from traveltimepy.requests.common import (
    Coordinates,
    Property,
    Snapping,
    SnappingAcceptRoads,
    SnappingPenalty,
    Location,
)
from traveltimepy.requests.routes import RoutesDepartureSearch
from traveltimepy.requests.transportation import Driving, PublicTransport

from traveltime_drive_time_comparisons.config import Mode
from traveltime_drive_time_comparisons.api_requests.base_handler import (
    BaseRequestHandler,
    RequestResult,
    SnappedCoordinates,
    create_async_limiter,
)

logger = logging.getLogger(__name__)


class TravelTimeRequestHandler(BaseRequestHandler):
    ORIGIN_ID = "o"
    DESTINATION_ID = "d"

    def __init__(self, app_id, api_key, max_rpm, api_endpoint):
        self.sdk_kwargs = {
            "app_id": app_id,
            "api_key": api_key,
            "_user_agent": "Travel Time Comparison Tool",
        }
        if api_endpoint is not None:
            self.sdk_kwargs["_host"] = api_endpoint

        self._rate_limiter = create_async_limiter(max_rpm)

    async def send_request(
        self,
        origin: Coordinates,
        destination: Coordinates,
        departure_time: datetime,
        mode: Mode,
    ) -> RequestResult:
        locations = [
            Location(id=self.ORIGIN_ID, coords=origin),
            Location(id=self.DESTINATION_ID, coords=destination),
        ]
        response = None
        async with AsyncClient(**self.sdk_kwargs) as client:
            try:
                response = await client.routes(
                    locations=locations,
                    departure_searches=[
                        RoutesDepartureSearch(
                            id=f"{origin} to {destination} at {departure_time} with {mode}",
                            departure_location_id=self.ORIGIN_ID,
                            arrival_location_ids=[self.DESTINATION_ID],
                            transportation=get_traveltime_specific_mode(mode),
                            departure_time=departure_time,
                            properties=[Property.TRAVEL_TIME, Property.ROUTE],
                            snapping=Snapping(
                                penalty=SnappingPenalty.DISABLED,
                                accept_roads=SnappingAcceptRoads.BOTH_DRIVABLE_AND_WALKABLE,
                            ),
                        )
                    ],
                    arrival_searches=[],
                )
            except Exception as e:
                logger.error(f"Exception during requesting TravelTime API, {e}")
                return RequestResult(None)

        if (
            not response
            or not response.results[0].locations
            or not response.results[0].locations[0].properties
        ):
            return RequestResult(None)

        properties = response.results[0].locations[0].properties[0]

        snapped = None
        distance = None
        route = properties.route
        if route and route.parts:
            all_coords = []
            for part in route.parts:
                if part.coords:
                    all_coords.extend(part.coords)
            if len(all_coords) >= 2:
                first_coord = all_coords[0]
                last_coord = all_coords[-1]
                snapped = SnappedCoordinates(
                    origin_lat=first_coord.lat,
                    origin_lng=first_coord.lng,
                    destination_lat=last_coord.lat,
                    destination_lng=last_coord.lng,
                )
            distance = sum(
                part.distance for part in route.parts if part.distance is not None
            )

        return RequestResult(
            travel_time=properties.travel_time,
            distance=distance,
            snapped_coords=snapped,
        )


class RouteNotFoundError(Exception):
    pass


def get_traveltime_specific_mode(mode: Mode) -> Union[Driving, PublicTransport]:
    if mode.value == Mode.DRIVING.value:
        return Driving()
    elif mode.value == Mode.PUBLIC_TRANSPORT.value:
        return PublicTransport()
    else:
        raise ValueError(f"Unsupported mode `{mode.value}`")
