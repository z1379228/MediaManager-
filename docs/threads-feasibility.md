# Threads feasibility review

Review date: 2026-07-14
Release decision: MediaManager 1.7.3 provides an official post and data-export
bridge only. It does not enable a Threads download provider.

## Evidence

- Meta's [Threads web announcement](https://about.fb.com/news/2025/04/new-features-threads-web-experience/)
  documents the migration from `threads.net` to `threads.com`.
- The [Instagram Terms of Use](https://www.facebook.com/help/instagram/581066165581870)
  prohibit automated access or collection without express permission. Threads
  supplements and incorporates the Instagram terms.
- Meta provides an official [Threads information download](https://www.facebook.com/help/instagram/259803026523198)
  workflow for a user's own posts and data, including HTML or JSON export.
- The locally installed yt-dlp 2026.7.4 extractor list contains no dedicated
  Threads extractor.
- Meta publishes Threads developer documentation, but an authorized API
  integration requires a separate app, permission and OAuth design review. It
  is not evidence that arbitrary public media downloading is allowed.

## Delivered scope

- Blank input opens `https://www.threads.com/`.
- A post must use HTTPS and match
  `/@<bounded-username>/post/<bounded-post-id>` on `threads.com` or the migrated
  `threads.net` host.
- Accepted old-host URLs are canonicalized to `www.threads.com`.
- HTTP, credentials, explicit ports, fragments, queries, profiles, short share
  paths, encoded separators and lookalike hosts are rejected locally.
- A separate explicit button opens Meta's Threads-data export instructions.
- Nothing connects before the user clicks. Sign-in, viewing and export remain
  in the system browser on Meta's official site.

## Explicit exclusions

MediaManager does not scrape posts, profiles, replies or feeds; resolve media
endpoints; import cookies or sessions; automate sign-in; download third-party
media; or bypass privacy, rate or access controls.

Future API work must start with documented Meta app permissions and a
user-owned OAuth flow. It should support only data the authorization explicitly
permits, remain disabled by default and use an independently versioned MOD.
