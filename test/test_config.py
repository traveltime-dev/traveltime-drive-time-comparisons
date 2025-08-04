from traveltime_drive_time_comparisons.config import (
    Provider,
    Providers,
    parse_json_to_providers,
)
from traveltime_drive_time_comparisons.api_requests.traveltime_credentials import (
    Credentials,
)


def test_json_config_parse():
    json = """
        {
          "traveltime": {
            "app-id": "<your-app-id>",
            "api-key": "<your-api-key>",
            "max-rpm": "60"
          },
          "api-providers": [
            {
              "name": "google",
              "enabled": true,
              "api-key": "<your-api-key>",
              "max-rpm": "60",
              "api-endpoint": "some-custom-endpoint.com"
            },
            {
              "name": "tomtom",
              "enabled": false,
              "api-key": "<your-api-key>",
              "max-rpm": "30"
            }
          ]
        }
    """

    providers = parse_json_to_providers(json)

    assert providers == Providers(
        base=Provider(
            name="traveltime",
            max_rpm=60,
            credentials=Credentials(app_id="<your-app-id>", api_key="<your-api-key>"),
            api_endpoint=None,
        ),
        competitors=[
            Provider(
                name="google",
                max_rpm=60,
                credentials=Credentials("<your-api-key>"),
                api_endpoint="some-custom-endpoint.com",
            )
        ],
    )


def test_json_config_parse_all_disabled_providers():
    json = """
        {
          "traveltime": {
            "app-id": "<your-app-id>",
            "api-key": "<your-api-key>",
            "max-rpm": "60"
          },
          "api-providers": [
            {
              "name": "google",
              "enabled": false,
              "api-key": "<your-api-key>",
              "max-rpm": "60"
            },
            {
              "name": "tomtom",
              "enabled": false,
              "api-key": "<your-api-key>",
              "max-rpm": "30"
            }
          ]
        }
    """

    providers = parse_json_to_providers(json)

    assert providers == Providers(
        base=Provider(
            name="traveltime",
            max_rpm=60,
            credentials=Credentials(app_id="<your-app-id>", api_key="<your-api-key>"),
            api_endpoint=None,
        ),
        competitors=[],
    )


def test_json_config_parse_empty_providers():
    json = """
        {
          "traveltime": {
            "app-id": "<your-app-id>",
            "api-key": "<your-api-key>",
            "max-rpm": "60"
          },
          "api-providers": []
        }
    """

    providers = parse_json_to_providers(json)

    assert providers == Providers(
        base=Provider(
            name="traveltime",
            max_rpm=60,
            credentials=Credentials(app_id="<your-app-id>", api_key="<your-api-key>"),
            api_endpoint=None,
        ),
        competitors=[],
    )
