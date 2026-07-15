from pathlib import Path

from core.dependency_health import DependencyReport, DependencyStatus
from core.dependency_snapshot import DependencySnapshotService


def _report(*available: str) -> DependencyReport:
    ids = (
        "yt-dlp",
        "yt-dlp-ejs",
        "ffmpeg",
        "javascript-runtime",
        "mega-get",
        "whisper-cli",
        "speech-model",
    )
    return DependencyReport(
        tuple(
            DependencyStatus(
                dependency_id,
                dependency_id,
                dependency_id in available,
                "1.0" if dependency_id in available else "",
                "",
                "test",
            )
            for dependency_id in ids
        )
    )


def test_snapshot_cache_is_reused_until_bounded_fingerprint_changes(
    tmp_path: Path,
) -> None:
    calls = 0

    def factory(_application: Path, _data: Path) -> DependencyReport:
        nonlocal calls
        calls += 1
        return _report("yt-dlp", "yt-dlp-ejs", "ffmpeg", "javascript-runtime")

    service = DependencySnapshotService(
        tmp_path,
        tmp_path / "data",
        report_factory=factory,
    )
    first = service.snapshot()
    second = service.snapshot()

    assert first is second
    assert calls == 1

    tool = tmp_path / "tools" / "mega-get.exe"
    tool.parent.mkdir()
    tool.write_bytes(b"tool")
    third = service.snapshot()

    assert third is not first
    assert calls == 2


def test_peek_and_invalidate_never_probe_or_refresh(tmp_path: Path) -> None:
    calls = 0

    def factory(_application: Path, _data: Path) -> DependencyReport:
        nonlocal calls
        calls += 1
        return _report()

    service = DependencySnapshotService(
        tmp_path,
        tmp_path / "data",
        report_factory=factory,
    )

    assert service.peek() is None
    assert calls == 0
    warmed = service.refresh()
    assert service.peek() is warmed
    assert calls == 1
    service.invalidate()
    assert service.peek() is None
    assert calls == 1


def test_snapshot_derives_readiness_for_each_catalog_mod(tmp_path: Path) -> None:
    service = DependencySnapshotService(
        tmp_path,
        tmp_path / "data",
        report_factory=lambda _application, _data: _report(
            "yt-dlp",
            "yt-dlp-ejs",
            "ffmpeg",
            "javascript-runtime",
            "mega-get",
        ),
    )

    snapshot = service.refresh()

    assert len(snapshot.readiness) == 16
    assert snapshot.readiness_for("youtube").ready
    assert snapshot.readiness_for("mega").ready
    assert not snapshot.readiness_for("speech-to-text").ready
    assert snapshot.readiness_for("speech-to-text").missing == (
        "whisper-cli",
        "speech-model",
    )
    assert snapshot.readiness_for("automation").ready
