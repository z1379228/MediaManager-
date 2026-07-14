# MediaManager 1.9 to 3.0 update roadmap

Current baseline: **3.0.0**. The implemented YouTube discovery MODs, recovery,
similar search, audio/video preview, auto-split workflow, batch import, Bilibili
danmaku baseline, notifications, custom background, UI scaling, application
icon, unified built-in MOD controls, resumable queue controls and portable ID
lists, manifest-v2 policy and signed side-by-side offline update foundation are
and verified public-analysis site matrices are not scheduled again.

The versions below are ordered by dependency and risk rather than calendar
date. A later version does not start until the exit gate of the preceding
foundation version is met.

## Ordered versions

| Priority | Version | Theme | Planned delivery | Exit gate |
| --- | --- | --- | --- | --- |
| P0 | **1.9.x** | Complete the 1.x daily workflow | **Implemented in 1.9.0:** queue pause/resume semantics, batch queue actions, configurable worker count from 1 to 4, safe partial-file continuation where supported, archive/playlist ID import and export, disposable-key release-signing dry runs, and a repeatable live smoke matrix for YouTube, generic sites and Bilibili. Git remains untouched until explicitly authorized. | No queue-state or archive loss; no production key enters the repository; minimum-size UI remains usable; full regression, history audit and copied-folder smoke pass. |
| P0 | **2.0** | Trusted modular release foundation | **Engineering complete in 2.0.0:** manifest v2, signed capability declarations, PID-bound host initialization, fail-closed external execution policy, finalized install/update/rollback/recovery checks and signed side-by-side offline update bundles. Production signing identity remains external. | Disposable-key pipeline and lifecycle regression pass. Unsigned or insufficiently isolated executable MODs remain disabled. A public trusted build still requires production Ed25519 and Authenticode identities. |
| P1 | **2.1** | Verified multi-site coverage | **Implemented in 2.1.0:** stable provider failure taxonomy, explicit allowlists, repeatable public-analysis evidence for YouTube, Vimeo, Dailymotion, SoundCloud, TikTok, Twitch, X and Bilibili, plus Bilibili bangumi/multipart/subtitle/danmaku contracts. Generic and Bilibili MODs remain disabled by default. | All eight public analysis cases pass; login, region, removed, rate-limit and temporary failures remain explicit and no bypass is attempted. |
| P1 | **2.2** | Local media library | **Implemented in 2.2.0:** persistent SQLite indexing, bounded artwork, local-only editable metadata, duplicate review, play history, tags, static and smart playlists, M3U/JSON import/export, and previewed same-volume moves. Offline files retain their metadata. | Library operations are bounded, reversible or previewed, never silently overwrite files and remain useful without network access. |
| P1 | **2.3** | `media-convert` MOD | **Implemented in 2.3.0:** a disabled-by-default local feature registry and FFmpeg queue for remux, H.264/H.265 conversion, audio extraction, same-format join, timed split and SRT extraction. Stream copy is preferred, estimates are previewed and explicit NVIDIA H.264 attempts fall back to CPU. | No tab or worker exists until enabled/work is submitted; `.part` output, no-overwrite commit, disable/cancel cleanup and fallback behavior are tested. |
| P1 | **2.4** | `speech-to-text` MOD | **Implemented in 2.4.0:** an optional local whisper.cpp adapter, explicit SHA-256 model import/removal, language selection, model/RAM preview and TXT/SRT/VTT jobs with transactional output cleanup. No model or adapter is downloaded automatically. | No model is bundled or started silently; missing whisper-cli is explicit, cancellation cleans staging, existing output is refused and source media is never modified. |
| P2 | **2.5** | Optional automation | **Implemented in 2.5.0:** a disabled-by-default Automation MOD with separately disabled schedule, watch-folder and HTTPS clipboard rules. Each rule has an action preset, interval, run window, rate limit, next-run display and SQLite candidate ledger. | No rule monitors or connects until both MOD and rule are enabled; bounded missed runs, unique candidate keys, interrupted-claim recovery, visible failure and explicit retry are tested. |
| P2 | **2.6** | Discovery and metadata v2 | **Implemented in 2.6.0:** bounded multi-result similar search with explainable ranking and low-confidence query fallbacks, plus a global dark Qt palette for popup lists, scroll viewports, dialogs and external MOD pages. | Similar requests remain capped at 20, deduplicated and user-triggered; no autoplay or background recommendations; bright native fallback surfaces are disabled. |
| P2 | **2.7** | Performance and accessibility | **Implemented in 2.7.0:** unchanged download queues skip all table and selection redraw work at a 750 ms polling cadence; thumbnail/network limits are explicit; core controls expose accessible names and `Ctrl+F`; dark text contrast and minimum-size layouts have regression coverage. | Clean startup starts no provider subprocess; 1 MiB/40-item thumbnail limits, 7:1 text contrast and the 940 x 620 UI content width are tested. |
| P2 | **2.8** | MOD developer ecosystem | **Integrated into 3.0:** schema-v2 template generator, manifest/package validator, contract checker and Chinese lifecycle documentation. A catalog remains deferred until a production signing identity exists. | Sample projects are created and validated without loading code; signature trust remains an install-time gate. |
| P0 | **2.9** | 3.0 release freeze | **Integrated into 3.0:** deterministic dependency/licence inventory, retained-version audit, full regression and existing signing/preflight drills. | No critical regression or retained-version checksum error; missing production identity remains explicit. |
| P0 | **3.0** | Stable modular media suite | **Engineering complete in 3.0.0:** consolidates the clean core UI, trusted MOD lifecycle, verified providers, local library and optional feature MODs. Adds only UI incremental refresh and release/developer tooling. | Development build passes regression, history audit and copied-folder verification. Public trusted release remains gated by external Ed25519 and Authenticode identities. |

## 1.9 completion record

Version 1.9.0 completed the intentionally narrow 1.x workflow stage:

1. Preserved the untracked source tree without publishing, staging or
   committing it implicitly.
2. Define queue pause/resume states and persistence. Running downloads use a
   controlled provider cancellation and resumable partial file when supported;
   the application must not suspend an arbitrary OS process.
3. Add pause/resume-all and bounded worker-count controls without making the
   default workspace busier.
4. Add archive and playlist-ID export/import with preview, limits and atomic
   writes.
5. Exercise the release-signing pipeline with disposable test keys while
   keeping all production private-key material outside the repository.
6. Record public-content live smoke results separately from offline contract
   tests; a failure keeps the provider in Beta instead of weakening validation.
7. Passed the 1.9 release audit, disposable signing drill, three-provider live
   matrix and copied-folder smoke test before 2.0 security integration began.

## Permanent product boundaries

- Free, advertising-free, local-first and no telemetry by default.
- Heavy or background capabilities are independent MODs and disabled by
  default.
- No DRM, payment, region, advertising or authentication bypass.
- Facebook, Instagram and Threads remain official-page/export bridges unless
  documented Meta permission exists. An extractor alone is not authorization.
- Bahamut Anime Crazy remains an official-playback bridge unless an authorized
  download/export API or compatible offline-use licence is published.
- No cloud conversion chain, forced account, sponsored search result or bundled
  offer.

## Version folder rule

Every completed minor line is staged in its own folder, for example
`Version/1.9`, `Version/2.0`, `Version/2.1`, `Version/2.2`, `Version/2.3`, `Version/2.4`, `Version/2.5`, `Version/2.6`, `Version/2.7` and `Version/3.0`. Patch updates
replace only the matching major/minor folder transactionally, then regenerate
`release-info.json` and `SHA256SUMS.txt`. Smoke tests run from a disposable copy,
never directly inside the retained version folder.
