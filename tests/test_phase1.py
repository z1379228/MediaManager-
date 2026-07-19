from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.logging.redaction import bounded_redacted_text, redact
from core.security.integrity_verifier import (
    IntegrityVerifier,
    release_signed_payload,
)
from core.security.safe_mode import SafeMode, SecurityMode
from core.settings import Settings, SettingsService, normalized_language
from core.storage.paths import AppPaths


class PhaseOneTests(unittest.TestCase):
    def test_portable_paths_remain_under_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            paths = AppPaths.discover(portable=True, app_root=root)
            paths.ensure_runtime_directories()
            self.assertEqual(paths.data, root / "UserData" / "Data")
            self.assertEqual(paths.security, root / "UserData" / "Security")
            self.assertEqual(paths.mod, root / "UserData" / "Mods")
            self.assertEqual(paths.builtin_mod, root / "mod" / "builtin")
            self.assertEqual(paths.release_security, root / "security")
            self.assertNotEqual(paths.security, paths.release_security)
            self.assertTrue(paths.plugin_packages.is_dir())
            self.assertTrue(paths.installed_plugins.is_dir())
            self.assertTrue(paths.quarantined_plugins.is_dir())

    def test_standard_mode_separates_builtins_from_user_mods(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            paths = AppPaths.discover(app_root=root)
            self.assertEqual(paths.builtin_mod, root / "mod" / "builtin")
            self.assertNotEqual(paths.mod, root / "mod")
            self.assertEqual(paths.plugin_registry, paths.mod / "registry.sqlite3")

    def test_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = SettingsService(Path(directory) / "settings.json")
            service.save(Settings(theme="dark"))
            self.assertEqual(service.load().theme, "dark")

    def test_language_is_limited_to_supported_mod_ui_locales(self) -> None:
        for locale in ("en", "ja", "zh-CN", "zh-TW"):
            self.assertEqual(normalized_language(locale), locale)
        self.assertEqual(normalized_language("fr"), "zh-TW")
        self.assertEqual(normalized_language(None), "zh-TW")

    def test_redacts_nested_secrets(self) -> None:
        value = {"access_token": "secret", "nested": ["Authorization: bearer-secret"]}
        result = redact(value)
        self.assertEqual(result["access_token"], "[REDACTED]")
        self.assertNotIn("bearer-secret", result["nested"][0])

    def test_redacts_url_secrets_mega_keys_and_windows_user(self) -> None:
        value = (
            "https://example.test/video?token=secret&x=1 "
            "https://mega.nz/file/abcdef#abcdefghijklmnop "
            r"C:\Users\Alice\Downloads\result.mp4"
        )
        result = redact(value)
        self.assertNotIn("secret", result)
        self.assertNotIn("abcdefghijklmnop", result)
        self.assertNotIn("Alice", result)
        self.assertIn("C:\\Users\\[USER]", result)

    def test_redacts_url_userinfo_without_changing_public_url(self) -> None:
        private_url = "https://user:password@example.test/video?x=1"
        public_url = "https://example.test/video?x=1"

        self.assertEqual(
            redact(private_url),
            "https://[REDACTED]@example.test/video?x=1",
        )
        self.assertEqual(redact(public_url), public_url)

    def test_redacts_complete_authorization_cookie_and_private_user_path(self) -> None:
        value = (
            "Authorization: Bearer bearer-secret-value\n"
            "Cookie: session=cookie-secret-value; csrf=csrf-secret-value\n"
            'failed at "C:\\Users\\Alice Smith\\Private Folder\\media.mp4"\n'
            "not_token=public-value"
        )

        result = str(redact(value))

        for secret in (
            "bearer-secret-value",
            "cookie-secret-value",
            "csrf-secret-value",
            "Alice Smith",
            "Private Folder",
            "media.mp4",
        ):
            self.assertNotIn(secret, result)
        self.assertIn("Authorization: [REDACTED]", result)
        self.assertIn("Cookie: [REDACTED]", result)
        self.assertIn("not_token=public-value", result)

    def test_bounded_redaction_handles_quoted_and_structured_secrets(self) -> None:
        values = (
            bounded_redacted_text({"token": "structured secret value"}),
            bounded_redacted_text('password="dummy alpha beta"'),
            bounded_redacted_text('{"token": "json secret value"}'),
            bounded_redacted_text(
                "{'Authorization': 'Bearer dictionary secret'}"
            ),
            bounded_redacted_text(
                '{"Authorization": Bearer unquoted-header-secret}'
            ),
            bounded_redacted_text(
                "{'Cookie': session=unquoted-cookie-secret}"
            ),
            bounded_redacted_text('{"token": unquoted-token-secret}'),
        )

        for result in values:
            self.assertIn("[REDACTED]", result)
            for secret in (
                "structured secret value",
                "dummy alpha beta",
                "json secret value",
                "dictionary secret",
                "unquoted-header-secret",
                "unquoted-cookie-secret",
                "unquoted-token-secret",
            ):
                self.assertNotIn(secret, result)

    def test_redacts_absolute_paths_without_hiding_diagnostic_fields(self) -> None:
        value = (
            r"failed at C:\Users\Alice,Smith\Private\media.mp4 "
            "exit_code=0x80000003 module=qt6core.dll\n"
            r"D:\Profiles\DemoUser\Private\file.mp4"
            "\n"
            r"\\server\home\RemoteUser\Private\file.mp4"
            "\n/home/posix-user/private/file.mp4\n"
            r"C:\Dev\MediaManager\private\file.mp4"
        )

        result = str(redact(value))

        for private_text in (
            "Alice",
            "Smith",
            "DemoUser",
            "RemoteUser",
            "posix-user",
            "MediaManager",
            "media.mp4",
            "file.mp4",
        ):
            self.assertNotIn(private_text, result)
        self.assertIn("exit_code=0x80000003", result)
        self.assertIn("module=qt6core.dll", result)

    def test_bounded_redaction_replaces_lone_surrogates(self) -> None:
        result = bounded_redacted_text(chr(0xD800), max_utf8_bytes=32)

        self.assertLessEqual(len(result.encode("utf-8")), 32)
        result.encode("utf-8").decode("utf-8")

    def test_bounded_redacted_text_limits_utf8_bytes_after_redaction(self) -> None:
        result = bounded_redacted_text(
            "token=secret-value " + "界" * 100,
            max_utf8_bytes=64,
        )

        self.assertNotIn("secret-value", result)
        self.assertLessEqual(len(result.encode("utf-8")), 64)
        result.encode("utf-8").decode("utf-8")

    def test_integrity_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "main.py"
            target.write_text("ok", encoding="utf-8")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            manifest = root / "release-manifest.json"
            manifest_bytes = json.dumps(
                {
                    "schema_version": 1,
                    "key_id": "test-release",
                    "files": {"main.py": digest},
                },
                separators=(",", ":"),
            ).encode()
            manifest.write_bytes(manifest_bytes)
            private_key = Ed25519PrivateKey.generate()
            public_key = base64.b64encode(
                private_key.public_key().public_bytes(
                    serialization.Encoding.Raw,
                    serialization.PublicFormat.Raw,
                )
            ).decode("ascii")
            manifest.with_name("release-manifest.sig").write_bytes(
                private_key.sign(release_signed_payload(manifest_bytes))
            )
            verifier = IntegrityVerifier(
                root,
                public_key=public_key,
                key_id="test-release",
            )
            self.assertTrue(verifier.verify(manifest).valid)
            target.write_text("tampered", encoding="utf-8")
            self.assertFalse(verifier.verify(manifest).valid)

    def test_unsigned_release_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "release-manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            result = IntegrityVerifier(
                root,
                public_key="unused",
                key_id="test",
            ).verify(manifest)
            self.assertFalse(result.valid)
            self.assertEqual(result.errors, ("signed release manifest is missing",))
    def test_blocked_mode_cannot_be_downgraded(self) -> None:
        mode = SafeMode()
        mode.block("root of trust failed")
        mode.enter_safe_mode("less severe")
        self.assertEqual(mode.mode, SecurityMode.BLOCKED)


if __name__ == "__main__":
    unittest.main()



