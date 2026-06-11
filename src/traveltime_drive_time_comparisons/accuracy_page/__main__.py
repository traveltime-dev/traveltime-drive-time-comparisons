"""CLI: generate the accuracy-page JSON aggregates from comparison output.csv files.

`--input` is either:

  * a single ``output.csv``  -> a whole country (e.g. the UK), or
  * a directory of ``*.csv``  -> one CSV per state/province (e.g. the US),
    each file named after its subdivision (``Alabama.csv``, ``New_York.csv``).

Examples:
    # whole country
    python -m traveltime_drive_time_comparisons.accuracy_page \\
        --input ./uk.csv --slug uk --output-dir ./generated/uk

    # state/province country (directory of per-state CSVs)
    python -m traveltime_drive_time_comparisons.accuracy_page \\
        --input ./us/ --slug us --output-dir ./generated/us
"""

import argparse
import csv
import glob
import os
import sys
from datetime import datetime, timezone
from typing import List, Optional

from traveltime_drive_time_comparisons.accuracy_page.aggregate import (
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


def _collect_csv_paths(input_path: str) -> List[str]:
    if os.path.isfile(input_path):
        return [input_path]
    return sorted(glob.glob(os.path.join(input_path, "*.csv")))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="traveltime_accuracy_page",
        description="Generate the accuracy-page JSON aggregates from comparison output.csv files.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="A single output.csv (whole country) or a directory of per-state/province CSVs.",
    )
    parser.add_argument(
        "--slug",
        required=True,
        help="Country slug for meta.json (e.g. us, au, ca, uk).",
    )
    parser.add_argument(
        "--output-dir", required=True, help="Folder to write the six JSON files into."
    )
    args = parser.parse_args(argv)

    csv_paths = _collect_csv_paths(args.input)
    if not csv_paths:
        where = "file" if os.path.isfile(args.input) else "directory"
        print(f"error: no CSV found at {args.input} ({where}).", file=sys.stderr)
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
