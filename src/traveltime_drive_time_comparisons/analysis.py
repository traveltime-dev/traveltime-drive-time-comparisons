import logging
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd

from pandas import DataFrame

from traveltime_drive_time_comparisons.common import (
    ACCURACY_COLUMN,
    PROVIDER_COLUMN,
    Fields,
    get_capitalized_provider_name,
)
from traveltime_drive_time_comparisons.config import Provider, Providers


def absolute_error(target: str, api_provider: str) -> str:
    return f"absolute_error_{target}_to_{api_provider}"


def relative_error(target: str, api_provider: str) -> str:
    return f"error_percentage_{target}_to_{api_provider}"


@dataclass
class QuantileErrorResult:
    absolute_error: int
    relative_error: int


def log_results(
    results_with_differences: DataFrame,
    quantile: float,
    target_provider: Provider,
    api_providers: Providers,
):
    target_name = target_provider.name
    capitalized_target = get_capitalized_provider_name(target_name)
    logging.info(f"Comparing {capitalized_target} to other providers:")
    for name in api_providers.all_names():
        if name != target_name:
            capitalized_provider = get_capitalized_provider_name(name)
            logging.info(
                f"\tMean relative error compared to {capitalized_provider} "
                f"API: {results_with_differences[relative_error(target_name, name)].mean():.2f}%"
            )
            quantile_errors = calculate_quantiles(
                results_with_differences, quantile, target_name, name
            )
            logging.info(
                f"\t{int(quantile * 100)}% of {capitalized_target} results differ from {capitalized_provider} API "
                f"by less than {int(quantile_errors.relative_error)}%"
            )


def format_results_for_csv(results_with_differences: DataFrame) -> DataFrame:
    formatted_results = results_with_differences.copy()

    # Drop all columns containing "absolute_error"
    absolute_error_columns = [
        col for col in formatted_results.columns if "absolute_error" in col
    ]
    formatted_results = formatted_results.drop(columns=absolute_error_columns)
    # Convert all relative error columns to int
    relative_error_columns = [
        col for col in formatted_results.columns if "error_percentage" in col
    ]
    for col in relative_error_columns:
        formatted_results[col] = formatted_results[col].astype(int)

    return formatted_results


def run_analysis(
    results: DataFrame, output_file: str, quantile: float, api_providers: Providers
):
    accumulated_results = results.copy()
    for target_provider in api_providers.all_providers():
        results_with_differences = calculate_differences(
            results, target_provider, api_providers
        )

        for col in results_with_differences.columns:
            if col not in accumulated_results.columns:
                accumulated_results[col] = results_with_differences[col]

        log_results(results_with_differences, quantile, target_provider, api_providers)

    logging.info(f"Detailed results can be found in {output_file} file")

    formatted_results = format_results_for_csv(
        accumulated_results
    )  # Use accumulated_results here

    formatted_results.to_csv(output_file, index=False)


def calculate_differences(
    results: DataFrame, target_provider: Provider, api_providers: Providers
) -> DataFrame:
    results_with_differences = results.copy()

    target_name = target_provider.name
    for name in api_providers.all_names():
        if name != target_name:
            absolute_error_col = absolute_error(target_name, name)
            relative_error_col = relative_error(target_name, name)

            results_with_differences[absolute_error_col] = abs(
                results[Fields.TRAVEL_TIME[name]]
                - results[Fields.TRAVEL_TIME[target_name]]
            )

            results_with_differences[relative_error_col] = (
                results_with_differences[absolute_error_col]
                / results_with_differences[Fields.TRAVEL_TIME[name]]
                * 100
            )

    return results_with_differences


def calculate_quantiles(
    results_with_differences: DataFrame,
    quantile: float,
    target_name,
    api_provider_name: str,
) -> QuantileErrorResult:
    quantile_absolute_error = results_with_differences[
        absolute_error(target_name, api_provider_name)
    ].quantile(quantile, "higher")
    quantile_relative_error = results_with_differences[
        relative_error(target_name, api_provider_name)
    ].quantile(quantile, "higher")
    return QuantileErrorResult(
        int(quantile_absolute_error), int(quantile_relative_error)
    )


def _calculate_provider_accuracy(
    provider_value: float, all_values: List[float], provider_index: int
) -> float:
    competitors_sum = sum(
        competitor_value
        for competitor_index, competitor_value in enumerate(all_values)
        if competitor_index != provider_index
    )
    competitors_average = competitors_sum / (len(all_values) - 1)
    accuracy = 1 - abs(provider_value - competitors_average) / provider_value
    return accuracy * 100


def _get_provider_comparison(
    provider_name: str,
    provider_value: float,
    all_values: List[float],
    provider_index: int,
) -> Tuple[str, float]:
    return (
        get_capitalized_provider_name(provider_name),
        _calculate_provider_accuracy(provider_value, all_values, provider_index),
    )


def calculate_accuracies(data: pd.DataFrame, columns: Dict[str, str]) -> pd.DataFrame:
    # only calculate providers that are present in the current search
    existing_fields = {k: v for k, v in columns.items() if v in data.columns}
    providers_data = data[list(existing_fields.values())]

    results = []
    for row in providers_data.itertuples():
        all_values = list(row)[1:]
        comparisons = [
            _get_provider_comparison(
                provider_name, provider_value, all_values, provider_index
            )
            for provider_index, (provider_name, provider_value) in enumerate(
                zip(existing_fields.keys(), all_values)
            )
        ]
        results.extend(comparisons)

    df = pd.DataFrame.from_records(results, columns=[PROVIDER_COLUMN, ACCURACY_COLUMN])
    return (
        df.groupby(PROVIDER_COLUMN)[ACCURACY_COLUMN]
        .mean()
        .reset_index()
        .sort_values(ACCURACY_COLUMN, ascending=False, ignore_index=True)
    )
