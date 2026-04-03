import argparse
import asyncio
import re
from datetime import date, timedelta
from pathlib import Path

import pytz
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def next_wednesday():
    today = date.today()
    days_ahead = (2 - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (today + timedelta(days=days_ahead)).isoformat()


def validate_date(text):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return "Date must be in YYYY-MM-DD format"
    try:
        parts = text.split("-")
        date(int(parts[0]), int(parts[1]), int(parts[2]))
        return True
    except ValueError:
        return "Invalid date"


def validate_departure_times(text):
    times = [t.strip() for t in text.split(",")]
    for t in times:
        if not re.match(r"^\d{2}:\d{2}$", t):
            return f"Invalid time format: '{t}'. Expected HH:MM"
    return True


CUSTOM_PATH_OPTION = "Enter custom path..."

INPUTS_DIR = Path(__file__).resolve().parent.parent.parent / "inputs"


def choose_input_file() -> str:
    if not INPUTS_DIR.is_dir():
        return questionary.path("Input CSV file:").unsafe_ask()

    regions = sorted(
        d.name
        for d in INPUTS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    source = questionary.select(
        "Input data source:",
        choices=["Browse pre-prepared datasets", CUSTOM_PATH_OPTION],
    ).unsafe_ask()

    if source == CUSTOM_PATH_OPTION:
        return questionary.path("Input CSV file:").unsafe_ask()

    region = questionary.select("Region:", choices=regions).unsafe_ask()
    region_dir = INPUTS_DIR / region

    files = sorted(f.name for f in region_dir.iterdir() if f.suffix == ".csv")
    if not files:
        console.print(f"[yellow]No CSV files found in {region_dir}[/yellow]")
        return questionary.path("Input CSV file:").unsafe_ask()

    chosen = questionary.select(
        "Dataset:",
        choices=files + [CUSTOM_PATH_OPTION],
    ).unsafe_ask()

    if chosen == CUSTOM_PATH_OPTION:
        return questionary.path("Input CSV file:").unsafe_ask()

    return str(region_dir / chosen)


def build_args(debug: bool = False) -> argparse.Namespace:
    console.print(
        Panel(
            "[bold cyan]TravelTime Drive Time Comparisons[/bold cyan]",
            subtitle="Interactive Mode",
        )
    )

    console.print("\n[bold]Core Settings[/bold]")

    input_file = choose_input_file()
    output_file = questionary.text(
        "Detailed results output CSV file:", default="output.csv"
    ).unsafe_ask()
    ao = (
        questionary.text("Accuracy summary output CSV (empty to skip):")
        .unsafe_ask()
        .strip()
    )
    accuracy_output = ao if ao else None
    config_file = questionary.path("Config file:", default="./config.json").unsafe_ask()
    date_str = questionary.text(
        "Date (YYYY-MM-DD):",
        default=next_wednesday(),
        validate=validate_date,
    ).unsafe_ask()
    departure_times = questionary.text(
        "Departure times (HH:MM, HH:MM, ...):",
        default="05:00, 13:00, 17:00",
        validate=validate_departure_times,
    ).unsafe_ask()
    time_zone_id = questionary.autocomplete(
        "Timezone:",
        choices=pytz.common_timezones,
    ).unsafe_ask()

    skip_data_gathering = None
    skip_plotting = None

    if debug:
        console.print("\n[bold]Debug Options[/bold]")
        skip_data_gathering = (
            questionary.confirm(
                "Skip data gathering (reuse existing output)?", default=False
            ).unsafe_ask()
            or None
        )
        skip_plotting = (
            questionary.confirm("Skip plotting?", default=False).unsafe_ask() or None
        )

    args = argparse.Namespace(
        input=input_file,
        output=output_file,
        config=config_file,
        date=date_str,
        departure_times=departure_times,
        time_zone_id=time_zone_id,
        skip_data_gathering=skip_data_gathering,
        skip_plotting=skip_plotting,
        accuracy_output=accuracy_output,
        debug=debug or None,
    )

    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    table.add_row("Input", args.input)
    table.add_row("Output", args.output)
    table.add_row("Config", args.config)
    table.add_row("Date", args.date)
    table.add_row("Departure times", args.departure_times)
    table.add_row("Timezone", args.time_zone_id)
    if args.skip_data_gathering:
        table.add_row("Skip data gathering", "Yes")
    if args.skip_plotting:
        table.add_row("Skip plotting", "Yes")
    if args.accuracy_output:
        table.add_row("Accuracy output", args.accuracy_output)
    if args.debug:
        table.add_row("Debug mode", "Yes")

    console.print(Panel(table, title="[bold]Summary[/bold]", border_style="cyan"))
    console.print()

    if not questionary.confirm("Proceed?", default=True).unsafe_ask():
        console.print("[yellow]Cancelled.[/yellow]")
        raise SystemExit(0)

    return args


def main():
    import sys

    debug = "--debug" in sys.argv
    args = build_args(debug=debug)

    from traveltime_drive_time_comparisons.main import run

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
