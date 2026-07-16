# X / Twitter capability boundary

Review date: 2026-07-16

## Decision

The current source provides an independent, disabled-by-default `twitter`
parent MOD with two trusted child MODs:

- `twitter-page` validates an official `x.com` or `twitter.com` status URL,
  canonicalizes it to HTTPS on `x.com`, and opens it only after a user click.
- `twitter-export` opens X's official account-data archive help only after a
  user click, then allows a separately downloaded local ZIP to be inspected and
  its bounded image/video entries indexed locally.

The provider ID remains `twitter` because built-in MOD identifiers require at
least two characters; the UI display name is **X / Twitter**. This is not a
download MOD and does not claim official X integration.

## Policy evidence

- X's official [Automation Rules](https://help.x.com/en/rules-and-policies/x-automation)
  prohibit non-API automation such as scripting the X website.
- X's official [Developer Guidelines](https://docs.x.com/developer-guidelines)
  likewise require the official API and list browser scripting, scraping and
  other non-API automation as prohibited.
- X provides an official [account-data archive workflow](https://help.x.com/en/managing-your-account/accessing-your-x-data)
  that lets an authenticated user request and download their own archive.

## Runtime and UI rules

- The MOD manager shows X / Twitter as a parent node. It shows the parent
  switch when expanded, and lists the two child switches only while the parent
  is enabled.
- Disabling the parent persists both child states as disabled. A clean start
  performs no X network request and starts no provider process.
- Accepted paths are limited to bounded `/user/status/<digits>` and
  `/i/web/status/<digits>` forms. HTTP, credentials, explicit ports, query
  parameters, fragments, lookalike hosts and unrelated X pages are rejected.
- MediaManager never receives an X password, OAuth token, Cookie or session.
  Sign-in and archive preparation remain on X's official site; only a ZIP the
  user explicitly selects is read locally, with scripts and metadata excluded.

## Explicit exclusions

X/Twitter hosts are removed from `generic-ytdlp`, its extractor matrix and its
live public-content smoke cases. The current source does not scrape posts,
profiles, replies or media; automate a browser; import cookies; bypass access,
rate or region controls; or download X media.

A future download/search child MOD requires a separately reviewed official API
flow, explicit user authorization, bounded permissions and its own tests. It
must not be reintroduced through the generic provider.
