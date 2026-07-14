# MediaManager 2.4.0

Version 2.4 adds optional, offline speech-to-text without bundling a model or
silently installing an executable.

## Speech to Text MOD

- Ships disabled by default and creates its workspace only after explicit
  enablement. Enabling does not start a worker or network request.
- Detects a local `whisper-cli` adapter and reports when it is absent; no
  executable is downloaded or installed automatically.
- Imports user-selected local GGML/GGUF model files only when a supplied
  64-character SHA-256 matches. Copies are atomic, bounded to 8 GiB and tracked
  in a local manifest; removal is explicit.
- Previews model size, conservative RAM estimate and TXT/SRT/VTT targets.
- Refuses source symlinks and existing output, never modifies the source, and
  commits staged outputs without replacement. Cancellation removes the entire
  per-job staging directory.
- Translation and speaker separation remain outside this baseline.

## Validation

- Model manager, adapter, cancellation, MOD UI, integrity and staging focus:
  `26 passed, 1 skipped`.
- Ruff and complete source regression: `432 passed, 2 skipped`.
- `Version/2.4` contains matching 2.4.0 EXE and wheel artifacts; all `36/36`
  hashes pass and the historical audit passes for 1.0 through 2.4.
- Copied-folder version, Portable verification and headless smoke all returned
  exit code `0`; the disposable copy was removed.
- The disposable signing drill verified all 34 protected files and retained no
  private key.

## Release state

This remains a `SAFE_MODE` development build. No model is present in the source
tree or staged release, and no cloud transcription service is used.
