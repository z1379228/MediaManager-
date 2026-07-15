# MediaManager 開發版更新紀錄 10.0～11.0

## 10.6

- 修正 Facebook provider 在 yt-dlp Python API 傳入字串型 `impersonate`，會在真正連線前觸發 `AssertionError` 的問題；現在使用 yt-dlp 正式 `ImpersonateTarget` 型別。
- Facebook 公開頁若已啟用 curl-cffi 仍沒有媒體，會明確說明可能受登入、貼文權限或地區限制，並重申不讀取 Cookie；未安裝 curl-cffi 時則顯示不同依賴原因。
- 修正核心雖能找到官方 Windows MEGAcmd，卻拒絕 `mega-get.bat`／`mega-speedlimit.bat`，導致 MEGA MOD 永遠無法初始化的問題；只對 MEGA 固定工具名稱放行 Windows `.bat`，其他任意批次檔仍拒絕。
- MEGA 獨立工作區現在會接收核心語言事件，從 MEGA MOD 語言資料切換繁中、簡中、英文與日文標題、副標題、啟用文字及網址提示。
- 網站下載按鈕現在同時檢查主 provider 已啟用；只貼入合法網址但主 MOD 關閉時，不再顯示可加入佇列的錯誤狀態。

### 10.6 實機與邊界驗證

- 官方 `MEGAcmdSetup64.exe` 2.5.2.0 由 `Mega Limited` 簽署且 Authenticode 驗證為 Valid；安裝後核心可同時載入 `mega-get.bat` 與 `mega-speedlimit.bat`，依賴狀態為核心 4/4、選用 1/3。
- MEGA 以刻意無效的完整公開分享網址執行 subprocess 端到端測試：provider 正確呼叫官方工具、回傳受控失敗，輸出資料夾保持 0 個檔案；成功下載仍由既有模擬官方工具測試覆蓋，未使用陌生網路分享冒充實機成功。
- 使用者提供的 Facebook Reel `1010600518536222` 已通過 typed impersonation 並進入真正網站解析；Facebook 回傳頁面不含可下載公開媒體，因此正確停在無 Cookie 存取限制，不再出現程式 `AssertionError`。
- MEGA 公開資料夾維持辨識但不下載：目前核心完成契約只接受單一可驗證檔案，尚無可安全限制遞迴大小與對應單一 transfer tag 的資料夾輸出契約。

### 10.6 發行狀態

- 通道：Development；維持 `SAFE_MODE`，不建立或上傳 Stable 版本。
- 依次版本政策只更新 10.6 來源與本整檔更新簡介；不覆寫既有 `Version/Development` 版本資料夾。
- Ruff：通過。
- Pytest：704 passed、2 skipped；兩項 skipped 均為此 Windows 帳戶不允許建立 symlink。
- 413 個 Git 已追蹤／待加入文字檔的嚴格 UTF-8、衝突標記與工具殘留掃描通過；版本稽核結果維持 3 個保留版本全部通過。

## 10.5

- YouTube／YouTube Music 維持單一專屬工作區：搜尋、官方縮圖、多選帶入、單片 30 秒試聽／60 秒影片預覽、播放清單展開與批量下載使用同一條受控流程；播放清單仍預設不勾選。
- YouTube 搜尋子 MOD 現在和其他網站群組一致，必須先啟用 YouTube 主 MOD 才能啟用或搜尋；核心語言事件會同步讀取 YouTube MOD 的繁中、簡中、英文與日文資料。
- Bilibili 新增內嵌專屬搜尋工作區，結果只接受 Bilibili 官方網址與 hdslb 官方縮圖；可依目前搜尋結果鎖定 UP 主、多選後帶入同頁下載設定。
- Bilibili UP 主空間可展開最近 50 支影片，改用完整但有界的中繼資料取得真實影片標題與官方縮圖；UP 主網址只能先展開，不能誤當成單一影片直接下載。
- Bilibili 分 P 先向官方影片資訊端點讀取 `pages[].part`、長度與首幀，失敗時才回退至 yt-dlp／母影片名稱；實測 186 分段影片可展開前 20 段並顯示真實名稱。
- 修正 Bilibili 分段下載把 DASH 來源錯誤降成 progressive-only 格式的問題；480p／720p／1080p 切段會保留視訊＋音訊選擇並交由 FFmpeg 合併。
- 修正含 `[BV…]` 的檔名被當成 glob 語法，造成已下載的彈幕 XML 找不到、ASS 不會產生的問題；現在使用受限 XML 清單與字面檔名比對。
- Bilibili 官方搜尋 API 若要求驗證或限流，介面會明確顯示原因並提供「官網搜尋／驗證」入口；不保存瀏覽器 Cookie、不改用 YouTube，也不繞過網站限制。
- YouTube 與 Bilibili 搜尋均為可取消、無乾淨啟動背景網路工作的子 MOD；主 MOD 關閉時子 MOD 會停用並隱藏可執行狀態。

### 10.5 實際網站驗證

- YouTube Music 範例播放清單展開 48 項，48 項皆可用且皆有縮圖；第一項 3 秒 MP3 試聽、搜尋結果 3 秒 H.264／AAC 預覽與下載均由 ffprobe 驗證。
- Bilibili 公開影片可展開 20 個具名分 P；UP 主頁前 5 支影片回傳真實標題；一般 3 秒 H.264／AAC 分段下載通過。
- Bilibili 10～18 秒彈幕案例保留 XML 與 ASS，產生 MKV，ffprobe 確認包含 H.264、音訊與 ASS 字幕流。
- 當前網路的 Bilibili 官方搜尋 API 回傳 412 瀏覽器驗證／限流；程式正確 fail closed，直接網址、分 P、UP 主清單、下載與彈幕流程不受此搜尋端點狀態影響。

### 10.5 發行狀態

- 通道：Development；維持 `SAFE_MODE`，不建立或上傳 Stable 版本。
- 依次版本政策只更新 10.5 來源與本整檔更新簡介；不覆寫 `Version/Development/10.3`，也不把未封裝的 10.4／10.5 假稱為公開附件。
- Ruff：通過。
- Pytest：700 passed、2 skipped；兩項 skipped 均為此 Windows 帳戶不允許建立 symlink。
- `pytest-timeout` 未安裝於本機虛擬環境，因此完整測試使用既有 pytest 參數完成；這不是測試失敗或功能阻擋。

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
