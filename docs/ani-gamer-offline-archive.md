# AniGamer offline archive compatibility

This note records the safe interoperability boundary for AniGamerPlus-style
offline output. The reference workflow produces a playable video together
with a subtitle sidecar (commonly `.ass`); MediaManager can now preserve that
pair when the user already owns the files.

## Supported workflow

1. Use the AniGamer workspace to select one official title and one episode.
2. Choose **Import Video + Subtitles**.
3. Select one local video and any matching subtitle sidecars (`.ass`, `.srt`,
   `.ssa`, `.sub`, `.ttml`, `.vtt`, or `.xml`).
4. MediaManager copies the video to `media/` and subtitles to `subtitles/` in
   the selected episode archive. `episode.json` records relative paths,
   byte sizes, source names, and SHA-256 digests.
5. **Verify Archive Integrity** checks every linked file without starting a
   provider or scanning the whole downloads directory.

The archive is intentionally a sidecar layout rather than a remuxed file.
This keeps subtitle selection reversible and allows an external player to
choose the appropriate language. A subtitle-only archive is accepted for
metadata workflows, while a normal playback archive should contain both a
video and at least one subtitle sidecar.

## Security boundary

The reference article describes cookie-assisted quality/access and FFmpeg
processing. MediaManager does not import browser cookies, bypass Cloudflare,
DRM, login, payment, region, or advertisements, and does not resolve or
download AniGamer streams. The import operation only copies files explicitly
selected by the user, rejects symlinks and unsupported types, applies bounded
size limits, writes atomically, and verifies SHA-256 on demand.

Reference: [AniGamerPlus 使用教學](https://ivonblog.com/posts/anigamerplus-docker/)

