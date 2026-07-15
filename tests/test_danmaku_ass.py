from __future__ import annotations

from pathlib import Path
import runpy

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONVERTER_PATH = ROOT / "mod" / "builtin" / "bilibili" / "danmaku_ass.py"


def test_converter_preserves_source_and_generates_positioned_ass(
    tmp_path: Path,
) -> None:
    xml = tmp_path / "clip.danmaku.xml"
    xml.write_text(
        "<i>"
        '<d p="0,1,25,16711680,0,0,user,1">移動{tag}\\text</d>'
        '<d p="1.5,5,30,65280,0,0,user,2">頂端</d>'
        '<d p="2,4,28,255,0,0,user,3">底部</d>'
        "</i>",
        encoding="utf-8",
    )
    ass = tmp_path / "clip.danmaku.ass"
    namespace = runpy.run_path(str(CONVERTER_PATH))

    count = namespace["convert_xml_to_ass"](xml, ass, width=1280, height=720)

    text = ass.read_text(encoding="utf-8-sig")
    assert count == 3
    assert xml.is_file()
    assert "PlayResX: 1280" in text
    assert r"\move(" in text
    assert r"\an8\pos(" in text
    assert r"\an2\pos(" in text
    assert "&H000000FF&" in text
    assert "移動｛tag｝＼text" in text
    assert "移動{tag}" not in text


def test_converter_rejects_xml_declarations_and_entities(tmp_path: Path) -> None:
    xml = tmp_path / "unsafe.xml"
    xml.write_text(
        '<!DOCTYPE i [<!ENTITY x "boom">]><i><d p="0,1,25,1">&x;</d></i>',
        encoding="utf-8",
    )
    namespace = runpy.run_path(str(CONVERTER_PATH))

    with pytest.raises(ValueError, match="entities"):
        namespace["convert_xml_to_ass"](xml, tmp_path / "unsafe.ass")

    assert not (tmp_path / "unsafe.ass").exists()


def test_converter_caps_comment_count(tmp_path: Path) -> None:
    xml = tmp_path / "many.xml"
    xml.write_text(
        "<i>"
        + "".join(
            f'<d p="{index},1,25,16777215,0,0,user,{index}">x</d>'
            for index in range(5)
        )
        + "</i>",
        encoding="utf-8",
    )
    namespace = runpy.run_path(str(CONVERTER_PATH))
    convert = namespace["convert_xml_to_ass"]
    convert.__globals__["MAX_COMMENTS"] = 2

    assert convert(xml, tmp_path / "many.ass") == 2


def test_converter_filters_and_retimes_segment_comments(tmp_path: Path) -> None:
    xml = tmp_path / "segment.danmaku.xml"
    xml.write_text(
        "<i>"
        '<d p="5,1,25,16777215,0,0,user,1">before</d>'
        '<d p="12,1,25,16777215,0,0,user,2">inside-a</d>'
        '<d p="18,5,25,16777215,0,0,user,3">inside-b</d>'
        '<d p="20,1,25,16777215,0,0,user,4">at-end</d>'
        "</i>",
        encoding="utf-8",
    )
    ass = tmp_path / "segment.danmaku.ass"
    namespace = runpy.run_path(str(CONVERTER_PATH))

    count = namespace["convert_xml_to_ass"](
        xml,
        ass,
        segment_start=10.0,
        segment_end=20.0,
    )

    text = ass.read_text(encoding="utf-8-sig")
    assert count == 2
    assert "before" not in text
    assert "at-end" not in text
    assert "0:00:02.00,0:00:10.00" in text
    assert "0:00:08.00,0:00:10.00" in text
    assert "inside-a" in text
    assert "inside-b" in text
    assert xml.is_file()


@pytest.mark.parametrize(
    ("segment_start", "segment_end"),
    ((-1, None), (10, 10), (20, 10), (False, 10), (0, float("inf"))),
)
def test_converter_rejects_invalid_segment_boundaries(
    tmp_path: Path,
    segment_start: object,
    segment_end: object,
) -> None:
    xml = tmp_path / "invalid-segment.xml"
    xml.write_text(
        '<i><d p="1,1,25,16777215,0,0,user,1">text</d></i>',
        encoding="utf-8",
    )
    namespace = runpy.run_path(str(CONVERTER_PATH))

    with pytest.raises(ValueError, match="segment boundaries"):
        namespace["convert_xml_to_ass"](
            xml,
            tmp_path / "invalid-segment.ass",
            segment_start=segment_start,
            segment_end=segment_end,
        )
