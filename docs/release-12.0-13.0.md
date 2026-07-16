# 開發版 12.0～13.0 更新紀錄

本文件集中記錄 12.x 的實際完成內容；開發次版本會依序附加於同一文件。這些內容是
Development 來源事實，不代表 Stable 正式版已建立、簽署或發布。

## 12.0（尚未封裝的來源更新）

- 新增預設關閉的 `direct-http` 父 MOD 與獨立可信工作區。它只接受明確 HTTPS
  檔案副檔名，不解析一般網頁、播放器、登入頁或串流 manifest。
- YouTube、Bilibili、動畫瘋、Facebook、Instagram、X、MEGA 及通用影音站的官方
  網域明確排除，不會被 Direct HTTP 搶接；中央網站路由也不新增通用後備規則。
- URL 禁止帳密、非預設連接埠、fragment、私有／回送／保留位址，初始主機及每次
  HTTPS 重新導向都重新驗證；檔案上限為 64 GiB。
- 下載採同目錄 `.part` 暫存，伺服器回應 `206 Partial Content` 時才續傳；完成後原子
  更名。使用者可為單檔指定 64 位十六進位 SHA-256，不相符時刪除不可信部分檔。
- 專屬 UI 提供單檔資訊、最多 100 筆批量、暫停／繼續／停止、重試、進度與安全輸出
  位置，不混入影音格式、字幕、彈幕或播放清單選項。
- 內建 MOD 數量增為 26；Bootstrap、能力宣告、MOD 管理、選用工作區及固定
  SHA-256 完整性清單同步更新。
- 最終驗證為 Ruff 通過、801 項 Pytest 通過；2 項 Windows symlink 測試因目前帳戶
  權限跳過。MOD 群組、依賴鎖檔、網站品質、保留版本與文字污染稽核均通過。
- 本輪只更新開發來源與整檔紀錄；未建立 `Version/Development/12.0`、EXE、
  `release-info.json`、`SHA256SUMS.txt` 或 GitHub Release，也未建立 Stable 版本。

## 12.1（已建立本機 Development 成品）

- 強化 MOD 管理內既有的可信手動自我檢查，不新增會與診斷頁重複、或可能把自身停用的
  provider。檢查仍只在使用者按下按鈕後執行，不連網、不啟動 provider、下載器或
  媒體工具，也不建立完整測試程序。
- 新增父／子 MOD 實際啟用狀態檢查；只有「父 MOD 存在且已停用，但子 MOD 仍啟用」
  才產生狀態阻擋，避免和 registry 缺少項目重複計算同一錯誤。
- 新增四語言綁定檢查，核對核心設定、外部宣告式 MOD UI locale，以及 7 個網站父
  MOD 的語言資源是否一致。
- 新增靜態網站路由矩陣，核對 YouTube／Music、Bilibili、Facebook、MEGA、動畫瘋
  與 Direct HTTP 網域隔離，不發出網路請求。
- 自我檢查會讀取目前 MOD 管理樹，驗證父 MOD 停用時子 MOD 不顯示、實際勾選狀態、
  按鈕是否可用，以及主視窗選用工作區、語言選單與停用下載 MOD 的關鍵按鈕狀態。
- 修正動畫瘋集數路由仍宣告規劃中 `ani-gamer-offline` 為下載 owner 的問題；現階段
  只保留官方搜尋與播放頁導覽，不宣告尚未完成的離線下載能力。
- 自我檢查結果表新增可直接閱讀的詳細資訊欄，保留穩定 remediation ID 與去識別
  JSON 匯出。
- Ruff 與 804 項 Pytest 通過；另有 2 項 Windows symlink 測試因目前帳戶權限跳過。
  MOD 群組、版本、依賴鎖檔、網站品質與文字污染稽核均通過。
- 已建立全新的 `Version/Development/12.1`，沒有替換舊版本；共 82 個檔案、
  385,212,173 bytes，`SHA256SUMS.txt` 驗證其中 81 個成品檔案全部通過。
- `MediaManager.exe` 為 80,765,566 bytes，SHA-256：
  `D897FA764D35EBD922A4852D3E45FE297D19CCB73AE56DA02FD637550D59A224`。
  wheel SHA-256：`24B14DCA0D8090873C61575511B4D86C53706C89B5101012D4D78AE42EE3CF4A`。
- 一次性 Ed25519 演練核對 79 個發行檔、成功偵測竄改且未保留私鑰；copied-folder
  的 `--version`、`--portable --verify-only`、`--portable --headless` 均以 exit code 0
  完成，GUI 也可正常啟動，smoke 複本及殘留程序已清除。
- 公開 provider analyze smoke 7/7 通過：YouTube、Vimeo、Dailymotion、SoundCloud、
  TikTok、Twitch 與 Bilibili 均取得有效 ID 與標題，未下載媒體。
- production Ed25519 身分仍未設定，EXE 的 Authenticode 為 `NotSigned`，因此正式發布
  preflight 維持阻擋；本成品只能作為 Development／`SAFE_MODE`，尚未建立 GitHub
  Release，也未建立 Stable 版本。

## 12.2（UI 修正版與 Threads 父／子 MOD）

- MEGA 專屬工作區改用可調整內容高度的垂直捲動區；下載佇列表保留最低可讀高度，
  `MEGAcmd` 分流說明移至獨立一列。矮工作區不再壓住優先級與加入佇列按鈕，且不產生
  水平捲動。
- 動畫瘋官方目錄把過寬的篩選列拆為兩列，作品與集數表的官方網站欄採固定寬度，
  作品封面與標題欄保留伸縮空間；選取作品並讀取集數後會顯示作品名稱，並將集數區
  自動捲入可視範圍。
- 執行環境表將「核心」與「選用 MOD」明確分開；選用工具未安裝時顯示
  「未安裝（不影響核心）」及所影響的 MEGA／Speech to Text MOD，不再使用模糊的
  「待處理」。完整工具路徑可由提示閱讀，也可直接複製。
- Threads 從唯讀候選清單升格為預設停用的獨立父 MOD，並新增 `threads-page` 官方
  貼文頁與 `threads-export` 官方資料匯出兩個子 MOD。父 MOD 啟用後才顯示並允許管理
  子 MOD；支援繁中、簡中、英文、日文，舊 `threads.net` 貼文會正規化至
  `threads.com`。
- Threads 現階段只開啟經驗證的官方貼文與 Meta 官方資料匯出說明，可安全預覽並
  匯入使用者自行取得的官方封存 ZIP；不讀取 Cookie、不使用網站自動化，也不宣稱
  具有未驗證的線上下載能力。
- 針對 MEGA、動畫瘋、依賴表與 Threads 的 136 項回歸測試已通過；全專案為
  808 項通過、2 項 Windows symlink 權限跳過。
- 首次建立的 `Version/Development/12.2` 揭露舊發行清單未帶入 Instagram、Threads、
  X/Twitter 等較新的宣告式 MOD。依不可覆寫規則保留該資料夾供稽核，但明確標記為
  **封裝不完整、不可發布或交付使用**；修正移至 12.3，不回寫 12.2。

## 12.3（發行清單完整性修正）

- 發行來源清單改以 `BUILTIN_PROVIDER_HASHES` 的固定 SHA-256 項目為真相來源，自動
  納入每個內建 MOD 的 provider、feature、group、locale 與政策檔，不再依賴容易漏項
  的舊手動清單。
- 新增回歸測試，要求發行資料夾內的 `mod/builtin` 清單與完整性固定清單完全相等；
  Threads、Instagram、X/Twitter 與 Direct HTTP 均不得再只存在於來源或 EXE 而漏出
  可攜版本資料夾。
- 已建立全新的 `Version/Development/12.3`，不覆寫 12.2；本機依 current + previous
  規則保留 12.2 與 12.3，12.1 已由建置工具依保留政策清除。
- 12.3 共 108 個檔案、385,261,187 bytes；`SHA256SUMS.txt` 驗證 107 個成品檔案
  全部通過，91 個固定內建 MOD 檔案零缺漏。Threads 父／子 MOD 與四語言共 8 個
  檔案均存在於可攜版本資料夾。
- `MediaManager.exe` 為 80,773,772 bytes，SHA-256：
  `446DDB1F9F9C32B05B272AFC47E8D784D72857FDD73666E4B19E4CFB31273A49`；wheel
  SHA-256：`E88C673F44C16FCEC09DE6881019DD9DFC18927E294752675DF233DF30022639`。
- copied-folder 的 `--version`、`--portable --verify-only`、`--portable --headless`
  均為 exit code 0，GUI 可持續啟動。one-file 子程序以精確執行檔路徑辨識後結束，
  smoke 複本已成功清除。
- 一次性 Ed25519 演練驗證 105 個發行檔、成功偵測竄改且沒有保留金鑰；完整來源測試
  為 Ruff 通過、809 項 Pytest 通過，2 項 Windows symlink 權限跳過。
- production Ed25519 身分仍未設定，EXE Authenticode 為 `NotSigned`，因此正式發布
  preflight 維持阻擋。12.3 僅標記為「目前可用 Development／SAFE_MODE」，不是
  Stable，也尚未建立或上傳 GitHub Release。

## 12.4（12.x 優化方案改正）

- 12.x 從零散擴張改成「先收斂再升版」：封裝完整性、響應式 UI、父／子 MOD 啟用、
  網域路由與四語言列為同一驗收門，不再以新增網站掩蓋既有功能未顯示或按鈕失效。
- 12.2 永久保留為封裝缺項的稽核證據，不回寫、不發布；12.3 成為唯一可用基線。
  12.4～12.9 只記錄來源里程碑，不建立六個重複的大型資料夾。

## 12.5（動畫瘋響應式工作區收斂）

- 作品篩選拆列、表格固定官方網站欄寬、作品與集數區保留最低高度；940×620 與更矮
  視窗均使用垂直捲動，不產生水平白色破圖。
- 選取作品並取得集數後顯示作品名稱、把集數區捲入畫面；作品／集數未選取時，後續
  動作保持停用，不再讓無效按鈕先執行再報錯。

## 12.6（父／子 MOD 與封裝來源收斂）

- 動畫瘋固定為 `ani-gamer` 父 MOD，下含 `ani-gamer-search`、
  `ani-gamer-episodes` 與 `ani-gamer-offline`；只有父 MOD 開啟時才顯示及允許開關子 MOD。
- 作品網址歸搜尋子 MOD，單集網址歸集數子 MOD，避免所有動畫瘋網址都錯綁同一搜尋器。
- 發行檔案繼續由內建 SHA-256 固定清單自動導出；新增子 MOD 若未被封裝，回歸測試會
  直接失敗，不再產生「來源有功能、可攜資料夾沒有」的成品。

## 12.7（選取單集離線索引）

- `ani-gamer-offline` 從「製作中」升格為真實、預設停用的宣告式子 MOD。只有使用者
  已選取官方作品與單集時，才能以原子寫入保存公開作品資料、單集資料及已載入封面。
- 每筆索引有 schema、官方網址、安全邊界與建立時間；檔名會清除 Windows 危險字元，
  所有輸出必須留在使用者選定資料夾內，拒絕符號連結與不安全既有路徑。

## 12.8（本機媒體匯入與取消清理）

- 使用者可明確選取自己已合法取得的本機影音檔，背景複製到該單集索引；副檔名與大小
  有上限，輸出採 `.part` 加原子更名，不覆寫既有媒體。
- 匯入可取消；取消、來源中途變更或寫入失敗時清除暫存檔。成功後記錄相對路徑、位元組
  數與 SHA-256，乾淨啟動不會自動繼續或建立任何下載工作。

## 12.9（四語言、自我檢查與錯誤回復）

- 番劇儲存名稱、用途、按鈕、狀態與錯誤訊息完整加入英文、日文、簡中、繁中；語言仍
  只由核心設定決定，不由子 MOD 保存第二份選擇。
- 手動唯讀自我檢查新增動畫瘋番劇儲存按鈕探針，核對父／子 MOD、作品／集數選取、
  保存、匯入及取消狀態；檢查不建立工作區、不連網、不啟動 provider。

## 13.0（動畫瘋父／子 MOD 完整整合）

- 12.4～12.9 的收斂項目合併為開發版 13.0；`ani-gamer-offline` 已移出製作中清單，
  並與搜尋、集數導覽一同顯示在動畫瘋父 MOD 下。
- 13.0 的「離線」明確指公開索引、封面與使用者本機媒體副本；它不擷取動畫瘋串流、
  不下載彈幕、不讀取 Cookie，也不繞過 DRM、登入、付費、地區、廣告或網站限制。
- 如果使用者沒有合法本機媒體，仍可保存作品／單集索引並以官方播放頁觀看；介面不會
  把這種降級結果誤標成影片下載成功。
- Ruff 與 813 項 Pytest 通過；2 項 Windows symlink 測試因目前帳戶權限跳過。
  MOD 群組為 8 組／4 語言，文字污染掃描通過 486 個檔案。
- 已建立全新的 `Version/Development/13.0`，沒有覆寫 12.x；共 109 個檔案、
  385,290,451 bytes，`SHA256SUMS.txt` 驗證 108 個成品檔案全部通過。92 個固定內建
  MOD 檔案與外部 `ani-gamer-offline/feature.json` 均零缺漏。
- `MediaManager.exe` SHA-256：
  `399873EB9AE32913779B75D415542A48B4535F17A810E0A9C3EFD43D65F29A29`；wheel
  SHA-256：`553CFAA6CD3A497EDFE48059B75C4780959F318643630E543743D39B57E7D061`。
- copied-folder 的 `--version`、`--portable --verify-only`、`--portable --headless` 均為
  exit code 0，隱藏 GUI 可持續執行；精確複本程序與 smoke 資料夾已清除。
- 一次性 Ed25519 演練驗證 106 個發行檔、成功偵測竄改且未保存私鑰。production
  Ed25519 身分仍未設定，EXE Authenticode 為 `NotSigned`，因此 preflight 只因這兩個
  正式發行身分條件維持阻擋；13.0 是 Development／`SAFE_MODE`，不是 Stable。
- 公開 provider analyze smoke 連續兩次為 6/7：YouTube、Vimeo、SoundCloud、TikTok、
  Twitch 與 Bilibili 通過；固定 Dailymotion 樣本的官方 JSON 端點兩次回 HTTP 502。
  此上游失敗保留為已知警告，沒有降低 smoke 標準，也沒有改成假通過。

12.x 與 13.0 內容集中在本文件，不為每個次版本建立零散 release 檔。
