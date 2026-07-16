# MEGA website MOD feasibility

Status: the current source implements a disabled-by-default public file/folder
adapter backed by the official `mega-get` command.

## Why MEGA needs a dedicated MOD

MEGA public links carry client-side decryption material and represent encrypted
cloud files or folders, not ordinary video pages. The official MEGA SDK provides
the client access engine, while MEGAcmd supplies a supported scriptable client
that can download a public link without signing in. This is a better trust
boundary than copying historical MegaDownloader behavior or passing a MEGA link
to the generic yt-dlp provider.

## Implemented surface

- `mega` is an independent main MOD with its own trusted download workspace;
  it is not routed through yt-dlp or another website MOD.
- The provider accepts only bounded modern HTTPS `mega.nz/file/...#...` and
  `mega.nz/folder/...#...` public links. The separate official bridge may still
  open `mega.io`/`mega.nz` home pages in the system browser.
- Analysis is local-only: it identifies file versus folder, shows a local
  file/folder thumbnail and reports whether official `mega-get` was detected.
- Public file and whole-folder downloads are routed through an explicitly
  injected, verified `mega-get` executable and the shared queue. A completed
  folder must produce exactly one confined root folder; its local tree is
  bounded to 10,000 entries and may not contain symbolic links.
- Share keys are removed from analysis labels and ordinary status/error text;
  the full link is passed only to the explicitly started local download process.
- Credentials, account sessions, legacy links, query parameters, nested folder
  paths, lookalike hosts and links without decryption material are rejected.

## Preserved boundary and next work

The adapter continues to:

1. Handle public file links without requiring account login.
2. Detect and disclose the external dependency without installing it silently.
3. Keep link keys out of ordinary logs, history labels and diagnostic bundles.
4. Use the shared queue for destination checks, progress, cancellation, retries
   and completion notifications.
5. Respect MEGA access controls, copyright requirements and transfer quotas; it
   must not use quota-bypass services or account/session scraping.
6. Remain disabled by default and start no provider process until the user
   explicitly requests analysis or download.

Per-file remote folder browsing, account sync, backup, upload, WebDAV and remote
cloud management remain out of scope for the download-only adapter. The current
UI downloads a public folder as one explicit job rather than pretending it can
preselect remote children without an authenticated listing contract.

Official references:

- https://mega.io/desktop
- https://github.com/meganz/sdk
- https://github.com/meganz/MEGAcmd
- https://github.com/meganz/MEGAcmd/blob/master/UserGuide.md
