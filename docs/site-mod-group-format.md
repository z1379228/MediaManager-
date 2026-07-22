# 網站父 MOD／子 MOD 與語言契約

目前所有能顯示在可信 UI 的網站功能都必須遵守下列規則；下載、搜尋與宣告式功能
三種內建登錄表共用同一套父子生命週期及四語言來源。

## 資料與語言

- 每個網站主 MOD 使用一個英文 `group_id`，例如 `youtube`、`bilibili`。
- 主目錄提供受核心雜湊保護的 `group.json` 與 `locales/`；只允許 `en`、`ja`、
  `zh-CN`、`zh-TW` 四個檔案，且每個檔案必須完整覆蓋該群組所有可見子 MOD。
- 語言檔可包含受驗證的 `ui` 字串表，供可信工作區顯示欄位、動作、狀態與錯誤。
  字串鍵與長度都有上限，MOD 不能藉此注入 HTML、Qt 物件或可執行內容。
- 核心 `settings.language` 是唯一語言來源。MOD 不保存第二份語言選擇；核心切換語言後
  發布 `ui.language.changed`，工作區、MOD 管理與搜尋來源同步重新讀取同一語言檔。
- 未知語言回退到 `zh-TW`；缺檔、少翻譯、額外欄位或無效 UTF-8 均視為群組驗證失敗，
  不可用空白頁或其他語言假裝成功。

## 父子生命週期

- 主 MOD 永遠可見；子 MOD 只有在主 MOD 已啟用時才顯示並允許開關。
- 停用主 MOD 會同步停用已啟用的子 MOD，取消主 MOD 擁有的工作，並發布每個狀態事件。
- 舊設定若出現「主 MOD 關閉、子 MOD 開啟」，Bootstrap 在建立 UI 前自動改為關閉子 MOD。
- YouTube 的主 MOD 是 `youtube`，子 MOD 為搜尋、影片試看、歷史、失效替代、相似內容
  與自動切割；YouTube Music 是同一網站家族，不另建重複主 MOD。
- Bilibili 的主 MOD 是 `bilibili`，子 MOD 是 `bilibili-search` 與
  `bilibili-danmaku`。停用彈幕子 MOD 時，下載仍可使用，但 XML、ASS 與 MKV
  控制會隱藏並清除，避免把額外能力誤當成主下載必要條件。
- 動畫瘋的主 MOD 是 `ani-gamer`，子 MOD 為負責目錄／作品搜尋的
  `ani-gamer-search`、負責分頁集數導覽的 `ani-gamer-episodes`，以及只保存選取單集
  公開索引、封面與使用者本機媒體的 `ani-gamer-offline`。主 MOD 未啟用時不顯示
  子 MOD；搜尋子 MOD 關閉時不發出目錄或搜尋請求，集數子 MOD 關閉時不讀取作品
  集數，番劇儲存子 MOD 關閉時保存與匯入按鈕不可用。G38-02 的動畫瘋 Cookie 只存於
  程序記憶體，停用父 MOD 或結束程式時清除；官方播放仍由官網處理。
- `facebook` 與 `mega` 是沒有子 MOD 的獨立主 MOD；兩者預設
  停用，啟用後才建立各自下載工作區。Facebook 不與 Instagram／Threads 共用下載
  provider；MEGA 也不經 `generic-ytdlp`。

## 各網域能力邊界

- YouTube／YouTube Music：影片、播放清單、格式、字幕、試聽／預覽及選用子功能。
- Bilibili：影片、番劇、分 P 與字幕；彈幕下載及轉換由獨立子 MOD 管理。
- Facebook：只處理使用者提供的公開影片頁，無音訊格式、字幕、分段或播放清單控制。
- MEGA：只處理公開檔案／整個公開資料夾傳輸與種類辨識，不顯示影音格式、字幕、試聽或播放清單。
- 動畫瘋：官方公開目錄、分類、搜尋、封面、分頁集數導覽、官方播放入口，以及選取
  單集的公開索引／本機媒體保存。G38-02 是唯一 Cookie 例外：只接受使用者主動貼上、
  只存於程序記憶體，且只供目錄／集數 discovery 對精確的
  `https://ani.gamer.com.tw` 使用。
- 動畫瘋 Cookie 不得來自瀏覽器 profile／Cookie DB，不自動更新且不接受 Cloudflare
  token；不得注入 WebEngine／系統瀏覽器，也不得供 downloader、離線保存或彈幕使用。
  動畫瘋仍不提供串流攔截／擷取、網站串流下載、廣告處理，或登入、DRM、付費、地區、
  Cloudflare 等限制的規避。

## 網域隔離

- 一個可執行 provider 只能屬於一個網站群組；`provider_id` 不可跨群組重複。
- `network.<site>` 權限與搜尋 `sites` 必須等於父群組，不得用 YouTube 代查 Bilibili
  或動畫瘋，也不得在 YouTube 工作區顯示其他網站選項。
- 每個群組與四語言資源都納入內建 MOD SHA-256；執行
  `python -m tools.audit_mod_groups --root .` 可快速檢查群組、語言與 provider 邊界。
- `generic-ytdlp` 是 9.1 暫留且預設停用的舊 Beta 相容 provider，沒有 YouTube／
  Bilibili 工作區入口。其網站必須逐站遷移成獨立主 MOD；新網站禁止加入此聚合 provider。

## 15.0 工作流能力矩陣

- 每個內建網站父 MOD 必須在自己的目錄提供受雜湊保護的 schema v2
  `site-matrix.json`，不可把網站能力硬塞入另一個父 MOD。
- 矩陣逐一宣告辨識、發現、分析、預覽、排隊、取消與完成七個階段；只能使用
  `supported`、`conditional`、`browser-mediated` 或 `not-applicable`。
- `ui_capabilities` 決定搜尋、縮圖、影音預覽、批量、下載、彈幕、官方頁、樹狀預覽
  與離線封存是否可顯示。沒有宣告的能力不得借用其他網站控制。
- `features` 使用有界且唯一的 ID，並區分已驗證公開分析、離線契約、本機 FFmpeg 或
  必須由官方瀏覽器處理的能力；`boundaries` 必須明列 Cookie、登入、地區、付費、
  DRM、廣告與私人內容限制。
- `python -m tools.site_quality_audit --root .` 只讀取這些固定 JSON，不連網、不啟動
  provider，也不建立暫存檔；Self Check 顯示同一份稽核摘要。

## 子網域路由

- 子網域不建立重複父 MOD；只有經確認的官方精確主機名稱與路徑才回到既有父 MOD。
- `music.youtube.com`、`m.youtube.com`、`youtu.be` 與只允許 `/embed/<id>` 的
  `www.youtube-nocookie.com` 都屬於 YouTube；隱私嵌入網域不接受 watch、playlist、
  shorts 或 live 等其他路徑。
- `space.bilibili.com` 只負責 UP 主清單，`b23.tv` 只負責短網址；
  `search.bilibili.com/all?keyword=...` 只歸屬 Bilibili 搜尋子 MOD，沒有下載 owner，
  因此不能誤送到下載佇列。
- Instagram 行動頁 `m.instagram.com` 正規化到 `www.instagram.com`；已確認的
  `mobile.x.com` 與既有 `mobile.twitter.com` 正規化到 `x.com`。這些官方工具入口
  不會因此自動取得下載能力。
- 不使用萬用字元子網域，也不接受 HTTP、明示連接埠、內嵌帳密、相似字網域或任意
  查詢欄位。新增子網域時必須同時補成功、錯誤網域及錯誤路徑測試。
