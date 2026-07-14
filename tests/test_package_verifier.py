from __future__ import annotations

import hashlib
import json
import stat
import zipfile

from core.plugins.package_verifier import PackageVerifier


def manifest() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "example.plugin",
        "name": "Example",
        "version": "1.0.0",
        "publisher": "trusted.example",
        "plugin_type": "processor",
        "entry_point": "plugin.py",
        "api_version": "1.0",
        "minimum_core_version": "0.1.0",
        "maximum_core_version": "1.0.0",
        "permissions": [],
        "external_tools": [],
        "dependencies": [],
        "files_manifest": "files.json",
        "signature": "plugin.sig",
    }


def package(path, extra_entries=()) -> None:
    source = b"def handle_request(request): return request\n"
    files = {"files": {"plugin.py": hashlib.sha256(source).hexdigest()}}
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("plugin.json", json.dumps(manifest()))
        archive.writestr("files.json", json.dumps(files))
        archive.writestr("plugin.sig", b"signature")
        archive.writestr("plugin.py", source)
        for info, content in extra_entries:
            archive.writestr(info, content)


def test_rejects_case_insensitive_path_collision(tmp_path) -> None:
    target = tmp_path / "collision.modpkg"
    package(target, (("PLUGIN.PY", b"duplicate"),))
    result = PackageVerifier().verify(target)
    assert not result.valid
    assert any("case-insensitive duplicate" in error for error in result.errors)


def test_rejects_zip_symbolic_link(tmp_path) -> None:
    target = tmp_path / "link.modpkg"
    link = zipfile.ZipInfo("link.py")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    package(target, ((link, "plugin.py"),))
    result = PackageVerifier().verify(target)
    assert not result.valid
    assert any("symbolic links are forbidden" in error for error in result.errors)


def test_rejects_windows_reserved_path(tmp_path) -> None:
    target = tmp_path / "reserved.modpkg"
    package(target, (("CON.txt", b"reserved"),))
    result = PackageVerifier().verify(target)
    assert not result.valid
    assert any("unsafe path" in error for error in result.errors)


def test_rejects_invalid_declared_hash(tmp_path) -> None:
    target = tmp_path / "bad-hash.modpkg"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("plugin.json", json.dumps(manifest()))
        archive.writestr("files.json", json.dumps({"files": {"plugin.py": "nope"}}))
        archive.writestr("plugin.sig", b"signature")
        archive.writestr("plugin.py", b"source")
    result = PackageVerifier().verify(target)
    assert not result.valid
    assert result.errors == ("invalid SHA-256 declaration: plugin.py",)

def test_accepts_data_only_package_without_entry_point(tmp_path) -> None:
    target = tmp_path / "data.modpkg"
    data = b"theme = dark\n"
    data_manifest = manifest()
    data_manifest["plugin_type"] = "data-only"
    data_manifest["entry_point"] = ""
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("plugin.json", json.dumps(data_manifest))
        archive.writestr(
            "files.json",
            json.dumps({"files": {"theme.txt": hashlib.sha256(data).hexdigest()}}),
        )
        archive.writestr("plugin.sig", b"signature")
        archive.writestr("theme.txt", data)
    result = PackageVerifier().verify(target)
    assert result.valid
