# MEGA website MOD feasibility

Status: candidate catalog and official-link bridge only. MediaManager does not
currently claim that MEGA downloads are supported.

## Why MEGA needs a dedicated MOD

MEGA public links carry client-side decryption material and represent encrypted
cloud files or folders, not ordinary video pages. The official MEGA SDK provides
the client access engine, while MEGAcmd supplies a supported scriptable client
that can download a public link without signing in. This is a better trust
boundary than copying historical MegaDownloader behavior or passing a MEGA link
to the generic yt-dlp provider.

## Implemented candidate surface

- `mega` appears in the read-only website MOD candidate catalog.
- The official bridge accepts only HTTPS `mega.io`/`mega.nz` home pages or
  bounded modern `mega.nz/file/...#...` and `mega.nz/folder/...#...` public
  links.
- Accepted links are opened by the system browser only after explicit user
  action. They are not sent to MediaManager providers, logs or background jobs.
- Credentials, account sessions, legacy links, query parameters, nested folder
  paths, lookalike hosts and links without decryption material are rejected.

## Future independent MOD boundary

A future `mega` download MOD may use a user-installed official MEGAcmd or a
separately packaged and verified MEGA SDK adapter. It must:

1. Handle public links first without requiring account login.
2. Detect and disclose the external dependency at startup without installing it
   silently.
3. Keep link keys out of ordinary logs, history labels and diagnostic bundles.
4. Use the shared queue for destination checks, progress, pause/cancel, retries
   and completion notifications.
5. Respect MEGA access controls, copyright requirements and transfer quotas; it
   must not use quota-bypass services or account/session scraping.
6. Remain disabled by default and add no background server until the user
   explicitly enables the MOD and starts a task.

Account sync, backup, upload, WebDAV and remote cloud management remain out of
scope for the first download-only adapter.

Official references:

- https://mega.io/desktop
- https://github.com/meganz/sdk
- https://github.com/meganz/MEGAcmd
- https://github.com/meganz/MEGAcmd/blob/master/UserGuide.md
