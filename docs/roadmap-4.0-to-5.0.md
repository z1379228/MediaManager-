# MediaManager 4.0～5.0 權威版本配置

本文件是 4.0 之後的歷史版本排序與取捨依據。`release-4.0-5.0.md` 記錄已完成結果，
`roadmap-5.0.md` 只保留 5.0 放行門檻；舊版提案不再反向改寫目前進度。

## 版本原則

- `4.0.0` 是目前公開的未簽署工程基線；4.0.x 僅處理錯誤、安全、CI 與相容性，
  不把既有附件重新描述成已完成正式信任鏈。
- 4.1～4.5 是可驗收的開發里程碑，不要求重複上傳大型 EXE；完成時提供中文
  更新說明，正式完整附件集中在 `5.0.0`。
- 已公開的 `v4.0.0` tag 與附件不可覆寫。若 4.0.x 修正必須公開，使用新的
  patch tag／Release；本機 `Version/4.0` 可依 current 規則換成最新版，舊附件
  仍由 GitHub Releases 保存。
- 任何里程碑只有在程式、測試、文件與版本資訊一致時才調整版本號。規劃文件
  先寫 4.1，不代表 `CORE_VERSION` 已經是 4.1.0。
- 4.x 維持 Search/Download v2 相容。需要破壞性調整時只能新增版本化合約，
  並在 5.0 提供明確遷移期，不直接改寫既有 v2 行為。
- 本機只保留 current + previous；更舊完整附件保留於 GitHub Releases。日常
  稽核目前版與上一版，重大發布、資安事件或定期維護才做完整歷史稽核。

## 版本配置

| 版本 | 狀態 | 核心範圍 | 完成門檻 |
| --- | --- | --- | --- |
| 4.0.0 | 現行基線 | 搜尋／下載能力 v2 schema、聯合搜尋後端、部分能力協商、重試決策元件與資源上限 | 以 `release-4.0-5.0.md` 為準，不把未接入 UI／佇列的元件算成完成 |
| 4.0.x | 維護中 | CI、自動合併、雜湊與行尾一致性、UI／測試穩定、4.0 staged 附件重建與文件校正 | 不改合約語意；Ruff、完整 Pytest、必要 CI 與 release preflight 綠燈 |
| 4.1.0 | 已完成 | 來源選擇與健康狀態、跨 MOD 結果頁、本機別名／拼字容錯、排序原因 | 不增加背景搜尋；失敗來源可見且不拖垮其他來源；詳見 `release-4.0-5.0.md` |
| 4.2.0 | 已完成 | 實際格式與容量摘要、多檔選擇／優先級、命名預覽、個別失敗重跑 | 提交前可確認；重啟可復原；不覆蓋既有檔案；詳見 `release-4.0-5.0.md` |
| 4.3.0 | 已完成 | Search/Download Adapter SDK、範例、合約測試器、相容報告、依賴宣告 | 第三方 MOD 可離線驗證；逾時或崩潰不凍結核心 UI；詳見 `release-4.0-5.0.md` |
| 4.4.0 | 已完成 | 強化 YouTube、Bilibili 回歸矩陣；MEGA 僅走官方 SDK／MEGAcmd 候選路徑 | 每個網站獨立 MOD；未經實測不得宣稱完整支援；詳見 `release-4.0-5.0.md` |
| 4.5.0 | 工程完成／發布阻擋 | 遷移、效能、診斷去識別、鎖定依賴、授權清冊、SBOM、簽署與 copied-folder smoke | copied-folder 通過；缺 production Ed25519／Authenticode，僅可作為 SAFE_MODE Preview；詳見 `release-4.0-5.0.md` |
| 5.0.0 | Preview 工程版 | 搜尋、MOD 適配與下載流程形成穩定可擴充產品面 | 工程門檻完成後可建置 Preview；production stable 仍須通過 `roadmap-5.0.md` 的正式雙簽章放行門檻 |

## 優化優先順序

### P0：現在先做

1. **版本與文件一致性。** `core/version.py`、`pyproject.toml`、README、wheel、
   `release-info.json`、版本資料夾與 Git tag 必須一致，並由測試阻止漂移。
   顯示版本之外另規劃 `development`、`preview`、`stable` build channel；未完成
   正式信任鏈的建置不得顯示為 stable。
2. **先補 4.0 接線缺口。** 將聯合搜尋接入 UI；在下載送出時落實播放清單、
   批次上限與續傳能力；將有界重試決策接入佇列並保留人工停止權。
3. **修正網站能力聲明。** `generic-ytdlp` 不得宣告 Facebook、Instagram 或
   Threads 自動下載能力；它們在完成獨立驗證前只保留官方頁面入口。
4. **搜尋結果可判讀。** 每筆結果維持縮圖、標題、作者、時長、來源及媒體類型；
   排序、相似與替代候選顯示原因，不建立黑箱推薦模型。
5. **下載前資訊完整。** 分析後只顯示實際可用格式、音軌、字幕、彈幕、估算容量
   及輸出名稱；批量工作先預覽再送出。
6. **故障隔離。** MOD 個別逾時、熔斷、資源配額、錯誤分類與重試，不讓單一
   外部工具造成全白畫面、無限等待或整體停擺。

### P1：4.x 內完成

1. 讓 YouTube 搜尋、歷史、相似、替代、播放器與自動切割繼續維持分離 MOD，
   共用版本化資料合約與有界快取。
2. 完成第三方 MOD 開發範例、安裝／停用／更新／回退流程與相容性報告。
3. MEGA 先完成公開分享連結的官方工具適配評估，不接收帳密、工作階段或繞過
   傳輸配額；Facebook、Instagram、Threads 保持官方入口邊界。
4. 建立可重複的網站 smoke matrix；離線合約測試與公開內容 live smoke 分開記錄。

### P2：5.0 後再評估

- MOD manifest／UI 新增固定語言區塊，只接受英文 `en`、日文 `ja`、簡體中文
  `zh-CN` 與繁體中文 `zh-TW`。這四種是永久上限，後續不再增加其他介面語言。
- BitTorrent、Magnet、ed2k 或 Gopeed／qBittorrent 外部控制整合。若加入，必須
  是另一個預設停用的傳輸 MOD，明示上傳／做種、連接埠、頻寬與儲存成本。
- 雲端帳號同步、上傳、WebDAV、遠端管理與跨裝置控制。
- 排程訂閱、RSS、自動推薦及更多媒體庫智慧分類。
- 公開圖片集／相簿下載、逐字稿與字幕全文搜尋、跨站鏡像來源群組，以及可選的
  aria2 類直接傳輸工作流。這些只保留為 5.0 穩定後的獨立 MOD 候選，不是
  4.x 或 5.0 的發布阻擋條件。

語言區塊只管理 MOD 名稱、說明、設定與錯誤訊息等介面文字，不限制媒體內容、
字幕、搜尋條件或來源語言。5.0 以前不修改現有 manifest schema；5.0 穩定後才以
新的版本化欄位加入，未知語言代碼必須 fail-closed，不使用任意外部翻譯服務。

## 功能刪減與禁止範圍

- 不重做完整 `music.youtube.com`；只保留低資源搜尋、歷史、相似與替代功能。
- 不在核心加入內建瀏覽器、任意下載前後腳本或所有 yt-dlp 網站開關。
- 不加入廣告、遙測、付費牆、強制帳號、背景自動播放或大型常駐圖片快取。
- 不把 MegaDownloader、iTubeGo、BitComet、uTorrent、qBittorrent、Vuze、
  Deluge 或 Gopeed 當相依套件；它們只提供工作流參考。
- 不處理 DRM、付費、私人、登入、地區或網站廣告限制的規避流程。

## 發行與資料夾配置

| 項目 | 規則 |
| --- | --- |
| 來源版本 | `core/version.py` 與 `pyproject.toml` 必須相同 |
| 本機封裝 | `Version/<major>.<minor>`，只保留 current + previous |
| 次版本 | 中文更新說明為主，不重複發布大型附件 |
| 大版本 | GitHub Releases 保留 EXE、wheel、`SHA256SUMS.txt`、`release-info.json` |
| PR | 必須通過 Ruff 與 Pytest，使用 Squash auto-merge，不直接推送 main |
| 簽署 | 正式 5.0 必須同時具備 Ed25519 release manifest 與 Authenticode；缺一只能標示 SAFE_MODE Preview。未簽署 4.0 是歷史工程基線，不作為先例 |
| 授權與 SBOM | 4.5 前補齊專案 `LICENSE`、鎖定建置依賴，並把 dependency inventory／SBOM 納入 staged checksum |
| smoke | 只測試版本資料夾的拷貝，不在保留的原始資料夾產生 `UserData` |

## 每個版本的完成定義

1. 範圍內功能與安全邊界有文件及對應測試。
2. Ruff、完整 Pytest、版本一致性、built-in MOD 雜湊與 current + previous 稽核通過。
3. UI 在預設、精簡與大字模式均無全白頁、破圖、阻塞提示或無法停止的預覽。
4. 新增網站有獨立能力聲明、依賴提示、錯誤分類與離線／live 驗證紀錄。
5. 大版本 copied-folder 啟動、`--version`、`--verify-only`、回退與簽署 preflight
   全部通過，且沒有殘留程序或暫存資料。
