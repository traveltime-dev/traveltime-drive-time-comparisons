import asyncio
import logging

import pandas as pd
import matplotlib.pyplot as plt

from traveltime_drive_time_comparisons import collect
from traveltime_drive_time_comparisons import config
from traveltime_drive_time_comparisons.analysis import (
    calculate_accuracies,
    run_analysis,
)
from traveltime_drive_time_comparisons.config import parse_config
from traveltime_drive_time_comparisons.common import CaseCategory, Fields
from traveltime_drive_time_comparisons.api_requests import factory
from traveltime_drive_time_comparisons.plot import (
    plot_accuracy_comparison,
    plot_relative_time_comparison,
)
from traveltime_drive_time_comparisons.snapping import (
    detect_bad_snapping,
    detect_restricted_roads,
    log_restricted_roads_summary,
    log_snapping_summary,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


async def run():
    args = config.parse_args()
    config_path = args.config

    # Get all providers that should be tested against TravelTime
    providers = parse_config(config_path)
    all_provider_names = providers.all_names()

    csv = pd.read_csv(
        args.input, usecols=[Fields.ORIGIN, Fields.DESTINATION]
    ).drop_duplicates()

    if len(csv) == 0:
        logger.info("Provided input file is empty. Exiting.")
        return

    request_handlers = factory.initialize_request_handlers(providers)
    if args.skip_data_gathering:
        travel_times_df = pd.read_csv(args.input)
    else:
        travel_times_df = await collect.collect_travel_times(
            args, csv, request_handlers, all_provider_names
        )

    travel_times_df = detect_bad_snapping(travel_times_df, all_provider_names)
    log_snapping_summary(travel_times_df)

    travel_times_df = detect_restricted_roads(travel_times_df)
    log_restricted_roads_summary(travel_times_df)

    clean_travel_times_df = travel_times_df[
        travel_times_df[Fields.CASE_CATEGORY] == CaseCategory.CLEAN
    ]

    filtered_travel_times_df = clean_travel_times_df.loc[
        clean_travel_times_df[
            [Fields.TRAVEL_TIME[provider] for provider in all_provider_names]
        ]
        .notna()
        .all(axis=1),
        :,
    ]

    all_rows = len(travel_times_df)
    clean_rows = len(clean_travel_times_df)
    filtered_rows = len(filtered_travel_times_df)
    bad_snap_rows = (
        travel_times_df[Fields.CASE_CATEGORY].str.startswith("bad_snap").sum()
    )
    restricted_road_rows = (
        travel_times_df[Fields.CASE_CATEGORY] == CaseCategory.RESTRICTED_ROAD
    ).sum()
    missing_data_rows = clean_rows - filtered_rows

    if bad_snap_rows > 0:
        logger.info(
            f"Excluded {bad_snap_rows} rows ({100 * bad_snap_rows / all_rows:.2f}%) due to bad snapping"
        )
    if restricted_road_rows > 0:
        pct = 100 * restricted_road_rows / all_rows
        logger.info(
            f"Excluded {restricted_road_rows} rows ({pct:.2f}%) due to restricted/private road warnings"
        )
    if missing_data_rows > 0:
        logger.info(
            f"Skipped {missing_data_rows} rows ({100 * missing_data_rows / all_rows:.2f}%) due to missing data"
        )

    if filtered_rows == 0:
        logger.info("All rows from the input file were skipped. Exiting.")
    else:
        accuracy_df = calculate_accuracies(filtered_travel_times_df, Fields.TRAVEL_TIME)
        logger.info(
            "Baseline summary, comparing to Google: \n" + accuracy_df.to_string()
        )

        # If accuracy output path is defined, write to it
        if args.accuracy_output:
            accuracy_df.to_csv(args.accuracy_output, index=False)

        run_analysis(travel_times_df, args.output, 0.90, providers)

        if not args.skip_plotting:
            if not accuracy_df.empty:
                plot_accuracy_comparison(accuracy_df, "Accuracy Score (Google = 100)")
                plot_relative_time_comparison(
                    accuracy_df, "Relative Time (Google = 100)"
                )
                plt.show()
            else:
                logger.info("No data available for plotting")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
