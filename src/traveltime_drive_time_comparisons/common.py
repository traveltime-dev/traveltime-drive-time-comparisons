from dataclasses import dataclass


GOOGLE_API = "google"
TOMTOM_API = "tomtom"
HERE_API = "here"
OSRM_API = "osrm"
MAPBOX_API = "mapbox"
TRAVELTIME_API = "traveltime"
VALHALLA_API = "valhalla"


PROVIDER_COLUMN = "Provider"
ACCURARY_SCORE_COLUMN = "Accuracy Score"
RELATIVE_TIME_COLUMN = "Relative Time"


@dataclass
class Fields:
    ORIGIN = "origin"
    DESTINATION = "destination"
    DEPARTURE_TIME = "departure_time"
    TRAVEL_TIME = {
        GOOGLE_API: "google_travel_time",
        TOMTOM_API: "tomtom_travel_time",
        HERE_API: "here_travel_time",
        OSRM_API: "osrm_travel_time",
        MAPBOX_API: "mapbox_travel_time",
        VALHALLA_API: "valhalla_travel_time",
        TRAVELTIME_API: "tt_travel_time",
    }
    SNAPPED_ORIGIN = {
        GOOGLE_API: "google_snapped_origin",
        TOMTOM_API: "tomtom_snapped_origin",
        HERE_API: "here_snapped_origin",
        OSRM_API: "osrm_snapped_origin",
        MAPBOX_API: "mapbox_snapped_origin",
        VALHALLA_API: "valhalla_snapped_origin",
        TRAVELTIME_API: "tt_snapped_origin",
    }
    SNAPPED_DESTINATION = {
        GOOGLE_API: "google_snapped_destination",
        TOMTOM_API: "tomtom_snapped_destination",
        HERE_API: "here_snapped_destination",
        OSRM_API: "osrm_snapped_destination",
        MAPBOX_API: "mapbox_snapped_destination",
        VALHALLA_API: "valhalla_snapped_destination",
        TRAVELTIME_API: "tt_snapped_destination",
    }
    DISTANCE = {
        GOOGLE_API: "google_distance",
        TOMTOM_API: "tomtom_distance",
        HERE_API: "here_distance",
        OSRM_API: "osrm_distance",
        MAPBOX_API: "mapbox_distance",
        VALHALLA_API: "valhalla_distance",
        TRAVELTIME_API: "tt_distance",
    }
    CASE_CATEGORY = "case_category"


def get_capitalized_provider_name(provider: str) -> str:
    if provider == "google":
        return "Google"
    elif provider == "tomtom":
        return "TomTom"
    elif provider == "here":
        return "HERE"
    elif provider == "osrm":
        return "OSRM"
    elif provider == "valhalla":
        return "Valhalla"
    elif provider == "mapbox":
        return "Mapbox"
    elif provider == "traveltime":
        return "TravelTime"
    else:
        raise ValueError(f"Unsupported API provider: {provider}")
