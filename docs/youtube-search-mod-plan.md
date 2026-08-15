# YouTube 搜尋 MOD 強化計畫

狀態：Canonical／Development 39.0.92；不對應新的 Testing／Stable 發行授權。

## Goal

讓公開 YouTube／YouTube Music 搜尋在不依賴登入、Cookie 或網站限制規避的前提
下保持可預期、可分頁、可隔離失敗，並保留第三方作者另行提供進階搜尋 MOD 的
擴充點。

成功條件：單一不完整 metadata 不會使整頁失敗；預設路徑不要求 API key；進階
方案不改變既有 Search v2 契約或內建 MOD 信任邊界。

## Scope

包含：公開搜尋、搜尋結果契約正規化、內容類型 capability、游標、排序／篩選、
相似音樂查詢，以及可選外部搜尋 adapter 的設計。

不包含：下載邏輯、登入、Cookie 匯入、廣告／地區／Cloudflare 規避、DRM、付費
內容、私有資料或背景收集。MediaManager 不保存 API key，也不將它寫入 Log、
manifest 或 Repository。

## Verified baseline

- 內建 `youtube-search` 對 `all`／`video` 使用 yt-dlp 的 bounded `ytsearch`，
  對 `music` 使用 YouTube Music `#songs` extractor；兩者皆為 flat extraction，
  最多 200 筆工作區結果、單頁最多 50 筆。
- 可信 UI 已提供本機片長、語言、內容類型、provider 與相關性篩選，並有獨立
  `youtube-similar` 查詢規劃。
- yt-dlp 的 flat extraction 可能省略完整 metadata，因此所有回傳欄位都必須在
  MOD／契約邊界驗證，而不能假設與完整影片解析相同。
- YouTube Data API `search.list` 可提供官方結構化搜尋與篩選，但需要使用者自己
  的 API 專案／憑證並受配額與官方政策約束，屬於不同部署條件。

參考：[yt-dlp README](https://github.com/yt-dlp/yt-dlp/blob/master/README.md)、
[YouTube Data API `search.list`](https://developers.google.com/youtube/v3/docs/search/list)。

## Priority and approach

| Priority | 方案 | 決策與理由 |
| --- | --- | --- |
| P0 | 強化既有 yt-dlp 內建 MOD | 採用。39.0.91 隔離不可信片長；39.0.92 將顯式 music scope 路由到 YouTube Music songs extractor。 |
| P1 | 第三方 `youtube-data-api-search` adapter | 可選設計。預設不安裝、不啟用；使用者在外部 MOD 自己的安全設定提供 API key，並明列 quota／錯誤狀態。 |
| P2 | 網頁抓取或存取限制規避 | 不採用。容易與網站政策、登入、廣告或 Cloudflare 邊界耦合，也不可作為搜尋可靠性的 fallback。 |

若實作 P1，manifest 必須使用 schema v2、runtime protocol 1.0，只宣告
`search` 與必要網路 capability；回傳仍經 `DiscoveryItemV1`／Search v2 驗證。
官方 API 的 `playlist`／`live` 等能力只有在 adapter 實際支援並通過 contract test
後才宣告，不擴大目前 yt-dlp MOD 的 capability。

## Dependencies and compatibility

- P0 沿用鎖定的 yt-dlp、JavaScript runtime 與現有 Search v2，沒有新依賴。
- P1 需要第三方 MOD 作者、使用者自己的 API key 與官方 API quota；核心只提供
  adapter host，不取得或代理憑證。
- 所有結果維持 additive contract；既有顯示、歷史、相似搜尋與下載選取流程不變。
- Testing 1.2.1／1.2.2 與已發布附件不可回寫。

## Risk and rollback

- metadata 正規化過嚴可能把可用片長降為未知；UI 必須保留未知片長結果，而不是
  丟棄整筆。Rollback 是還原對應 helper、pinned hash、測試與版本文件。
- YouTube Music songs extractor 若在未來 yt-dlp 版本改變，失敗必須維持明確的
  provider error；不得靜默退回一般搜尋並把非歌曲結果宣稱為 music scope。
- 官方 API 方案可能遇到 quota、金鑰權限、政策或欄位差異；因此只能是明確啟用的
  外部 MOD，不得成為預設搜尋的隱性必要條件。
- provider 失敗維持來源級隔離，不以無限重試或另一條未授權網路路徑掩蓋錯誤。

## Validation

- Fake yt-dlp regression 覆蓋有效小數、`NaN`、布林、負值與超界片長，並逐筆以
  `DiscoveryItemV1.from_dict()` 驗證。
- Fake yt-dlp 路由 regression 驗證 `music.youtube.com/search#songs`、原查詢 URL
  round-trip、`playlistend` 與結果分類；`all`／`video` 仍驗證 bounded `ytsearch`。
- 執行 YouTube MOD matrix、search scope、subprocess provider 與 UI 非互動測試。
- 執行 repository runner、Ruff／文字污染、MOD／網站／依賴／版本稽核、隔離
  `compileall` 與 `git diff --check`。
- P1 若日後實作，必須以 fake HTTP contract test 覆蓋 quota、401／403、timeout、
  空頁、未知欄位、分頁 token 與取消；不得用 production 憑證作自動測試。
