# 開發版 14.0～15.0 實際更新紀錄

本文件只記錄實際完成並通過對應測試的內容。15.0 規劃請見
[`roadmap-development-15.0.md`](roadmap-development-15.0.md)；規劃項目不等於已完成。

## 14.0

- 開發版 14.0.0 已建立於全新的 `Version/Development/14.0`，維持 `SAFE_MODE`，
  沒有建立 Testing、Stable 或上傳 GitHub Release。
- Ruff、825 項測試、8 個網站父群組 × 4 語言、487 個來源文字檔污染掃描、
  current + previous 版本雜湊及 copied-folder CLI／GUI smoke 通過；2 項 Windows
  symlink 權限測試略過。
- 公開 provider smoke 為 6/7；Dailymotion 固定樣本兩次遇到上游 HTTP 502，仍標記
  FAIL／`temporary-upstream`。production Ed25519 與 Authenticode 尚未具備，不能升格。

## 14.1

- 開發版 14.1.0 已建立於全新的 `Version/Development/14.1`；14.0 已封裝附件保持
  原樣，沒有覆寫或上傳新成品。
- 下載佇列改為延伸多選，批次控制新增全選、取消選取及取消全部未結束任務；主按鈕
  可取消所有選取中的活動任務，清除功能只移除完成、失敗與已取消紀錄。
- YouTube／Bilibili 播放清單選取與 TXT／CSV 批量匯入改成真正作用於完整清單的
  「全選／全部取消」，篩選結果仍可獨立反向勾選。
- 動畫瘋選取作品後，即使集數導覽子 MOD 尚未啟用，也可按「啟用集數導覽並載入」；
  UI 會先取得使用者同意，再啟用子 MOD 並讀取官方公開集數。雙擊作品也走相同流程，
  不再只開啟官網而看不到集數。
- 動畫瘋仍只提供公開目錄、封面、集數與官方播放入口，不擷取網站串流、不處理或
  規避廣告、DRM、登入、付費及地區限制。
- Ruff 與完整 828 項測試通過；2 項 Windows symlink 權限測試明確略過。
- 封裝後實測發現動畫瘋官方作品頁會要求 Cloudflare 瀏覽器驗證，造成集數導覽顯示
  原始 HTTP 403；14.1 因此保留作為回退與錯誤比對，不標記為目前可用或上傳候選。

## 14.2

- 開發版 14.2.0 已建立於全新的 `Version/Development/14.2`，沒有覆寫 14.1，也沒有
  建立 Testing、Stable 或上傳 GitHub Release。
- 動畫瘋搜尋與集數 provider 將官方 HTTP 403 映射為固定的瀏覽器驗證狀態；可信 UI
  顯示四語言說明，不再把 `[PROVIDER_ERROR] HTTPError` 直接交給使用者。
- 當 Cloudflare 要求瀏覽器驗證時，使用者可開啟官網並貼入標準
  `animeRef.php?sn=...` 作品網址，再貼入 `animeVideo.php?sn=...` 單集網址；程式不
  匯入 Cookie、不模擬瀏覽器驗證、不處理廣告，也不擷取播放器或串流。
- Ruff、831 項測試、current + previous 版本稽核、copied-folder 的三種 CLI 與 GUI
  smoke、7/7 公開 provider smoke 通過；2 項 Windows symlink 權限測試明確略過。
- 一次性 Ed25519 演練驗證 106 個檔案、未保留私鑰且成功偵測竄改。production
  Ed25519 尚未配置、EXE Authenticode 為 `NotSigned`，因此維持 `SAFE_MODE`。

## 14.3

- Bilibili 搜尋、UP 主篩選、分 P 名稱／縮圖、格式與完整清單選取維持在專屬工作區，
  不借用 YouTube 搜尋或控制。
- 彈幕 XML、ASS 與可選 MKV 只在 `bilibili-danmaku` 子 MOD 啟用時顯示；彈幕處理
  失敗不會把未完成封裝冒充成功媒體。

## 14.4

- Facebook 維持只接受官方公開影片頁的窄能力，提供網址分類、縮圖、分析、排隊及
  取消；不加入搜尋、播放清單、字幕、分段或音訊專用控制。
- 登入、權限、私人內容、地區及上游限制使用可理解錯誤，不匯入 Cookie 或自動登入。

## 14.5

- MEGA 工作區分辨公開檔案與資料夾，提供有界樹狀預覽、10,000 項上限、路徑穿越／
  symlink 拒絕與完成輸出驗證。
- 工作控制只作用於 MediaManager 自己的佇列與程序，不發送會影響其他 MEGAcmd 工作的
  全域暫停或取消命令。

## 14.6

- 動畫瘋番劇儲存保存官方作品／單集入口、封面、本機媒體副本及 SHA-256；支援取消、
  `.part` 清理與重新驗證。
- 功能不解析網站串流、不下載動畫瘋媒體、不移除廣告，也不規避播放器、Cloudflare、
  DRM、登入、付費或地區限制。

## 14.7

- YouTube、Bilibili 與動畫瘋搜尋維持明確來源，分別處理游標、部分失敗、縮圖、預覽
  能力、取消與選取保留；停用或缺失來源時 fail closed。
- 歷史、替代及相似內容只由 YouTube 對應子 MOD 提供，不對其他網站顯示假能力。

## 14.8

- 網站 MOD SDK 的 schema v2 父／子範本加入標準 DNS host ownership、最小
  `network.<parent>`／`media.write` 權限、30 秒請求逾時、3 秒取消寬限與程序樹終止政策。
- `validate-site` 可離線檢查相依關係、四語 `ui.json`、runtime protocol 與上述政策；
  驗證不安裝、不執行，也不讓未簽章 MOD 在 `SAFE_MODE` 啟動。

## 14.9

- 移除已被 Direct HTTP 實作取代的 `direct-transfer` 製作中重複項目；Gopeed 與 P2P
  仍保留為不可啟用的 P2 候選。
- 8 個網站父 MOD 新增 schema v2 工作流能力矩陣，與 5 個通用白名單站點一併執行
  離線稽核；明確記錄搜尋、預覽、批量、下載、彈幕與封存是否可用。
- Self Check 加入唯讀能力矩陣結果及最近一次手動 provider smoke schema 2 JSON 匯入；
  自檢不連網、不啟動 provider、不建立暫存資料。

## 15.0

- 來源版本整合為開發版 15.0.0；建立獨立 `Version/Development/15.0`，沒有覆寫
  14.2、建立 Testing／Stable 或上傳附件。
- Ruff 與完整 835 項測試通過；2 項 Windows symlink 權限測試明確略過。
- 成品包含 115 個檔案，`SHA256SUMS.txt` 記錄 114 項；EXE SHA-256 為
  `0f187b7201f84882aa68a63bb43a731e3ce0309ade7a0948ae8f39acd50fadab`，wheel
  SHA-256 為 `742ee66ecd0373d8d55e999e3224b0a4b5268ef7a3776421eed069c2ab23dd06`。
- copied-folder 的版本、verify-only、headless 與 GUI 啟動通過；版本稽核同時通過
  5.0、Testing 1.0、Development 14.2 與 Development 15.0。
- provider smoke 初跑為 6/7：TikTok 固定測試網址失效，且工具被發現仍從來源樹載入
  provider，而不是指定成品。15.0 因此只保留供回歸，不列目前可發布；修正必須進入
  新的 15.1，不覆寫本資料夾。
