import pytest
from mailgun.client import Config

@pytest.mark.parametrize(
    "api_url",
    [
        "https://api.eu.mailgun.net/v3",
        "https://api.eu.mailgun.net/v3/",
    ],
    ids=["without_trailing_slash", "with_trailing_slash"]
)
def test_api_url_with_trailing_version(api_url: str) -> None:
    """
    Regression test for #40: v1.7.0 silently broke api_url values containing /v3.
    Tests that an explicitly passed version segment does not result in duplication.
    """
    config = Config(api_url=api_url)

    # Before the fix, this evaluated to 'https://api.eu.mailgun.net/v3/v3' and failed.
    assert config._baked_urls["v3"] == "https://api.eu.mailgun.net/v3", (
        f"URL contains duplicated version segments for input: '{api_url}'"
    )
