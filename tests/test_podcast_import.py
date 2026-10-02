from __future__ import annotations

from pathlib import Path

import pytest

from core.podcast_import import (
    MAX_PODCAST_FEED_BYTES,
    PodcastImportService,
    PodcastEpisode,
    PodcastFeed,
    PodcastResource,
    export_podcast_feed,
    parse_podcast_feed,
    podcast_resource_preview_lines,
)


RSS_DOCUMENT = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>安全測試節目</title>
    <description>本機 Feed</description>
    <link>https://podcasts.example.org/show</link>
    <item>
      <guid>episode-1</guid>
      <title>第一集</title>
      <author>測試作者</author>
      <pubDate>Fri, 11 Sep 2026 12:00:00 GMT</pubDate>
      <enclosure url="https://cdn.example.org/audio/episode-1.mp3"
                 type="audio/mpeg" length="12345" />
      <podcast:transcript url="https://cdn.example.org/text/episode-1.vtt"
                          type="text/vtt" language="zh-TW" />
      <podcast:chapters url="https://cdn.example.org/chapters/episode-1.json"
                        type="application/json+chapters" />
    </item>
    <item>
      <title>不安全附件</title>
      <enclosure url="http://127.0.0.1/private.mp3" type="audio/mpeg" />
    </item>
  </channel>
</rss>
"""


def test_parse_local_rss_with_podcasting_resources(tmp_path: Path) -> None:
    path = tmp_path / "show.rss"
    path.write_text(RSS_DOCUMENT, encoding="utf-8")

    feed = parse_podcast_feed(path)

    assert feed.title == "安全測試節目"
    assert feed.source_format == "RSS 2.0"
    assert feed.homepage_url == "https://podcasts.example.org/show"
    assert len(feed.episodes) == 2
    episode = feed.episodes[0]
    assert episode.entry_id == "episode-1"
    assert episode.enclosure_url.endswith("episode-1.mp3")
    assert episode.enclosure_bytes == 12345
    assert episode.transcripts[0].url.endswith("episode-1.vtt")
    assert episode.transcripts[0].language == "zh-TW"
    assert episode.chapters is not None
    assert episode.chapters.url.endswith("episode-1.json")
    assert feed.episodes[1].enclosure_url == ""
    assert "不是可接受的 HTTPS" in feed.issues[0]


def test_parse_local_atom_enclosure(tmp_path: Path) -> None:
    path = tmp_path / "show.atom"
    path.write_text(
        """<feed xmlns="http://www.w3.org/2005/Atom">
        <title>Atom 節目</title>
        <subtitle>摘要</subtitle>
        <link rel="alternate" href="https://podcasts.example.org/atom" />
        <entry>
          <id>atom-1</id><title>Atom 第一集</title>
          <updated>2026-09-11T12:00:00Z</updated>
          <author><name>Atom 作者</name></author>
          <link rel="enclosure" href="https://cdn.example.org/atom/one.opus"
                type="audio/opus" length="42" />
        </entry>
        </feed>""",
        encoding="utf-8",
    )

    feed = parse_podcast_feed(path)

    assert feed.source_format == "Atom"
    assert feed.title == "Atom 節目"
    assert feed.episodes[0].author == "Atom 作者"
    assert feed.episodes[0].enclosure_url.endswith("one.opus")


@pytest.mark.parametrize(
    ("filename", "payload", "message"),
    (
        ("show.txt", b"<rss />", "must be an RSS"),
        ("show.xml", b"<!DOCTYPE rss><rss />", "DTD and entity"),
        ("show.xml", b"<rss>", "XML is invalid"),
        ("show.xml", b"<html />", "not an RSS or Atom"),
    ),
)
def test_podcast_import_rejects_unsafe_or_invalid_documents(
    tmp_path: Path,
    filename: str,
    payload: bytes,
    message: str,
) -> None:
    path = tmp_path / filename
    path.write_bytes(payload)

    with pytest.raises(ValueError, match=message):
        parse_podcast_feed(path)


def test_podcast_import_bounds_file_episode_count_and_depth(tmp_path: Path) -> None:
    oversized = tmp_path / "large.rss"
    oversized.write_bytes(b"x" * (MAX_PODCAST_FEED_BYTES + 1))
    with pytest.raises(ValueError, match="2 MiB"):
        parse_podcast_feed(oversized)

    many = tmp_path / "many.rss"
    many.write_text(
        "<rss><channel><title>x</title>"
        + "<item><title>x</title></item>" * 501
        + "</channel></rss>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="500-episode"):
        parse_podcast_feed(many)

    deep = tmp_path / "deep.xml"
    deep.write_text(
        "<rss><channel>" + "<x>" * 40 + "</x>" * 40 + "</channel></rss>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="nesting is too deep"):
        parse_podcast_feed(deep)

    encoded_dtd = tmp_path / "encoded-dtd.xml"
    encoded_dtd.write_bytes(
        '<?xml version="1.0" encoding="UTF-16"?>'
        '<!DOCTYPE rss [<!ENTITY x "expanded">]>'
        '<rss><channel><title>&x;</title></channel></rss>'.encode("utf-16")
    )
    with pytest.raises(ValueError, match="DTD and entity"):
        parse_podcast_feed(encoded_dtd)


def test_podcast_service_obeys_feature_gate(tmp_path: Path) -> None:
    path = tmp_path / "show.rss"
    path.write_text(RSS_DOCUMENT, encoding="utf-8")
    service = PodcastImportService()

    with pytest.raises(RuntimeError, match="disabled"):
        service.parse(path)
    assert service.set_enabled(True) == 0
    assert service.parse(path).title == "安全測試節目"
    service.close()
    assert not service.is_enabled


def test_podcast_import_rejects_linklike_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "show.rss"
    path.write_text(RSS_DOCUMENT, encoding="utf-8")
    original = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda candidate: candidate == path or original(candidate),
    )

    with pytest.raises(ValueError, match="is a link"):
        parse_podcast_feed(path)


def test_local_podcast_exports_are_atomic_and_neutralize_csv_formulas(
    tmp_path: Path,
) -> None:
    episode = PodcastEpisode(
        "episode-1",
        "=Untrusted title",
        "+Untrusted author",
        "2026-09-12",
        "https://cdn.example.org/show/episode.mp3",
        "audio/mpeg",
        123,
        "00:03:00",
        (
            PodcastResource(
                "https://cdn.example.org/show/transcript.vtt", "text/vtt", "en"
            ),
        ),
        PodcastResource(
            "https://cdn.example.org/show/chapters.json", "application/json"
        ),
    )
    feed = PodcastFeed("Example", "", "", "RSS 2.0", (episode,), ())

    m3u = export_podcast_feed(feed, tmp_path / "show.m3u8", "m3u")
    csv = export_podcast_feed(feed, tmp_path / "show.csv", "csv")

    assert m3u.read_text(encoding="utf-8") == (
        "#EXTM3U\n#EXTINF:-1,=Untrusted title\n"
        "https://cdn.example.org/show/episode.mp3\n"
    )
    csv_text = csv.read_text(encoding="utf-8-sig")
    assert "'=Untrusted title" in csv_text
    assert "'+Untrusted author" in csv_text
    assert not list(tmp_path.glob(".*.tmp"))


def test_podcast_resource_preview_is_local_metadata_only() -> None:
    episode = PodcastEpisode(
        "episode-1",
        "Episode",
        "",
        "",
        "",
        "",
        None,
        "",
        (
            PodcastResource(
                "https://example.org/transcript.vtt", "text/vtt", "zh-TW"
            ),
        ),
        PodcastResource("https://example.org/chapters.json", "application/json"),
    )

    assert podcast_resource_preview_lines(episode) == (
        "逐字稿 1：text/vtt · zh-TW\nhttps://example.org/transcript.vtt",
        "章節：application/json\nhttps://example.org/chapters.json",
    )
