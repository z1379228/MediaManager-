# Multi-site download and danmaku roadmap

## Product direction

MediaManager remains free, advertising-free and local-first. The long-term goal
is broad website coverage through independently maintained MODs rather than
site-specific logic in the trusted core.

Support means downloading content the user is authorized to save without
bypassing DRM, payment, authentication or regional access controls. A site that
cannot meet that boundary may still support metadata, search or opening in the
user's browser, but must not be presented as downloadable.

## Provider layers

1. `generic-ytdlp`: bounded support for sites handled by maintained yt-dlp
   extractors, with per-site smoke tests and clear unsupported-site errors.
2. Dedicated site MODs: only for sites that require distinct metadata, login,
   playlist, subtitle or rate-limit behavior.
3. Shared download contracts: format choices, subtitles, thumbnails, playlist
   entries and optional comment/danmaku tracks remain transport-neutral.

Broad support is not a promise that every site always works. Extractor support
must be versioned and verified because websites change independently.

## Activation and UI rules

Each website or closely related site family is an independently switchable
MOD. Installing or bundling a MOD does not mean it stays active.

- New optional site MODs are disabled by default.
- A disabled MOD starts no provider process, schedules no work, performs no
  network requests and contributes no site-specific page to the default UI.
- Enabling a MOD adds only the controls required for that site's supported
  capabilities.
- Provider processes start lazily on the first analyze, search, preview or
  download request and stop when disabled or when the application exits.
- Site status and enable/disable controls remain discoverable in the MOD
  manager even when their feature pages are hidden.
- Common download queue, history and output controls stay in the trusted UI;
  site-specific authentication, danmaku and metadata options stay with their
  owning MOD.
- A generic yt-dlp provider is also optional and never silently takes ownership
  of a URL that an enabled dedicated provider supports.

This keeps the default interface clean and makes CPU, memory and network cost
proportional to the features the user actually enables.

## Social-site MOD boundaries

The MOD manager contains a read-only candidate catalog so planned or bounded
sites remain discoverable without being presented as installed download
providers.

- `facebook`: feasibility completed in 1.7.2. Meta prohibits automated access or
  collection without prior permission, so the installed yt-dlp extractor is
  not enabled. The UI validates bounded official video URLs, opens them in the
  system browser and links to Meta's official data-export instructions.
- `instagram`: feasibility completed in 1.7.2 with the same official-tool-only
  boundary. It is now a parent MOD with separate official-page and data-export
  child controls. Posts, Reels and IGTV pages can be opened after local URL
  validation; MediaManager does not import sessions, cookies or stories.
- `twitter`: X/Twitter is a separate parent MOD with official-post and
  account-archive child controls. X explicitly prohibits non-API website
  automation, so its hosts are excluded from `generic-ytdlp`; only locally
  validated official URLs are opened after an explicit click.
- `threads`: feasibility completed in 1.7.3. The current web host is
  `threads.com`, the previous `threads.net` host is canonicalized to it, and
  bounded post pages plus Meta's official Threads-data export help can be
  opened. The bundled yt-dlp list has no dedicated extractor and automated
  collection remains excluded.

They must not create separate always-visible core pages. A future download
provider requires documented platform permission in addition to a maintained
extractor and the existing transport-neutral contracts.

## Bilibili priority

Bilibili is the first non-YouTube priority because current yt-dlp extractors
cover videos, bangumi, playlists, search, audio and live content. The extractor
also exposes Bilibili danmaku as an XML subtitle track.

Initial delivery:

1. Analyze Bilibili URLs and show title, owner, duration, thumbnail and parts.
2. Offer video/audio formats and ordinary subtitle tracks.
3. Offer danmaku as an explicit optional sidecar download.
4. Convert supported danmaku into ASS for compatible offline players.
5. Prefer MKV plus ASS when retaining positioned/color comments; keep the
   original XML when conversion cannot preserve information.
6. Never burn danmaku permanently into video by default. Burning is slower,
   irreversible and belongs in a later explicit export action.

Login or premium formats may be offered only through an opt-in user-owned
session flow. Credentials and cookies must not be collected by a third party or
stored inside a MOD package.

## Bahamut Anime Crazy feasibility

The 1.7.1 feasibility review found no supported basis for a MediaManager video
or danmaku downloader. The official service terms limit use to the viewing
functions supplied by the service and prohibit reproduction as well as
advertising, playback and stream bypass. The installed yt-dlp 2026.7.4
extractor set also has no Bahamut or AniGamer extractor.

The only delivered integration is therefore an official-playback bridge in the
candidate MOD catalog. It accepts only the HTTPS homepage or canonical
`/animeVideo.php?sn=<digits>` page on `ani.gamer.com.tw`, then asks the operating
system to open that page. It does not inspect endpoints, import cookies, parse
streams, download video or export danmaku, and it makes no background request.

Download support may be reconsidered only if Bahamut publishes an authorized
download/export API or an offline-use licence with a compatible integration
path. See `docs/ani-gamer-feasibility.md` for the evidence and decision record.

## No-advertising requirements

- No banners, sponsored search results, redirects or notification advertising.
- No embedded third-party converter pages.
- No telemetry or advertising identifiers.
- No remote conversion service hidden behind a local UI.
- Funding or donation links, if ever added, must stay optional and outside
  normal download/search workflows.

## Delivery order

1. Search thumbnails and selected-item 30-second audio preview. **Complete.**
2. Optional, disabled-by-default `youtube-player` MOD with bounded local video
   preview. **Complete.**
3. Shared format/subtitle/thumbnail result contract. **Complete.** Discovery,
   playlist and media-option contracts are versioned and transport-neutral.
4. `generic-ytdlp` provider with a tested site matrix. **Initial Beta complete
   in 1.5.0.** Vimeo, Dailymotion, SoundCloud, TikTok and Twitch use
   an explicit host allowlist, separate generic-network permission and offline
   extractor/contract tests. It remains disabled by default; live smoke status
   must be recorded before any site graduates from Beta.
5. Bilibili provider and XML danmaku sidecar. **Initial delivery complete in
   1.6.0.** The provider has an explicit host allowlist and independent network
   permission, stays disabled by default, reports multipart metadata and keeps
   requested danmaku as a separate XML file. Live-site smoke verification is
   still required before removing the initial support label.
6. Danmaku-to-ASS conversion and compatible container presets. **Complete in
   1.7.0.** Conversion is bounded and preserves source XML; optional MKV muxing
   uses FFmpeg stream copy, retains external ASS and falls back to the original
   media plus sidecars on failure.
7. Bahamut Anime Crazy feasibility. **Complete in 1.7.1.** The result is an
   official-playback bridge only; no download or danmaku provider is created.
8. Facebook and Instagram feasibility. **Complete in 1.7.2.** Instagram is now
   an official-page and official-export parent/child group; automated download
   remains excluded. Facebook download remains a separate Testing capability.
9. Threads public-content feasibility. **Complete in 1.7.3.** The result is an
   official-page and official-export bridge only, with no download provider.
10. X/Twitter feasibility. **Complete in development 11.2.** Non-API website
    automation and generic download ownership are removed. The result is an
    official-post and official-account-archive parent/child group.

## Optional post-download MODs

- `speech-to-text`: local, on-demand transcription with TXT, SRT and VTT output.
  Speaker separation and translation are later optional capabilities because
  they add model size, memory use and privacy considerations.
- `media-convert`: remux, convert and compress downloaded or local media. Start
  with bounded FFmpeg presets and stream-copy where possible. GPU acceleration
  is optional and must fall back cleanly; AI upscaling is not a core priority.
