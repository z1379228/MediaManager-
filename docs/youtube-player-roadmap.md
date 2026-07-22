# Optional youtube-player MOD

## Product rule

Audio preview remains a lightweight search feature. In-app video playback is a
separate, independently switchable `youtube-player` MOD. It is enabled on new
profiles while preserving any existing saved choice.

When disabled, the MOD:

- starts no process;
- downloads no video data;
- creates no player widget or site-specific page;
- contributes no video-preview button to search results.

## Version 1 scope

The first version is an explicit, bounded local preview rather than an embedded
browser:

1. The user enables `youtube-player` from the search MOD menu or built-in MOD
   status controls.
2. Selecting a search result reveals a `影片預覽` action.
3. Pressing it requests at most 480p and a bounded preview interval.
4. The provider writes into a random application temporary session.
5. Trusted QtMultimedia UI plays only the validated local preview file.
6. Stop, replacement, MOD disable, panel close and application exit remove the
   complete preview session.

The initial interval should be 60 seconds. A later version may offer a longer
user-selected range after measuring bandwidth, disk and startup impact.

## Safety and resource limits

- Never autoplay search results.
- Never load advertising, comments, tracking scripts or an embedded converter.
- Cap resolution, duration, output bytes, provider time and idle time.
- Keep audio preview available when the video-player MOD is disabled.
- Reject paths outside the assigned preview session.
- Do not bypass DRM, payment, authentication or regional access controls.
- Do not persist stream URLs, cookies or temporary playback files in history.

## Why not QtWebEngine by default

Embedding a complete website browser would substantially increase package size,
memory use, background network activity and attack surface. A bounded local
preview preserves the clean default UI and the existing provider isolation
model. Browser-based playback can remain an external-open action.

## Delivery stages

1. Core/provider video-preview boundary. **Complete.**
2. Built-in `youtube-player` provider manifest and integrity pin. **Complete.**
3. Bounded 480p/60-second preview creation and cleanup tests. **Complete.**
4. Optional search-page toggle and trusted player dialog. **Complete.**
5. Live public-video validation and Version 1.2 packaging. **Complete.**
