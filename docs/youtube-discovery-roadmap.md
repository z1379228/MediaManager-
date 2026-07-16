# YouTube discovery MOD roadmap

These features remain outside the MediaManager core and are split into small MODs
with independent versioning and maintenance.

## Shared contract

A versioned discovery contract will define compact search results (`video_id`,
URL, title, artist/uploader, duration, language, category, thumbnail URL and
availability) plus bounded history events. MODs share the contract but not each
other's internal storage.

## youtube-search

Provides lightweight video/music search and result lists. The functional goal is
a small music-oriented browser inspired by music.youtube.com, not a clone. The
first version avoids autoplay, heavy artwork caching, infinite scrolling and
background recommendation requests.

## youtube-history

Stores a bounded local history of search terms, selected results and replacement
choices. It derives simple user preference counters for video versus music,
language, artist and music category. No cloud profile is required.

## youtube-recovery

When a stored video is unavailable, search by its original title and present
replacement candidates for explicit user selection. If the first search has no
useful match, run a second-stage query using available artist, language or music
category signals. Replacements never happen silently.

## youtube-similar

Adds a per-video action that presents a bounded, ranked set of similar video or
music candidates. Candidate generation uses title, artist, language and category
signals plus local history preferences. Results are user-triggered and do not
continuously fetch recommendations.

## Delivery order

1. Shared contract and `youtube-search`.
2. Bounded `youtube-history` and preference counters.
3. Explicit `youtube-recovery` replacement workflow.
4. User-triggered `youtube-similar` ranked result list.
5. Later UI polish and richer recommendation signals if requested.

## Implemented baseline

The shared discovery contract and the first `youtube-search` MOD baseline are
implemented. Search runs in the isolated MOD subprocess, returns bounded results
with small thumbnails, supports an explicit 30-second audio preview, can be
enabled or disabled independently, and exposes an action to add a selected
result to the existing download queue. Release integrity pins include all
bundled YouTube MODs.

The website-specific YouTube workspace now consumes the provider's opaque next-page
cursor through the trusted discovery service. **Load more** merges canonical media
identities up to 200 visible results, preserves the current selection, and keeps the
previous page intact when a later request is cancelled or fails. It does not use
infinite scrolling or issue a background request without an explicit user action.

The `youtube-history` baseline is implemented. It stores at most 500 local
search and selection events, exposes bounded recent history, and derives simple
content-type, language, artist and category counters. It is independently
enabled or disabled and does not add another main UI tab. Since 1.7.4, the
YouTube search page exposes a compact on-demand menu with local totals,
preference hints and up to eight deduplicated recent queries; opening the menu
does not start a network request.

Version 1.8 adds an explicit all/music/video search scope. The selection is
sent through the isolated provider request instead of being treated as a local
visual filter. Music hints are added only after an explicit user choice, while
recovery and similar searches retain the neutral all-results behavior.

The `youtube-recovery` baseline is implemented. It plans a title-first search,
uses artist, language and category fallback queries only when no valid primary
candidate remains, excludes the original video ID, and ranks explainable
candidates for explicit user selection. It never replaces media silently.

The `youtube-similar` baseline is implemented. It builds at most three bounded
queries, merges unique candidates, excludes the original video ID, applies
title, artist, language, category and optional local-preference weights, then
returns up to 20 ranked candidates. Search-query matches with weak localized
title overlap remain visible as labelled low-confidence fallbacks. It runs only
when explicitly requested and never enables autoplay or background
recommendations.

All built-in MOD JSON IPC now reads and writes explicit UTF-8 bytes so Chinese
queries and metadata remain correct on Windows systems using a CP950 console
code page.

Failed-download recovery metadata is now integrated with the durable queue.
Downloads created from search results retain video ID, title, artist, language
and category across restarts. Manually entered URLs retain ID, title and artist
when the user explicitly reads video information first. Failed tasks can open an
explicit recovery-candidate dialog; accepted replacements preserve priority,
output folder and segment boundaries while using the new candidate identity.
