# 目前專案狀態

狀態日期：2026-08-01

## 結論

MediaManager 目前工作來源為 Development `39.0.39`。`39.0.13` 修正搜尋聚合
與歷史污染；`39.0.14` 補齊 Search v2 provider 已宣告但通用 UI 無法選擇的
`playlist`／`live` 內容類型；`39.0.15` 改善 YouTube 相似音樂種子查詢精度；
`39.0.16` 防止搜尋詞組別名誤改較長單字；`39.0.17` 保證修正後查詢不突破
Search v2 的 200 字元上限；`39.0.18` 在通用 UI 提供所有已啟用來源的有界聚合搜尋；
`39.0.19` 讓已顯示結果能即時套用片長與語言篩選，不重新送出 provider 請求；
`39.0.20` 讓通用 Search v2 下一頁安全追加，且失敗不再清空已載入結果；
`39.0.21` 統一 YouTube 官方網域別名的搜尋結果身分，避免跨頁或多來源重複列出；
`39.0.22` 修正搜尋 MOD 停用後仍保留舊游標及假啟用控制項的狀態落差；
`39.0.23` 修正相似音樂與替代搜尋未同步檢查其綁定搜尋來源的依賴狀態；
`39.0.24` 讓多來源聚合搜尋可安全追加仍有下一頁的來源；`39.0.25` 在工作區
達到 200 筆有界容量時終止分頁並停用下一頁操作；`39.0.26` 修正所選搜尋
來源消失後可能退回停用來源的狀態錯誤；`39.0.27` 防止搜尋進行中切換來源
狀態後，舊 worker 的晚到結果覆蓋新狀態；`39.0.28` 讓 MOD 管理介面送出的
外部狀態事件也清除舊搜尋結果與分頁游標；`39.0.29` 修正聚合搜尋在各來源
頁面總量大於顯示上限時，游標跳過尚未合併結果的分頁資料遺失；`39.0.30`
防止帶 userinfo 或顯式連接埠的非 canonical URL 佔用官方 YouTube 去重身分；
`39.0.31` 在 Discovery 結果契約統一驗證有界純 HTTPS URL，讓畸形外部結果
被隔離為無效回應，不再中斷其他正常搜尋來源；`39.0.32` 讓共用 Search registry
在派送前拒絕重複或無效的 provider ID，避免配額失真與重複外部請求；`39.0.33`
以有界方式正規化 provider iterable，拒絕字串／不可迭代輸入，且最多讀取
17 項便判定超過 16 個來源上限，避免無限 generator 或過長清單造成無界耗用；
`39.0.34` 讓公開 Discovery service 在來源查找前共用同一正規化入口，不再先
完整展開輸入或把拆解後的字元誤報為不存在的來源；`39.0.35` 統一搜尋結果
上限的型別驗證，拒絕布林、字串與小數被靜默轉成整數後派送。
`39.0.36` 讓 federated provider cursor mapping 在任何搜尋 MOD 派送前有界正規化，
不再完整物化過長 Mapping，亦不接受契約外容器或無效游標值；`39.0.37` 在服務與
registry 入口先驗證 Search v2 查詢欄位，讓無來源與有來源路徑維持同一錯誤契約；
`39.0.38` 拒絕非字串的外層分頁游標，避免假值觸發重複首分頁請求；`39.0.39`
讓搜尋 capability 身分驗證在任何 registry mutation 前完成，失敗註冊不再污染狀態。
已封存的 Testing `1.2.0` 仍以 Development `39.0.11` 為來源；公開的
[Testing `1.2.1`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.1)
仍由 Development `39.0.12` 建置且保持不可變。Testing `1.2.2` 已獲授權由
Development `39.0.39` 的乾淨 source freeze 建置、建立新目錄與 prerelease；
它維持未簽署 Testing 身分，不是 Stable。Development 40.0 仍為
`NO PLAN / NO RELEASE`，Repository 也沒有可發布 Stable 候選。

## 已完成範圍

- 核心、可信 UI、下載佇列、媒體庫、版本與 MOD 生命週期已有非 UI 回歸。
- YouTube、Bilibili、MEGA、Direct HTTP 與 generic Beta 的網站權限分離。
- 官方媒體主機採 exact-host、窄路徑與 provider/site-matrix 一致性檢查。
- 外部 MOD 提供 schema v2、Ed25519 發布者信任、依賴圖、交易復原、受控程序
  與宣告式 UI。
- 格式工廠、localhost-only Gopeed Bridge、選用 Speech to Text 與 Automation
  已納入內建 MOD 管理。
- 可信桌面使用 channel-neutral `MediaManager v1.0` 產品名稱；實際核心與發布
  metadata 仍維持三軌分離。
- Development 39.0.12 的 YouTube 工作區可由單一選取結果啟動相似音樂搜尋；
  候選只使用公開搜尋與既有本機排序，不使用 Cookie、私人推薦或觀看紀錄。
- Development 39.0.13 保留媒體 ID 原始大小寫，避免聚合與跨頁合併漏掉不同
  結果；通用搜尋只在目前世代、初始頁且所有來源成功後寫入本機搜尋歷史。
- Development 39.0.14 的通用搜尋內容類型隨目前 provider capability 動態更新；
  切換來源會移除不支援的類型並優先安全回退至 `all`，不新增網路 fallback。
- Development 39.0.15 的相似音樂查詢優先組合所選結果的歌手與曲名，再保留
  歌手類型、偏好歌手或曲名 related 的有界備援；仍只使用公開 YouTube 搜尋。
- Development 39.0.16 將 `lo-fi`、`sound track`、`bg music` 等本機別名限制
  為完整詞組匹配，不再破壞 `flo-fi`、`sound tracker`、`bg musicology` 等較長單字。
- Development 39.0.17 逐次檢查本機詞組與拼字 correction 的結果長度；若修正
  會突破 200 字元契約便保留原查詢，避免 UI、歷史與 provider 實際查詢分歧。
- Development 39.0.18 將既有 federated search 接入通用 UI；至少兩個來源啟用
  且具有共同內容類型時才顯示聚合選項，結果保留來源與失敗隔離。
- Development 39.0.19 快取最近一次聯合搜尋的原始結果；片長或語言條件改變時
  只在本機重新篩選、排序與顯示；遠端搜尋條件變更、新搜尋、錯誤、相似或替代
  流程會清除舊快取。
- Development 39.0.20 將單一來源的下一頁合併至既有有界結果，沿用 canonical
  identity 去重並保留實際來源；載入更多失敗時保留結果與游標，允許安全重試。
- Development 39.0.21 在 canonical identity 層以 authoritative exact-host 清冊
  統一 YouTube 官方網域別名；第三方網站的相同 ID 與大小寫不同 ID 仍維持獨立。
- Development 39.0.22 在搜尋來源可用性改變時清除舊游標與聯合結果快取；搜尋
  與下一頁按鈕只有在目前單一來源已啟用，或聚合來源仍符合共同能力時才可用。
- Development 39.0.23 讓相似音樂與替代搜尋只有在 `youtube-search` 仍啟用時
  才可操作；服務層會在啟動規劃 MOD 前驗證綁定來源，避免無效子程序與晚期錯誤。
- Development 39.0.24 以有界 HMAC 聚合游標綁定原查詢、內容類型與來源順序；
  下一頁只呼叫仍有游標的來源，canonical 去重追加結果，暫時失敗則保留該來源
  的原游標供重試，已耗盡來源不會重新查詢第一頁。
- Development 39.0.25 在跨頁合併達工作區 200 筆上限時捨棄後續游標；可信 UI
  會停用「下一頁」並顯示已達容量，不再發出無法增加可見結果的重複請求。
- Development 39.0.26 在搜尋來源清單重建時以 provider ID 尋找第一個實際
  啟用來源；不再無條件優先停用的 YouTube，也不依受聚合項位移的位置索引。
- Development 39.0.27 在搜尋條件或 MOD 狀態變更時，若仍有搜尋進行中便遞增
  generation、清除 busy 與游標狀態；晚到回應會因世代不符而被可信 UI 忽略。
- Development 39.0.28 統一 MOD 管理事件與本頁 QAction 的搜尋失效流程；外部
  停用或啟用搜尋 provider 後不再保留可被重新啟用的舊結果快取與下一頁游標。
- Development 39.0.29 將聚合頁面上限公平分配給本次實際查詢來源，讓每個
  provider 的下一頁游標緊接已合併結果；超額回傳會被分類為無效回應，不再
  靜默截斷並前移游標。
- Development 39.0.30 以共用 exact-host 路由判斷 canonical YouTube 身分；
  userinfo、顯式連接埠、非 HTTPS 或不合法路徑不再與合法官方結果互相去重，
  避免外部 MOD 的非 canonical 結果先到後排擠官方項目。
- Development 39.0.31 將既有 Discovery 欄位規則集中到 `DiscoveryItemV1`
  建構邊界，拒絕無主機、畸形 IPv6、超範圍 port、URL credentials、空白控制
  字元與超過 4096 字元的結果 URL；壞來源被分類為無效回應，其他來源仍可顯示。
- Development 39.0.32 在 `SearchAdapterRegistry.search()` 自身驗證 provider 選擇
  必須是唯一、非空的字串；不再只依賴上層 `DiscoveryService`，直接使用 registry
  的呼叫端也不會讓同一 MOD 重複請求或以重複項稀釋每來源頁面配額。
- Development 39.0.33 將 provider iterable 的展開限制為來源上限加一項；字串不再
  被拆成單字元來源，不可迭代輸入統一回報穩定的 validation error，超長或無限
  generator 也不會在拒絕前被完整消耗。
- Development 39.0.34 將來源選擇正規化提升為 `SearchAdapterRegistry` 的共用
  入口，`DiscoveryService.federated_search()` 在可用性／啟用狀態查找前即採用
  同一個 16 項上限與錯誤契約，避免公開服務路徑繞過 39.0.33 的底層防護。
- Development 39.0.35 將搜尋結果上限正規化集中於共用 registry 邊界；公開
  Discovery service 在建立 Search v2 查詢前使用同一入口，非整數型別不再被
  `int()` 靜默截斷或轉換，既有整數 0→1、超過 50→50 行為保持相容。
- Development 39.0.36 將 federated cursor mapping 的展開限制為來源上限加一組；
  只接受 Mapping，並在派送前驗證唯一非空 provider ID 與 1～500 字元游標，
  避免超長輸入的無界物化及無效呼叫被誤列為 provider failure。
- Development 39.0.37 將 Search v2 查詢本身的正規化與型別驗證提升到共用契約；
  即使沒有註冊或啟用任何 provider，空白／非字串查詢、無效內容類型、布林頁面
  大小與非字串游標也會在路由前拒絕，不再靜默回傳空結果或污染 provider 健康狀態。
- Development 39.0.38 在外層簽署游標解碼前先驗證實際字串型別；`None`、布林、
  整數與空容器不再因為是假值而跳過解碼、重查第一頁及改寫來源健康計數。
- Development 39.0.39 在 Search provider 寫入下載 registry 與服務索引前，先建立
  並核對宣告 capability 的 provider ID；身分不符的外部 MOD 失敗後，同 ID 修正版
  可在同一服務實例重新註冊，不再被殘留的「already registered」狀態阻擋。

## 已退役或取消

- 動畫瘋整合已自目前來源與 runtime 註冊移除；舊 UserData 與保留版本不改寫。
- 已取消的 Stable 1.0 候選、舊 Testing 候選與未授權 build 工作目錄都不是
  可發布資產。
- Development 40.0 與後續 roadmap 為 `NO PLAN / NO RELEASE`，不以空版本續號。

## 目前 Testing 工作

- Testing `1.2.0` 本機封存已存在於 `Version/Testing/1.2`，版本稽核確認核心
  為 Development `39.0.11`。封存來源固定為 revision
  `fab5cb9333274e54f65a35b2f44a86699f0f349f`；目前 39.0.39 工作樹不會回寫
  該不可變候選；GitHub 上沒有對應 Testing 1.2.0 Release 或 tag。
- Testing `1.2.1` 已建立於 `Version/Testing/1.2.1`；tag
  `test-v1.2.1` 精確指向 source revision
  `05442d7875da5367cd23babc2ce4e2e3e0cb87a2`。
- 主要下載附件是 `MediaManager-Testing-1.2.1.zip` 與同名 `.zip.sha256`；
  [GitHub prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.1)
  共有 9 個附件，ZIP digest 已與 sidecar 閉合。
- [Testing `1.2.2`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)
  已由 Development `39.0.39` 的乾淨 source freeze
  `f7c65ee1a8e92828ede299bcbdff5e66d16f6810` 建立於
  `Version/Testing/1.2.2`，並以 `test-v1.2.2` 發布為具有 9 個附件的
  prerelease；`MediaManager-Testing-1.2.2.zip` SHA-256 為
  `2dd688ceb6a3af9c3e100dca1c61a326ac8be2a19237b217bd2f8a21b6a7e2c4`，
  已與 ZIP sidecar 及 GitHub asset digest 閉合，且未覆寫 1.2.1。
- Testing 1.0 是不可覆寫的歷史版本，不以目前 39.x 來源重建或冒用。
- Testing 1.1 使用唯一修訂 tag `test-v1.1.0-r2`，精確指向 source revision
  `09b3a86e00938241d27050088583ebf81d9fb182`；9 個附件已發布且 digest 閉合。
- Testing 1.2.1 與 1.2.2 產物維持未簽署 `SAFE_MODE`、非 Stable；實際身分與雜湊以發行頁的
  `release-info.json`、`SHA256SUMS.txt` 與 ZIP sidecar 為準。

## 尚未成立的發行條件

- 沒有同一候選集上的 production Authenticode、Ed25519、checksum、SBOM、
  copied-folder smoke 與 release preflight 證據。
- 截圖只能證明可見版面；Tab／Shift+Tab、UIA／NVDA、讀屏、Windows 高對比及
  真實互動流程仍需人工驗證。
- 外部網站會變動；離線 regression 與 extractor 存在不等於即時網站 smoke。

這些未成立項目不阻擋 Testing 使用，但阻擋任何 Stable 或已簽署正式發布宣稱。

## 歷史與回復

目前樹不保留逐版 roadmap 與重複 release journal。過去決策仍可從 Git 歷史、
不可變 `Version/` 產物及 GitHub Releases 的 checksum／metadata 追查。不得為了
縮小 Repository 而刪除公開附件、改寫 tag、重寫 Git 歷史或清除 UserData。
