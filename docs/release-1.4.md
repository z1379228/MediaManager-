# MediaManager 1.4.3

Version 1.4 stabilizes image rendering in the trusted desktop UI.

## 1.4.3 preview stop control

- Search results now provide an explicit **停止試聽** action while a 30-second
  audio preview is preparing or playing.
- Stopping a preparation invalidates its callback generation, so a late worker
  result is cleaned instead of unexpectedly starting playback.
- End-of-media and playback errors release the local source, remove the bounded
  preview session and restore the action state automatically.
- Video-preview callbacks use the same generation envelope and cannot reopen a
  stale preview after disable or shutdown.
- Transactional version-folder renames retry a short Windows scanner lock up to
  five times with bounded backoff; persistent permission failures still abort.

## 1.4.2 batch import and workflow review

- The YouTube download panel can import UTF-8 TXT and CSV lists through an
  explicit file picker and trusted preview.
- Input is bounded to 2 MiB and 500 rows. Invalid, duplicate and unsupported
  URLs are shown with a reason and are not queued.
- CSV rows may carry title and artist metadata. Confirmed rows preserve the
  current download priority, segment, format and subtitle settings and enter
  the durable queue as one atomic batch.
- A broad workflow review keeps conversion, joining, subtitle editing and watch
  folders outside the clean core UI as a future disabled-by-default
  `media-convert` MOD.

## 1.4.1 maintenance optimization

- Search-result thumbnail generations are independent from preview actions, so
  starting audio or video preview cannot invalidate unfinished thumbnails.
- Starting a replacement search or closing the UI cancels obsolete thumbnail
  transfers; active unique requests are bounded and time out after eight
  seconds.
- Selected custom backgrounds are copied into the managed settings directory,
  keeping portable profiles stable when the original image is moved or removed.
- Wheel packaging uses the existing virtual environment with network access
  disabled, avoiding repeated build-dependency downloads.

## Thumbnail reliability

- YouTube thumbnail replies are accepted only after successful HTTPS and HTTP
  response validation.
- Non-image responses, oversized payloads and oversized decoded images are
  rejected before they reach the table view.
- Thumbnails are decoded and cached at a bounded display size instead of
  retaining arbitrary source dimensions.
- Concurrent requests for the same thumbnail share one network reply.
- Thumbnail callbacks are tied to the active search generation, row and result,
  so an older search cannot repaint a newer result table.

## Background reliability

- Custom backgrounds are decoded from their actual content rather than their
  extension alone.
- Invalid dimensions, failed decodes and oversized images are rejected without
  replacing the current background.
- Large accepted backgrounds are downsampled during decoding to reduce resize
  stalls and transient redraw artifacts.

This remains a development artifact in `SAFE_MODE` until a release Ed25519
identity, signed release manifest and Authenticode signature are supplied.

## Validation

- Ruff and Python compilation checks passed.
- Unit and integration suite: 261 passed, 1 skipped.
- `Version/1.4` checksum manifest: 23 of 23 files passed with no unlisted files.
- Packaged dependency health: 4 of 4 ready.
- A copied `Version/1.4` folder returned zero from integrity-only and portable
  headless startup checks. Its GUI remained active during a five-second
  offscreen smoke check, and all smoke processes and temporary files were
  removed afterward.
- Formal release preflight remains intentionally blocked because the compiled
  Ed25519 release identity is empty; the EXE is also Authenticode `NotSigned`.
