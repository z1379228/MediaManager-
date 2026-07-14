# MediaManager 1.8.4

Version 1.8 begins the focused YouTube search refinement stage while preserving
the lightweight, opt-in MOD architecture completed in 1.7.x. Patch 1.8.4 makes
the built-in MOD manager directly actionable and removes ambiguous blank pages.

## 1.8.4 MOD management repair

- Opens the built-in MOD status page by default when no external package is
  installed instead of presenting an empty external table.
- Renames the main-shell action from **外部 MOD** to **MOD 管理** because the
  dialog now owns both built-in and external controls.
- Gives all nine built-in download and discovery MODs explicit enable/disable
  buttons with persisted registry state.
- Publishes a shared state-change event so the download and YouTube search
  workspaces update immediately when a manager button is used.
- Identifies a download task's owning provider even while that provider is
  disabled; disabling a download MOD cancels its active or queued work first.
- Replaces the empty external UI page with an explanation of the verified
  `ui.json` requirement and directs built-in features to their correct page.

## 1.8.3 UI sizing and responsive workspace

- Adds persistent compact, standard and large UI choices under the appearance
  menu; legacy settings continue to use the standard size.
- Raises the smallest default field, badge, detail and table-header text for
  improved readability while retaining the clean 14 px standard baseline.
- Uses a restrained 15 px large mode instead of scaling every spacing token,
  avoiding unnecessary visual bulk.
- Separates the provider and output-path rows and makes the download workspace
  vertically scrollable when the available height is insufficient.
- Validates both standard and large modes at the minimum 940 x 620 window size
  without clipped or overlapping controls.

## 1.8.2 application identity

- Adds a transparent, dark-blue media icon designed to remain recognizable at
  Windows taskbar and file-list sizes.
- Embeds a multi-resolution ICO in `MediaManager.exe` and includes the PNG at
  runtime for the Qt main window.
- Reuses the same icon for optional system-tray completion notifications, with
  the platform drive icon retained only as a safe fallback.
- Protects both icon assets in release preflight and preserves them in the
  staged version folder for reproducible builds.

## 1.8.1 selected download task details

- Adds a compact detail card that remains hidden until a download row is
  selected.
- Shows bounded failure details directly instead of relying only on a tooltip,
  while retaining the complete error text for an explicit copy action.
- Shows the completed output path and enables **開啟檔案位置** only when the
  path is a real non-symlink file inside the task's resolved output directory.
- Treats moved, deleted, outside-root or non-completed outputs as unavailable
  and never opens them through the task action.
- Double-clicking a completed task uses the same validated path gate.

## Explicit search scope

- Adds a compact **全部／音樂／影片** selector to the YouTube search row.
- Sends the selected scope through `DiscoveryService` and the subprocess IPC
  boundary into the independent `youtube-search` MOD.
- Rejects unknown scope values in both the trusted service and provider host.
- Adds a music search hint only when the user explicitly selects **音樂**; the
  neutral and video modes do not silently rewrite the query.
- Classifies neutral results with bounded title/metadata signals so the type
  column is more useful without a second metadata request.
- Leaves recovery and similar searches in the neutral scope and adds no
  autoplay, infinite scrolling, background recommendation or artwork cache.

## Validation

- Focused discovery, IPC, UI and built-in integrity regression:
  `44 passed, 1 skipped`.
- Focused download detail, queue, notification and UI regression: `34 passed`.
- Ruff, Python bytecode compilation and the full source regression completed:
  `376 passed, 1 skipped`.
- The 1180 x 780 YouTube search workspace was rendered offscreen and inspected;
  the additional selector does not crowd the search row or restore the native
  tab-bar line.
- The staged `Version/1.8` folder contains version-matched EXE and wheel
  artifacts; all `31/31` listed SHA-256 hashes pass.
- Historical release audit: 1.0 through 1.8 all pass, covering 225 listed
  hashes with no missing or unlisted files.
- Copied-folder smoke test: `--version`, portable `--verify-only` and portable
  `--headless` all returned exit code `0`, with no process or smoke data left
  in the retained version folder.
- Release preflight checked all 29 protected files and remains intentionally
  blocked only because the compiled release Ed25519 identity is invalid; the
  executable is also Authenticode `NotSigned`.

## Release state

This is a usable development artifact in `SAFE_MODE`. A valid compiled release
identity, signed release manifest and Authenticode signature remain mandatory
before a public release is described as trusted or signed.
