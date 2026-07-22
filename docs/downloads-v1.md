# Download workflow v1

The MediaManager core owns only the priority queue, durable task history, retry,
cancellation, progress snapshots, and output selection. Platform-specific URL
recognition and extraction belong to download MODs.

The bundled YouTube MOD lives under `mod/builtin/youtube` and runs in a separate
provider-host process. It communicates with the core using one JSON object per
line. Disabling the MOD is persisted in `mod/provider-state.json`; disabled MODs
cannot analyze URLs or receive new tasks.

Queue state is atomically stored in `Data/download-queue.json`. Tasks that were
`QUEUED`, `RUNNING`, or `RETRYING` when the application stopped are restored as
`PAUSED`; reopening the application never restarts network work automatically.
Completed, failed, and cancelled tasks remain as history. Paused tasks require
an explicit resume, while failed or cancelled tasks can be retried manually.

A segment uses optional start and end times in seconds. The YouTube MOD passes
that range to yt-dlp and asks FFmpeg to force keyframes at cuts. MediaManager
does not bypass DRM or access controls; users are responsible for downloading
only content they are authorized to save.

## Encoding presets

The trusted YouTube and Bilibili workspaces expose bounded quality and encoding
presets:

- **1440p** and **2160p (4K)** select source streams no higher than the chosen
  resolution. The automatic default remains capped at 1080p so upgrades do not
  unexpectedly increase bandwidth, merge time, or disk use.
- **H.264/AAC 1080p** selects compatible AVC/AAC source streams and muxes them
  into MP4. It does not perform a video transcode.
- **AAC/M4A 256k** and **MP3 320k** provide explicit high-bitrate FFmpeg
  outputs. Raising bitrate cannot recover detail absent from the source.
- **Opus 160k** extracts the selected audio through FFmpeg as Opus at about
  160 kbps.
- **FLAC** converts the selected audio to FLAC. A lossy web source remains
  lossy; this option does not restore or improve missing source quality.
- **WAV PCM** creates an uncompressed, large audio file. It is intended for
  editing compatibility and likewise does not improve a lossy source.

The UI shows the applicable note next to the selected format. Codec-specific
video choices appear after analysis only when compatible streams are reported.
High-resolution segmented downloads retain bounded video/audio stream
selection before FFmpeg merges the requested range. These presets are declared
by the dedicated YouTube and Bilibili MODs only;
Facebook, MEGA and the generic Beta provider keep their narrower capabilities.

## Advanced format and container checks

YouTube and Bilibili analysis may report width, height, frame rate, dynamic
range, source extension, video/audio codecs and estimated bytes. Older provider
responses without `dynamic_range` remain valid and display it as unknown.

The trusted UI offers Auto, MP4, MKV and WebM for video requests. Auto remains
the default. MKV is the general fallback; explicit MP4 or WebM requires an
analysis result containing compatible source tracks:

- MP4 accepts bounded MP4 video using H.264/AVC, H.265/HEVC or AV1, plus
  M4A/MP4 AAC-compatible audio.
- WebM accepts bounded WebM VP8, VP9 or AV1 video plus Opus/Vorbis audio.
- Audio-only presets keep their codec-owned extension and reject video
  container choices.

An incompatible explicit choice blocks queue insertion with a suggested
container. The application does not silently transcode codecs or change the
user's selected container. The selected container is persisted with the queue,
included in duplicate-download identity and reflected in generated filenames.

## Opt-in live diagnostic

Run the following command from the repository root after building a new Testing
candidate. Replace `<version>` with that candidate's folder; do not run this
against or alter a retained historical attachment:

```powershell
.\.venv\Scripts\python.exe tools\youtube_e2e.py --release-root Version\Testing\<version>
```

This network-dependent diagnostic checks the complete search, analysis,
metadata-based split planning and three-second segment-download path using the
bundled Deno, FFmpeg and ffprobe.
It searches for Blender Foundation's open Big Buck Bunny movie and deletes the
temporary output from `.work/youtube-e2e` after validation. Pass
`--keep-output` only when the test segment is needed for manual diagnosis. The
command is deliberately separate from pytest so normal regression tests remain
deterministic and usable offline.

The auto-split preview is created only after the user selects **準備切割** on an
analyzed video. The YouTube MOD writes a 64 kbps MP3 into a random session under
the application temporary directory, limits the source to two hours and 100 MB,
and removes the complete session when the trusted editor closes. MOD data never
loads executable Qt code; MediaManager renders and validates the editor itself.

After explicit confirmation, the complete plan becomes one atomic batch of
audio-only M4A requests. Every task persists its start/end range, generated
filename and media mode. A duplicate or invalid segment rejects the whole batch;
ordinary video archive identities retain their pre-auto-split format for upgrade
compatibility. Failed replacement downloads preserve the same segment, filename
and audio-only options.


## Composite-audio splitting

Long compilation detection, user-confirmed audio previews and atomic segment
queue expansion are implemented in the independent `youtube-auto-split` MOD.
See [youtube-auto-split-roadmap.md](youtube-auto-split-roadmap.md). Audio
analysis provides candidates only and never cuts automatically.

## Playlist selection

Use **展開播放清單** with exactly one YouTube playlist URL. Expansion is capped
at 500 entries and occurs in the isolated provider. The selection dialog keeps
unavailable and duplicate entries visible with a reason, while only explicitly
selected available entries become one atomic queue batch. Title/author filters
and select, clear and invert actions apply only to the currently visible rows.

## TXT/CSV batch import

The trusted download panel accepts a local UTF-8 `.txt` or `.csv` list after an
explicit file selection. TXT uses one URL per non-comment line. CSV accepts
`url`/`link`/`網址`/`連結`, optional title/name and optional artist/author/uploader
headers; a headerless file uses URL, title and artist as its first three
columns.

Imports are limited to 2 MiB and 500 data rows. The parser rejects symbolic
links, embedded credentials, malformed URLs and oversized metadata. Duplicate
or unsupported URLs remain visible with a reason but cannot be selected. Valid
rows are shown in a trusted preview and become one atomic queue batch only after
confirmation, retaining the current output folder, priority, time segment,
format and subtitle options.

## Generic yt-dlp Beta

The separately switchable `generic-ytdlp` download MOD is disabled by default
and currently routes only explicit Vimeo, Dailymotion, SoundCloud, TikTok and
Twitch hosts. YouTube remains owned by its dedicated MOD; Bilibili and social
sites are deliberately excluded from this provider. Facebook remains a
separate Testing download MOD. Instagram, Threads and X/Twitter are separate
official-tools parent MODs without download providers; X additionally prohibits
non-API website automation.

The generic MOD uses `network.generic` rather than YouTube permission, rejects
URLs containing embedded credentials and exposes the shared analyze, playlist,
format, subtitle, segment and durable-queue contracts. Its site matrix verifies
extractor presence and offline provider behavior; it does not promise that a
website cannot change before the next live smoke check.

## Bilibili and danmaku XML

The dedicated `bilibili` MOD is enabled on new profiles and accepts explicit
`bilibili.com` and `b23.tv` hosts. It does not use the generic provider and has
its own `network.bilibili` permission. Initial support covers metadata,
multi-part list expansion, the shared format/segment queue and ordinary
subtitle selection.

When every URL currently entered belongs to the enabled Bilibili MOD, the UI
shows a compact **保留彈幕 XML** option. It requests yt-dlp's `danmaku` subtitle
track as a separate XML sidecar. It does not embed or burn comments into the
video, so the original media remains unchanged and no additional conversion
work runs by default.

Two nested options appear only after XML retention is selected. **轉為 ASS**
performs a local, bounded conversion while retaining the
source XML. **嵌入 MKV** uses FFmpeg stream copy to place that ASS track in a
Matroska container without re-encoding the video or audio. If conversion or
muxing fails, MediaManager keeps the original media and every sidecar already
created rather than deleting usable output.

The durable queue stores timed-comment mode and container preset separately
from ordinary subtitle languages. This keeps retries, archive duplicate keys,
playlist expansion and TXT/CSV batches deterministic without pretending that
ASS or MKV is a language code.
