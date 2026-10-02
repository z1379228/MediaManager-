"""Bounded, network-free import of local Podcast RSS and Atom documents."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import io
import ipaddress
import os
from pathlib import Path
from urllib.parse import urlsplit
import uuid
import xml.etree.ElementTree as ET


MAX_PODCAST_FEED_BYTES = 2 * 1024 * 1024
MAX_PODCAST_EPISODES = 500
MAX_PODCAST_XML_NODES = 20_000
MAX_PODCAST_XML_DEPTH = 32
_SUPPORTED_SUFFIXES = frozenset({".atom", ".rss", ".xml"})
_FORBIDDEN_XML_MARKERS = (b"<!DOCTYPE", b"<!ENTITY")


class _RejectingTreeBuilder(ET.TreeBuilder):
    """Reject DTDs even when the input encoding hides byte-level markers."""

    def doctype(self, name: str, public_id: str, system_id: str) -> None:
        raise ValueError(
            "podcast feed DTD and entity declarations are not accepted"
        )


@dataclass(frozen=True, slots=True)
class PodcastResource:
    url: str
    mime_type: str = ""
    language: str = ""
    relation: str = ""


@dataclass(frozen=True, slots=True)
class PodcastEpisode:
    entry_id: str
    title: str
    author: str
    published: str
    enclosure_url: str
    enclosure_type: str
    enclosure_bytes: int | None
    duration: str
    transcripts: tuple[PodcastResource, ...]
    chapters: PodcastResource | None


@dataclass(frozen=True, slots=True)
class PodcastFeed:
    title: str
    description: str
    homepage_url: str
    source_format: str
    episodes: tuple[PodcastEpisode, ...]
    issues: tuple[str, ...]


class PodcastImportService:
    """Feature gate around local-only podcast document parsing."""

    provider_id = "podcast-import"
    display_name = "Podcast / RSS"

    def __init__(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def available(self) -> bool:
        return True

    def set_enabled(self, enabled: bool) -> int:
        self._enabled = bool(enabled)
        return 0

    def parse(self, path: Path) -> PodcastFeed:
        if not self._enabled:
            raise RuntimeError("Podcast / RSS MOD is disabled")
        return parse_podcast_feed(path)

    def close(self) -> None:
        self._enabled = False


def podcast_resource_preview_lines(episode: PodcastEpisode) -> tuple[str, ...]:
    """Return declared resource metadata; deliberately never fetches URLs."""

    lines: list[str] = []
    for index, transcript in enumerate(episode.transcripts, start=1):
        details = " · ".join(
            value for value in (transcript.mime_type, transcript.language) if value
        ) or "未標示格式"
        lines.append(f"逐字稿 {index}：{details}\n{transcript.url}")
    if episode.chapters is not None:
        details = episode.chapters.mime_type or "未標示格式"
        lines.append(f"章節：{details}\n{episode.chapters.url}")
    return tuple(lines)


def _m3u_text(feed: PodcastFeed) -> str:
    lines = ["#EXTM3U"]
    for episode in feed.episodes:
        if not episode.enclosure_url:
            continue
        title = " ".join(episode.title.splitlines()).strip() or "未命名單集"
        lines.extend((f"#EXTINF:-1,{title}", episode.enclosure_url))
    return "\n".join(lines) + "\n"


def _csv_cell(value: object) -> str:
    """Preserve untrusted text as data when the CSV is opened in a spreadsheet."""

    result = str(value or "").replace("\r", " ").replace("\n", " ")
    if result.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + result
    return result


def _csv_text(feed: PodcastFeed) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        (
            "title", "author", "published", "duration", "enclosure_url",
            "enclosure_type", "enclosure_bytes", "transcript_urls", "chapters_url",
        )
    )
    for episode in feed.episodes:
        writer.writerow(
            tuple(
                _csv_cell(value)
                for value in (
                    episode.title,
                    episode.author,
                    episode.published,
                    episode.duration,
                    episode.enclosure_url,
                    episode.enclosure_type,
                    episode.enclosure_bytes,
                    " | ".join(item.url for item in episode.transcripts),
                    episode.chapters.url if episode.chapters is not None else "",
                )
            )
        )
    return buffer.getvalue()


def export_podcast_feed(
    feed: PodcastFeed,
    destination: Path,
    format_id: str,
) -> Path:
    """Export an already parsed Feed locally, with an atomic replacement."""

    writers = {"m3u": _m3u_text, "csv": _csv_text}
    try:
        payload = writers[format_id](feed)
    except KeyError as error:
        raise ValueError("podcast export format must be m3u or csv") from error
    destination = destination.expanduser().resolve(strict=False)
    if not destination.name:
        raise ValueError("podcast export needs a file name")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.{uuid.uuid4().hex}.tmp"
    )
    try:
        # utf-8-sig keeps spreadsheet imports readable without changing M3U.
        temporary.write_text(
            payload,
            encoding="utf-8-sig" if format_id == "csv" else "utf-8",
            newline="",
        )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def _local_name(tag: object) -> str:
    return str(tag).rsplit("}", 1)[-1].casefold()


def _bounded_text(element: ET.Element | None, limit: int) -> str:
    if element is None:
        return ""
    value = " ".join("".join(element.itertext()).split())
    return value[:limit]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    expected = name.casefold()
    return next(
        (item for item in element if _local_name(item.tag) == expected),
        None,
    )


def _child_text(element: ET.Element, name: str, limit: int) -> str:
    return _bounded_text(_child(element, name), limit)


def _safe_https_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    url = value.strip()
    if not 1 <= len(url) <= 4096 or "\x00" in url:
        return ""
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").casefold()
        port = parsed.port
    except ValueError:
        return ""
    if (
        parsed.scheme.casefold() != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
        or len(parsed.query) > 2000
    ):
        return ""
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        if not address.is_global:
            return ""
    return url


def _bounded_attribute(
    element: ET.Element,
    name: str,
    limit: int,
) -> str:
    value = element.attrib.get(name, "")
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _resource_from_element(
    element: ET.Element,
    *,
    url_attribute: str,
) -> PodcastResource | None:
    url = _safe_https_url(element.attrib.get(url_attribute))
    if not url:
        return None
    return PodcastResource(
        url,
        _bounded_attribute(element, "type", 120),
        _bounded_attribute(element, "language", 32),
        _bounded_attribute(element, "rel", 40),
    )


def _enclosure_bytes(value: object) -> int | None:
    try:
        size = int(str(value))
    except (TypeError, ValueError):
        return None
    return size if 0 <= size <= 64 * 1024**3 else None


def _podcast_resources(
    element: ET.Element,
) -> tuple[tuple[PodcastResource, ...], PodcastResource | None]:
    transcripts: list[PodcastResource] = []
    chapters: PodcastResource | None = None
    for child in element:
        name = _local_name(child.tag)
        if name == "transcript" and len(transcripts) < 16:
            resource = _resource_from_element(child, url_attribute="url")
            if resource is not None:
                transcripts.append(resource)
        elif name == "chapters" and chapters is None:
            chapters = _resource_from_element(child, url_attribute="url")
    return tuple(transcripts), chapters


def _rss_episode(
    element: ET.Element,
    index: int,
) -> tuple[PodcastEpisode, tuple[str, ...]]:
    issues: list[str] = []
    enclosure_url = ""
    enclosure_type = ""
    enclosure_bytes = None
    enclosure = _child(element, "enclosure")
    if enclosure is not None:
        enclosure_url = _safe_https_url(enclosure.attrib.get("url"))
        enclosure_type = _bounded_attribute(enclosure, "type", 120)
        enclosure_bytes = _enclosure_bytes(enclosure.attrib.get("length"))
        if not enclosure_url:
            issues.append(f"第 {index} 集的 enclosure 不是可接受的 HTTPS 網址")
    else:
        issues.append(f"第 {index} 集沒有 enclosure")
    transcripts, chapters = _podcast_resources(element)
    title = _child_text(element, "title", 300) or f"未命名單集 {index}"
    entry_id = (
        _child_text(element, "guid", 300)
        or _child_text(element, "link", 300)
        or f"rss-entry-{index}"
    )
    return (
        PodcastEpisode(
            entry_id,
            title,
            _child_text(element, "author", 200),
            _child_text(element, "pubdate", 100),
            enclosure_url,
            enclosure_type,
            enclosure_bytes,
            _child_text(element, "duration", 40),
            transcripts,
            chapters,
        ),
        tuple(issues),
    )


def _atom_link(element: ET.Element, relation: str) -> ET.Element | None:
    expected = relation.casefold()
    return next(
        (
            item
            for item in element
            if _local_name(item.tag) == "link"
            and _bounded_attribute(item, "rel", 40).casefold() == expected
        ),
        None,
    )


def _atom_episode(
    element: ET.Element,
    index: int,
) -> tuple[PodcastEpisode, tuple[str, ...]]:
    issues: list[str] = []
    enclosure = _atom_link(element, "enclosure")
    enclosure_url = ""
    enclosure_type = ""
    enclosure_bytes = None
    if enclosure is not None:
        enclosure_url = _safe_https_url(enclosure.attrib.get("href"))
        enclosure_type = _bounded_attribute(enclosure, "type", 120)
        enclosure_bytes = _enclosure_bytes(enclosure.attrib.get("length"))
        if not enclosure_url:
            issues.append(f"第 {index} 集的 enclosure 不是可接受的 HTTPS 網址")
    else:
        issues.append(f"第 {index} 集沒有 enclosure")
    author = _child(element, "author")
    transcripts, chapters = _podcast_resources(element)
    return (
        PodcastEpisode(
            _child_text(element, "id", 300) or f"atom-entry-{index}",
            _child_text(element, "title", 300) or f"未命名單集 {index}",
            _child_text(author, "name", 200) if author is not None else "",
            _child_text(element, "published", 100)
            or _child_text(element, "updated", 100),
            enclosure_url,
            enclosure_type,
            enclosure_bytes,
            _child_text(element, "duration", 40),
            transcripts,
            chapters,
        ),
        tuple(issues),
    )


def _validate_tree(root: ET.Element) -> None:
    nodes = 0
    stack = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > MAX_PODCAST_XML_NODES:
            raise ValueError("podcast feed contains too many XML nodes")
        if depth > MAX_PODCAST_XML_DEPTH:
            raise ValueError("podcast feed XML nesting is too deep")
        stack.extend((child, depth + 1) for child in node)


def _is_linklike(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(is_junction and is_junction())


def _read_feed_document(path: Path) -> bytes:
    candidate = Path(path)
    if candidate.suffix.casefold() not in _SUPPORTED_SUFFIXES:
        raise ValueError("podcast feed must be an RSS, XML, or Atom file")
    if _is_linklike(candidate) or not candidate.is_file():
        raise ValueError("podcast feed is missing or is a link")
    if candidate.stat().st_size > MAX_PODCAST_FEED_BYTES:
        raise ValueError("podcast feed exceeds the 2 MiB limit")
    with candidate.open("rb") as source:
        payload = source.read(MAX_PODCAST_FEED_BYTES + 1)
    if len(payload) > MAX_PODCAST_FEED_BYTES:
        raise ValueError("podcast feed exceeds the 2 MiB limit")
    upper = payload.upper()
    if any(marker in upper for marker in _FORBIDDEN_XML_MARKERS):
        raise ValueError("podcast feed DTD and entity declarations are not accepted")
    return payload


def parse_podcast_feed(path: Path) -> PodcastFeed:
    """Parse a bounded local document without fetching referenced URLs."""

    payload = _read_feed_document(path)
    try:
        parser = ET.XMLParser(target=_RejectingTreeBuilder())
        root = ET.fromstring(payload, parser=parser)
    except ET.ParseError as error:
        raise ValueError("podcast feed XML is invalid") from error
    _validate_tree(root)
    root_name = _local_name(root.tag)
    issues: list[str] = []
    episodes: list[PodcastEpisode] = []

    if root_name == "rss":
        channel = _child(root, "channel")
        if channel is None:
            raise ValueError("RSS podcast feed has no channel")
        items = tuple(item for item in channel if _local_name(item.tag) == "item")
        if len(items) > MAX_PODCAST_EPISODES:
            raise ValueError("podcast feed exceeds the 500-episode limit")
        for index, item in enumerate(items, start=1):
            episode, episode_issues = _rss_episode(item, index)
            episodes.append(episode)
            issues.extend(episode_issues)
        return PodcastFeed(
            _child_text(channel, "title", 300) or "未命名 Podcast",
            _child_text(channel, "description", 1000),
            _safe_https_url(_child_text(channel, "link", 4096)),
            "RSS 2.0",
            tuple(episodes),
            tuple(issues[:100]),
        )

    if root_name == "feed":
        entries = tuple(item for item in root if _local_name(item.tag) == "entry")
        if len(entries) > MAX_PODCAST_EPISODES:
            raise ValueError("podcast feed exceeds the 500-episode limit")
        for index, entry in enumerate(entries, start=1):
            episode, episode_issues = _atom_episode(entry, index)
            episodes.append(episode)
            issues.extend(episode_issues)
        homepage = _atom_link(root, "alternate")
        return PodcastFeed(
            _child_text(root, "title", 300) or "未命名 Podcast",
            _child_text(root, "subtitle", 1000),
            _safe_https_url(homepage.attrib.get("href"))
            if homepage is not None
            else "",
            "Atom",
            tuple(episodes),
            tuple(issues[:100]),
        )

    raise ValueError("document is not an RSS or Atom podcast feed")
