import pytest

from contracts.split_plan_v1 import SplitPlanV1
from trusted_ui.split_dialog import (
    build_edited_plan,
    split_filename_preview,
    split_plan_review,
)


def draft() -> SplitPlanV1:
    return SplitPlanV1.from_dict(
        {
            "source_url": "https://youtu.be/example",
            "source_title": "Study mix",
            "duration": 300,
            "composite_likely": False,
            "segments": [
                {
                    "index": 1,
                    "start": 0,
                    "end": 120,
                    "title": "Track 01",
                    "evidence": [
                        {
                            "source": "silence",
                            "confidence": 0.65,
                            "detail": "silence boundary heuristic",
                        }
                    ],
                },
                {
                    "index": 2,
                    "start": 120,
                    "end": 300,
                    "title": "Track 02",
                    "evidence": [
                        {
                            "source": "silence",
                            "confidence": 0.65,
                            "detail": "silence boundary heuristic",
                        }
                    ],
                },
            ],
            "warnings": [
                "Audio silence detection is heuristic and requires user confirmation."
            ],
        }
    )


def test_build_edited_plan_marks_boundaries_user_confirmed() -> None:
    plan = build_edited_plan(draft(), [(0, "Opening"), (125.5, "Second")])
    assert plan.composite_likely
    assert plan.segments[0].end == 125.5
    assert plan.segments[1].title == "Second"
    assert plan.segments[0].evidence[0].source == "manual"
    assert plan.warnings == ()


def test_split_review_flags_placeholder_names_and_low_confidence() -> None:
    warnings = split_plan_review(draft())
    assert any("預設名稱" in warning for warning in warnings)
    assert any("信心偏低" in warning for warning in warnings)


def test_split_filename_preview_is_bounded_and_windows_safe() -> None:
    value = split_filename_preview("Study: Mix", 1, "A/B?", 12, 120)
    assert value.endswith(".m4a")
    assert not any(character in value for character in '<>:"/\\|?*')
    assert len(value) <= 180


@pytest.mark.parametrize(
    "rows",
    [
        [(0, "Only one")],
        [(1, "Not zero"), (20, "Second")],
        [(0, "First"), (0, "Duplicate")],
        [(0, "First"), (301, "Outside")],
    ],
)
def test_build_edited_plan_rejects_invalid_boundaries(rows) -> None:
    with pytest.raises(ValueError):
        build_edited_plan(draft(), rows)
