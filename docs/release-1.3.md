# MediaManager 1.3.3

Version 1.3 begins the transport-neutral media-option contract needed by future
site MODs.

## Format presets

- Automatic compatible video, capped at 1080p.
- Highest-quality 1080p, 720p and 480p video presets.
- M4A and MP3 audio extraction presets.
- Presets are bounded identifiers rather than arbitrary yt-dlp format strings.

## Subtitle options

- Subtitles are disabled by default.
- The user may request up to eight explicitly named languages, or all available
  subtitle tracks.
- Normal and automatically generated subtitle tracks are written as sidecars;
  they are not burned permanently into the video.

## Durability and safety

- Format and subtitle choices persist across restart and failed-item recovery.
- The durable archive distinguishes materially different output requests while
  preserving the legacy identity for the default preset.
- The isolated provider validates the same bounded option set again before
  creating yt-dlp arguments.

## Playlist expansion

- A playlist URL is expanded inside the isolated YouTube provider and returns
  at most 500 versioned, validated entries.
- The trusted UI lists title, author, duration and availability before any
  download starts.
- Users can filter by title or author, select/clear/invert visible entries and
  explicitly confirm the final atomic batch.
- Private, removed, malformed and repeated entries remain visible with a reason
  but cannot be selected; one bad entry does not abort playlist inspection.
- Selected entries retain the current priority, format and subtitle options.

The bounded TXT/CSV import originally planned here is delivered in 1.4.2.

## 1.3.2 dependency detection fix

- Frozen builds now preserve `yt-dlp-ejs` distribution metadata.
- The health check also reads the package's public `version` attribute when
  metadata is unavailable, instead of the nonexistent `__version__` attribute.
- A bundled EJS installation is therefore reported correctly instead of
  producing a false 3/4 environment warning.

## 1.3.3 deep reliability pass

- Provider stdout now has a bounded message size and backlog; stderr is drained
  concurrently with a 64 KiB diagnostic cap, preventing a noisy MOD from
  deadlocking or consuming unbounded memory.
- Successful downloads are accepted only when the provider returns a nonempty,
  regular file inside the requested output directory. Required operation
  permissions and finite segment times are enforced before execution.
- Queue writes are transactional for add/retry operations. Retry cannot bypass
  duplicate detection, one malformed saved record no longer discards every
  valid task, and state supports 10,000 bounded tasks instead of failing after
  1,000.
- Application shutdown now signals running downloads, waits within one shared
  deadline, and persists them as queued work for a later restart.
- Frozen builds use the canonical `--plugin-host` entry point. A plugin is not
  marked started until its isolated host returns the expected protocol, plugin
  ID and one-time nonce handshake. Windowed frozen host processes explicitly
  restore only their redirected stdin/stdout/stderr pipe handles.
- Capability validation now occurs before authenticated rate limiting, and
  replay/rate-limit state is concurrency-safe.
- YouTube search operations are mutually exclusive and generation-checked;
  closing the main window explicitly cleans previews and ignores late worker
  results. Idle download tables are no longer rebuilt every 350 ms.
- Dependency health now requires yt-dlp 2026.7.4+, yt-dlp-ejs 0.8.0 with both
  solver resources, and FFmpeg/ffprobe 6.0+.
- Interrupted `Version/<major>.<minor>` staging transactions can recover a
  committed target or roll back the previous target on the next build.

This remains a development artifact in `SAFE_MODE` until a release Ed25519
identity, signed release manifest and Authenticode signature are supplied.

## Validation

- Unit and integration suite: 246 passed, 1 skipped for 1.3.3.
- Live YouTube diagnostic: the explicit 720p preset produced a three-second
  H.264/AAC segment and passed bundled ffprobe validation.
