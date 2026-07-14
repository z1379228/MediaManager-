# MediaManager 1.2.2

This release adds the optional `youtube-player` MOD while keeping the default
search interface lightweight.

## Player behavior

- Audio preview remains available as the normal 30-second preview action.
- Video preview is a separate MOD and is disabled by default.
- Enabling `播放影片預覽` in the YouTube search MOD menu reveals a 60-second
  video-preview action.
- Preview downloads are limited to 480p and 80 MiB, do not autoplay until the
  user presses the action, and are played from a random local temporary session.
- Closing the preview, disabling the MOD, or closing the search panel removes
  the temporary session.
- The player uses Qt Multimedia and does not embed a browser, advertising, or
  tracking code.

## Validation

- Unit and integration suite: 193 passed, 1 skipped.
- UI integration covers default-hidden, explicit enablement and disable cleanup.
- Live YouTube smoke test: 3-second H.264/AAC preview created, probed, and its
  temporary session removed successfully.

This remains a SAFE_MODE development release until the external Ed25519 release
identity and signed release manifest are supplied.

## Download completion notifications

- One summary is emitted when the current busy queue becomes idle; multi-URL
  and split batches do not generate one notification per file.
- The in-app completion banner is enabled by default and can open the latest
  successful output folder.
- Windows system-tray notifications are optional and disabled by default.
- Notification preferences are stored locally. No sound, telemetry or remote
  notification service is used.
