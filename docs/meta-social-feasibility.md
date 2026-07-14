# Facebook and Instagram feasibility review

Review date: 2026-07-14
Release decision: MediaManager 1.7.2 provides official-page and official-export
bridges only. It does not enable a Facebook or Instagram download provider.

## Evidence

- The [Meta Terms of Service](https://www.facebook.com/terms) prohibit access
  or collection from Meta products by automated means without prior permission
  and prohibit attempts to access data without permission.
- Meta's [automated data collection terms](https://www.facebook.com/legal/automated_data_collection_terms)
  define scraping, bots, crawlers and other programmatic retrieval mechanisms
  as automated data collection subject to Meta permission.
- Meta explains that users retain rights to content they create and provides an
  official [Facebook Page data download](https://www.facebook.com/help/www/466076673571942)
  workflow. Instagram also has an official
  [information download help page](https://www.facebook.com/help/instagram/181231772500920),
  which may require the user to sign in on Meta's own site.
- The official [yt-dlp repository](https://github.com/yt-dlp/yt-dlp) and the
  locally installed 2026.7.4 extractor list confirm Facebook and Instagram
  extractor code exists. The local list also marks `instagram:user` as
  currently broken, demonstrating that extractor presence is not a stable
  support guarantee.

## Delivered scope

Facebook and Instagram stay excluded from `generic-ytdlp`. The candidate MOD
page supplies a shared, compact official-site bridge:

- Facebook accepts the HTTPS homepage, canonical `watch` or `video.php` URLs
  with a numeric video id, numeric Reel URLs and bounded Page video paths.
- Instagram accepts the HTTPS homepage and canonical post, Reel or IGTV paths
  with a bounded shortcode.
- Both canonicalize to the official `www` host and reject HTTP, credentials,
  explicit ports, fragments, lookalike hosts, open-redirect paths, tracking
  parameters and unrelated pages.
- An explicit button opens Meta's official data-export help. MediaManager never
  receives the user's Meta password, browser cookies or exported archive.
- No network request occurs before the user clicks a button. Media playback,
  sign-in and data export remain in the system browser on Meta's official site.

## Explicit exclusions

MediaManager does not scrape profiles, feeds, comments, stories or private
content; import cookies or sessions; automate sign-in; resolve private media
URLs; bypass rate, region or access controls; or download third-party Facebook
and Instagram media.

Download support can be reconsidered only after documented Meta permission or
an official API/licence allows the intended third-party download workflow. A
maintained extractor and public test content would still be required afterward.
