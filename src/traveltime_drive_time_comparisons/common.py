from dataclasses import dataclass


GOOGLE_API = "google"
TOMTOM_API = "tomtom"
HERE_API = "here"
OSRM_API = "osrm"
MAPBOX_API = "mapbox"
TRAVELTIME_API = "traveltime"
OPENROUTES_API = "openroutes"
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
        OPENROUTES_API: "openroutes_travel_time",
        VALHALLA_API: "valhalla_travel_time",
        TRAVELTIME_API: "tt_travel_time",
    }


def get_capitalized_provider_name(provider: str) -> str:
    if provider == "google":
        return "Google"
    elif provider == "tomtom":
        return "TomTom"
    elif provider == "here":
        return "HERE"
    elif provider == "osrm":
        return "OSRM"
    elif provider == "openroutes":
        return "OpenRoutes"
    elif provider == "valhalla":
        return "Valhalla"
    elif provider == "mapbox":
        return "Mapbox"
    elif provider == "traveltime":
        return "TravelTime"
    else:
        raise ValueError(f"Unsupported API provider: {provider}")
