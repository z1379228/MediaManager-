# MediaManager

平台無關的桌面媒體管理器。平台功能將由受隔離、具最小權限的 MOD 提供；核心負責安全、工作、儲存、網路與憑證代理。

目前來源版本為開發版 16.1（核心相容版本 16.1.0）；最新完整 Development 成品仍為
`Version/Development/16.0`，既有 15.0 未被覆寫。16.0 的 Ruff、844 項測試、版本／
污染／MOD 稽核、7/7 封裝 provider smoke、一次性簽署演練與 copied-folder 啟動均
已通過。16.1 正在建立可重現來源與建置基線，尚未封裝；Development 成品維持
`SAFE_MODE`，尚未上傳，也不是可宣告的 Stable 正式版。16.1 目前來源回歸為
848 passed、2 skipped。
GitHub 的
[`test-v1.0.0`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.0.0)
是既有測試版 Pre-release；它不會被開發版 14.x 覆寫。已公開附件一律不可覆寫，
重建必須使用新版本號。
目前來源包含：

- Windows EXE、主視窗與通知區使用專用多尺寸圖示，小尺寸仍保持清楚辨識
- 外觀選單提供精簡、標準與大字三種介面大小，下載工作區在小視窗可安全捲動
- 插件管理顯示三十一個內建 MOD；父 MOD 啟用後才顯示並允許開關其子 MOD
- 下載工作可多選／全選、取消所選或全部未結束任務、清除已結束列表、暫停／繼續，
  並可選擇 1–4 個同時工作
- 下載封存與播放清單 ID 可經預覽後安全匯入／匯出
- 外部 MOD manifest v2、簽章／權限生命週期與側邊離線更新基礎
- 八個公開網站家族的可重複 smoke matrix 與一致錯誤分類
- Bilibili bangumi、分 P 與字幕資訊；彈幕 XML／ASS／MKV 由獨立子 MOD 控制
- YouTube／Bilibili 父 MOD 與子 MOD 分層；主 MOD 開啟後才顯示子 MOD
- 核心四語言設定同步內建網站 MOD 的工作區、名稱與控制位置
- 聯合搜尋採每來源有界收集與 round-robin 合併，指定缺失或停用來源時 fail closed
- 內建 MOD 編目、依賴快照與選用工作區共用單一生命週期來源
- MOD 管理提供手動唯讀自我檢查、最近一次 provider smoke JSON 匯入及去識別 JSON
  匯出；16.0 會核對父子狀態、四語言綁定、網站路由、8 個網站父 MOD／5 個通用
  站點能力矩陣、實際 MOD 樹，以及動畫瘋作品／集數與番劇儲存按鈕狀態，
  不啟動下載器或媒體工具
- 第三方網站 MOD schema v2 範本可宣告標準 DNS host ownership、最小權限、請求逾時、
  取消寬限與程序樹終止政策，並以四語宣告式 `ui.json` 離線驗證

- 依序初始化的 Bootstrap 與 AppContext
- 一般／Portable 路徑服務
- 乾淨的 PySide6 媒體庫、搜尋、下載佇列與 MOD 管理介面
- 可關閉的 YouTube 搜尋／下載 MOD，含搜尋範圍、分頁載入、歷史、縮圖、試聽與
  選用影片預覽；載入更多採有界去重且保留目前選取
- 預設關閉且彼此獨立的 Bilibili 搜尋與下載 MOD；搜尋不借用 YouTube，下載支援
  分段、彈幕 XML、ASS 與可選 MKV 封裝；官方搜尋要求驗證或節流時不會繞過或改查
  其他網站；搜尋分頁會保留 UP 主篩選及既有選取
- 預設關閉的動畫瘋主 MOD、官方目錄／搜尋子 MOD、集數導覽子 MOD及番劇儲存子 MOD；
  可信 UI 會在載入集數前明確詢問是否啟用集數子 MOD。官方頁未要求瀏覽器驗證時可
  顯示近期熱播、新上架、全部動畫、熱門排序、官方篩選、封面與分頁集數；Cloudflare
  阻擋時不顯示原始 403、不繞過驗證，改由使用者從官網貼入標準作品與單集網址。
  功能不借用 YouTube、不擷取串流，播放仍交由官方頁面。番劇儲存只保存選取單集的公開索引、
  已載入封面及使用者明確選取的本機媒體副本，支援取消、`.part` 清理與 SHA-256
- 預設關閉的 Facebook 公開影片下載 MOD；啟用後才顯示獨立工作區，可讀取縮圖並
  分流至 Facebook provider，不讀取 Cookie、私人貼文或登入內容
- 預設關閉的 MEGA 公開檔案下載 MOD；啟用後才顯示完全獨立的雲端檔案工作區，不含
  YouTube／Bilibili 的格式、字幕、播放清單或試聽控制。使用本機官方 `mega-get`
  下載，並可選擇以 `mega-speedlimit` 套用連線數與速率上限；公開資料夾會驗證本機
  樹狀輸出、禁止符號連結並限制為 10,000 項
- Instagram、Threads 與 X/Twitter 已拆成各自的父 MOD；父 MOD 啟用後可分別勾選官方媒體頁與
  官方帳號資料匯出子 MOD。官方封存 ZIP 可在本機經有界安全檢查後只匯入媒體並建立
  `media-index.json`；不讀取 Cookie、不執行網站自動化，也不宣稱提供線上下載
- 預設關閉的 Direct HTTP 父 MOD 與專屬工作區，只接受明確 HTTPS 檔案副檔名，
  支援 `.part` 續傳與選用 SHA-256；既有網站網域、私有位址、登入頁及未知網頁一律拒絕
- 預設關閉的 `Media Convert → Local Ad Segment Trim` 本機子 MOD，可手動輸入最多
  50 個剪除區間、預覽第一切點前後 5 秒並另存 H.264/AAC 新檔；不接收網站網址、
  不覆寫原檔，也不移除或繞過網站廣告
- 播放清單選取，以及具預覽與檢查結果的 TXT／CSV 批量匯入
- 格式、字幕、優先級、時間區段、重試、取消與完成通知
- YouTube／Bilibili 可選 1440p、2160p（4K）、H.264/AAC 1080p 相容輸出，
  以及 AAC/M4A 256k、MP3 320k、Opus 160k、FLAC 與 WAV PCM 轉碼；介面會
  說明高位元率及無損容器不會提升原始來源音質
- YouTube 下載可分辨人工／自動字幕來源，選用媒體資訊、縮圖與章節，並儲存網域設定；
  Bilibili 可篩選 UP 主／分 P 清單，彈幕與字幕分開顯示並選擇標準或韌性重試
- 讀取影片資訊後顯示解析度、FPS、HDR/SDR、影音編碼與容量，並可驗證 MP4、
  MKV、WebM 容器相容性；不相容選項會在加入工作前阻擋
- 可選取的任務詳情、失敗原因複製與安全輸出位置開啟
- 可攜 Deno、FFmpeg、ffprobe 與本機依賴健康提示
- 原子寫入的設定、佇列、歷史與下載封存
- Trust Store、SHA-256 完整性驗證與 fail-closed 簽章介面
- `NORMAL`、`SAFE_MODE`、`BLOCKED` 安全狀態
- 可自選背景，以及不依賴圖片資源的低負載漸層預設背景
- 下載表格增量更新與依工作狀態調整的低負載刷新
- 加入下載前輸出路徑與 256 MiB 磁碟保留空間預檢
- 第三方 MOD schema v2 範本、安裝前驗證工具與中文開發流程
- YouTube 最近搜尋選單可依本機偏好提供有界、需手動觸發的搜尋建議
- 長音訊切割確認會提示過短、低信心、預設名稱與時間間隙並預覽輸出名稱
- 內建網站能力與 Bilibili 彈幕政策具有不連網、可重複的品質稽核

## 執行

```powershell
python main.py
python main.py --portable --headless
python main.py --portable --verify-only
```

`main.py` 是唯一的正式入口；直接執行、安裝後的 `mediamanager` 指令與
PyInstaller 桌面程式都使用相同的參數解析、Bootstrap 與主視窗啟動流程。
`desktop.py` 僅保留為舊版啟動方式的相容轉接。

本機開發封裝位於 `Version/Development/<major>.<minor>`，測試封裝位於
`Version/Testing/<major>.<minor>`；GitHub 下載頁只發布
3.0、4.0 等大版本完整檔案，次版本改以中文更新簡介說明。整個版本資料夾可
移動到其他位置
執行；不要只移動 EXE，因為同層的 MOD、工具與 checksum 檔案也是版本
的一部分。

## 路徑架構

- 核心與正式入口：應用程式根目錄
- 待安裝插件：`mod/packages/*.modpkg`
- 已安裝插件：`mod/installed/<plugin-id>`
- 隔離插件：`mod/quarantine`
- 插件登錄資料庫：`mod/registry.sqlite3`

插件根目錄固定置於核心旁的 `mod`，不因一般或 Portable 模式而改變。
插件套件會先驗證結構、檔案雜湊、發布者信任與 Ed25519 簽章，再以暫存目錄交易式安裝；新安裝插件預設停用。公鑰使用 Base64 編碼的 32-byte Ed25519 公鑰（可加上 `ed25519:` 前綴），簽章可使用原始 64-byte 或 Base64 格式。

開發版與測試版沒有簽署的 `security/release-manifest.json`，因此會刻意以
`SAFE_MODE` 啟動。正式版本必須由發行流程產生並簽署 manifest；不可把開發用金鑰
放進原始碼。

## 測試

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

建立並交易式更新目前版本資料夾：

```powershell
.\.venv\Scripts\python.exe -m tools.build_version
```

批次稽核所有保留版本的版本號、wheel 與 SHA-256 完整性：

```powershell
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
```

日常只檢查最新版與上一版；重大發布需要完整歷史時使用 `--full-history`，並先
從 GitHub Releases 還原未保留在本機的歷史附件。

## 文件與版本紀錄

請從 [`docs/README.md`](docs/README.md) 進入目前有效文件、開發版區間紀錄與唯讀
歷史索引。舊 release 與 roadmap 會保留供稽核，但不再由專案首頁混列成目前功能或
安裝指引。
