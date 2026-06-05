import pytest
from mailgun.client import Config

@pytest.mark.parametrize(
    "api_url",
    [
        "https://api.eu.mailgun.net/v3",
        "https://api.eu.mailgun.net/v3/",
        "https://api.eu.mailgun.net/v4",
        "https://api.eu.mailgun.net/v4/",
    ],
    ids=["v3_without_trailing_slash",
         "v3_with_trailing_slash",
         "v4_without_trailing_slash",
         "v4_with_trailing_slash",
         ]
)
def test_api_url_with_trailing_version(api_url: str) -> None:
    """
    Regression test for #40: v1.7.0 silently broke api_url values containing /v3.
    Tests that an explicitly passed version segment does not result in duplication.
    """
    config = Config(api_url=api_url)

    # Before the fix, this evaluated to 'https://api.eu.mailgun.net/v3/v3' and failed.
    if "mailgun" in api_url:
        assert config._baked_urls["v3"] == "https://api.eu.mailgun.net/v3"
        assert config._baked_urls["v4"] == "https://api.eu.mailgun.net/v4"


def test_api_url_emits_semantic_warning_on_version_suffix(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    with caplog.at_level(logging.WARNING):
        config = Config(api_url="https://api.eu.mailgun.net/v3/")

    assert config._baked_urls["v3"] == "https://api.eu.mailgun.net/v3"
    assert "Semantic Configuration Warning" in caplog.text
    assert "should be the base domain" in caplog.text
