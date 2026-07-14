"""Resource-bounded Bilibili XML danmaku to ASS conversion."""

from __future__ import annotations

import math
from pathlib import Path
from xml.etree import ElementTree


MAX_XML_BYTES = 32 * 1024 * 1024
MAX_COMMENTS = 50_000
MAX_TEXT_CHARS = 500
_SCROLL_SECONDS = 10.0
_FIXED_SECONDS = 5.0


def _scan_unsafe_declarations(path: Path) -> None:
    tail = b""
    with path.open("rb") as source:
        while chunk := source.read(64 * 1024):
            sample = (tail + chunk).upper()
            if b"<!DOCTYPE" in sample or b"<!ENTITY" in sample:
                raise ValueError("XML declarations and entities are not accepted")
            tail = sample[-16:]


def _ass_time(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{fraction:02d}"


def _ass_color(value: int) -> str:
    value &= 0xFFFFFF
    red = (value >> 16) & 0xFF
    green = (value >> 8) & 0xFF
    blue = value & 0xFF
    return f"&H00{blue:02X}{green:02X}{red:02X}&"


def _safe_text(value: str) -> str:
    cleaned = "".join(
        character
        for character in value[:MAX_TEXT_CHARS]
        if character in "\n\t" or ord(character) >= 32
    )
    return (
        cleaned.replace("\\", "＼")
        .replace("{", "｛")
        .replace("}", "｝")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", r"\N")
        .strip()
    )


def _header(width: int, height: int) -> list[str]:
    return [
        "[Script Info]",
        "Title: MediaManager Bilibili Danmaku",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding"
        ),
        (
            "Style: Danmaku,Microsoft JhengHei,36,&H00FFFFFF,&H00FFFFFF,"
            "&H00101010,&H60000000,0,0,0,0,100,100,0,0,1,2,0,7,10,10,10,1"
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]


def convert_xml_to_ass(
    xml_path: Path,
    ass_path: Path,
    *,
    width: int = 1920,
    height: int = 1080,
) -> int:
    """Convert bounded Bilibili `<d p=...>` entries and retain the source XML."""

    source_candidate = Path(xml_path)
    target_candidate = Path(ass_path)
    if source_candidate.is_symlink() or target_candidate.is_symlink():
        raise ValueError("danmaku conversion does not accept symbolic links")
    source = source_candidate.resolve()
    target = target_candidate.resolve()
    if (
        not 640 <= width <= 7680
        or not 360 <= height <= 4320
        or not source.is_file()
        or source.stat().st_size > MAX_XML_BYTES
        or target.parent != source.parent
        or target.suffix.casefold() != ".ass"
    ):
        raise ValueError("danmaku conversion paths or dimensions are invalid")
    _scan_unsafe_declarations(source)

    lines = _header(width, height)
    lane_height = 48
    lane_count = max(1, (height - 96) // lane_height)
    scroll_lanes = [0.0] * lane_count
    top_lanes = [0.0] * lane_count
    bottom_lanes = [0.0] * lane_count
    count = 0

    for _event, element in ElementTree.iterparse(source, events=("end",)):
        if element.tag != "d":
            element.clear()
            continue
        fields = element.attrib.get("p", "").split(",")
        try:
            start = float(fields[0])
            mode = int(fields[1])
            font_size = min(72, max(12, int(float(fields[2]))))
            color = int(fields[3])
        except (IndexError, TypeError, ValueError, OverflowError):
            element.clear()
            continue
        text = _safe_text(element.text or "")
        element.clear()
        if (
            not text
            or not math.isfinite(start)
            or not 0 <= start <= 604_800
            or mode not in {1, 2, 3, 4, 5, 6}
        ):
            continue
        if count >= MAX_COMMENTS:
            break

        if mode in {4, 5}:
            lanes = bottom_lanes if mode == 4 else top_lanes
            lane = min(range(lane_count), key=lanes.__getitem__)
            lanes[lane] = start + _FIXED_SECONDS
            y = height - 36 - lane * lane_height if mode == 4 else 36 + lane * lane_height
            alignment = 2 if mode == 4 else 8
            motion = rf"\an{alignment}\pos({width // 2},{y})"
            end = start + _FIXED_SECONDS
        else:
            lane = min(range(lane_count), key=scroll_lanes.__getitem__)
            scroll_lanes[lane] = start + min(4.0, _SCROLL_SECONDS * 0.45)
            y = 34 + lane * lane_height
            estimated_width = min(width * 2, max(80, int(len(text) * font_size * 0.62)))
            if mode == 6:
                motion = rf"\move({-estimated_width},{y},{width + 24},{y})"
            else:
                motion = rf"\move({width + 24},{y},{-estimated_width},{y})"
            end = start + _SCROLL_SECONDS

        tags = rf"{{{motion}\fs{font_size}\c{_ass_color(color)}}}"
        lines.append(
            "Dialogue: 0,"
            f"{_ass_time(start)},{_ass_time(end)},Danmaku,,0,0,0,,{tags}{text}"
        )
        count += 1

    if count == 0:
        raise ValueError("danmaku XML contains no convertible comments")
    temporary = target.with_suffix(".ass.tmp")
    try:
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
        temporary.replace(target)
    finally:
        if temporary.exists() and temporary.parent == target.parent:
            temporary.unlink()
    return count
