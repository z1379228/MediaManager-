# youtube-auto-split v1 MOD

Status: complete in the Version 1.0 development artifact. The versioned
split-plan contract, safe filename formatter, metadata and bounded FFmpeg
detectors, low-bitrate preview, trusted boundary editor and atomic audio-only
queue expansion are implemented. The rebuilt artifact passed full regression,
checksum, unified-entrypoint and GUI smoke verification.

## Goal

Handle long compilation videos such as 作業用 BGM, study mixes, album uploads,
or multi-song collections. The feature remains outside the core queue as an
independently maintainable `youtube-auto-split` MOD. It produces ordinary,
explicit segment requests only after user confirmation.

## Stage 1: composite detection

A long duration makes a video a candidate, but never proves that it contains
multiple tracks. Detection uses bounded signals in this order:

1. Existing chapter metadata supplied by the source.
2. Timestamps and track names parsed from the title or description.
3. Audio boundary candidates based on sustained low energy or silence.
4. Optional change-point hints such as abrupt energy or spectral changes.

The result contains proposed boundaries, confidence, signal source and warnings.
Continuous DJ mixes, crossfades, live recordings and speech may have no reliable
audio gap. Low-confidence results must remain unsplit by default.

## Stage 2: user-confirmed audio preview

When multiple-track composition is likely, ask whether to prepare a split.
Create temporary low-bitrate audio previews instead of downloading every final
segment immediately. The confirmation UI must allow the user to:

- play each proposed segment and short audio around every cut;
- move a boundary, merge adjacent segments, add a cut or remove a cut;
- edit a detected track name;
- cancel without changing the original download;
- explicitly confirm before final segment tasks enter the queue.

Preview files are bounded temporary data and are removed after confirmation or
cancellation. No automatic silent replacement or irreversible cutting is
allowed.

## Stage 3: queue expansion and filename template

A confirmed plan becomes one atomic batch of ordinary segment requests. The
initial filename template is:

```text
{source-title}-{index:02d}-{track-title-or-unnamed}-{start}-{duration}.{ext}
```

Example:

```text
作業用BGMxxxxxx-01-曲名-00m00s-03m42s.m4a
作業用BGMxxxxxx-02-未命名-03m42s-04m18s.m4a
```

Unsafe filesystem characters are replaced, repeated whitespace is collapsed,
and path length is bounded. The v1 confirmed-split default is audio-only AAC in
an M4A container; ordinary unsplit downloads continue to use their selected
download preset.

## Resource and safety limits

- Analysis is user-triggered and never runs continuously in the background.
- Prefer chapters and description timestamps before decoding audio.
- Analyze a downsampled mono audio stream and bound duration, memory and process
  time.
- Never claim audio-only detection is certain.
- Preserve the original URL, title, boundaries and detection evidence in the
  draft so the result is reproducible and editable.
- Reuse the durable duplicate archive; each confirmed segment has independent
  start/end identity.

## Proposed delivery order

1. Versioned split-plan contract and filename sanitizer. **Complete.**
2. Chapter/description timestamp detector. **Complete.**
3. Bounded FFmpeg audio boundary analyzer. **Complete.**
4. Audio preview and boundary editor UI. **Complete.**
5. Atomic queue expansion, retry and cleanup tests. **Complete.**
