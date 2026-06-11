# accuracy_page

Generates the per-country JSON aggregates the accuracy page renders, from the
comparison tool's `output.csv` files.

It produces six files:

```
headline.json  bands.json  time-of-day.json  bias.json  by-state.json  meta.json
```

## Usage

`--input` is either a single CSV (a whole country) or a directory of CSVs (one
per state/province, each named after its subdivision):

```bash
# whole country: one output.csv
python -m traveltime_drive_time_comparisons.accuracy_page \
    --input ./uk.csv --slug uk --output-dir ./generated/uk

# state/province country: a directory of per-state CSVs
#   ./us/Alabama.csv, ./us/New_York.csv, ...
python -m traveltime_drive_time_comparisons.accuracy_page \
    --input ./us --slug us --output-dir ./generated/us
```

After `pip install -e .` the console script `traveltime_accuracy_page` is also
available.

## Input

Each CSV is one complete comparison run (`output.csv`). Within a file, rows are deduplicated per route on
`(origin, destination, time-of-day slot)`, then the `case_category == "clean"`
filter is applied (Google governs whether a route is usable).
