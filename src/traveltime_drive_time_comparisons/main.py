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
from traveltime_drive_time_comparisons.collect import Fields
from traveltime_drive_time_comparisons.api_requests import factory
from traveltime_drive_time_comparisons.plot import (
    plot_accuracy_comparison,
    plot_relative_time_comparison,
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
        travel_times_df = pd.read_csv(
            args.input,
            usecols=[
                Fields.ORIGIN,
                Fields.DESTINATION,
                Fields.DEPARTURE_TIME,
            ]  # base fields
            + [Fields.TRAVEL_TIME[provider] for provider in all_provider_names],
        )
    else:
        travel_times_df = await collect.collect_travel_times(
            args, csv, request_handlers, all_provider_names
        )

    filtered_travel_times_df = travel_times_df.loc[
        travel_times_df[
            [Fields.TRAVEL_TIME[provider] for provider in all_provider_names]
        ]
        .notna()
        .all(axis=1),
        :,
    ]

    filtered_rows = len(filtered_travel_times_df)
    if filtered_rows == 0:
        logger.info("All rows from the input file were skipped. Exiting.")
    else:
        all_rows = len(travel_times_df)
        skipped_rows = all_rows - filtered_rows
        if skipped_rows > 0:
            logger.info(
                f"Skipped {skipped_rows} rows ({100 * skipped_rows / all_rows:.2f}%)"
            )

        accuracy_df = calculate_accuracies(filtered_travel_times_df, Fields.TRAVEL_TIME)
        logger.info(
            "Baseline summary, comparing to Google: \n" + accuracy_df.to_string()
        )

        run_analysis(filtered_travel_times_df, args.output, 0.90, providers)

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
