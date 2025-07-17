import pandas as pd
from traveltime_drive_time_comparisons.analysis import (
    QuantileErrorResult,
    absolute_error,
    calculate_accuracies,
    calculate_differences,
    calculate_quantiles,
    relative_error,
)
from traveltime_drive_time_comparisons.common import (
    GOOGLE_API,
    HERE_API,
    OSRM_API,
    TOMTOM_API,
    TRAVELTIME_API,
    Fields,
)
from traveltime_drive_time_comparisons.config import Provider, Providers
from traveltime_drive_time_comparisons.api_requests.traveltime_credentials import (
    Credentials,
)

ABSOLUTE_ERROR_GOOGLE = absolute_error(TRAVELTIME_API, GOOGLE_API)
RELATIVE_ERROR_GOOGLE = relative_error(TRAVELTIME_API, GOOGLE_API)

PROVIDERS = Providers(
    base=Provider(
        name="traveltime",
        max_rpm=60,
        credentials=Credentials(app_id="test", api_key="test"),
        api_endpoint=None,
    ),
    competitors=[
        Provider(
            name="google",
            max_rpm=60,
            credentials=Credentials("test"),
            api_endpoint=None,
        )
    ],
)


def test_calculate_differences_calculate_absolute_and_relative_differences():
    data = {
        Fields.TRAVEL_TIME[GOOGLE_API]: [100, 200, 300],
        Fields.TRAVEL_TIME[TRAVELTIME_API]: [90, 210, 290],
    }
    df = pd.DataFrame(data)
    result_df = calculate_differences(df, PROVIDERS.base, PROVIDERS)

    assert result_df[ABSOLUTE_ERROR_GOOGLE].tolist() == [10, 10, 10]
    assert result_df[RELATIVE_ERROR_GOOGLE].tolist() == [10.0, 5.0, 10.0 / 3]


def test_calculate_differences_survives_division_by_zero():
    data = {
        Fields.TRAVEL_TIME[GOOGLE_API]: [0, 200, 300],
        Fields.TRAVEL_TIME[TRAVELTIME_API]: [90, 210, 290],
    }
    df = pd.DataFrame(data)
    result_df = calculate_differences(df, PROVIDERS.base, PROVIDERS)

    assert result_df[ABSOLUTE_ERROR_GOOGLE].tolist() == [90, 10, 10]
    assert result_df[RELATIVE_ERROR_GOOGLE].tolist() == [float("inf"), 5.0, 10.0 / 3]


odd_data = {
    ABSOLUTE_ERROR_GOOGLE: [10, 20, 30, 40, 50],
    RELATIVE_ERROR_GOOGLE: [5.0, 10.0, 15.0, 20.0, 25.0],
}
odd_df = pd.DataFrame(odd_data)


def test_calculate_quantiles_return_exact_element_for_quantile_which_provides_an_exact_division():
    # Test 1: Basic Quantile Test

    result = calculate_quantiles(odd_df, 0.5, TRAVELTIME_API, GOOGLE_API)

    assert isinstance(result, QuantileErrorResult)
    assert result.absolute_error == 30
    assert result.relative_error == 15

    assert calculate_quantiles(
        odd_df, 0.25, TRAVELTIME_API, GOOGLE_API
    ) == QuantileErrorResult(20, 10)
    assert calculate_quantiles(
        odd_df, 0.75, TRAVELTIME_API, GOOGLE_API
    ) == QuantileErrorResult(40, 20)

    assert calculate_quantiles(
        odd_df, 0.0, TRAVELTIME_API, GOOGLE_API
    ) == QuantileErrorResult(10, 5)
    assert calculate_quantiles(
        odd_df, 1.0, TRAVELTIME_API, GOOGLE_API
    ) == QuantileErrorResult(50, 25)


def test_calculate_quantiles_return_next_element_for_quantile_which_does_not_provide_an_exact_division():
    even_data = {
        ABSOLUTE_ERROR_GOOGLE: [10, 20, 30, 40],
        RELATIVE_ERROR_GOOGLE: [5.0, 10.0, 15.0, 20.0],
    }
    even_df = pd.DataFrame(even_data)

    assert calculate_quantiles(
        odd_df, 0.01, TRAVELTIME_API, GOOGLE_API
    ) == QuantileErrorResult(20, 10)
    assert calculate_quantiles(
        even_df, 0.5, TRAVELTIME_API, GOOGLE_API
    ) == QuantileErrorResult(30, 15)
    assert calculate_quantiles(
        odd_df, 0.99, TRAVELTIME_API, GOOGLE_API
    ) == QuantileErrorResult(50, 25)


def test_calculate_quantiles_for_unsorted_list():
    random_order_data = {
        ABSOLUTE_ERROR_GOOGLE: [40, 10, 30, 50, 20],
        RELATIVE_ERROR_GOOGLE: [25.0, 20.0, 10.0, 15.0, 5.0],
    }
    random_order_df = pd.DataFrame(random_order_data)
    assert calculate_quantiles(
        random_order_df, 0.25, TRAVELTIME_API, GOOGLE_API
    ) == QuantileErrorResult(20, 10)
    assert calculate_quantiles(
        random_order_df, 0.75, TRAVELTIME_API, GOOGLE_API
    ) == QuantileErrorResult(40, 20)


def test_calculate_accuracies():
    data = pd.DataFrame(
        {
            Fields.TRAVEL_TIME[GOOGLE_API]: [100, 200, 300],
            Fields.TRAVEL_TIME[TOMTOM_API]: [110, 190, 310],
            Fields.TRAVEL_TIME[HERE_API]: [90, 210, 290],
            Fields.TRAVEL_TIME[OSRM_API]: [105, 195, 305],
        }
    )

    result = calculate_accuracies(data, Fields.TRAVEL_TIME)

    assert len(result) == 4
    assert list(result["Accuracy Score"].round()) == [100.0, 97.0, 94.0, 94.0]
    assert list(result["Relative Time"].round()) == [100.0, 101.0, 103.0, 97.0]
