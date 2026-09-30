# accuracy_page_data

Generates the per-country JSON aggregates the accuracy page renders, from the
comparison tool's `output.csv` files.

It produces six files:

```
headline.json  bands.json  time-of-day.json  bias.json  by-state.json  meta.json
```

## Usage

`--input` (`-i`) takes one or more paths, each a CSV file or a directory of
CSVs. One CSV = a whole country; many CSVs = one per state/province, each named
after its subdivision (`Alabama.csv` → "Alabama").

```bash
# whole country: one output.csv
python -m traveltime_drive_time_comparisons.accuracy_page_data \
    -i ./uk.csv -s uk -o ./generated/uk

# state/province country: a directory of per-state CSVs
#   ./us/Alabama.csv, ./us/New_York.csv, ...
python -m traveltime_drive_time_comparisons.accuracy_page_data \
    -i ./us -s us -o ./generated/us

# ... or the CSVs listed explicitly (no shared directory needed)
python -m traveltime_drive_time_comparisons.accuracy_page_data \
    -i Alabama.csv New_York.csv -s us -o ./generated/us
```

After `pip install -e .` the console script `traveltime_accuracy_page_data` is also
available.

## Input

Each CSV is one complete comparison run (`output.csv`). Within a file, rows are deduplicated per route on
`(origin, destination, time-of-day slot)`, then the `case_category == "clean"`
filter is applied (Google governs whether a route is usable).
