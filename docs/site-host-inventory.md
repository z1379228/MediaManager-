# 網站與官方媒體子網域清冊

狀態：Canonical／Development 39.0.8 來源稽核（2026-07-23）

本清冊記錄 MediaManager 目前接受的**精確輸入主機名稱**。主機白名單不使用
萬用字元；名稱相似的未知子網域不會因母網域已支援而自動取得信任。實際網址仍須通過
各 provider 的路徑、查詢參數、認證資訊、連接埠與大小限制。

## 專屬網站 MOD

| 網站 | 可接受的輸入主機 | 備註 |
| --- | --- | --- |
| YouTube | `youtube.com`、`www.youtube.com`、`m.youtube.com`、`music.youtube.com`、`youtu.be`、`www.youtube-nocookie.com`、`youtubekids.com`、`www.youtubekids.com` | `youtube-nocookie` 只接受合法 embed；YouTube Kids 只接受無播放清單的 `watch?v=...`。 |
| Bilibili | `bilibili.com`、`www.bilibili.com`、`m.bilibili.com`、`space.bilibili.com`、`b23.tv`、`bilibili.tv`、`www.bilibili.tv` | 搜尋頁另限 `search.bilibili.com`；國際版只接受公開 `video`／`play` 路徑。 |
| Facebook | `facebook.com`、`www.facebook.com`、`m.facebook.com`、`web.facebook.com`、`mbasic.facebook.com`、`fb.watch` | 只接受公開影片、reel、watch 或短網址契約。 |
| MEGA | `mega.nz`、`www.mega.nz` | 只處理公開 file／folder URL；下載需使用者自行安裝 MEGAcmd。 |
| Instagram | `instagram.com`、`www.instagram.com`、`m.instagram.com` | 官方頁／匯出工作區；不自動登入或抓取 Cookie。 |
| Threads | `threads.com`、`www.threads.com`、`threads.net`、`www.threads.net` | 官方頁／匯出工作區。 |
| X / Twitter | `x.com`、`www.x.com`、`m.x.com`、`mobile.x.com`、`twitter.com`、`www.twitter.com`、`m.twitter.com`、`mobile.twitter.com` | 官方頁／匯出工作區。 |

`api.bilibili.com` 是 Bilibili 搜尋 provider 的受限外送 API 主機，不是可貼入的媒體
頁面。圖片 CDN、說明站、管理後台與 API 主機也不因出現在網路請求中而成為輸入主機。

## Generic yt-dlp 公開媒體頁

| 網站 | 可接受的輸入主機 | 2026-07-23 證據 |
| --- | --- | --- |
| Vimeo | `vimeo.com`、`www.vimeo.com`、`player.vimeo.com` | 官方嵌入文件與安裝版 extractor 契約。 |
| Dailymotion | `dailymotion.com`、`www.dailymotion.com`、`geo.dailymotion.com`、`dai.ly` | 官方 iframe 文件使用 `geo.dailymotion.com/player/...`；安裝版 extractor 可識別。 |
| SoundCloud | `soundcloud.com`、`www.soundcloud.com`、`m.soundcloud.com`、`on.soundcloud.com` | 官方 mobile／share URL 與安裝版 extractor 契約。 |
| TikTok | `tiktok.com`、`www.tiktok.com`、`m.tiktok.com`、`vm.tiktok.com`、`vt.tiktok.com` | 官方公開短網址與安裝版 extractor 契約。 |
| Twitch | `twitch.tv`、`www.twitch.tv`、`m.twitch.tv`、`clips.twitch.tv`、`player.twitch.tv`、`go.twitch.tv` | 官方 Video & Clips 文件使用 `player.twitch.tv`；舊官方 `go` 頁會保留媒體路徑導向目前站點，安裝版 extractor 可識別。 |

官方參考：

- [Vimeo 嵌入參數](https://help.vimeo.com/hc/en-us/articles/30021987305873-How-do-I-embed-parameters-to-a-Vimeo-com-URL)
- [Dailymotion iFrame (Web)](https://developers.dailymotion.com/docs/iframe-web)
- [TikTok Embed Player](https://developers.tiktok.com/doc/embed-player/)
- [Twitch Video & Clips](https://dev.twitch.tv/docs/embed/video-and-clips/)
- [YouTube Kids 網頁版可用性](https://support.google.com/youtubekids/answer/7348648)
- [Bilibili 國際版 About](https://www.bilibili.tv/about)

## 明確排除

- `player.bilibili.com`：目前安裝版專屬 Bilibili extractor 與既有 canonical URL 正規化
  不支援該嵌入 URL；不可只靠 generic fallback 擴張權限。
- `live.bilibili.com`：目前產品不支援直播工作流。
- `www.biliintl.com`：目前不是可用的 Bilibili 國際版媒體頁；不以相似名稱取得信任。
- `kids.youtube.com`：目前會導向一般 YouTube Kids 入口且不保留媒體 ID；支援的是官方
  `youtubekids.com`／`www.youtubekids.com` 精確主機。
- `youtube-nocookie.com`：根主機目前無有效 TLS hostname；只保留
  `www.youtube-nocookie.com` 的 embed 契約。
- `touch.dailymotion.com`：目前無 DNS 與 extractor 證據，不因 Dailymotion 母網域支援而加入。
- `ani.gamer.com.tw`：既有動畫瘋 provider 已退休且 unowned，不重新啟用、不繞過登入、
  Cloudflare、DRM、廣告、付費或地區限制。
- 任何拼字相似、未知、使用者資訊、非預設連接埠或非 HTTPS 的 URL。

## 同步與驗證

來源與責任如下：

1. `core/site_routing.py`：專屬網站的 exact-host 與 URL 形狀分類。
2. `mod/builtin/*/provider.json`：provider 可接受的主機。
3. `mod/builtin/*/site-matrix.json`：已宣告能力、邊界與最近證據日期。
4. `core/bootstrap/bootstrap.py`：封裝後的內建 provider 宣告。
5. `core/downloads/site_quality.py`：離線核對 generic manifest／matrix，以及專屬下載
   manifest／canonical route 主機集合一致。
6. `tests/test_site_routing.py`、`tests/test_site_mod_catalog.py`、
   `tests/test_generic_ytdlp.py`、YouTube／Bilibili／Facebook provider 測試：正向、仿冒主機、
   manifest drift 與已安裝 extractor regression。

新增主機前必須同時具備官方公開 URL 證據、安裝版 extractor／專屬 provider 支援、最小
路徑契約、rollback 與 regression。只有 CDN 或 generic extractor 可讀，不能單獨構成支援證據。
