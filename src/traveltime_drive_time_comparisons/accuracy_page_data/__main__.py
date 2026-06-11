"""CLI: generate the accuracy-page JSON aggregates from comparison output.csv files.

``--input`` takes one or more paths, each a CSV file or a directory of ``*.csv``.
Each CSV is one subdivision, named after its filename (``Alabama.csv`` -> "Alabama"):

  * one CSV            -> a whole country (e.g. the UK)
  * many CSVs / a dir  -> one CSV per state/province (e.g. the US)

Examples:
    # whole country
    python -m traveltime_drive_time_comparisons.accuracy_page_data \\
        --input ./uk.csv --slug uk --output-dir ./generated/uk

    # state/province country — a directory of per-state CSVs ...
    python -m traveltime_drive_time_comparisons.accuracy_page_data \\
        --input ./us/ --slug us --output-dir ./generated/us

    # ... or the CSVs listed explicitly (no shared directory needed)
    python -m traveltime_drive_time_comparisons.accuracy_page_data \\
        --input Alabama.csv New_York.csv --slug us --output-dir ./generated/us
"""

import argparse
import csv
import glob
import os
import sys
from datetime import datetime, timezone
from typing import List, Optional

from traveltime_drive_time_comparisons.accuracy_page_data.aggregate import (
    AGGREGATE_FILES,
    aggregate,
    dumps,
    extract_rows,
)


def _read_csv(path: str) -> List[dict]:
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _subdivision_name(csv_path: str) -> str:
    return os.path.splitext(os.path.basename(csv_path))[0].replace("_", " ")


def _collect_csv_paths(inputs: List[str]) -> List[str]:
    paths: List[str] = []
    for item in inputs:
        if os.path.isdir(item):
            paths.extend(sorted(glob.glob(os.path.join(item, "*.csv"))))
        elif os.path.isfile(item):
            paths.append(item)
    return paths


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="traveltime_accuracy_page_data",
        description="Generate the accuracy-page JSON aggregates from comparison output.csv files.",
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        nargs="+",
        metavar="PATH",
        help="One or more CSV files and/or directories of CSVs. One CSV = whole country; many = per state/province.",
    )
    parser.add_argument(
        "-s",
        "--slug",
        required=True,
        help="Country slug for meta.json (e.g. us, au, ca, uk).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="Folder to write the six JSON files into.",
    )
    args = parser.parse_args(argv)

    csv_paths = _collect_csv_paths(args.input)
    if not csv_paths:
        print(f"error: no CSV files found in {args.input}.", file=sys.stderr)
        return 2

    rows: List[dict] = []
    total_scanned = 0
    od_pairs = set()
    latest_mtime: Optional[datetime] = None

    for csv_path in csv_paths:
        name = _subdivision_name(csv_path)
        srows, scanned, sod = extract_rows(name, _read_csv(csv_path))
        rows.extend(srows)
        total_scanned += scanned
        od_pairs |= sod
        mtime = datetime.fromtimestamp(os.path.getmtime(csv_path), tz=timezone.utc)
        if latest_mtime is None or mtime > latest_mtime:
            latest_mtime = mtime
        print(f"  {name}: +{len(srows)} clean rows")

    if not rows:
        print(f"error: no clean rows found in {args.input}.", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    generated_at = _iso(now)
    data_collected_at = _iso(latest_mtime) if latest_mtime is not None else generated_at

    payloads = aggregate(
        rows, args.slug, total_scanned, len(od_pairs), generated_at, data_collected_at
    )

    os.makedirs(args.output_dir, exist_ok=True)
    for key, filename in AGGREGATE_FILES.items():
        out_path = os.path.join(args.output_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(dumps(payloads[key]))
        print(f"  wrote {out_path}")

    print(
        f"Done: {len(rows)} clean rows from {len(csv_paths)} CSV(s) -> {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
