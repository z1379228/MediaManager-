from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

from core.downloads.direct_http_policy import direct_http_url_candidate


def load_provider():
    path = (
        Path(__file__).parents[1]
        / "mod"
        / "builtin"
        / "direct-http"
        / "provider.py"
    )
    spec = importlib.util.spec_from_file_location("direct_http_provider_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Headers:
    def __init__(
        self,
        *,
        length: int,
        filename: str | None = None,
        content_type: str = "application/octet-stream",
    ) -> None:
        self.length = length
        self.filename = filename
        self.content_type = content_type

    def get(self, key: str):
        return str(self.length) if key.casefold() == "content-length" else None

    def get_filename(self):
        return self.filename

    def get_content_type(self):
        return self.content_type


class Response:
    def __init__(self, url: str, body: bytes, *, status: int = 200) -> None:
        self.url = url
        self.body = body
        self.offset = 0
        self.status = status
        self.headers = Headers(length=len(body), filename="release.zip")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self):
        return self.url

    def read(self, size: int):
        chunk = self.body[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def test_direct_http_candidate_is_explicit_and_never_takes_site_mod_urls() -> None:
    assert direct_http_url_candidate("https://downloads.example.org/release.zip")
    assert direct_http_url_candidate(
        "https://cdn.example.org/video.mp4?token=bounded"
    )
    for value in (
        "http://downloads.example.org/release.zip",
        "https://downloads.example.org/page",
        "https://127.0.0.1/release.zip",
        "https://www.youtube.com/media/release.zip",
        "https://cdn.facebook.com/media/video.mp4",
        "https://mega.nz/file/release.zip",
        "https://mega.io/file/release.zip",
        "https://cdn.threads.com/media/video.mp4",
    ):
        assert not direct_http_url_candidate(value)


def test_direct_http_analyze_reports_bounded_file_metadata(monkeypatch) -> None:
    provider = load_provider()
    monkeypatch.setattr(provider, "_global_host", lambda _host: None)
    response = Response(
        "https://downloads.example.org/release.zip", b"", status=200
    )
    response.headers = Headers(
        length=1234,
        filename="release.zip",
        content_type="application/zip",
    )
    monkeypatch.setattr(provider, "_open_for_analysis", lambda _url: response)

    result = provider.analyze(
        {"url": "https://downloads.example.org/release.zip"}
    )

    assert result["title"] == "release.zip"
    assert result["expected_bytes"] == 1234
    assert result["content_type"] == "application/zip"


def test_direct_http_download_streams_atomically_and_checks_sha256(
    tmp_path: Path, monkeypatch
) -> None:
    provider = load_provider()
    monkeypatch.setattr(provider, "_global_host", lambda _host: None)
    body = b"direct data"

    class Opener:
        def open(self, _request, timeout):
            assert timeout == 30
            return Response("https://downloads.example.org/release.zip", body)

    monkeypatch.setattr(provider, "build_opener", lambda *_args: Opener())
    result = provider.download(
        {
            "url": "https://downloads.example.org/release.zip",
            "output_dir": str(tmp_path),
            "provider_options": {
                "expected_sha256": hashlib.sha256(body).hexdigest()
            },
        }
    )

    assert Path(result).read_bytes() == body
    assert not (tmp_path / ".release.zip.part").exists()


def test_direct_http_download_resumes_only_on_partial_response(
    tmp_path: Path, monkeypatch
) -> None:
    provider = load_provider()
    monkeypatch.setattr(provider, "_global_host", lambda _host: None)
    (tmp_path / ".release.zip.part").write_bytes(b"first-")

    class Opener:
        def open(self, request, timeout):
            assert request.headers["Range"] == "bytes=6-"
            return Response(
                "https://downloads.example.org/release.zip",
                b"second",
                status=206,
            )

    monkeypatch.setattr(provider, "build_opener", lambda *_args: Opener())
    result = provider.download(
        {
            "url": "https://downloads.example.org/release.zip",
            "output_dir": str(tmp_path),
        }
    )

    assert Path(result).read_bytes() == b"first-second"


def test_direct_http_provider_rejects_private_resolution_and_bad_hash(
    tmp_path: Path, monkeypatch
) -> None:
    provider = load_provider()
    monkeypatch.setattr(
        provider.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (provider.socket.AF_INET, 1, 6, "", ("127.0.0.1", 443))
        ],
    )
    with pytest.raises(ValueError, match="non-public"):
        provider._validated_url("https://downloads.example.org/release.zip")

    monkeypatch.setattr(provider, "_global_host", lambda _host: None)
    with pytest.raises(ValueError, match="SHA-256"):
        provider.download(
            {
                "url": "https://downloads.example.org/release.zip",
                "output_dir": str(tmp_path),
                "provider_options": {"expected_sha256": "bad"},
            }
        )
