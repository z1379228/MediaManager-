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

## Additional transfer-manager review (2026-07-15)

The reference set now also includes MegaDownloader, the current MEGA Desktop
App (formerly MEGAsync), iTubeGo, BitComet, uTorrent / µTorrent, qBittorrent, Vuze,
Deluge and Gopeed. They are workflow references only; they are not bundled,
called, endorsed or treated as proof that MediaManager supports the same
protocols.

The useful, non-duplicated directions are:

1. **MEGA stays an independent MOD.** Public MEGA links require
   client-side key handling and are not ordinary media-page extraction. The
   Development 9.2 adapter validates modern official `mega.nz` public-share
   URLs and routes public files to an explicitly detected official `mega-get`.
   It discloses the dependency, avoids account/session import, respects transfer
   quotas and access controls, and leaves folder download for later work.
2. **Multi-file selection and priority are reusable queue concepts.**
   BitComet, µTorrent and qBittorrent show clear per-file selection, priority,
   bandwidth and scheduling controls. MediaManager should expose those only
   when a provider returns a multi-file package; they do not justify adding a
   torrent engine to the core.
3. **P2P is a separate transport boundary.** qBittorrent, Vuze and Deluge are
   BitTorrent clients, not website downloaders. Any future `p2p-transfer` MOD
   must be disabled by default, make upload/seeding visible, exclude built-in
   torrent search, and require explicit bandwidth, storage and legal-use
   confirmation.
4. **Gopeed validates the existing modular direction.** Its HTTP API and
   extension model support keeping protocol engines outside a clean UI. A
   future local adapter may hand tasks to a user-installed Gopeed instance, but
   remote control, open ports and API tokens must never be enabled by default.
5. **iTubeGo mostly overlaps current work.** Batch/playlist selection,
   subtitles, format presets, thumbnails and search already have MediaManager
   owners. No duplicate browser, search engine or paid-conversion surface is
   added.

MegaDownloader is retained only as a historical MEGA-link workflow reference;
because there is no current official MEGA distribution or supported integration
contract for it, MediaManager must not depend on it or direct users to an
unverified installer.

## Reference groups

Desktop applications are the primary product and workflow references:

- SurFast Video Downloader
- 4K Video Downloader Plus
- MediaHuman YouTube Downloader
- JDownloader
- Stacher
- MegaDownloader (historical workflow reference only)
- MEGA Desktop App / MEGAsync
- iTubeGo
- BitComet
- uTorrent / µTorrent
- qBittorrent
- Vuze
- Deluge
- Gopeed

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

## Implemented or already scheduled

1. Download archive and duplicate detection.
   Implemented with queue history kept separate.
2. Explainable recovery candidates.
   Implemented; title/artist match reasons remain visible and replacement is explicit.
3. Format and naming presets.
   Implemented as bounded named presets; richer preflight detail remains in 4.2.
4. Completion and failure notifications.
   Implemented as local, user-controlled notifications.
5. Bounded search thumbnails and selected-item audio preview.
   Implemented with bounded thumbnails and explicit preview actions.

## Existing optional MODs and 4.x work

1. Automation, smart playlists, playlist/archive import/export, local
   speech-to-text, and bounded media conversion already exist as optional MODs.
2. Per-source scheduling, richer post-download metadata correction, and the 4.x
   search/download preflight work stay on the authoritative 4.0-to-5.0 roadmap.
3. Newly scanned gallery, transcript-search, cross-site mirror, and optional
   direct-transfer ideas are deferred until after 5.0 stable and do not expand
   the current release scope.

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
- https://mega.io/desktop
- https://github.com/meganz/sdk
- https://github.com/meganz/MEGAcmd
- https://itubego.com/youtube-downloader/
- https://www.bitcomet.com/en/features
- https://www.utorrent.com/
- https://www.qbittorrent.org/
- https://www.vuze.com/
- https://deluge-torrent.org/
- https://gopeed.com/docs

## Implemented download archive

The durable download archive is implemented in the transport-neutral queue.
Successful requests are keyed by canonical YouTube ID and segment boundaries.
Identical full or segmented requests are rejected atomically across batches,
history clearing and application restarts, while different time segments remain
allowed.
