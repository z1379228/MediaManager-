from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
from types import SimpleNamespace
import zipfile

import pytest

from tools.audit_versions import audit_version
from tools import package_self_contained_zip as packaging


_SOURCE_REVISION = "a" * 40


def package_self_contained_zip(
    release_root: Path,
    output_dir: Path,
    *,
    revision: str | None = None,
) -> packaging.SelfContainedZipPackage:
    return packaging.package_self_contained_zip(
        release_root,
        output_dir,
        expected_source_revision=_SOURCE_REVISION,
        revision=revision,
    )


@pytest.fixture(autouse=True)
def _accept_fixture_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        packaging,
        "audit_staged_runtime",
        lambda _root: SimpleNamespace(valid=True, errors=()),
    )


def _write_release(
    root: Path,
    *,
    core_version: str = "39.0.10",
    release_version: str = "1.1.0",
    track: str = "Testing",
) -> Path:
    major, minor, _patch = release_version.split(".")
    release = root / "Version" / track / f"{major}.{minor}"
    release.mkdir(parents=True)
    (release / "MediaManager.exe").write_bytes(b"test executable")
    assets = release / "assets"
    assets.mkdir()
    (assets / "application.txt").write_text("asset\n", encoding="utf-8")
    (assets / "說明.txt").write_text("離線說明\n", encoding="utf-8")
    wheel = release / f"mediamanager-{core_version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"mediamanager-{core_version}.dist-info/METADATA",
            (
                "Metadata-Version: 2.4\n"
                "Name: mediamanager\n"
                f"Version: {core_version}\n"
            ),
        )
    (release / "release-info.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "tool_schema_version": 3,
                "core_version": core_version,
                "release_version": release_version,
                "build_channel": track.casefold(),
                "release_track": track,
                "version_folder": f"{major}.{minor}",
                "source_revision": "a" * 40,
                "source_fingerprint": "b" * 64,
                "build_id": "c" * 64,
                "portable_tools": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _rewrite_checksums(release)
    assert audit_version(release).valid
    return release


def _rewrite_checksums(release: Path) -> None:
    files = sorted(
        path
        for path in release.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    (release / "SHA256SUMS.txt").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  "
            f"{path.relative_to(release).as_posix()}\n"
            for path in files
        ),
        encoding="utf-8",
    )


def test_package_contains_exact_audited_release_under_one_folder(
    tmp_path: Path,
) -> None:
    release = _write_release(tmp_path)
    result = package_self_contained_zip(release, tmp_path / "upload")
    archive_path = Path(result.archive)

    expected_relative = tuple(
        sorted(
            path.relative_to(release).as_posix()
            for path in release.rglob("*")
            if path.is_file()
        )
    )
    expected_names = tuple(
        f"{result.top_level}/{relative}" for relative in expected_relative
    )
    with zipfile.ZipFile(archive_path) as archive:
        assert tuple(archive.namelist()) == expected_names
        assert archive.testzip() is None
        assert all(
            info.date_time == packaging._FIXED_ZIP_TIMESTAMP
            and info.compress_type == zipfile.ZIP_DEFLATED
            for info in archive.infolist()
        )
        for relative in expected_relative:
            assert archive.read(f"{result.top_level}/{relative}") == (
                release.joinpath(*relative.split("/")).read_bytes()
            )

    assert result.top_level == "MediaManager-Testing-1.1.0"
    assert result.files == len(expected_relative)
    assert result.bytes == archive_path.stat().st_size
    assert result.source_revision == _SOURCE_REVISION
    assert result.sha256 == hashlib.sha256(archive_path.read_bytes()).hexdigest()
    assert Path(result.checksum).read_text(encoding="ascii") == (
        f"{result.sha256}  {archive_path.name}\n"
    )


def test_package_is_byte_deterministic_for_the_same_release(
    tmp_path: Path,
) -> None:
    release = _write_release(tmp_path)

    first = package_self_contained_zip(release, tmp_path / "upload-one")
    second = package_self_contained_zip(release, tmp_path / "upload-two")

    assert first.sha256 == second.sha256
    assert Path(first.archive).read_bytes() == Path(second.archive).read_bytes()


def test_extracted_package_passes_the_version_audit(tmp_path: Path) -> None:
    release = _write_release(tmp_path)
    result = package_self_contained_zip(release, tmp_path / "upload")
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(result.archive) as archive:
        archive.extractall(extracted)
    restored = tmp_path / "restored" / "Version" / "Testing" / "1.1"
    shutil.copytree(extracted / result.top_level, restored)

    report = audit_version(restored)

    assert report.valid, report.errors
    assert report.checked == result.files - 1


def test_package_refuses_to_overwrite_existing_outputs(tmp_path: Path) -> None:
    release = _write_release(tmp_path)
    output = tmp_path / "upload"
    first = package_self_contained_zip(release, output)

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        package_self_contained_zip(release, output)

    assert Path(first.archive).is_file()
    assert Path(first.checksum).is_file()


def test_package_revision_cannot_override_track_or_version(
    tmp_path: Path,
) -> None:
    release = _write_release(tmp_path)
    result = package_self_contained_zip(
        release,
        tmp_path / "upload",
        revision="r3",
    )

    assert result.top_level == "MediaManager-Testing-1.1.0-r3"
    assert Path(result.archive).name == "MediaManager-Testing-1.1.0-r3.zip"


@pytest.mark.parametrize(
    "expected",
    ("b" * 40, "a" * 39, "A" * 40, "unavailable"),
)
def test_package_rejects_unconfirmed_source_revision_without_output(
    tmp_path: Path,
    expected: str,
) -> None:
    release = _write_release(tmp_path)
    output = tmp_path / "upload"

    with pytest.raises(ValueError, match="source revision|source freeze"):
        packaging.package_self_contained_zip(
            release,
            output,
            expected_source_revision=expected,
        )

    assert not output.exists()


@pytest.mark.parametrize(
    "revision",
    ("Stable-9.9.9", "r0", "R3", "r3/escape", "r3.extra"),
)
def test_package_rejects_invalid_revision(
    tmp_path: Path,
    revision: str,
) -> None:
    release = _write_release(tmp_path)

    with pytest.raises(ValueError, match="revision must match"):
        package_self_contained_zip(
            release,
            tmp_path / "upload",
            revision=revision,
        )


def test_package_rejects_tampered_release_without_partial_output(
    tmp_path: Path,
) -> None:
    release = _write_release(tmp_path)
    (release / "MediaManager.exe").write_bytes(b"tampered")
    output = tmp_path / "upload"

    with pytest.raises(ValueError, match="staged release audit failed"):
        package_self_contained_zip(release, output)

    assert not output.exists()


def test_package_rejects_runtime_or_user_data(tmp_path: Path) -> None:
    release = _write_release(tmp_path)
    user_data = release / "UserData"
    user_data.mkdir()
    (user_data / "settings.json").write_text("{}", encoding="utf-8")
    _rewrite_checksums(release)
    assert audit_version(release).valid

    with pytest.raises(ValueError, match="runtime or user data"):
        package_self_contained_zip(release, tmp_path / "upload")


def test_package_rejects_failed_runtime_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = _write_release(tmp_path)
    monkeypatch.setattr(
        packaging,
        "audit_staged_runtime",
        lambda _root: SimpleNamespace(
            valid=False,
            errors=("portable runtime is incomplete",),
        ),
    )

    with pytest.raises(ValueError, match="staged runtime audit failed"):
        package_self_contained_zip(release, tmp_path / "upload")


def test_package_rejects_private_keys(tmp_path: Path) -> None:
    release = _write_release(tmp_path)
    private_key = release / "security" / "release-private.pem"
    private_key.parent.mkdir()
    private_key.write_bytes(
        b"-----BEGIN PRIVATE KEY-----\nnot-a-real-secret\n"
    )
    _rewrite_checksums(release)
    assert audit_version(release).valid

    with pytest.raises(ValueError, match="private key is not allowed"):
        package_self_contained_zip(release, tmp_path / "upload")


def test_package_detects_valid_release_mutation_during_packaging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = _write_release(tmp_path)
    output = tmp_path / "upload"
    original = packaging._write_zip

    def write_then_mutate(*args: object, **kwargs: object) -> None:
        original(*args, **kwargs)
        (release / "late-file.txt").write_text("late\n", encoding="utf-8")
        _rewrite_checksums(release)
        assert audit_version(release).valid

    monkeypatch.setattr(packaging, "_write_zip", write_then_mutate)

    with pytest.raises(
        ValueError,
        match="staged release files changed during packaging",
    ):
        package_self_contained_zip(release, output)

    assert not tuple(output.glob("*.zip"))
    assert not tuple(output.glob("*.sha256"))


def test_package_rejects_linklike_release_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = _write_release(tmp_path)
    original = packaging._is_linklike

    def fake_is_linklike(path: Path) -> bool:
        return path.name == "application.txt" or original(path)

    monkeypatch.setattr(packaging, "_is_linklike", fake_is_linklike)

    with pytest.raises(ValueError, match="link-like release entry"):
        package_self_contained_zip(release, tmp_path / "upload")


@pytest.mark.parametrize(
    "component",
    (
        "CON",
        "aux.txt",
        "CONIN$",
        "COM¹.log",
        "file:name",
        "bad?.txt",
        "control\x1f.txt",
        "trailing.",
        "trailing ",
    ),
)
def test_windows_unsafe_components_are_rejected(
    component: str,
) -> None:
    with pytest.raises(ValueError, match="Windows-safe"):
        packaging._validate_windows_component(
            component,
            label="test component",
        )


def test_windows_component_limit_counts_utf16_units() -> None:
    packaging._validate_windows_component("a" * 255, label="test component")

    with pytest.raises(ValueError, match="Windows-safe"):
        packaging._validate_windows_component(
            "a" * 256,
            label="test component",
        )
    with pytest.raises(ValueError, match="Windows-safe"):
        packaging._validate_windows_component(
            "😀" * 128,
            label="test component",
        )


def test_windows_relative_paths_reject_casefold_collisions() -> None:
    with pytest.raises(ValueError, match="case-insensitive"):
        packaging._validate_windows_relative_paths(
            (
                PurePosixPath("Docs/Readme.txt"),
                PurePosixPath("docs/README.TXT"),
            )
        )

    with pytest.raises(ValueError, match="case-insensitive"):
        packaging._validate_windows_relative_paths(
            (
                PurePosixPath("Data"),
                PurePosixPath("data"),
                PurePosixPath("data/child.txt"),
            )
        )


def test_package_rejects_output_inside_the_release_without_creating_it(
    tmp_path: Path,
) -> None:
    release = _write_release(tmp_path)
    output = release / "upload"

    with pytest.raises(ValueError, match="must not overlap"):
        package_self_contained_zip(release, output)

    assert not output.exists()


def test_package_rejects_output_that_contains_the_release(
    tmp_path: Path,
) -> None:
    release = _write_release(tmp_path)
    output = release.parent

    with pytest.raises(ValueError, match="must not overlap"):
        package_self_contained_zip(release, output)

    assert not tuple(output.glob("*.zip"))
    assert not tuple(output.glob("*.sha256"))


def test_package_fails_closed_without_atomic_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = _write_release(tmp_path)
    output = tmp_path / "upload"

    def reject_link(_source: Path, _target: Path) -> None:
        raise OSError("unsupported")

    operation = "rename" if packaging.os.name == "nt" else "link"
    monkeypatch.setattr(packaging.os, operation, reject_link)

    with pytest.raises(OSError, match="atomic no-overwrite"):
        package_self_contained_zip(release, output)

    assert not tuple(output.iterdir())


def test_archive_publish_failure_removes_published_checksum(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = _write_release(tmp_path)
    output = tmp_path / "upload"
    operation = "rename" if packaging.os.name == "nt" else "link"
    original = getattr(packaging.os, operation)

    def fail_archive(source: Path, target: Path) -> None:
        if target.suffix == ".zip":
            raise OSError("archive publication failed")
        original(source, target)

    monkeypatch.setattr(packaging.os, operation, fail_archive)

    with pytest.raises(OSError, match="atomic no-overwrite"):
        package_self_contained_zip(release, output)

    assert not tuple(output.iterdir())


def test_atomic_publish_race_has_exactly_one_complete_winner(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.tmp"
    second = tmp_path / "second.tmp"
    final = tmp_path / "final.zip"
    first.write_bytes(b"first complete payload")
    second.write_bytes(b"second complete payload")

    def publish(source: Path) -> bool:
        try:
            packaging._publish_without_overwrite(source, final)
        except (FileExistsError, OSError):
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(executor.map(publish, (first, second)))

    assert outcomes.count(True) == 1
    assert outcomes.count(False) == 1
    assert final.read_bytes() in {
        b"first complete payload",
        b"second complete payload",
    }
