# 同類軟體與參考模板重掃

狀態：`CANONICAL REFERENCE MATRIX / 2026-07-22 / G39-05 GOPEED OPENAPI CONTRACT / NO AUTOMATIC DEPENDENCY`

本文件只回答「哪些產品或專案仍適合作為設計模板」。它不授權複製程式碼、加入依賴、
啟動新版本、連線外部服務或繞過網站限制。任何實作都必須先在 canonical roadmap 中有可重現
缺口、failing regression、Scope、Risk、Rollback 與 Validation；僅有參考軟體具備某功能，
不構成 MediaManager 的 material delta。

## 2026-07-22 官方重掃結論

「模板類別」只描述參考方式；「本專案處置」才描述是否已吸收、延後或僅保留既有邊界。
兩者不得再混用為 roadmap 狀態。

| 參考軟體 | 官方快照（版本或文件日期） | 模板類別 | 本專案處置 | 可借鑑的安全邊界 |
|---|---|---|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp/releases/latest) | `2026.07.04` | `PRIMARY` | `MOSTLY ABSORBED / UPDATE NEEDS SEPARATE AUDIT` | provider 版本契約、輸入／輸出安全、穩定錯誤分類與更新前相容檢查；不擴張站點或限制繞過能力 |
| [Parabolic](https://github.com/NickvisionApps/Parabolic/releases/latest) | `V2026.5.0` | `PRIMARY` | `MOSTLY ABSORBED` | 有界 URL → preflight → queue、失敗狀態、總時長與啟動／設定恢復 |
| [Tartube](https://github.com/axcore/tartube/releases/latest) | stable `v2.5.231` | `PRIMARY` | `MOSTLY ABSORBED` | 本機媒體庫、archive／恢復、工作量、分頁與並行上限 |
| [HandBrake](https://handbrake.fr/news.php) | `1.11.2`（`2026-03-22`） | `PRIMARY` | `PARTLY ABSORBED / OPTIONAL CLI ONLY` | 本機視訊 preset、queue、preview、字幕／章節與硬體編碼能力工作流；不處理受保護媒體 |
| [Shutter Encoder](https://github.com/paulpacifico/shutter-encoder/releases/tag/20.2) | `v20.2`（`2026-06-28`） | `PRIMARY` | `MOSTLY ABSORBED` | render queue、preset、檔案資訊、remux／lossless 與明確 post-processing stage；只限本機媒體 |
| [FFmpeg](https://ffmpeg.org/download.html) | `8.1.2`（`2026-06-17`） | `PRIMARY ENGINE` | `EXISTING PINNED LOCAL BOUNDARY / G39-04 EXTENDED` | 影音／圖片轉檔、壓縮、修剪、合併與 filter；只依實際 build 能力顯示，不自動下載未知 Windows binary |
| [VLC](https://www.videolan.org/vlc/releases/3.0.23.html) | `3.0.23`（`2026-01-08`） | `OPTIONAL VALIDATION` | `REFERENCE ONLY / NO DEPENDENCY` | 未來只作輸出預覽與人工相容驗證模板，不作主要轉檔引擎 |
| [Format Factory](https://www.pcfreetime.com/formatfactory/) | `5.22.0.0`（`2026-03-11`） | `WORKFLOW ONLY` | `REFERENCE ONLY / NO BINARY INTEGRATION` | 分類、批次、壓縮、剪裁、合併與浮水印 UX；官方頁不足以獨立證明無捆綁、可重現建置及完整來源授權 |
| [AnyRec](https://www.anyrec.io/video-converter/) | Windows `1.0.66`（`2026-04-14`） | `WORKFLOW ONLY` | `PROPRIETARY / NO INTEGRATION` | 批次、裝置 preset、進度、壓縮、裁切、字幕與浮水印工作流；不重包、散布或複製專有資產 |
| [CloudConvert](https://cloudconvert.com/docs/getting-started/introduction) | 雲端 API（2026-07-22 文件重掃） | `EXTERNAL CLOUD BOUNDARY` | `EXCLUDED AS AUTOMATIC FALLBACK` | 只參考任務狀態與格式分類；檔案上傳、暫存、API key、額度與付費風險必須逐次揭露並另行同意 |
| [FileCentipede](https://www.filecxx.com/zh_TW/index.html) | 官網 `2.99.6`（`2024-12-06`）；[GitHub release](https://github.com/filecxx/FileCentipede/releases) 仍為 `2.82` | `WORKFLOW ONLY` | `REFERENCE ONLY / NO DEPENDENCY` | 只比較傳輸佇列、進度、輸出位置與失敗可見性；browser extension、Cookie、P2P、M3U8 與站點流程排除 |
| [Gopeed](https://github.com/GopeedLab/gopeed/releases/latest) | `v1.9.3` | `ADAPTER CONTRACT` | `G39-05 OFFICIAL OPENAPI-ALIGNED LOCAL BRIDGE / EXTERNAL INSTALL` | 只接使用者自行啟動的 localhost REST API；token 僅記憶體、explicit action、無 auto-start／remote／browser extension／搜尋／自動開埠 |
| [MEGAcmd](https://github.com/meganz/MEGAcmd/tags) | tags `2.5.2`（Win／Linux／macOS）；[UserGuide](https://github.com/meganz/MEGAcmd/blob/master/UserGuide.md) 仍標 `2.5.0` | `ADAPTER CONTRACT` | `EXISTING SCOPE ONLY / NOT A UI TEMPLATE` | 只沿用官方本機 CLI 的公開 MEGA 檔案 adapter 邊界；不從 tag／指南推論本機安裝版本 |

上述版本與日期是本輪官方頁面唯讀重掃結果，不代表已安裝、已升級或已通過 MediaManager
相容驗證。FileCentipede 官網版本與 GitHub release 不一致、MEGAcmd tags 與 UserGuide 版本不同，
因此刻意分列來源而不推定哪個是可執行檔版本。新增或更新任何依賴前仍需另做官方 release
note、授權、安全與 runtime 稽核。

## 模板分級規則

- `PRIMARY`：仍有可核對的官方維護來源；只借鑑通用架構與失敗邊界，不代表引入其程式碼或依賴。
- `WORKFLOW ONLY`：只觀察產品工作流與可見狀態，不複製 UI、資產、程式碼或專有行為。
- `ADAPTER CONTRACT`：只核對既有 adapter 的外部程序契約；不是 UI 模板，也不自動擴張 provider scope。
- `EXCLUDED IN CURRENT SCOPE`：不屬於 34.0～40.0；只有新的獨立需求、風險分析與明確授權才可重新評估。
- `HISTORICAL / RETIRED`：只保留歷史追溯；不得當成待辦、依賴來源或恢復已移除功能的理由。

## Primary active templates

目前保留六組可重用方向；參考分類不等於自動加入依賴：

1. **Provider 與安全契約：yt-dlp**
   - 版本鎖、provider capability、bounded stderr、取消與明確錯誤分類已有對應實作。
   - 更新前仍需 dependency lock、相容性 smoke 與 rollback；不得用 extractor 功能擴張網站範圍。
2. **工作流與狀態：Parabolic**
   - URL 輸入、preflight、排隊、進度、完成／失敗與重試已有共用下載佇列。
   - 「失敗任務篩選」與「清單總時長」只有在本機測試先證明現有 UI 缺口時才成為候選。
3. **媒體庫與恢復：Tartube**
   - 原子 history／archive、bounded pagination、startup recovery 與資源上限已有對應能力。
   - 不引入遠端控制、帳號同步、背景排程或網站專屬擷取。
4. **本機媒體引擎：FFmpeg**
   - 既有 Media Convert 已有影音轉檔、壓縮、修剪、佇列、取消、原子另存與 H.264
     NVENC→CPU fallback。G39-02 以 failing regression 新增 PNG／JPEG／WebP 靜態影像與
     bounded redacted stderr；這是目前唯一實作中的格式工作。
   - 後續必須以 `-version`、`-buildconf`、`-formats`、`-encoders`、`-filters`、`-hwaccels` 查證
     實際 build 能力；未量測不得宣稱 CPU／GPU 加速幅度。
5. **轉檔工作流：HandBrake + Shutter Encoder + VLC**
   - 只借鑑 preset、queue、磁碟 preflight、preview、輸出 probe 與錯誤回復；HandBrakeCLI／VLC
     若要成為選配 adapter，仍需獨立授權、版本、雜湊、GPL 邊界與 rollback 審查。
6. **本機外部傳輸：Gopeed**
   - 只使用 localhost `/api/v1` contract 管理使用者明確建立的工作；MediaManager 不啟動、安裝或
     遠端控制 Gopeed，也不保存 API token。
   - P2P 只接受使用者提供的 magnet／ed2k，另有合法用途、上傳行為、容量及路徑 Gate；browser
     extension、內建 torrent 搜尋、自動開埠與遠端 dashboard 不在 scope。

## Workflow-only references

Stacher、4K Video Downloader Plus、MediaHuman、MusicBee、JDownloader、iTubeGo、iDownerGo 與
TopClipper 是未在本輪逐一驗證版本的既有工作流觀察，不列入「目前官方模板」。Format Factory、
AnyRec 與 FileCentipede 已依使用者指定重新核對，但仍只作 workflow reference。這些產品可比較文案、佇列、失敗回復、
輸出位置與可見狀態，但不是程式碼或依賴來源。專有授權、維護現況不足或包含瀏覽器／站點
專屬能力時，只保留產品工作流觀察，不推論其內部實作，也不複製其 UI 或資產。

## Historical / retired

- [miyouzi/aniGamerPlus](https://github.com/miyouzi/aniGamerPlus/releases/latest) 與
  [BoringMan314/aniGamerPlus](https://github.com/BoringMan314/aniGamerPlus)、動畫瘋相關
  FileCentipede／TopClipper 流程及先前 AniGamer 專屬比較，
  自 38.1.15 起只保留為 38.1.0～38.1.14 歷史證據；不得重新註冊 MOD 或接到通用 adapter。
- MegaDownloader 為舊版歷史參考；目前公開 MEGA 工作只以官方 MEGAcmd adapter 邊界為準。
- 已被本專案吸收且沒有新 failing regression 的命名、queue、retry、history、hash、log rotation、
  archive 與 bounded concurrency 項目標記 `ABSORBED / NO RELEASE`，不重複規劃。

## Excluded / deferred

- P2P 搜尋、tracker 探索、browser extension、自動開埠、遠端 dashboard、雲端帳號、自動排程與遠端控制；
  G39-04 只允許使用者明確提供 magnet／ed2k 並交給已設定的 localhost Gopeed。
- 瀏覽器 Cookie／profile 匯入、Cloudflare／登入／代理／地區規避、DRM、付費、廣告跳過或移除。
- 播放串流攔截、瀏覽器／WebView cache、M3U8、金鑰、分段、解密與播放中媒體保存。
- 把已知網站頁面、登入頁、manifest 或媒體頁轉送至通用下載器。詳見
  [Direct HTTP 安全邊界](direct-http-boundary.md)。

## G39-02 已證明缺口與後續候選

G39-02 已以 `image-png` unsupported 與舊 `_run()` 無失敗診斷取得 RED `4 failed`，因此不再是
「只有參考產品具備」的推測性工作。第一工作包只加入本機靜態影像與安全診斷；文件、光碟、
浮水印、完整 GPU capability probe、輸出 probe、磁碟 preflight、持久佇列及 MP4 fast-start
仍各自維持 evidence-gated：

- **文件**：需獨立、預設停用的本機 adapter，先處理 macro、sandbox、文件炸彈、授權與格式保真；
  CloudConvert 不得成為自動 fallback。
- **DVD／CD**：只允許使用者持有且未受保護的媒體；CSS、AACS、區碼、DRM 或其他保護繞過排除。
- **浮水印**：先評估使用者選取的本機圖像 overlay；文字浮水印需額外處理字型與 filter escaping。
- **CPU／GPU**：必須先探測實際 encoder／filter／hwaccel 並保留 CPU fallback，再用固定 workload
  量測；不能從產品宣傳推論速度或穩定性。
- **技術支援與穩定性**：G39-02 已保存 bounded redacted stderr；輸出 ffprobe、磁碟 preflight、
  結構化進度與可恢復 queue 仍需獨立 regression。

## 更新後執行計畫

| Priority | 工作 | 狀態／下一步 |
|---:|---|---|
| P0 | G39-02 第一工作包 | `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`：Development 39.0.0 已完成 PNG／JPEG／WebP、來源／protocol Gate、UI／automation wiring 與 bounded redacted FFmpeg stderr |
| P1 | G39 後續能力 | capability／ffprobe／disk preflight 優先；浮水印、文件與未受保護光碟各自需要獨立 evidence gate，不平行啟動 |
| P2 | G40-01 Development Exit Gate | 保持 `WAITING / AUTHORIZATION + STAGED VERIFY/HEADLESS SAFE_MODE EVIDENCE REQUIRED`；不得由模板或 G39 source-only 變更自動啟動 |

canonical Gate、授權與停止條件以
[Development 34.0～40.0 主計畫](roadmap-development-34.0-40.0.md) 為準。

## 本輪驗證

- RED `4 failed`；conversion／bootstrap／catalog GREEN `26 passed`，包含本機 FFmpeg 8.1.2
  BMP→PNG 實際 smoke；targeted Ruff 與 JSON parse 通過。
- 完整 runner `1222 passed, 7 skipped`；最終 conversion security 組 `21 passed, 1 skipped`。
  Ruff／文字 `357 / 552`、MOD `7 / 4`、網站 `12 / 33 / 49`、依賴鎖 `10`、版本文件 `4`、
  保留版本 `5`、Repository 外 compileall、SAFE_MODE verify-only 與 diff check 均通過。

## 計畫決策

本輪重掃先確認多數通用工作流已吸收，但 `image-png` 與 FFmpeg 失敗診斷出現可重現、可回退的
material gap，因此結論更新為 `REFERENCE REFRESHED / G39-02 SOURCE VALIDATED / NO EXTERNAL BINARY`。
表中的 `PRIMARY`、`WORKFLOW ONLY` 與 `ADAPTER CONTRACT` 只是參考分類，不代表 roadmap 的
`ACTIVE` 工作。38.1.15 的 material delta 來自使用者決定移除動畫瘋 MOD，而不是參考軟體新增功能。
G39-01 固定 workload baseline 仍維持 `MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE`；
Development 39.0.0 只代表 G39-02 的實質加法功能，不是推測性最佳化。Format Factory／AnyRec 不被
整合，CloudConvert 不作 fallback；不建立重複計畫或未經證據的功能。
