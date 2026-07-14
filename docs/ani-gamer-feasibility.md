# Bahamut Anime Crazy feasibility review

Review date: 2026-07-14
Release decision: MediaManager 1.7.1 provides an official-playback bridge only.

## Evidence

- The [official service terms](https://ani.gamer.com.tw/animeRule.php) describe
  authorized use through the viewing functions supplied by the service. They
  also prohibit reproduction and attempts to bypass advertising, playback or
  stream restrictions.
- The [official animation page](https://ani.gamer.com.tw/animeVideo.php?sn=44866)
  exposes the site's own player and danmaku controls; posting danmaku is tied to
  the official signed-in experience. This does not establish permission for a
  third-party export or downloader.
- The [official playback troubleshooting page](https://ani.gamer.com.tw/anime403info.php)
  documents dependencies on the supported player environment and IP state,
  including problems caused by proxies, VPNs and browser components. A client
  must not work around these checks.
- The locally installed yt-dlp 2026.7.4 extractor list contains no dedicated
  Bahamut or AniGamer extractor.

## Delivered scope

The MOD manager's candidate-site page contains a small official-playback card.
It is deliberately not a provider and does not add a default workspace page.

- Blank input opens `https://ani.gamer.com.tw/`.
- An episode URL must be HTTPS, use the exact `ani.gamer.com.tw` host and match
  `/animeVideo.php?sn=<1 to 10 ASCII digits>`.
- Lookalike hosts, credentials, ports, fragments, extra parameters and other
  paths are rejected before the system browser is called.
- Nothing connects in the background. Opening occurs only after an explicit
  user click and playback remains in the official browser experience.

## Explicit exclusions

MediaManager does not inspect private endpoints, extract stream URLs, import or
store AniGamer cookies, download video, export danmaku, remove advertising, or
bypass login, region, IP, player or other access controls.

This decision can be reviewed only if the service publishes an authorized API,
export facility or offline-use licence that permits third-party integration.
