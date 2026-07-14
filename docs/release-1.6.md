# MediaManager 1.6.0

Version 1.6 adds the first dedicated Bilibili workflow and refreshes the
default workspace background without increasing startup or idle resource use.

## Bilibili MOD

- Adds a disabled-by-default `bilibili` provider for explicit `bilibili.com`
  and `b23.tv` hosts.
- Keeps Bilibili out of `generic-ytdlp` and uses the independent
  `network.bilibili` permission.
- Supports bounded metadata analysis, multipart list expansion, shared format
  and segment options, and durable queue routing.
- Adds an explicit **保留彈幕 XML** option that appears only when the current
  input is entirely Bilibili. Mixed-site batches cannot inherit it by mistake.
- Downloads danmaku as a separate XML sidecar. It does not embed or burn
  comments into the video.

## Appearance refresh

- Replaces the flat default fill with a procedural deep-blue/violet gradient,
  bounded radial light and a subtle lower vignette.
- Adds a readability vignette to custom images while retaining the managed
  background copy, decode limits and resize cache.
- Uses softer translucent cards, inputs and tables to keep the selected image
  visible without reducing text contrast.
- Ships no additional bitmap, animation, network request or background worker.

## Validation

- Ruff and Python bytecode compilation completed successfully.
- Targeted Bilibili, UI, integrity and release tests: `56 passed`.
- Full regression: `289 passed, 1 skipped`.
- Release checksum: all `28/28` listed files match, with no missing or
  unlisted files.
- Runtime dependencies: `4/4 Ready` (`yt-dlp 2026.7.4`, `yt-dlp-ejs 0.8.0`,
  `FFmpeg 8.1.2` and `Deno 2.9.2`).
- Copied-folder smoke test: portable `--verify-only` and `--headless` both
  returned exit code `0`, with no process left running.
- The default background was rendered offscreen at 1180 × 780 and saved
  successfully for visual inspection.
- Release preflight checked all 26 protected files and remains intentionally
  blocked only because the compiled release Ed25519 identity is not valid;
  the executable is also `NotSigned`.

## Release state

This remains a development artifact in `SAFE_MODE` until a valid release
Ed25519 identity, signed release manifest and Authenticode signature are
supplied. Initial Bilibili support has offline extractor and contract coverage;
live network behavior is not claimed until a repeatable smoke matrix is run.
