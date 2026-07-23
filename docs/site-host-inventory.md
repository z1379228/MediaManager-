# 網站與官方媒體子網域清冊

狀態：Canonical／Development 39.0.10 最終來源完整性稽核（2026-07-23）

本清冊記錄 MediaManager 目前接受的**精確輸入主機名稱**。白名單不使用
萬用字元；未知子網域不會因母網域已支援而自動取得信任。網址還必須通過各
provider 的 HTTPS、路徑、查詢參數、使用者資訊、連接埠與大小限制。

## 專屬網站 MOD

| 網站 | 可接受的精確輸入主機 | 最小契約 |
| --- | --- | --- |
| YouTube | `youtube.com`、`www.youtube.com`、`m.youtube.com`、`music.youtube.com`、`youtu.be`、`www.youtube-nocookie.com`、`youtubekids.com`、`www.youtubekids.com` | `youtube-nocookie` 只接受 `/embed/<id>`；YouTube Kids 只接受無播放清單的 `/watch?v=...`。 |
| Bilibili | `bilibili.com`、`www.bilibili.com`、`m.bilibili.com`、`space.bilibili.com`、`player.bilibili.com`、`b23.tv`、`bilibili.tv`、`www.bilibili.tv` | `player.bilibili.com` 只接受目前安裝版 extractor 可處理的 HTTPS `/player.html?aid=<正整數>`，以及經驗證的可選官方參數。 |
| Bilibili 搜尋 | `search.bilibili.com` | 只接受 `/all?keyword=<單一非空值>`；不是下載主機。 |
| Facebook | `facebook.com`、`www.facebook.com`、`m.facebook.com`、`web.facebook.com`、`mbasic.facebook.com`、`fb.watch` | 只接受公開影片、reel、watch 或短網址契約。 |
| MEGA | `mega.nz`、`www.mega.nz` | 只處理公開 file／folder URL；下載需使用者自行安裝 MEGAcmd。 |
| Instagram | `instagram.com`、`www.instagram.com`、`m.instagram.com` | 官方頁／匯出工作區；不自動登入或抓取 Cookie。 |
| Threads | `threads.com`、`www.threads.com`、`threads.net`、`www.threads.net` | 官方頁／匯出工作區。 |
| X / Twitter | `x.com`、`www.x.com`、`m.x.com`、`mobile.x.com`、`twitter.com`、`www.twitter.com`、`m.twitter.com`、`mobile.twitter.com` | 官方頁／匯出工作區。 |

## Generic yt-dlp 公開媒體頁

| 網站 | 可接受的精確輸入主機 | 證據與契約 |
| --- | --- | --- |
| Vimeo | `vimeo.com`、`www.vimeo.com`、`player.vimeo.com` | 官方嵌入文件與安裝版 extractor。 |
| Dailymotion | `dailymotion.com`、`www.dailymotion.com`、`geo.dailymotion.com`、`dai.ly` | 官方 iframe 使用 `geo.dailymotion.com/player/...`；安裝版 extractor 可識別。 |
| SoundCloud | `soundcloud.com`、`www.soundcloud.com`、`m.soundcloud.com`、`on.soundcloud.com`、`w.soundcloud.com` | 官方 Widget 使用 `w.soundcloud.com/player/`；只接受單一 `url=`，其內層目標必須是精確 SoundCloud／`api.soundcloud.com` HTTPS 媒體 URL。 |
| TikTok | `tiktok.com`、`www.tiktok.com`、`m.tiktok.com`、`vm.tiktok.com`、`vt.tiktok.com` | 官方公開媒體／短網址與安裝版 extractor。 |
| Twitch | `twitch.tv`、`www.twitch.tv`、`m.twitch.tv`、`clips.twitch.tv`、`player.twitch.tv`、`go.twitch.tv` | 官方 Video & Clips 文件確認 player／clips；安裝版 extractor 可識別清冊內主機。 |

Direct HTTP 是另一個受限 adapter：它只接受使用者明確提供、通過 SSRF／副檔名／
容量政策且不屬於網站 MOD 的直接 HTTPS 檔案 URL。它不是任意網站解析 fallback，
也不會讓未知子網域繼承上表的網站權限。

## 程式會連線但不可貼入的主機

下列項目已納入程式碼掃描；其存在不會使它成為媒體輸入主機：

| 主機或後綴 | 用途與限制 |
| --- | --- |
| `api.bilibili.com` | Bilibili 搜尋／公開 metadata API 的固定外送目標。 |
| `*.hdslb.com` | Bilibili provider／可信縮圖載入器的 HTTPS 圖片 CDN 後綴；只消費 provider 回傳的有限圖片 URL。 |
| `i.ytimg.com`、`img.youtube.com` | YouTube 縮圖。 |
| `*.fbcdn.net` | Facebook provider 回傳的 HTTPS 縮圖。 |
| `*.bahamut.com.tw` | 既有可信縮圖載入器後綴；動畫瘋工作流已退休，不能作為媒體路由。 |
| `api.soundcloud.com` | 只可作為 `w.soundcloud.com/player/` 的單一內層 `url` 目標，不是頂層 generic 輸入。 |
| `mega.io`、`help.x.com`、Facebook／Instagram help URL、GitHub dependency URL | 由使用者明確按下按鈕才開啟的首頁、說明或安裝文件，不是解析／下載主機。 |
| `127.0.0.1` | 使用者自行啟動之 Gopeed REST API；loopback-only，不是公網網站支援。 |

## 已確認存在但未納入

- `player.bilibili.com` 的 `bvid`／`episodeId` 官方形式存在，但目前安裝版
  `BiliBiliPlayer` extractor 只匹配 `aid`；因此不以文件證據取代實際 extractor
  能力，也不退回 generic fallback。
- `t.bilibili.com` 的動態貼文 extractor 存在，但不是目前已定義的媒體輸入工作流。
- `live.bilibili.com`：目前產品沒有直播工作流。
- `www.biliintl.com`：不以相似名稱取得 Bilibili 國際版權限。
- `player.soundcloud.com`、`p.soundcloud.com`：安裝版 extractor 保留舊匹配式，
  但目前官方 Widget 文件只證明 `w.soundcloud.com`。
- `touch.dailymotion.com`：安裝版 extractor 的廣泛匹配不足以構成目前官方 URL 證據。
- `kids.youtube.com`：不保留媒體 ID；只信任官方
  `youtubekids.com`／`www.youtubekids.com`。
- `youtube-nocookie.com`：只信任文件所用的 `www.youtube-nocookie.com`。
- `ani.gamer.com.tw`：動畫瘋 provider 已退休且 unowned；不重新啟用、不轉送至
  generic／Direct HTTP，也不繞過登入、Cloudflare、DRM、廣告、付費或地區限制。
- 任何拼字相似、未知、帶使用者資訊、非預設連接埠或非 HTTPS 的 URL。

## 官方證據

- [Bilibili 站外播放器使用文件](https://player.bilibili.com/player/?bvid=1Xm421579d)
- [SoundCloud Widget API](https://developers.soundcloud.com/docs/api/html5-widget)
- [Vimeo 嵌入參數](https://help.vimeo.com/hc/en-us/articles/30021987305873-How-do-I-embed-parameters-to-a-Vimeo-com-URL)
- [Dailymotion iFrame (Web)](https://developers.dailymotion.com/docs/iframe-web)
- [TikTok Embed Player](https://developers.tiktok.com/doc/embed-player/)
- [Twitch Video & Clips](https://dev.twitch.tv/docs/embed/video-and-clips/)
- [YouTube Kids 網頁版可用性](https://support.google.com/youtubekids/answer/7348648)
- [Bilibili 國際版 About](https://www.bilibili.tv/about)

## 同步與驗證

1. `core/site_routing.py`：專屬網站 exact-host 與 URL 形狀分類。
2. `mod/builtin/*/provider.json`：provider 可接受的精確主機。
3. `mod/builtin/*/site-matrix.json`：能力、邊界與最近證據日期。
4. `core/bootstrap/bootstrap.py`：封裝後內建 provider 宣告。
5. `core/downloads/builtin_integrity.py`：本輪 manifest／matrix SHA-256。
6. `core/downloads/site_quality.py`：generic manifest／matrix 與專屬
   manifest／canonical route 集合離線一致性。
7. `tests/test_site_routing.py`、`tests/test_generic_ytdlp.py`、各專屬 provider
   測試：正向、仿冒主機、歧義查詢、manifest drift、integrity pin 與安裝版
   extractor regression。

新增主機前必須同時具備官方公開 URL、安裝版 extractor／專屬 provider、最小
路徑契約、rollback 與 regression。只有 DNS、CDN 或 generic extractor 可讀，
不能單獨構成支援證據。
