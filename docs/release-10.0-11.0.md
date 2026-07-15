# MediaManager 開發版更新紀錄 10.0～11.0

## 10.4

- MEGA 從共用影音 `DownloadPanel` 完整拆出，改用獨立雲端檔案工作區；YouTube／Bilibili 的格式、字幕、播放清單、試聽、影片預覽與切段控制不再出現在 MEGA。
- MEGA 公開分享輸入會分別顯示檔案、資料夾與無效連結；一次最多加入 50 個公開檔案。資料夾目前保持可辨識但禁止下載，避免遞迴輸出無法完整驗證。
- 指定檔名後可顯示影片、壓縮檔、文件、音訊、圖片或未知類型；公開分享 ID 不含副檔名時維持「下載後判定」，不猜測內容。
- 新增預設關閉的 MEGAcmd 連線分流設定，可選 1／2／4／6 條下載連線與 0～1024 MiB/s 速率上限；只有使用者勾選後才呼叫官方 `mega-speedlimit`，乾淨啟動不執行工具。
- 下載要求新增有界、可持久化的 provider options；只允許最多 16 個不重複文字鍵值，MEGA provider 再以自己的 allowlist 與數值範圍 fail closed 驗證。
- MEGA 工作表只列出 MEGA 佇列項目，提供重試、開始前暫停／繼續、開始前停止及安全開啟輸出位置，不會控制或清除其他網站的工作。

### 10.4 已知限制

- 公開資料夾下載仍未開放；目前下載 provider 要求官方 MEGAcmd 產生恰好一個可驗證的檔案，尚未建立安全的多檔遞迴完成契約。
- 自訂連線數與速率上限需要同一套官方 MEGAcmd 的 `mega-speedlimit`；只有 `mega-get` 時仍可下載，但必須沿用目前 MEGAcmd 設定。
- MEGAcmd 連線設定可能影響同一個本機 MEGAcmd 工作階段，因此介面預設不套用，且不宣稱為影音分段下載。
- 執行中的公開檔案傳輸由 MEGAcmd server 管理；10.4 尚未取得可安全對應單一工作的 transfer tag，因此不送出可能誤停其他工作或其他應用程式的全域暫停／取消命令。

### 10.4 驗證狀態

- 通道：Development；維持 `SAFE_MODE`，不建立或上傳 Stable 版本。
- `Version/Development/10.3` 保持不變；本輪只更新 10.4 來源與紀錄，尚未建立發行附件。
- Ruff：通過。
- Pytest：693 passed、2 skipped；兩項 skipped 均為此 Windows 帳戶不允許建立 symlink。

## 10.3

- YouTube／YouTube Music 網址區會明確區分單一影片、純播放清單、播放清單中的單一影片與多網址批量；只有可展開的清單網址會啟用「展開播放清單」，避免單片網址觸發錯誤流程。
- 單一影片在下載工作區新增 30 秒試聽與 60 秒影片預覽；影片預覽仍須由使用者啟用 YouTube Player 子 MOD，停止、關閉或切換網址時會清除暫存媒體。
- YouTube 內嵌「展開搜尋」結果新增相同的試聽／影片預覽控制，選取結果後才啟用，不會在乾淨啟動時自動下載或播放。
- 播放清單展開後預設不勾選任何項目，必須由使用者明確選取後才能加入下載佇列。
- 共用「網站搜尋」明確顯示 YouTube 搜尋、Bilibili 搜尋與動畫瘋官方搜尋；子搜尋因主 MOD 未啟用而隱藏時，來源摘要會直接說明啟用條件。

### 10.3 已知限制

- 音訊與影片預覽仍由 yt-dlp／FFmpeg 準備本機暫存片段；來源不可用、受登入或地區限制時不會嘗試繞過網站限制。
- Bilibili 搜尋維持主／子 MOD 規則，必須先啟用 Bilibili 主 MOD 才會列入共用搜尋來源。

### 10.3 發行狀態

- 通道：Development；維持 `SAFE_MODE`。
- 不建立或上傳 Stable 版本。
- `Version/Development/10.2` 保持不變；10.3 使用新的獨立資料夾。
- Ruff：通過。
- Pytest：681 passed、2 skipped；兩項 skipped 均為此 Windows 帳戶不允許建立 symlink。

## 10.2

- 網站搜尋的單一結果會把受限的影片 ID、標題、作者、長度、語言與類別帶入對應下載工作區；不必重複讀取網路資訊即可建立具正確來源資料的單片下載，仍可手動讀取完整格式清單。
- YouTube／YouTube Music 播放清單選取視窗新增「影片預覽 60 秒」與停止按鈕；僅在使用者啟用 YouTube Player 子 MOD 時執行，關閉、停止或失敗都會清除預覽暫存。
- 執行中的下載按下暫停或停止後，工作列與詳情立即顯示過渡狀態；Windows 會先終止 yt-dlp 所在的 Job Object，連同 FFmpeg 與 JavaScript runtime 子程序一起停止。
- 暫停與停止意圖會寫入原子佇列狀態。程式重新啟動後，舊的執行中或等待中工作一律還原為暫停，必須由使用者明確按下繼續，不再自動連網下載。
- 維持網站主 MOD／子 MOD 分層、`SAFE_MODE` 與無 Cookie／不繞過網站限制的既有界線。

### 10.2 已知限制

- 60 秒影片預覽需要啟用 YouTube 主 MOD 與 YouTube Player 子 MOD；未啟用時按鈕保持停用並顯示原因。
- 暫停採停止程序並保留 yt-dlp 部分檔案的方式；能否從既有位元組續傳仍取決於來源網站與伺服器是否支援 Range。

### 10.2 發行狀態

- 通道：Development；維持 `SAFE_MODE`。
- 不建立或上傳 Stable 版本。
- `Version/Development/10.0` 與 `10.1` 保持不變；10.2 使用新的獨立資料夾。
- Ruff：通過。
- Pytest：680 passed、2 skipped；兩項 skipped 均為此 Windows 帳戶不允許建立 symlink。

## 10.1

- YouTube／YouTube Music 播放清單契約新增向後相容的縮圖欄位；展開後顯示受限 CDN 縮圖，並提供 30 秒試聽與明確的停止按鈕。關閉視窗、播放結束、錯誤或取消準備時都會清除暫存音訊。
- Bilibili 分段標題依 `title`、`part`、完整標題、集數與母影片標題依序後備，不再只顯示「未命名分段」；作者與 hdslb 縮圖也可從母影片資料補齊。
- 網站搜尋維持分站查詢，介面常駐列出 YouTube、Bilibili、動畫瘋等目前可選來源，避免下拉框只顯示目前項目造成誤判。
- Facebook 公開頁加入 yt-dlp 官方 `curl-cffi` 瀏覽器模擬支援，但不讀取 Cookie、不繞過登入、權限、地區或網站限制。無法解析時顯示可操作的繁中原因，不再只回傳原始 extractor 錯誤。
- MEGA 在取得實際檔名後可區分影片、壓縮檔、文檔、音訊、圖片與未知檔案；公開分享 ID 本身不包含可判斷的副檔名，因此安裝官方 `mega-get` 前仍誠實顯示為未知類型。
- 執行環境改成「核心」與「選用」兩組：yt-dlp、EJS、FFmpeg、JavaScript runtime 為核心；MEGAcmd、whisper-cli、語音模型只影響各自 MOD。`核心 4/4｜選用 0/3` 代表核心可正常使用。
- 發行工具不再覆寫既有 `Version/Development/X.Y`。修正版必須提高開發次版本並建立全新資料夾，保留上一版供回退與檔案差異確認。

### 10.1 已知限制

- 使用者提供的 Facebook Reel `1010600518536222` 在 yt-dlp 2026.07.04 與 Chrome 模擬下仍由上游 extractor 回報 `Cannot parse data`；MediaManager 不會改用帳號 Cookie 或存取限制繞過方案。
- MEGA 公開連結在沒有官方 MEGAcmd 時只能辨識檔案或資料夾分享；實際檔案類型要等官方客戶端揭露／下載出檔名後才能分類。
- MEGAcmd `mega-get`、whisper-cli 與本機語音模型仍為選用待安裝項目，不阻擋核心啟動或 YouTube／Bilibili 功能。

### 10.1 發行狀態

- 通道：Development；維持 `SAFE_MODE`。
- 不建立或上傳 Stable 版本。
- `Version/Development/10.0` 保持不變；10.1 使用新的獨立資料夾。
- Ruff：通過。
- Pytest：676 passed、2 skipped；兩項 skipped 均為此 Windows 帳戶不允許建立 symlink。
- 內建 MOD 群組稽核：4 groups、4 locales 通過。
- 依賴鎖檔：9 個直接發行依賴均有精確版本且與建置環境一致。
