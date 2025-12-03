import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
import pytz
from pandas import DataFrame
from pytz.tzinfo import BaseTzInfo
from traveltimepy.requests.common import Coordinates

from traveltime_drive_time_comparisons.common import (
    Fields,
    get_capitalized_provider_name,
)
from traveltime_drive_time_comparisons.config import Mode
from traveltime_drive_time_comparisons.api_requests.base_handler import (
    BaseRequestHandler,
    SnappedCoordinates,
)


logger = logging.getLogger(__name__)


async def fetch_travel_time(
    origin: str,
    destination: str,
    api: str,
    departure_time: datetime,
    request_handler: BaseRequestHandler,
    mode: Mode,
) -> Dict[str, str]:
    origin_coord = parse_coordinates(origin)
    destination_coord = parse_coordinates(destination)

    async with request_handler.rate_limiter:
        logger.debug(
            f"Sending request to {api} for {origin_coord}, {destination_coord}, {departure_time}"
        )
        result = await request_handler.send_request(
            origin_coord, destination_coord, departure_time, mode
        )
        logger.debug(
            f"Finished request to {api} for {origin_coord}, {destination_coord}, {departure_time}"
        )
        return wrap_result(
            origin,
            destination,
            result.travel_time,
            result.distance,
            result.snapped_coords,
            departure_time,
            api,
        )


def parse_coordinates(coord_string: str) -> Coordinates:
    lat, lng = [c.strip() for c in coord_string.split(",")]
    return Coordinates(lat=float(lat), lng=float(lng))


def wrap_result(
    origin: str,
    destination: str,
    travel_time: Optional[int],
    distance: Optional[int],
    snapped_coords: Optional[SnappedCoordinates],
    departure_time: datetime,
    api: str,
):
    result = {
        Fields.ORIGIN: origin,
        Fields.DESTINATION: destination,
        Fields.DEPARTURE_TIME: departure_time.strftime("%Y-%m-%d %H:%M:%S%z"),
        Fields.TRAVEL_TIME[api]: travel_time,
        Fields.DISTANCE[api]: distance,
    }
    if snapped_coords:
        if (
            snapped_coords.origin_lat is not None
            and snapped_coords.origin_lng is not None
        ):
            result[Fields.SNAPPED_ORIGIN[api]] = (
                f"{snapped_coords.origin_lat},{snapped_coords.origin_lng}"
            )
        if (
            snapped_coords.destination_lat is not None
            and snapped_coords.destination_lng is not None
        ):
            result[Fields.SNAPPED_DESTINATION[api]] = (
                f"{snapped_coords.destination_lat},{snapped_coords.destination_lng}"
            )
    return result


def localize_datetime(date: str, time: str, timezone: BaseTzInfo) -> datetime:
    datetime_instance = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    return timezone.localize(datetime_instance)


def generate_tasks(
    data: DataFrame,
    time_instants: List[datetime],
    request_handlers: Dict[str, BaseRequestHandler],
    mode: Mode,
) -> list:
    tasks = []
    for index, row in data.iterrows():
        for time_instant in time_instants:
            for api, request_handler in request_handlers.items():
                task = fetch_travel_time(
                    row[Fields.ORIGIN],
                    row[Fields.DESTINATION],
                    api,
                    time_instant,
                    request_handler,
                    mode=mode,
                )
                tasks.append(task)
    return tasks


async def collect_travel_times(
    args,
    data,
    request_handlers: Dict[str, BaseRequestHandler],
    provider_names: List[str],
) -> DataFrame:
    timezone = pytz.timezone(args.time_zone_id)
    time_instants = generate_time_instants(args.departure_times, args.date, timezone)

    tasks = generate_tasks(data, time_instants, request_handlers, mode=Mode.DRIVING)

    capitalized_providers_str = ", ".join(
        [get_capitalized_provider_name(provider) for provider in provider_names]
    )
    logger.info(f"Sending {len(tasks)} requests to {capitalized_providers_str} APIs")

    results = await asyncio.gather(*tasks)

    results_df = pd.DataFrame(results)

    agg_dict = {Fields.TRAVEL_TIME[provider]: "first" for provider in provider_names}
    for provider in provider_names:
        snapped_origin_col = Fields.SNAPPED_ORIGIN[provider]
        snapped_dest_col = Fields.SNAPPED_DESTINATION[provider]
        distance_col = Fields.DISTANCE[provider]
        if snapped_origin_col in results_df.columns:
            agg_dict[snapped_origin_col] = "first"
        if snapped_dest_col in results_df.columns:
            agg_dict[snapped_dest_col] = "first"
        if distance_col in results_df.columns:
            agg_dict[distance_col] = "first"

    deduplicated = results_df.groupby(
        [Fields.ORIGIN, Fields.DESTINATION, Fields.DEPARTURE_TIME], as_index=False
    ).agg(agg_dict)
    deduplicated.to_csv(args.output, index=False)
    return deduplicated


def generate_time_instants(
    departure_times_str: str, date: str, timezone: BaseTzInfo
) -> List[datetime]:
    if departure_times_str.strip() != "":
        times = [
            departure_time.strip() for departure_time in departure_times_str.split(",")
        ]
        return [localize_datetime(date, time, timezone) for time in times]
    else:
        raise ValueError("At least one departure time must be provided.")
