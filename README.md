# MediaManager v1.0

免費、無廣告、本機優先的媒體整理與模組化下載工作區。核心負責安全邊界、
佇列、媒體庫與可信 UI；網站解析、轉換、轉錄及自動化等重功能由可個別停用的
內建或第三方 MOD 提供。

目前來源版本為開發版 39.0（核心相容版本 39.0.95）。`MediaManager v1.0`
是產品顯示名稱，不表示 Stable 已發布。Development `39.0.13` 修正搜尋結果
去重與歷史污染；`39.0.14` 讓通用搜尋依目前 provider 宣告顯示內容類型，第三方
Search v2 MOD 可使用 `playlist`／`live` 能力；`39.0.15` 讓 YouTube 相似音樂優先
以所選結果的歌手與曲名共同搜尋，降低常見曲名造成的過寬候選；`39.0.16`
限制搜尋詞組別名只能匹配完整詞組，不再誤改較長單字；`39.0.17` 確保本機
別名與拼字修正後仍符合 Search v2 的 200 字元上限；`39.0.18` 將服務層既有的
多來源合併接入通用 UI，可搜尋所有已啟用且具有共同內容類型的來源；`39.0.19`
讓片長與語言條件在結果載入後立即以本機快取重新篩選，不必再次查詢網站；
`39.0.20` 讓通用搜尋以 canonical 去重追加下一頁，並在載入更多失敗時保留既有結果；
`39.0.21` 將同一媒體 ID 的 YouTube 官方網域別名視為同一搜尋結果，同時保留
跨網站及大小寫不同 ID 的身分界線；`39.0.22` 讓搜尋 MOD 可用性變更立即失效
舊游標與結果快取，並依實際來源狀態停用搜尋／下一頁控制項；`39.0.23` 讓依賴
YouTube 搜尋來源的相似音樂與替代搜尋同步反映 MOD 狀態；`39.0.24` 讓多來源聚合
搜尋以查詢與來源集合綁定的安全游標繼續載入，且只續查仍有下一頁的來源；
`39.0.25` 在工作區達 200 筆結果時終止分頁，避免無法顯示的新頁仍被重複請求；
`39.0.26` 在所選搜尋來源消失時改選實際啟用來源，不再退回停用或錯位項目；
`39.0.27` 讓搜尋條件或來源變更立即使進行中的舊請求失效，避免晚到結果回寫；
`39.0.28` 讓 MOD 管理介面的外部狀態事件也失效舊搜尋快取與分頁游標；
`39.0.29` 按來源分配聚合頁面配額，避免總量截斷後跳過尚未顯示的來源結果；
`39.0.30` 只讓通過 exact-host 路由的 URL 共用官方 YouTube 搜尋身分；
`39.0.31` 在共用 Discovery 契約拒絕無主機、畸形、內嵌帳密、過長或帶控制字元
的 HTTPS 結果，避免單一外部搜尋 MOD 中斷其他正常來源；`39.0.32` 在共用
Search registry 拒絕重複、空白或非字串的來源選擇，避免同一 MOD 被重複派送。
`39.0.33` 讓 provider iterable 最多只讀取 17 項，並明確拒絕字串及不可迭代
輸入，避免無限 generator 或過長來源清單造成無界耗用與錯誤派送；`39.0.34`
讓公開 Discovery service 與 registry 共用相同有界來源選擇契約，不再由服務層
先完整展開輸入而繞過底層防護；`39.0.35` 拒絕布林、字串及小數型搜尋結果
上限，不再以隱式整數轉換改變請求，同時保留合法整數的 1～50 有界相容行為。
`39.0.36` 在 federated 分頁派送前有界驗證 provider cursor mapping，拒絕契約外
容器及空白、超長或非字串游標，避免完整消耗過長 Mapping 或把輸入錯誤降級成
單一來源失敗；`39.0.37` 將 Search v2 查詢欄位驗證提前至服務與 registry 入口，
無來源時不再把非法輸入當成空結果，有來源時也不再誤列為 provider failure；
`39.0.38` 拒絕非字串的外層分頁游標，避免 `None`、`False`、`0` 或空容器被
誤當成沒有游標而重新查詢第一頁；`39.0.39` 在寫入任何 registry 前驗證搜尋
capability 身分，錯誤的第三方 MOD 不再留下阻止同 ID 修正版註冊的部分狀態。
`39.0.40` 讓本機搜尋排序對查詢、標題與作者統一套用 Unicode NFKC
正規化，全形拉丁字元與組合／分解重音字元不再因編碼形式差異失去精確命中。
`39.0.41` 讓偏好搜尋建議在填滿顯示上限後立即停止讀取歷史事件，並只將
實際 `search` 事件列入「最近搜尋」，避免 selection 紀錄被誤標成搜尋。
`39.0.42` 讓「最近搜尋」與偏好建議共用 Unicode NFKC 身分鍵，保留最新的原始
顯示文字，同時合併全形／半形與組合／預組重音等價詞。
`39.0.43` 讓精確的「作者＋標題」或「標題＋作者」查詢優先於只把整串查詢文字
放進標題的較弱結果，改善音樂搜尋的本機排序。
`39.0.44` 讓偏好建議的歷史事件 fallback 只接受實際 `search` 事件；selection
仍用於作者、語言與內容類型偏好統計，但不再被當成使用者主動輸入的搜尋詞。
`39.0.45` 讓以空白、連字號、長短破折號、直線、冒號或間隔點分隔的精確
「作者／標題」查詢使用相同跨欄位排序，不必改寫使用者輸入。
`39.0.46` 讓已知搜尋拼字修正可辨識括號、逗號等標點包圍的完整單字，修正時
保留原標點、空白與查詢順序，且維持 200 字元查詢上限。
`39.0.47` 將嚴格的「作者＋標題」完整跨欄位結果固定列為最高優先級，避免它被
標題片語加作者關鍵字的較弱候選反向超車。
`39.0.48` 讓已載入結果的語言篩選共用 Unicode NFKC 正規化，全形語言代碼與
組合／預組重音形式不再因編碼差異漏掉結果。
`39.0.49` 讓拉丁字搜尋片語遵守單字邊界，不再把 `art` 誤判為 `cartoon` 內的
完整命中；中日韓與泰文等慣用無空格文字仍保留既有子字串搜尋。
`39.0.50` 讓正規化後與查詢完全相等的標題優先於只包含同一片語的延伸標題，
例如正式曲名不再因 provider 順序排在 `live cover` 類結果之後。
`39.0.51` 讓作者欄位完全相等的作品優先於只在標題提及作者名稱的內容，改善
以歌手或創作者名稱搜尋時的結果順位。
`39.0.52` 將中英混合片語的首尾分別套用文字系統邊界，`art 音樂` 不再誤命中
`cart 音樂`，同時保留純中文與日文的無空格子字串搜尋。
`39.0.53` 將偏好作者的全形／半形、大小寫與 Unicode 等價鍵合併計數，讓本機
搜尋建議與 YouTube 相似音樂加權使用同一偏好身分，不再漏掉等價作者名稱。
`39.0.54` 將相似音樂的標題／作者 token 與重複種子判斷套用相同 Unicode 身分，
全形與半形作者可正確視為相同，並保留第三個查詢槽位給不同的關聯詞。
`39.0.55` 讓未輸入拉丁重音的搜尋仍可比對重音標題與作者，同時保留原始重音
完全相等及跨欄位精確結果的較高順位，不改寫送往 provider 的查詢文字。
`39.0.56` 讓相似音樂候選的語言與分類使用同一個 Unicode／大小寫身分比較，
避免不同搜尋來源的等價 metadata 因格式差異失去相關性分數。
`39.0.57` 讓缺少作者 metadata 的相似音樂種子優先搜尋精確曲名，再以 related
查詢補充候選，不增加既有三個查詢的上限。
`39.0.58` 讓 `作者-曲名`、`作者｜曲名` 等無空格分隔輸入也使用精確跨欄位
排序，不必要求使用者在分隔符前後補空白。
`39.0.59` 合併偏好作者名稱中的前後與重複空白，避免同一作者被拆分計數後
錯選次要搜尋建議。
`39.0.60` 讓相似音樂查詢計畫以 Unicode／大小寫等價身分去重，避免有限的
三個查詢槽位被全形與半形等價查詢重複占用，並保留語言與分類備援查詢。
`39.0.61` 讓 YouTube 音樂訊號的拉丁詞使用完整詞界，`mixed`／`mixing` 等一般
單字不再誤觸 `mix` 訊號；中日文等無空格訊號仍保留子字串判斷。
`39.0.62` 顯式補齊 `remix`、`songs`、`albums`、`playlists` 與 `mixes` 等常見
音樂詞形，在維持嚴格詞界的同時恢復合法音樂查詢與分類召回。
`39.0.63` 在 History 偏好共用契約拒絕布林總數與布林計數，避免外部 MOD 的
畸形偏好資料被當成整數送入搜尋建議或相似音樂加權。
`39.0.64` 統一搜尋排序、歷史建議與相似音樂計畫的拉丁重音身分，讓
`Beyoncé`／`Beyonce` 等搜尋等價文字合併計數、去除重複建議並保留有限查詢槽。
`39.0.65` 將同一身分規則延伸到相似候選的標題與作者 token，避免未輸入重音的
候選失去 title／artist 相關性分數。
`39.0.66` 讓相似 token 分別遵守 DiscoveryItem 的標題 300、作者 200 字元契約，
避免 39.0.65 的共用 helper 截斷合法長標題尾端關鍵字。
`39.0.67` 補齊 `soundtrack`、`soundtracks`、`OST` 與 `karaoke` 音樂詞形，
並以完整詞界避免 `post`／`cost` 等一般單字被誤分類。
`39.0.68` 保留 Search v2 的 200 字元契約：music scope 只有在仍容得下時才
附加提示，不截斷或改寫 195–200 字元的有效使用者查詢。
`39.0.69` 統一直撇號與智慧撇號的本機搜尋身分，避免同名作品排序失真、歷史
建議重複，以及相似音樂的有限查詢槽被同一作者的標點變體占用。
`39.0.70` 將常見排版連字號與破折號納入相同的本機搜尋身分，補回以 ASCII
連字號輸入時的同名作品排序，並去除建議與相似計畫中的破折號變體重複。
`39.0.71` 利用 yt-dlp 已回傳的嚴格 `Artist - Topic` 頻道後綴辨識一般標題的
音樂結果，改善 all scope 與後續相似音樂分類，不增加外部請求。
`39.0.72` 統一連字號／破折號兩側的空格差異，改善同名排序並避免歷史建議
與相似音樂計畫把 `Artist-Title`、`Artist - Title` 視為不同搜尋身分。
`39.0.73` 統一直雙引號與左右智慧雙引號的本機搜尋身分，改善同名排序並避免
歷史建議及相似音樂計畫因排版引號差異產生重複。
`39.0.74` 讓相似音樂的標題與作者 token 將底線視為詞界，與共用搜尋排序一致，
補回 `Hello_World` 類 provider 標題原本遺失的相關性分數。
`39.0.75` 忽略本機搜尋身分中的 Unicode 文字／Emoji 顯示選擇符，讓 `❤` 與
`❤️` 等只差呈現形式的文字維持相同排序、建議與相似查詢身分。
`39.0.76` 讓既有 `lo-fi → lofi` 查詢別名接受常見排版連字號／破折號，同時
維持完整詞界，不改寫 `flo–fi` 等較長單字。
`39.0.77` 將常見 Unicode 負號 U+2212 納入既有連字號比較身分與 `lo-fi`
別名，讓複製文字的精確排序、建議、相似音樂與 YouTube Topic 分類維持一致。
`39.0.78` 讓 Bilibili 專用搜尋工作區套用與通用／YouTube 搜尋相同的本機
查詢準備流程，使已知別名與拼字修正不再因入口不同而失效；官方網址不改寫。
`39.0.79` 讓 Bilibili 專用結果套用既有穩定本機相關性排序，完全同名作品可
優先於延伸標題；相同分數仍保留 provider 原順序，分頁與官方來源規則不變。
`39.0.80` 在 YouTube 與 Bilibili 專用工作區達 200 筆共用容量時清除下一頁
游標並停用載入更多，避免繼續送出無法增加顯示結果的外部請求。
`39.0.81` 讓明確的 `"標題" by 作者` 查詢使用既有作者／標題跨欄位精確排序；
未加引號的 `by` 仍視為一般標題文字，避免誤拆作品名稱。
`39.0.82` 讓整個查詢以成對雙引號包住時，也能將未帶引號的同名正式標題視為
完全相等；未閉合引號保持一般文字語意。
`39.0.83` 讓 `"標題" 作者`、`作者 - "標題"` 等明確引號曲名＋作者語法沿用
既有跨欄位精確排序，部分曲名仍不會被提升。
`39.0.84` 將成對引號的精確欄位候選同時套用作者，讓 `“作者”` 搜尋不再落後
於只在標題提及作者的內容；未閉合引號仍不剝除。
`39.0.85` 讓 `“作者” 標題`、`標題 - “作者”` 及雙欄皆加引號的明確語法沿用
既有跨欄位精確排序；部分作者仍不會被提升為完整匹配。
`39.0.86` 統一 `「」`、`『』`、`《》`、`〈〉` 成對標記的本機搜尋身分，讓東亞
書名／引號語法可用於精確排序、歷史建議去重與相似音樂偏好；錯配標記不剝除。
`39.0.87` 重整作者／標題的有限分隔符候選，補上 `/`、全形 `／`、日文中點
`・` 與 `|`／`:` 的單側空白形式；仍只接受完整 metadata 欄位組合。
`39.0.88` 讓 `/`、`|`、`:`、`·`、`・` 兩側空白只影響顯示、不再拆成不同的
本機搜尋身分；歷史建議與相似音樂會去除等價變體，但不會移除分隔符本身。
`39.0.89` 讓既有 `lo-fi → lofi` 查詢修正接受 `lo - fi` 與排版破折號的有限
空白形式，同時維持完整詞界，不會改寫 `flo - fi` 或 `lo - fighter`。
`39.0.90` 為格式工廠新增本機影片影像浮水印：只接受使用者選取的單一影片與
單一 PNG／JPEG／WebP／BMP／TIFF 影像，以固定右下位置輸出新的 H.264／AAC
檔案，不覆寫來源，也不接受網站網址或自訂 FFmpeg filter。
`39.0.91` 在 YouTube flat-search MOD 邊界正規化片長 metadata；`NaN`、布林、
負值或超過 Discovery v1 上限的值會降為未知片長，不再使整頁公開搜尋失敗。
`39.0.92` 讓顯式 YouTube `music` scope 與相似音樂查詢使用 yt-dlp 內建的
YouTube Music `#songs` 搜尋；一般 `all`／`video` scope 仍沿用有界 `ytsearch`。
`39.0.93` 在格式工廠新增下載後本機轉換 preset：以 H.265 Main10 NVENC p7、
VBR 平均 300 kbps 與 Opus 串流複製輸出 MKV；保留來源 FPS 與解析度，不套用
縮放、裁切或影音濾鏡。此 preset 需要本機 `hevc_nvenc`，且來源第一條音訊必須
已是 Opus；不符合時會明確拒絕，不會偷偷改用 CPU 或重新壓縮音訊。
`39.0.94` 保留本機品質量測較佳的 p7／HQ 參數，並在原子提交前以 ffprobe
驗證 Matroska、HEVC Main 10、10-bit、Opus、來源解析度及固定影格率；任何偏離
都會刪除暫存輸出而不留下看似完成但規格錯誤的檔案。來源與輸出 Opus 壓縮
封包也必須有相同 SHA-256，將 Passthru 從命令意圖提升為可驗證的音質保證。
`39.0.95` 讓啟動流程直接進入主畫面，不再自動彈出首次 MOD 設定或依賴環境
視窗；MOD 與執行環境仍可從主畫面的明確按鈕檢視及調整，啟動不會靜默改變
MOD 狀態或安裝工具。
Testing `1.2.3` 對應 Development `39.0.94`，僅作為本機未簽署、
`SAFE_MODE` 候選；本輪不 push、不簽署、不發布，也不覆寫任何既有 Testing
產物。一般使用者的最新公開下載仍是 Testing `1.2.2`。
Testing `1.2.2` 已由 Development `39.0.39` source freeze
`f7c65ee1a8e92828ede299bcbdff5e66d16f6810` 建立並發布為
[GitHub prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)，
納入 39.0.13～39.0.39 的搜尋強化與失敗隔離修正；它維持未簽署 Testing
身分，不是 Stable 正式套件，也不會覆寫既有
[Testing 1.2.1](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.1)。

## 主要能力

- YouTube 公開搜尋、單一結果的相似音樂候選、Bilibili、MEGA、Direct HTTP
  與網站矩陣明列的獨立工作區。
- 本機媒體庫、原子寫入的下載佇列、歷史、取消、重試與恢復。
- 格式工廠：使用本機 FFmpeg 進行影片、音訊、影像、字幕、切割、串接、壓縮、
  固定位置影像浮水印，以及 H.265 Main10 NVENC／Opus Passthru MKV 處理；
  不宣稱支援文件、DVD 或 CD 轉換。
- Gopeed Bridge／P2P Transfer：只連接使用者自行啟動的 localhost Gopeed API。
- 選用 Speech to Text 與 Automation；未安裝不影響核心。
- schema v2 第三方 MOD、Ed25519 發布者簽章、最小權限、受控程序與宣告式 UI。

實際能力以 MOD 管理、[依賴檢查](docs/dependency-health.md)與
[網站主機清冊](docs/site-host-inventory.md)為準。外部工具名稱不表示 MediaManager
會自動安裝、捆綁或承諾其全部功能。

## 安裝

### 方法一：Testing 1.2.2 免安裝、自包含 ZIP（一般使用者）

1. 從 [Testing 1.2.2 prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)
   下載
   [`MediaManager-Testing-1.2.2.zip`](https://github.com/z1379228/MediaManager-/releases/download/test-v1.2.2/MediaManager-Testing-1.2.2.zip)
   及
   [`MediaManager-Testing-1.2.2.zip.sha256`](https://github.com/z1379228/MediaManager-/releases/download/test-v1.2.2/MediaManager-Testing-1.2.2.zip.sha256)。
2. 將兩個檔案放在同一資料夾，於該資料夾開啟 PowerShell 並核對雜湊：

   ```powershell
   Get-FileHash -Algorithm SHA256 .\MediaManager-Testing-1.2.2.zip
   Get-Content .\MediaManager-Testing-1.2.2.zip.sha256
   ```

   兩者的 SHA-256 必須相同；另以同一發行頁的 `SHA256SUMS.txt` 與
   `release-info.json` 核對內容及來源 revision。
3. 將 ZIP 解壓縮到新的空資料夾，進入含有 `MediaManager.exe` 的資料夾後執行
   `MediaManager.exe`。不需要另外安裝 Python。

Testing 1.2.2 是未簽署測試版，Windows 可能顯示無法驗證發布者的警告。只應從上述
GitHub Release 下載並在雜湊一致時執行；不要關閉 Windows 安全功能。自包含 ZIP
已包含目前封裝的執行檔、資產與可攜工具，建議優先使用 ZIP，而不是單獨下載
`MediaManager.exe`。發行附件不包含 `UserData`；直接雙擊 EXE 時使用標準 Windows
使用者資料位置，不等同於 `--portable` 資料模式。詳見
[GitHub 免安裝自包含 ZIP](docs/self-contained-zip.md)。

### 方法二：從原始碼安裝

必要條件為 Windows 10／11 x64、Git 與 Python 3.14 以上。在 PowerShell 執行：

```powershell
git clone https://github.com/z1379228/MediaManager-.git
Set-Location .\MediaManager-
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[ui]"
.\.venv\Scripts\python.exe -B .\main.py --verify-only
.\.venv\Scripts\python.exe .\main.py
```

若要執行測試與開發工具，將安裝命令改為
`.\.venv\Scripts\python.exe -m pip install -e ".[ui,dev]"`。`--verify-only`
只驗證核心完整性；啟動 UI 後可從主畫面的核心／選用 MOD 工具狀態按鈕開啟
「執行環境」，再按「重新檢查」確認外部工具。

`main.py` 是唯一正式入口；`desktop.py` 只保留為舊版相容轉接。可攜模式會把
使用者資料放在程式旁的 `UserData/`。更完整的更新、移除與排錯說明見
[INSTALL.md](INSTALL.md)及[依賴檢查](docs/dependency-health.md)。

## 安全邊界

- 不繞過 DRM、登入、Cookie、Cloudflare、廣告、付費、地區或網站存取限制。
- Cookie、Token、私鑰、production 憑證與個人資料不得寫入 Repository 或 Log。
- URL、檔案、MOD manifest、IPC 與外部程序輸出一律視為不可信。
- 新安裝或更新的第三方 MOD 預設停用；發布者信任與使用者啟用是兩個獨立決定。
- 宣告式 MOD UI 不執行外部 HTML、Qt 物件或任意腳本。
- Development、Testing 與 Stable 的身分、雜湊、簽章及發布 Gate 不可互相冒用。

第三方 MOD 作者請從 [MOD-DEVELOPMENT.md](MOD-DEVELOPMENT.md) 開始。安全與
發行細節見 [MOD 套件契約](docs/mod-package-v1.md)及
[簽章流程](docs/release-signing.md)。

## Repository 結構

- `core/`：安全、下載、設定、儲存、媒體庫與 MOD 生命週期。
- `trusted_ui/`：PySide6 可信 UI。
- `contracts/`：核心與 MOD 共用的版本化資料契約。
- `mod/builtin/`：可個別啟用或停用的內建 MOD。
- `plugin_host/`：外部可執行 MOD 的受控程序入口。
- `tests/`、`tools/`：回歸測試、品質、版本與發行工具。
- `docs/`：目前有效的規格、狀態與維護文件。
- `Version/`：不可覆寫的 Development／Testing／Stable 產物。

## 驗證

```powershell
.\.venv\Scripts\python.exe -m tools.quality_audit
.\.venv\Scripts\python.exe -m tools.run_tests
.\.venv\Scripts\python.exe -m tools.audit_mod_groups --root .
.\.venv\Scripts\python.exe -m tools.site_quality_audit --root .
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
.\.venv\Scripts\python.exe -m tools.audit_version_docs
.\.venv\Scripts\python.exe -B .\main.py --verify-only
git diff --check
```

Repository 測試應透過 `tools.run_tests` 使用 Repository 外的每輪唯一暫存目錄；
不得讓 raw pytest 回退到 Repository 根目錄。

## 文件

- [文件索引](docs/README.md)
- [目前專案狀態](docs/project-status.md)
- [Development 39.0–40.0 更新紀錄](docs/release-39.0-40.0.md)
- [下載工作契約](docs/downloads-v1.md)
- [第三方 MOD 開發指南](docs/mod-developer-guide.md)
- [版本與發布政策](docs/version-layout.md)
- [GitHub 免安裝自包含 ZIP](docs/self-contained-zip.md)

舊 roadmap、過期候選與逐版日誌不再留在目前樹；需要稽核時由 Git 歷史與
GitHub Releases 的不可變附件追查。已公開的 EXE、checksum、release metadata
與 tag 不得刪除或覆寫。

## License

[MIT](LICENSE)
