# Versioned release folders

All staged MediaManager releases live under `Version/<major>.<minor>`.
The folder name is derived from `CORE_VERSION`: `1.0.0` becomes `1.0`,
`1.1.0` becomes `1.1`, and so on.

Build and stage the current version with:

```powershell
.\.venv\Scripts\python.exe -m tools.build_version
```

The default Windows build requires pinned, verified portable Deno and FFmpeg
runtimes. Fetch them once into the ignored local tool cache with:

```powershell
.\.venv\Scripts\python.exe -m tools.portable_runtime
```

The downloads and extracted executables are checked against fixed SHA-256 values.
Successful builds copy Deno, FFmpeg, ffprobe, and their license notices into
`Version/<version>/tools`.
Use `--without-portable-runtime` only for a deliberately reduced build.

Temporary PyInstaller and wheel output stays under `.work/<major>.<minor>` and is
removed after a successful build. Use `--keep-work` only when build diagnostics are needed.
Each version folder contains the EXE, wheel, portable tools, built-in MOD files,
`release-info.json`, and `SHA256SUMS.txt`. Re-staging the same version uses a
transactional staging directory and removes stale files from the older staged
copy. Build caches are not included.

Audit every retained version after building, copying or signing:

```powershell
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
```

The audit validates folder/version alignment, wheel metadata, portable tools,
safe checksum paths, every listed hash, missing files, unlisted files and
interrupted staging residue. A post-stage release manifest and signature are
accepted only when both are present; cryptographic release readiness remains
the responsibility of `tools.release_preflight`.

Never run portable GUI or headless smoke tests directly inside a retained
`Version/<major>.<minor>` folder. Portable mode writes `UserData` beside the
executable and makes the staged folder fail its checksum inventory. Copy the
complete folder under `.work/smoke-<version>`, test that copy, verify no process
remains and then remove only that smoke directory. `--version` and
`--verify-only` may be used for read-only historical checks, followed by another
`tools.audit_versions` run.

Formal signing and preflight use the staged folder as their root:

```powershell
.\.venv\Scripts\python.exe -m tools.sign_release --root Version\1.0 --private-key <external-key-path>
.\.venv\Scripts\python.exe -m tools.release_preflight --root Version\1.0
```
