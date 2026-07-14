# Comparable software options

Reviewed against the current official feature descriptions for Tartube, yt-dlp,
Stacher, MusicBee, 4K Video Downloader Plus, MediaHuman, Format Factory,
HandBrake, Shutter Encoder and Parabolic, plus the user's broader reference list
below.

## Broad workflow review (2026-07-14)

The review found one high-value core improvement and one clear MOD boundary:

1. **Adopted in 1.4.2: bounded TXT/CSV batch import with preview.** Queue-first
   desktop tools make large input sets manageable before work starts.
   MediaManager now validates at most 500 local rows, shows invalid and
   unsupported items, and requires explicit confirmation before one atomic
   queue insertion.
2. **Planned as `media-convert`, not core UI.** Format Factory and Shutter
   Encoder demonstrate useful conversion, join/split, stream-copy, subtitle,
   output naming and watch-folder workflows. These fit a disabled-by-default
   local MOD using named FFmpeg presets, because the dependencies and controls
   are unrelated to ordinary URL downloading.
3. **Already covered; do not duplicate.** Named format presets, playlist
   selection, subtitles, chapters/splitting, history, retries, thumbnails,
   optional preview and portable runtimes already exist in MediaManager's
   current architecture.
4. **Deferred from the default surface.** Clipboard monitoring, scheduled
   subscriptions, FTP/email delivery and cloud accounts create background,
   privacy or maintenance cost. They remain optional candidates only if a
   concrete offline-first use case appears.

The product remains free, local-first and ad-free. Online conversion chains,
advertising redirects, forced browser notifications and bundled offers are not
acceptable reference patterns.

## Reference groups

Desktop applications are the primary product and workflow references:

- SurFast Video Downloader
- 4K Video Downloader Plus
- MediaHuman YouTube Downloader
- JDownloader
- Stacher

Web converters are secondary references for short interaction flows only:

- GetVideos.Net, VD6S, Y2Mate, Loader.to and SaveFrom
- YT1s, SSYouTube, SaveAny, TubeRipper and YTMP3
- EZDownload.net and FDownload.App for Facebook-specific URL recognition only

Adjacent workflow references are not downloader templates:

- TurboScribe for optional post-download transcription and subtitle exports
- VideoProc Converter AI for a separate convert/compress pipeline
- Tenorshare iCareFone for device-library organization, not website download

MediaManager must not copy advertising redirects, opaque server-side
conversion, forced tracking, notification prompts or unclear download chains.
Features borrowed from either group still require local validation, bounded
resource use and an explicit MOD or trusted-core ownership decision.

## Review checklist

For each planned UI or feature block, compare these areas before implementation:

1. Result recognition: thumbnail, title, author, duration, media type and a
   bounded on-demand preview.
2. Download preparation: format, quality, audio/video choice, naming preset and
   output location without exposing every extractor flag.
3. Batch control: playlist expansion, duplicate handling, priority, pause,
   retry, cancellation and visible partial failure.
4. Recovery: unavailable-item replacement, match reasons and preservation of
   original metadata.
5. Local organization: tags, artwork, archive history and library search.
6. Cost and safety: startup weight, background activity, network requests,
   temporary data, authentication, telemetry and update trust.

An existing MediaManager design becomes a revision candidate when a comparable
desktop workflow provides materially clearer identification or fewer steps
without weakening isolation, resource bounds or user confirmation.

## Add as near-term options

1. Download archive and duplicate detection.
   yt-dlp already treats successful IDs as a durable archive. MediaManager should
   expose this as a small independent MOD and keep queue history separate.
2. Explainable recovery candidates.
   Show title/artist match reasons and never replace a missing item silently.
3. Format and naming presets.
   Small named presets are easier to maintain than exposing every yt-dlp option.
4. Completion and failure notifications.
   Keep notifications local and user-controlled.
5. Bounded search thumbnails and selected-item audio preview.
   Load small artwork only for visible results and create preview audio only
   after an explicit action.

## Add later

1. Playlist or channel schedules with per-source presets.
2. Metadata/tag correction and smart local playlists.
3. Import/export of playlists and archive IDs.
4. A disabled-by-default local speech-to-text MOD with TXT/SRT/VTT export.
5. A bounded media-convert MOD using named FFmpeg presets and stream-copy first.
6. Optional metadata correction after download, including artist/title tags and
   chapter-aware audio naming, without making network enrichment automatic.

## Do not prioritize

1. Arbitrary pre/post-download scripts in the trusted UI.
2. Expanding the default UI to every site supported by yt-dlp.
3. Always-on autoplay, background recommendations or large artwork caches.
4. Cloud profiles or telemetry.
5. Private-content download flows that request page source, passwords or
   third-party cookies.
6. iOS device management that adds Apple driver/service dependencies to the
   clean downloader release.

## Rationale

Tartube is strong at monitoring, scheduling and local archiving. yt-dlp provides
reliable archive IDs and filters. Stacher exposes queue-oriented convenience and
advanced hooks. MusicBee is substantially deeper in tags and smart playlists.
MediaManager should keep those as optional MOD-sized capabilities while focusing
its default surface on a clean queue, explicit recovery and local-first history.

Sources:

- https://tartube.org/
- https://tartube.sourceforge.io/
- https://github.com/yt-dlp/yt-dlp/wiki/FAQ
- https://changelog.stacher.io/
- https://www.getmusicbee.com/
- https://www.4kdownload.com/products/videodownloader
- https://www.mediahuman.com/youtube-video-downloader/
- https://www.mediahuman.com/howto/user-interface-in-detail5.html
- https://www.pcfreetime.com/formatfactory/feature.php?language=en
- https://handbrake.fr/docs/en/latest/workflow/select-preset.html
- https://handbrake.fr/features.php
- https://www.shutterencoder.com/
- https://www.shutterencoder.com/documentation/
- https://github.com/NickvisionApps/Parabolic/releases

## Implemented download archive

The durable download archive is implemented in the transport-neutral queue.
Successful requests are keyed by canonical YouTube ID and segment boundaries.
Identical full or segmented requests are rejected atomically across batches,
history clearing and application restarts, while different time segments remain
allowed.
