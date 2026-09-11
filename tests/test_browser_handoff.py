from __future__ import annotations

from urllib.parse import quote

import pytest

from core.browser_handoff import (
    build_browser_handoff_uri,
    parse_browser_handoff,
)


def test_browser_handoff_accepts_direct_and_protocol_urls() -> None:
    media_url = "https://www.youtube.com/watch?v=example"

    direct = parse_browser_handoff(media_url)
    protocol = parse_browser_handoff(
        "mediamanager://add?url="
        f"{quote(media_url, safe='')}&title={quote('Browser share', safe='')}"
    )

    assert direct.url == media_url
    assert direct.title == "瀏覽器交付"
    assert direct.site_family == "youtube"
    assert protocol.url == media_url
    assert protocol.title == "Browser share"
    assert protocol.to_payload() == {
        "url": media_url,
        "title": "Browser share",
        "provider_id": "browser-handoff",
    }


def test_browser_handoff_uri_builder_round_trips_bounded_metadata() -> None:
    url = "https://www.bilibili.com/video/BV1example"

    value = build_browser_handoff_uri(url, title="  Shared   video  ")

    assert value.startswith("mediamanager://add?")
    assert parse_browser_handoff(value).title == "Shared video"
    assert parse_browser_handoff(value).url == url


@pytest.mark.parametrize(
    "value",
    (
        "",
        "http://www.youtube.com/watch?v=example",
        "https://user@example.com/watch?v=example",
        "https://example.com/video",
        "https://www.instagram.com/reel/example",
        "mediamanager://remove?url=https%3A%2F%2Fyoutu.be%2Fexample",
        "mediamanager://add?url=https%3A%2F%2Fyoutu.be%2Fexample&url=x",
        "mediamanager://add?url=https%3A%2F%2Fyoutu.be%2Fexample&extra=x",
    ),
)
def test_browser_handoff_rejects_untrusted_or_non_downloadable_inputs(
    value: str,
) -> None:
    with pytest.raises(ValueError):
        parse_browser_handoff(value)


def test_browser_handoff_rejects_oversized_input() -> None:
    with pytest.raises(ValueError, match="too long"):
        parse_browser_handoff("m" * 8193)
