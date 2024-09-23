# TravelTime/Google comparison tool

This tool compares the travel times obtained from [TravelTime Routes API](https://docs.traveltime.com/api/reference/routes),
[Google Maps Directions API](https://developers.google.com/maps/documentation/directions/get-directions),
[TomTom Routing API](https://developer.tomtom.com/routing-api/documentation/tomtom-maps/routing-service),
[HERE Routing API](https://www.here.com/docs/bundle/routing-api-v8-api-reference)
and [Mapbox Directions API](https://docs.mapbox.com/api/navigation/directions/).
Source code is available on [GitHub](https://github.com/traveltime-dev/traveltime-google-comparison).

## Features

- Get travel times from TravelTime API, Google Maps API, TomTom API, HERE API and Mapbox API in parallel, for provided origin/destination pairs and a set 
    of departure times.
- Departure times are calculated based on user provided start time, end time and interval.  
- Analyze the differences between the results and print out the average error percentage.

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
pip install traveltime-google-comparison
```

## Setup
Provide credentials for the APIs via environment variables.

For Google Maps API:

```bash
export GOOGLE_API_KEY=[Your Google Maps API Key]
```

For TomTom API:

```bash
export TOMTOM_API_KEY=[Your TomTom API Key]
```

For HERE API:

```bash
export HERE_API_KEY=[Your HERE API Key]
```

For Mapbox API:

```bash
export MAPBOX_API_KEY=[Your Mapbox API Key]
```

For TravelTime API:
```bash
export TRAVELTIME_APP_ID=[Your TravelTime App ID]
export TRAVELTIME_API_KEY=[Your TravelTime API Key]
```

## Usage
Run the tool:
```bash
traveltime_google_comparison --input [Input CSV file path] --output [Output CSV file path] \
    --date [Date (YYYY-MM-DD)] --start-time [Start time (HH:MM)] --end-time [End time (HH:MM)] \
    --interval [Interval in minutes] --time-zone-id [Time zone ID] 
```
Required arguments:
- `--input [Input CSV file path]`: Path to the input file. Input file is required to have a header row and at least one 
    row with data, with two columns: `origin` and `destination`.
    The values in the columns must be latitude and longitude pairs, separated 
    by comma and enclosed in double quotes. For example: `"51.5074,-0.1278"`. Columns must be separated by comma as well.
    Check out the [project's repository](https://github.com/traveltime-dev/traveltime-google-comparison.git) 
    for examples in the `examples` directory and more pre-prepared routes in the `inputs` directory.
- `--output [Output CSV file path]`: Path to the output file. It will contain the gathered travel times. 
  See the details in the [Output section](#output)
- `--date [Date (YYYY-MM-DD)]`: date on which the travel times are gathered. Use a future date, as Google API returns
  errors for past dates (and times). Take into account the time needed to collect the data for provided input.
- `--start-time [Start time (HH:MM)]`: start time in `HH:MM` format, used for calculation of departure times.
  See [Calculating departure times](#calculating-departure-times)
- `--end-time [End time (HH:MM)]`: end time in `HH:MM` format, used for calculation of departure times.
  See [Calculating departure times](#calculating-departure-times)
- `--interval [Interval in minutes]`: interval in minutes, used for calculation of departure times. 
   See [Calculating departure times](#calculating-departure-times)
- `--time-zone-id [Time zone ID]`: non-abbreviated time zone identifier in which the time values are specified. 
  For example: `Europe/London`. For more information, see [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).



Optional arguments:
- `--google-max-rpm [int]`: Set max number of parallel requests sent to Google API per minute. Default is 60.
  It is enforced on per-second basis, to avoid bursts.
- `--tomtom-max-rpm [int]`: Set max number of parallel requests sent to TomTom API per minute. Default is 60.
  It is enforced on per-second basis, to avoid bursts.
- `--mapbox-max-rpm [int]`: Set max number of parallel requests sent to Mapbox API per minute. Default is 60.
  It is enforced on per-second basis, to avoid bursts.
- `--here-max-rpm [int]`: Set max number of parallel requests sent to HERE API per minute. Default is 60.
  It is enforced on per-second basis, to avoid bursts.
- `--traveltime-max-rpm [int]`: Set max number of parallel requests sent to TravelTime API per minute. Default is 60.
  It is enforced on per-second basis, to avoid bursts.

Example:

```bash
traveltime_google_comparison --input examples/uk.csv --output output.csv --date 2023-09-20 \
    --start-time 07:00 --end-time 20:00 --interval 180 --time-zone-id "Europe/London"
```

## Calculating departure times
Script will collect travel times on the given day for departure times between provided start-time and end-time, with the
given interval. The start-time and end-time are in principle inclusive, however if the time window is not exactly divisible by the 
given interval, the end-time will not be included. For example, if you set the start-time to 08:00, end-time to 20:00 
and interval to 240, the script will sample both APIs for departure times 08:00, 12:00, 16:00 and 20:00 (end-time 
included). But for interval equal to 300, the script will sample APIs for departure times 08:00, 13:00 and 18:00 (end-time 
is not included).

## Output
The output file will contain the `origin` and `destination` columns from input file, with additional 4 columns: 
  - `departure_time`: departure time in `YYYY-MM-DD HH:MM:SS±HHMM` format, calculated from the start-time, end-time and interval.
    It includes date, time and timezone offset.
  - `google_travel_time`: travel time gathered from Google Directions API in seconds
  - `tt_travel_time`: travel time gathered from TravelTime API in seconds
  - `error_percentage`: relative error between Google and TravelTime travel times in percent, relative to Google result.

### Sample output
```csv
origin,destination,departure_time,google_travel_time,tomtom_travel_time,tt_travel_time,error_percentage_google,error_percentage_tomtom
"50.077012199999984, -5.2234787","50.184134100000726, -5.593753699999999",2024-09-20 07:00:00+0100,2276.0,2388.0,2071.0,9,13
"50.077012199999984, -5.2234787","50.184134100000726, -5.593753699999999",2024-09-20 10:00:00+0100,2702.0,2578.0,2015.0,25,21
"50.077012199999984, -5.2234787","50.184134100000726, -5.593753699999999",2024-09-20 13:00:00+0100,2622.0,2585.0,2015.0,23,22
"50.077012199999984, -5.2234787","50.184134100000726, -5.593753699999999",2024-09-20 16:00:00+0100,2607.0,2596.0,2130.0,18,17
"50.077012199999984, -5.2234787","50.184134100000726, -5.593753699999999",2024-09-20 19:00:00+0100,2398.0,2431.0,1960.0,18,19
"50.09814150000003, -5.2586104000000065","50.2165765000003, -5.4758540000000036",2024-09-20 07:00:00+0100,2175.0,2357.0,1861.0,14,21
```

## License
This project is licensed under MIT License. For more details, see the LICENSE file.
