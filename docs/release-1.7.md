# MediaManager 1.7.4

Version 1.7 completes the first local Bilibili danmaku conversion workflow with
explicit, durable options and non-destructive fallback behavior. Patch 1.7.1
also closes the Bahamut Anime Crazy feasibility stage without adding a stream
or danmaku extractor. Patch 1.7.2 applies the same fail-closed review to
Facebook and Instagram. Patch 1.7.3 completes the Threads review and adds the
historical release audit workflow. Patch 1.7.4 fixes the dark workspace tab bar
and exposes the already-local YouTube search history through a compact menu.

## 1.7.4 workspace tab and YouTube search polish

- Disables Qt's native tab-bar base line explicitly, removing the bright
  horizontal artifact beside the selected **下載工作區** tab on Windows/Fusion.
- Adds a stylesheet guard so the workspace tab container remains transparent
  and borderless across platform styles.
- Adds a compact **最近搜尋** menu to YouTube search without introducing another
  permanent panel, background request or artwork cache.
- Shows bounded local search/selection counts, the strongest content/language
  preference signals and up to eight deduplicated recent queries.
- Re-running a recent query remains an explicit click and still obeys the
  independently switchable `youtube-search` and `youtube-history` MOD states.

## 1.7.3 release audit and Threads bridge

- Adds `tools.audit_versions`, a read-only batch audit for all retained version
  folders, and repairs test-only `UserData` pollution found in 1.0 through 1.2.
- Requires portable GUI/headless smoke tests to run from disposable copied
  folders so retained releases remain immutable.
- Confirms yt-dlp 2026.7.4 has no dedicated Threads extractor and keeps Threads
  outside `generic-ytdlp`.
- Adds current `threads.com` and migrated `threads.net` post URLs to the shared
  official-site bridge, canonicalizing accepted posts to `www.threads.com`.
- Links to Meta's official Threads-data export instructions without receiving
  passwords, cookies, sessions or exported archives.
- Records the decision and future official-API review boundary in
  `docs/threads-feasibility.md`.

## 1.7.2 Meta social-site feasibility

- Confirms that yt-dlp 2026.7.4 contains Facebook and Instagram extractors but
  keeps both hosts excluded from `generic-ytdlp` because extractor availability
  does not establish permission for automated product access.
- Replaces separate site-specific UI blocks with one data-driven official-site
  bridge for AniGamer, Facebook and Instagram.
- Accepts only bounded canonical Facebook watch, video and Reel forms or
  Instagram post, Reel and IGTV forms; rejects lookalike hosts, credentials,
  ports, fragments, tracking parameters, redirect endpoints and unrelated
  profile paths.
- Adds explicit links to Meta's official data-export help for user-owned
  information. No password, browser cookie, session or page source is accepted.
- Records the policy evidence and future re-evaluation conditions in
  `docs/meta-social-feasibility.md`.

## 1.7.1 official-playback bridge

- Adds Bahamut Anime Crazy to the candidate website MOD catalog as
  **official playback only**, not as an installed download provider.
- Accepts only the HTTPS homepage or a canonical official episode URL and opens
  it with the system browser after an explicit click.
- Rejects lookalike hosts, credentials, explicit ports, fragments, extra query
  parameters and internal endpoint paths.
- Performs no background network request and does not inspect streams, import
  cookies, download media, export danmaku or bypass ads and access controls.
- Records the official-policy evidence and conditions for any future review in
  `docs/ani-gamer-feasibility.md`.

## Danmaku conversion

- Adds a separately hashed `danmaku_ass.py` component inside the Bilibili MOD.
- Converts Bilibili XML comments into positioned ASS events with scrolling,
  top and bottom modes, bounded font sizes and decimal-to-ASS color mapping.
- Escapes ASS control characters and rejects XML declarations/entities,
  symbolic links, files over 32 MiB, more than 50,000 converted comments and
  invalid output paths.
- Always retains the source XML. Failed or empty conversions leave the media
  and XML usable.

## MKV compatibility

- Adds an optional **嵌入 MKV** action after ASS conversion is selected.
- Uses the bundled FFmpeg with stream copy, so video and audio are not
  re-encoded.
- Writes to a temporary MKV and replaces the output only after FFmpeg succeeds.
- If muxing fails, the original media, XML and generated ASS remain available.
- A real local smoke test generated a short H.264 video, muxed ASS and used
  ffprobe to confirm the resulting `ass` subtitle stream.

## Contract and UI

- Adds backward-compatible `timed_comment_mode` and `container_preset` fields
  to the media options contract and durable download queue.
- Preserves these fields through playlist expansion, TXT/CSV import, recovery,
  queue restart and archive duplicate detection.
- Keeps the default UI clean: ASS appears only after Bilibili XML is selected;
  MKV appears only after ASS and only for video formats.

## Validation

- Ruff and Python bytecode compilation completed successfully.
- Focused 1.7.3 official bridges, URL boundaries, generic-provider exclusion,
  historical audit and built-in integrity regression: `76 passed, 1 skipped`.
- Real FFmpeg/ffprobe MKV and ASS stream smoke test passed.
- Full regression: `362 passed, 1 skipped`.
- Release checksum: all `29/29` listed files match, with no missing or
  unlisted files.
- Runtime dependencies: `4/4 Ready` (`yt-dlp 2026.7.4`, `yt-dlp-ejs 0.8.0`,
  `FFmpeg 8.1.2` and `Deno 2.9.2`).
- Historical release audit: 1.0 through 1.7 all pass, covering 194 listed
  hashes plus matching wheel and executable versions.
- Wheel metadata reports 1.7.4 and includes the Threads validator and official
  bridge.
- Copied-folder smoke test: `--version`, portable `--verify-only` and portable
  `--headless` all returned exit code `0`, with no process left running.
- Release preflight checked all 27 protected files and remains intentionally
  blocked only because the compiled release Ed25519 identity is not valid;
  the executable is also `NotSigned`.

## Release state

This remains a development artifact in `SAFE_MODE` until a valid release
Ed25519 identity, signed release manifest and Authenticode signature are
supplied. Live Bilibili downloading is still not claimed until a repeatable
public-content smoke matrix is completed. AniGamer video or danmaku downloading
is not claimed or implemented; 1.7.1 opens only validated official pages.
Facebook and Instagram automated downloading is likewise not claimed or
enabled; 1.7.2 supplies only validated official pages and Meta export help.
Threads follows the same boundary in 1.7.3 and has no download provider.
