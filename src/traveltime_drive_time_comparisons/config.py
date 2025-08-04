import argparse
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import pandas
import json

from traveltime_drive_time_comparisons.api_requests.traveltime_credentials import (
    Credentials,
)

DEFAULT_GOOGLE_RPM = 60
DEFAULT_TOMTOM_RPM = 60
DEFAULT_HERE_RPM = 60
DEFAULT_OSRM_RPM = 60
DEFAULT_OPENROUTES_RPM = 20
DEFAULT_MAPBOX_RPM = 60
DEFAULT_VALHALLA_RPM = 60
DEFAULT_TRAVELTIME_RPM = 60

GOOGLE_API_KEY_VAR_NAME = "GOOGLE_API_KEY"
TOMTOM_API_KEY_VAR_NAME = "TOMTOM_API_KEY"
OPENROUTES_API_KEY_VAR_NAME = "OPENROUTES_API_KEY"
HERE_API_KEY_VAR_NAME = "HERE_API_KEY"
MAPBOX_API_KEY_VAR_NAME = "MAPBOX_API_KEY"
TRAVELTIME_APP_ID_VAR_NAME = "TRAVELTIME_APP_ID"
TRAVELTIME_API_KEY_VAR_NAME = "TRAVELTIME_API_KEY"

pandas.set_option("display.max_columns", None)
pandas.set_option("display.width", None)


@dataclass
class Provider:
    name: str
    max_rpm: int
    credentials: Credentials
    api_endpoint: Optional[str]


@dataclass
class Providers:
    base: Provider
    competitors: List[Provider]

    def all_names(self) -> List[str]:
        return [self.base.name] + [competitor.name for competitor in self.competitors]

    def all_providers(self) -> List[Provider]:
        return [self.base] + [competitor for competitor in self.competitors]


class Mode(Enum):
    DRIVING = "driving"
    PUBLIC_TRANSPORT = "public_transport"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch and compare travel times from TravelTime Routes API and it's competitors"
    )
    parser.add_argument("--input", required=True, help="Input CSV file path")
    parser.add_argument("--output", required=True, help="Output CSV file path")
    parser.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
    parser.add_argument(
        "--departure-times",
        required=True,
        help="Departure times, separated by `,` (HH:MM, HH:MM)",
    )
    parser.add_argument(
        "--time-zone-id",
        required=True,
        help="Non-abbreviated time zone identifier e.g. Europe/London",
    )
    parser.add_argument(
        "--config",
        required=False,
        default="./config.json",
        help="Path to your config file. Default - ./config.json",
    )
    parser.add_argument(
        "--skip-data-gathering",
        action=argparse.BooleanOptionalAction,
        help=(
            "If set, reads already gathered data from input file and skips data gathering. "
            "Input file must conform to the output file format."
        ),
    )
    parser.add_argument(
        "--skip-plotting",
        action=argparse.BooleanOptionalAction,
        help=("If set, graphs of the final summary will not be shown."),
    )
    return parser.parse_args()


def parse_json_to_providers(json_data: str) -> Providers:
    data = json.loads(json_data)

    # Parse TravelTime (base provider)
    traveltime_data = data["traveltime"]
    base_provider = Provider(
        name="traveltime",
        max_rpm=int(traveltime_data["max-rpm"]),
        credentials=Credentials(
            app_id=traveltime_data["app-id"], api_key=traveltime_data["api-key"]
        ),
        api_endpoint=traveltime_data.get("api-endpoint"),
    )

    # Parse competitor providers
    competitors = []
    for provider_data in data["api-providers"]:
        enabled = provider_data["enabled"]
        if enabled:
            competitor = Provider(
                name=provider_data["name"],
                max_rpm=int(provider_data["max-rpm"]),
                credentials=Credentials(api_key=provider_data["api-key"]),
                api_endpoint=provider_data.get("api-endpoint"),
            )
            competitors.append(competitor)

    return Providers(base=base_provider, competitors=competitors)


def parse_config(file_path: str):
    with open(file_path, "r") as file:  # letting it crash if this fails
        content = file.read()
        return parse_json_to_providers(content)
