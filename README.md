# TravelTime Drive Time Comparisons tool

This tool compares the travel times obtained from [TravelTime Routes API](https://docs.traveltime.com/api/reference/routes),
[Google Maps Directions API](https://developers.google.com/maps/documentation/directions/get-directions),
[TomTom Routing API](https://developer.tomtom.com/routing-api/documentation/tomtom-maps/routing-service),
[HERE Routing API](https://www.here.com/docs/bundle/routing-api-v8-api-reference),
[Mapbox Directions API](https://docs.mapbox.com/api/navigation/directions/),
[OpenRoutes API](https://openrouteservice.org/dev/#/api-docs/v2/directions/%7Bprofile%7D/get),
[OSRM Routes API](https://project-osrm.org/docs/v5.5.1/api/?language=cURL#route-service),
and [Valhalla Routes API](https://valhalla.github.io/valhalla/api/turn-by-turn/api-reference/).
Source code is available on [GitHub](https://github.com/traveltime-dev/traveltime-drive-time-comparisons).

## Features

- Get travel times from TravelTime API, Google Maps API, TomTom API, HERE API, Mapbox API, OSRM API and Valhalla API in parallel, for provided origin/destination pairs and a set 
    of departure times.
- Analyze the differences between the results and print out an accuracy comparison, also the average error percentage when compared to TravelTime.

## Prerequisites

The tool requires Python 3.8+ installed on your system. You can download it from [here](https://www.python.org/downloads/).

## Installation
Create a new virtual environment with a chosen name (here, we'll name it 'env'):
```bash
python -m venv env
```

Activate the virtual environment:
```bash
source env/bin/activate
```

Install the project and its dependencies:
```bash
pip install traveltime-drive-time-comparisons
```

## Setup
Provide credentials and desired max requests per minute for the APIs inside the `config.json` file.
You can also disable unwanted APIs by changing the `enabled` value to `false`.

```json
{
  "traveltime": {
    "app-id": "<your-app-id>",
    "api-key": "<your-api-key>",
    "max-rpm": "60"
  },
  "api-providers": [
    {
      "name": "google",
      "enabled": true,
      "api-key": "<your-api-key>",
      "max-rpm": "60"
    },
    ...other providers
  ]
}
```

## Usage
Run the tool:
```bash
traveltime_drive_time_comparisons --input [Input CSV file path] --output [Output CSV file path] \
    --date [Date (YYYY-MM-DD)] --departure-times [Departure times (HH:MM, HH:MM)] --time-zone-id [Time zone ID] 
```
Required arguments:
- `--input [Input CSV file path]`: Path to the input file. Input file is required to have a header row and at least one 
    row with data, with two columns: `origin` and `destination`.
    The values in the columns must be latitude and longitude pairs, separated 
    by comma and enclosed in double quotes. For example: `"51.5074,-0.1278"`. Columns must be separated by comma as well.
    Check out the [project's repository](https://github.com/traveltime-dev/traveltime-drive-time-comparisons.git) 
    for examples in the `examples` directory and more pre-prepared routes in the `inputs` directory.
- `--output [Output CSV file path]`: Path to the output file. It will contain the gathered travel times. 
  See the details in the [Output section](#output)
- `--date [Date (YYYY-MM-DD)]`: date on which the travel times are gathered. Use a future date, as Google API returns
  errors for past dates (and times). Take into account the time needed to collect the data for provided input.
- `--departure-times [Departure times (HH:MM)]`: All departure times in `HH:MM` format, separated by comma ",", spaces can be used.
- `--time-zone-id [Time zone ID]`: non-abbreviated time zone identifier in which the time values are specified. 
  For example: `Europe/London`. For more information, see [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

Optional arguments:
- `--config [Config file path]`: Path to the config file. Default - ./config.json

Example:

```bash
traveltime_drive_time_comparisons --input examples/uk.csv --output output.csv --date 2023-09-20 \
    --departure-times "07:00, 10:00, 13:00, 16:00, 19:00" --time-zone-id "Europe/London"
```

## Console output

The console output contains results from the cross-validation. These results are calculated by
comparing one provider's results with the average of all competitors. This process is repeated for
all providers
```
2025-01-24 15:30:00 | INFO | Provider cross-validation results: 
     Provider  Accuracy %
0  TravelTime   90.717912
1      Google   82.346109
2      TomTom   75.481112

```

It also contains more detailed comparisons with each API 
```
2025-06-11 13:23:36 | INFO | Comparing TravelTime to other providers:
2025-06-11 13:23:36 | INFO | 	Mean relative error compared to Google API: 12.91%
2025-06-11 13:23:36 | INFO | 	90% of TravelTime results differ from Google API by less than 32%
2025-06-11 13:23:36 | INFO | 	Mean relative error compared to TomTom API: 26.50%
2025-06-11 13:23:36 | INFO | 	90% of TravelTime results differ from TomTom API by less than 48%
2025-06-11 13:23:36 | INFO | Comparing Google to other providers:
2025-06-11 13:23:36 | INFO | 	Mean relative error compared to TravelTime API: 17.11%
2025-06-11 13:23:36 | INFO | 	90% of Google results differ from TravelTime API by less than 48%
2025-06-11 13:23:36 | INFO | 	Mean relative error compared to TomTom API: 33.21%
2025-06-11 13:23:36 | INFO | 	90% of Google results differ from TomTom API by less than 40%
2025-06-11 13:23:36 | INFO | Comparing TomTom to other providers:
2025-06-11 13:23:36 | INFO | 	Mean relative error compared to TravelTime API: 19.58%
2025-06-11 13:23:36 | INFO | 	90% of TomTom results differ from TravelTime API by less than 32%
2025-06-11 13:23:36 | INFO | 	Mean relative error compared to Google API: 24.60%
2025-06-11 13:23:36 | INFO | 	90% of TomTom results differ from Google API by less than 29%
```

## File output
The output file will contain the `origin` and `destination` columns from input file, with some additional columns: 
  - `departure_time`: departure time in `YYYY-MM-DD HH:MM:SS±HHMM` format.
    It includes date, time and timezone offset.
  - `*_travel_time`: travel time gathered from alternative provider API in seconds
  - `tt_travel_time`: travel time gathered from TravelTime API in seconds
  - `error_percentage_*`: relative error between provider and TravelTime travel times in percent, relative to provider result.

### Sample output with 3 providers - TravelTime, Google and TomTom
```csv
origin,destination,departure_time,tt_travel_time,google_travel_time,tomtom_travel_time,error_percentage_traveltime_to_google,error_percentage_traveltime_to_tomtom,error_percentage_google_to_traveltime,error_percentage_google_to_tomtom,error_percentage_tomtom_to_traveltime,error_percentage_tomtom_to_google
"33.05187660000014 , -117.1350031999999","33.14408130000009 , -117.02942509999977",2025-06-20 13:00:00-0700,1970.0,2224.0,1869.0,11,5,12,18,5,15
"33.05187660000014 , -117.1350031999999","33.14408130000009 , -117.02942509999977",2025-06-20 16:00:00-0700,2052.0,3042.0,2274.0,32,9,48,33,10,25
"37.36713689999986 , -122.09885940000017","37.35365440000001 , -122.21751989999996",2025-06-20 13:00:00-0700,1868.0,1832.0,1317.0,1,41,1,39,29,28
"37.36713689999986 , -122.09885940000017","37.35365440000001 , -122.21751989999996",2025-06-20 16:00:00-0700,2004.0,1896.0,1345.0,5,48,5,40,32,29
```

## License
This project is licensed under MIT License. For more details, see the LICENSE file.
