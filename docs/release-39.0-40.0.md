# Development 39.0–40.0 更新紀錄

本文件是目前開發世代的 canonical release 摘要；逐工作包的歷史證據仍由 Git
歷史與不可變版本附件保存。產品顯示名稱 `MediaManager v1.0` 不取代核心、Testing
或 Stable 的三軌版本身分。

## 39.0.0–39.0.8

- 完成本機格式工廠、FFmpeg／ffprobe 能力與輸出驗證、原子提交及失敗回復。
- 完成 localhost-only Gopeed Bridge／P2P Transfer、Direct HTTP 安全邊界及選用
  Speech to Text 相依檢查。
- 固定 Stable `1.0.0`、Testing `1.1.0` 與 Development 的獨立公開身分。
- 加入 receipt-bound build handoff、不可覆寫版本資料夾、本機歷史清理計畫器及
  production Ed25519 公開信任身分；正式私鑰不進入 Repository。

## 39.0.9–39.0.10

- 新增 `player.bilibili.com` 與 `w.soundcloud.com` 的 exact-host、窄路徑／查詢
  驗證及 provider／site-matrix／integrity 一致性回歸。
- 可信桌面改用 channel-neutral `MediaManager v1.0` 顯示；內部相容、MOD 與
  release metadata 仍使用 Development `39.0.10`。
- GitHub 文件收斂為目前狀態、有效契約與本摘要；已結案 roadmap、過期候選與
  退役功能文件由 Git 歷史追查，不覆寫已公開附件。
- 暫存清理保留 `dist/UserData` 及整個 `.work`；`.work` 可能包含 rollback
  backups、build receipts、Git worktrees 與驗證證據，只能經精準人工稽核清除。

## 39.0.11

- YouTube 搜尋新增內容類型、頁面／數量、時長、排序、來源與顯示欄位，並保留
  多來源搜尋的逐 provider 上限及取消、歷史與選取流程。
- 新增只接受已稽核 staged release 的 deterministic 自包含 ZIP 工具；拒絕
  UserData、秘密、link-like、路徑衝突、來源 revision 不一致與覆寫既有附件。
- Testing 公開候選身分升為 `1.2.0`；`MediaManager v1.0` 產品名稱及 Stable
  `1.0.0` 身分不變。
- 候選來源已通過 `90` 項定向回歸、完整 `1364 passed, 7 skipped`、quality
  audit、Repository 外 compileall、版本／MOD／網站／依賴稽核及
  `git diff --check`。
- 本次獲授權 commit 作為 Development `39.0.11` source freeze；build、未簽署
  EXE、Testing staging 與 ZIP 亦已獲授權，但仍必須由工具輸出證明。push、
  簽署與發布未獲授權，不得將 1.1 產物改名為 1.2。

## 39.0.12（工作來源）

- YouTube 專用工作區新增「搜尋相似音樂」入口；只在恰好選取一筆結果且
  YouTube 主 MOD、搜尋 MOD 與相似內容 MOD 均啟用時可執行。
- 相似候選沿用既有 `youtube-similar` 排序及公開 `ytsearch` 管線，固定使用
  music query scope、單次最多顯示 20 筆，並排除原始項目與重複影片；搜尋
  提示不等於 YouTube 官方分類，候選內容仍需由使用者確認。
- 此流程不讀取 Cookie、觀看紀錄或私人推薦 API，不自動下載，也不改變現有
  Testing `1.2.0` 產物。Development `39.0.12` 已被選為 Testing `1.2.1`
  來源，並已由 revision `05442d7875da5367cd23babc2ce4e2e3e0cb87a2`
  完成 source freeze、未簽署 EXE、自包含 ZIP 與 GitHub prerelease。
- 工作來源驗證：完整 repository runner `1388 passed, 7 skipped`；Ruff／文字污染
  quality audit 覆蓋 `366 / 474` 個檔案，Repository 外 compileall 通過。
- 稽核證據：版本文件 `4`、MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`；本機保留的 Testing `1.1` 與 `1.2` 共 `2` 個版本均通過 checksum 稽核。

## 39.0.13（搜尋正確性修正）

- 修正搜尋 canonical key 對 `video_id` 使用不分大小寫比較的根因；媒體 ID 的
  大小寫屬於來源身分一部分，現在只正規化主機名稱，避免聚合或跨頁合併時把
  `AbC123` 與 `aBc123` 等不同結果無聲合併。
- 通用網站搜尋的本機歷史改為只記錄目前 generation 的初始搜尋成功結果；取消／
  過期回應、下一頁、執行失敗及含 provider failure 的部分結果不再污染歷史建議。
- 本修正版不新增網站、主機權限、內容類型或網路 fallback，不改寫已公開的 Testing
  `1.2.1`。尚未取得 build、Testing `1.2.2`、stage、commit、push 或發布授權。
- Regression-first 證據：舊實作會把 `AbC123` 與 `aBc123` 合併成一筆；通用
  搜尋在載入下一頁後會把同一 query 記錄兩次。修正後定向搜尋、歷史、UI 狀態與
  版本回歸為 `89 passed`，完整 repository runner 為
  `1391 passed, 7 skipped`。
- Quality audit 通過 Ruff `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案；
  MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4` 及
  本機 Testing `1.2`／`1.2.1` 共 `2` 個保留版本均通過。Repository 外
  compileall、source-only `--verify-only` 與 `git diff --check` 亦通過；verify
  正確維持未簽署 development `SAFE_MODE`。

## 39.0.14（Search v2 內容類型能力對齊）

- 修正通用搜尋 UI 固定只提供 `all`／`music`／`video` 的能力落差；內容類型
  現在依目前選取 provider 的 `SearchCapabilityV2.content_types` 動態建立，正式
  支援第三方 Search v2 MOD 已可宣告的 `playlist` 與 `live`。
- 切換搜尋來源時保留仍受支援的選項；原選項不受新來源支援時優先回退至 `all`，
  否則使用 provider 宣告的第一個類型。游標仍會失效，避免跨來源或跨類型重用。
- 不替 YouTube 或 Bilibili 虛構未宣告的 playlist／live 搜尋能力，不新增主機、
  權限、Cookie、跨站 fallback 或網路請求。Testing `1.2.1` 保持不可變。
- Regression-first 證據：測試 provider 宣告 `all/playlist/live` 時，舊 UI 仍只顯示
  `all/music/video`；修正後能依 provider 切換選項，服務層亦驗證可路由擴充類型。
- 定向搜尋、UI、服務契約與版本回歸為 `68 passed`；完整 repository runner 為
  `1393 passed, 7 skipped`。Quality audit、MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、保留版本 checksum、Repository 外
  compileall、source-only `--verify-only` 與 `git diff --check` 均通過。
- 本輪尚未取得 build、Testing `1.2.2`、stage、commit、push 或發布授權。

## 39.0.15（YouTube 相似音樂種子精度）

- 修正相似音樂只分別搜尋「歌手 + music」與「曲名 + related」、沒有將使用者
  選取結果的歌手與曲名放在同一查詢的精度缺口。常見或很短的曲名不再先產生
  過寬的純歌手候選。
- 查詢計畫現在優先使用「歌手 + 曲名」，接著保留「歌手 + 類型」及偏好歌手或
  曲名 related 的有界備援；最多仍為 3 個查詢，沿用原本的去重與 200 字元上限。
- 若曲名已包含歌手名稱，不重複附加歌手。此修正不讀 Cookie、私人推薦或觀看
  紀錄，不新增主機、權限、下載或網路 fallback；Testing `1.2.1` 保持不可變。
- Regression-first 證據：以歌手 `Aimer`、曲名 `Stay` 為種子時，舊計畫第一查詢
  是過寬的 `Aimer music`；修正後第一查詢為 `Aimer Stay`，並保留 music 備援。
- token 邊界、UTF-8 IPC、Bootstrap 與內建 MOD 完整性定向回歸為
  `27 passed, 1 skipped`；完整 repository runner 為
  `1394 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1` 共 `2` 個保留版本、
  Repository 外 compileall、source-only `--verify-only` 與 `git diff --check` 均通過。
- 本輪尚未取得 build、Testing `1.2.2`、stage、commit、push 或發布授權。

## 39.0.16（搜尋詞組別名邊界修正）

- 修正本機搜尋清理以單純子字串取代詞組別名的根因；`lo-fi`、`sound track`、
  `bg music` 現在只在完整詞組邊界匹配，不再破壞 `flo-fi`、`sound tracker`、
  `bg musicology` 等合法的較長單字。
- 修正只影響既有有界本機查詢清理，不新增別名、網路 fallback、主機、權限、
  Cookie 或下載行為；Testing `1.2.1` 保持不可變。
- Regression-first 證據：舊實作把測試輸入改為
  `flofi beats soundtracker background musicology`；邊界修正後保留原查詢且沒有
  虛假的 correction 紀錄。
- 定向搜尋、UI、相似音樂與版本回歸為 `79 passed`；完整 repository runner 為
  `1395 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1` 共 `2` 個保留版本、
  Repository 外 compileall、source-only `--verify-only` 與 `git diff --check` 均通過。
- 本輪尚未取得 build、Testing `1.2.2`、stage、commit、push 或發布授權。

## 39.0.17（搜尋 correction 長度契約）

- 修正查詢先截為 200 字元、再因詞組別名或拼字 correction 擴張而突破 Search v2
  上限的契約落差；通用搜尋 UI、YouTube 工作區、歷史與 provider 因此可能持有
  不同長度的查詢。
- 每個 correction 現在先建立候選結果，只有候選仍不超過 200 字元才套用；超限時
  保留使用者原查詢，且不產生未實際套用的 correction 紀錄。既有短查詢修正不變。
- Regression-first 證據：200 字元並以 `bg music` 或 `offical` 結尾的查詢，舊
  實作分別擴張至 208 與 201 字元；修正後均保持原本 200 字元。
- 修正只影響本機查詢正規化，不新增網路 fallback、主機、權限、Cookie 或下載
  行為；Testing `1.2.1` 保持不可變。本輪亦尚未取得 build、Testing `1.2.2`、
  stage、commit、push 或發布授權。
- 定向搜尋、UI、相似音樂與版本回歸為 `80 passed`；完整 repository runner 為
  `1396 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1` 共 `2` 個保留版本、
  Repository 外 compileall、source-only `--verify-only` 與 `git diff --check` 均通過。

## 39.0.18（通用 UI 多來源聚合搜尋）

- 接通服務層既有的有界 federated search：通用搜尋來源選單在至少兩個搜尋 MOD
  已啟用且存在共同內容類型時，新增「所有已啟用來源（聚合）」選項。
- 聚合內容類型取所有已啟用來源 capability 的交集，不把某一 provider 專屬的
  `playlist`／`live` 等類型傳給不支援的來源；各結果仍保留實際 provider 身分。
- 聚合搜尋沿用既有逐來源上限、交錯合併、canonical 去重與來源失敗隔離。由於
  Search v2 游標綁定單一 provider，聚合模式只載入各來源第一頁；使用者可切回
  單一來源使用下一頁，不會混用或猜測跨來源游標。
- 本機歷史、相似、替代與預覽的 YouTube-only 邊界不變；聚合查詢不寫入 YouTube
  搜尋歷史。此功能不新增 provider、主機、權限、Cookie、下載或網路 fallback，
  Testing `1.2.1` 保持不可變。
- Regression-first 證據：兩個來源均啟用時，舊 UI 仍沒有聚合選項；修正後只顯示
  共同內容類型、明確路由兩個 provider，且即使兩者都回傳 cursor 也不開放聚合分頁。
- 定向搜尋、UI、相似音樂與版本回歸為 `81 passed`；完整 repository runner 為
  `1397 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1` 共 `2` 個保留版本、
  Repository 外 compileall、source-only `--verify-only` 與 `git diff --check` 均通過。
- 本輪尚未取得 build、Testing `1.2.2`、stage、commit、push 或發布授權。

## 39.0.19（搜尋結果片長與語言即時篩選）

- 修正通用搜尋只在結果首次抵達時讀取片長與語言條件的缺口；結果已顯示後切換
  任一條件，舊 UI 不會更新表格，容易讓使用者誤以為篩選器無效。
- 現在保留最近一次 `FederatedSearchResult` 的有界本機快取，條件變更時重新執行
  既有 `matching_search_indices` 與本機排序，再更新表格，不呼叫搜尋 provider。
- 遠端搜尋條件變更、開始新的搜尋、相似或替代流程，以及錯誤或非聯合搜尋結果
  抵達時會清除快取，避免舊資料在不同工作間被重新顯示；來源、權限、Cookie 與
  網路 fallback 均不變。
- Regression-first 證據：載入短片繁中、長片繁中與短片英文共 3 筆後，舊實作
  切換「4 分鐘內」仍顯示 3 筆；修正後依序收斂為 2 筆及繁中 1 筆，且 provider
  搜尋 mock 維持未呼叫；再變更遠端筆數條件後，本機篩選也不會復活舊快取。
  Testing `1.2.1` 保持不可變。
- 定向搜尋、UI、相似音樂與版本回歸為 `82 passed`；完整 repository runner 為
  `1398 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1` 共 `2` 個保留版本、
  Repository 外 compileall、source-only `--verify-only` 與 `git diff --check` 均通過。
- 本輪尚未取得 build、Testing `1.2.2`、stage、commit、push 或發布授權。

## 39.0.20（通用搜尋安全追加下一頁）

- 修正通用 Search v2 的「下一頁」直接取代第一頁，且載入更多例外會清空先前
  成功結果的缺口；該 UI 沒有上一頁控制，因此舊行為會使使用者無法回到既有結果。
- 新增共用的有界 federated page 合併：依 canonical media identity 去重、保留
  首次出現順序與每筆實際來源，總數維持最多 200 筆；游標只採用最新成功頁。
- 下一頁例外或單一來源失敗且沒有新項目時，既有結果與原游標會保留，使用者可
  重試同一頁；初始搜尋失敗仍採既有清空行為，聚合搜尋仍不提供跨來源分頁。
- Regression-first 證據：第一頁 `one / two`、第二頁 `two / three` 在舊實作只剩
  `two / three`；修正後為 `one / two / three`。再模擬下一頁例外，3 筆結果維持，
  狀態明確顯示「載入更多失敗」。Testing `1.2.1` 保持不可變。
- 定向搜尋、UI、分頁、相似音樂與版本回歸為 `84 passed`；完整 repository
  runner 為 `1400 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 均通過。
- 本輪尚未取得 build、Testing `1.2.2`、stage、commit、push 或發布授權。

## 39.0.21（YouTube 官方網域別名去重）

- 修正 canonical media identity 將 hostname 直接納入影片 ID 鍵的缺口；同一支
  YouTube 影片若跨 `www.youtube.com`、`youtu.be`、`music.youtube.com` 等官方
  網域別名出現在不同頁或不同來源，舊實作會重複列出。
- 身分正規化只採用 `core.site_routing.YOUTUBE_HOSTS` 的 authoritative exact-host
  清冊，不接受 suffix 或相似網域，也不改變網站路由、存取、下載或 provider 權限。
  第三方網站的相同 `video_id` 仍保留為不同結果，opaque ID 大小寫也維持敏感。
- Regression-first 證據：第一頁 `www.youtube.com/watch?v=SameId`、第二頁
  `youtu.be/SameId` 與 `example.com/watch?v=SameId` 在舊實作共顯示 3 筆；修正後
  只合併兩個官方 YouTube 別名，第三方結果保留。相關分頁、路由與 Discovery
  初步回歸為 `30 passed`；搜尋、UI、版本與相似功能定向回歸為 `94 passed`。
- 完整 repository runner 為 `1401 passed, 7 skipped`。Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、
  網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing
  `1.2`／`1.2.1` 共 `2` 個保留版本、Repository 外 compileall、source-only
  `--verify-only` 與 `git diff --check` 均通過。
- Testing `1.2.1` 保持不可變；本輪尚未取得 build、Testing `1.2.2`、stage、
  commit、push 或發布授權。

## 39.0.22（搜尋 MOD 狀態與分頁控制一致性）

- 修正搜尋結果已有下一頁游標時停用目前搜尋 MOD，UI 只重建來源清單、沒有失效
  舊游標與聯合結果快取的缺口；搜尋與下一頁按鈕因此仍看似可用，點擊後才被服務
  層拒絕或收到游標不匹配錯誤。
- 搜尋來源 MOD 的啟用狀態改變時，現在沿用遠端條件變更的失效路徑，立即清除舊
  游標與本機聯合結果快取。搜尋／下一頁控制項也會檢查目前單一 provider 是否已
  啟用；聚合模式則要求至少兩個已啟用來源且仍具有共同內容類型。
- Regression-first 證據：載入 `opaque-next-page` 後停用 `youtube-search`，舊 UI
  仍保留游標；修正後游標與快取清空、兩個控制項停用，Bilibili 獨立來源與既有
  分頁追加行為保持通過。初步 offscreen UI 回歸為 `3 passed`；搜尋、UI、分頁、
  相似與版本定向回歸為 `85 passed`。
- 完整 repository runner 為 `1402 passed, 7 skipped`。Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、
  網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing
  `1.2`／`1.2.1` 共 `2` 個保留版本、Repository 外 compileall、source-only
  `--verify-only` 與 `git diff --check` 均通過。
- 此修正不取消或中止 provider 執行緒，不新增網站、網路 fallback、下載或權限；
  Testing `1.2.1` 保持不可變。本輪尚未取得 build、Testing `1.2.2`、stage、
  commit、push 或發布授權。

## 39.0.23（相似與替代搜尋的綁定來源狀態）

- 修正 `youtube-similar` 與 `youtube-recovery` 雖綁定 `youtube-search`，但可信 UI
  只檢查衍生 MOD 自身狀態的依賴落差。停用 YouTube 搜尋後，既有結果仍會留下
  可點擊的相似音樂與替代搜尋按鈕，操作後才由搜尋服務拒絕。
- UI 現在將綁定搜尋來源納入兩個按鈕的可用條件；直接方法呼叫也會先提示啟用
  `youtube-search`。服務層在執行相似／替代規劃 MOD 前先驗證綁定搜尋 provider
  已註冊且啟用，避免啟動不會產生有效結果的子程序。
- Regression-first 證據：修正前 offscreen UI 仍顯示兩個按鈕可用，服務層亦先
  呼叫規劃 MOD；三個新增測試均失敗。修正後相同 `3 passed`，且未改變由
  `youtube-player`、下載 provider 或外部瀏覽器獨立負責的操作。
- 搜尋狀態、相似、替代、服務與版本定向回歸為 `72 passed`；完整 repository
  runner 為 `1405 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only`
  與 `git diff --check` 均通過。
- 此修正不新增網站、主機權限、Cookie、網路 fallback 或下載能力；Testing
  `1.2.1` 保持不可變。本輪尚未取得 build、Testing `1.2.2`、stage、commit、
  push 或發布授權。

## 39.0.24（多來源聚合搜尋分頁）

- 修正聚合搜尋雖收到每個 provider 的下一頁游標，可信 UI 卻固定清空游標並停用
  「下一頁」的功能缺口。使用者不必切換成單一來源，即可繼續載入仍有後續頁面的
  聚合來源。
- 服務層將各 provider 的原始游標封裝為有界 HMAC token，綁定正規化查詢、內容
  類型與完整來源順序；竄改 token、換查詢或換來源集合都會被拒絕。provider 只會
  收到自己的原始游標，不會取得其他網站的游標。
- 續頁只呼叫 token 中仍有游標的來源，維持多來源逐 provider `20` 筆上限；已耗盡
  來源不會重跑第一頁。暫時失敗的來源保留原游標供下一次重試，成功且耗盡的來源
  則移出下一輪。UI 沿用既有 canonical 去重、有界 `200` 筆追加與失敗保留結果。
- Regression-first 證據：修正前服務回傳兩個彼此獨立的單站 token，UI 仍清空
  聚合游標，兩個新增測試皆失敗；修正後服務、adapter、失敗重試與 offscreen UI
  四項核心回歸為 `4 passed`。
- 搜尋服務、Search v2、分頁、offscreen UI 與版本定向回歸為 `75 passed`；完整
  repository runner 為 `1408 passed, 7 skipped`。Quality audit 通過 Ruff `366`
  個 Python 檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only`
  與 `git diff --check` 均通過。
- 此修正不新增 provider、主機權限、Cookie、網路 fallback 或下載能力；Testing
  `1.2.1` 保持不可變。本輪尚未取得 build、Testing `1.2.2`、stage、commit、
  push 或發布授權。

## 39.0.25（工作區分頁容量終止）

- 修正搜尋工作區已達 `200` 筆有界容量後仍保留 provider 或聚合下一頁游標的
  狀態缺口。舊行為會讓「下一頁」維持可用，但後續結果必然被容量上限截斷，
  因而產生不能增加可見結果的重複網路請求。
- 跨頁合併一旦達到工作區上限便捨棄後續游標；可信 UI 同步清空目前游標、
  停用「下一頁」，並以 tooltip 與狀態文字說明已達最多 `200` 筆結果。
- Regression-first 證據：修正前 helper 與 offscreen UI 都保留未使用游標，兩項
  新增測試為 `2 failed`；修正後相同回歸為 `2 passed`，第二次操作不會呼叫
  provider。
- 搜尋、分頁、offscreen UI 與版本定向回歸為 `98 passed`；完整 repository
  runner 為 `1410 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only`
  與 `git diff --check` 均通過。
- 此修正不變更 provider 請求格式、網站權限、Cookie、主機清冊、下載能力或
  `200` 筆既有容量；Testing `1.2.1` 保持不可變。本輪尚未取得 build、
  Testing `1.2.2`、stage、commit、push 或發布授權。

## 39.0.26（搜尋來源安全 fallback）

- 修正目前選取的第三方搜尋來源消失後，來源清單無條件退回 YouTube 項目的
  狀態錯誤。若 YouTube 已停用，即使 Bilibili 或其他來源仍可用，搜尋控制項也會
  顯示在停用來源；加入聚合項後，直接使用 status 位置索引還可能指到錯誤項目。
- 清單重建現在先保留仍存在的選擇；選擇已消失時，只在 YouTube 實際啟用時
  優先使用它，否則按啟用 provider ID 尋找第一個可用來源。索引不再依賴聚合項
  是否存在，搜尋按鈕會同步反映新來源的可用狀態。
- Regression-first 證據：修正前 offscreen UI 在原來源移除且 YouTube 停用時
  錯選 `youtube-search`，新增測試為 `1 failed`；修正後選取
  `bilibili-search` 且控制項可用，相同回歸為 `1 passed`。
- 搜尋、分頁、offscreen UI 與版本定向回歸為 `99 passed`；完整 repository
  runner 為 `1411 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only`
  與 `git diff --check` 均通過。
- 此修正不註冊新 provider、不發出網路請求，也不變更網站權限、Cookie、
  下載能力或聚合搜尋契約；Testing `1.2.1` 保持不可變。本輪尚未取得 build、
  Testing `1.2.2`、stage、commit、push 或發布授權。

## 39.0.27（搜尋世代失效）

- 修正搜尋 worker 執行期間若使用者停用搜尋 MOD 或來源條件改變，既有
  `invalidate_search_cursor` 只清除游標與快取，卻沒有使進行中的 generation
  失效；舊請求完成後仍會被接受並重新顯示已不符合目前來源狀態的結果。
- 搜尋條件失效時若目前 busy action 是搜尋，可信 UI 會遞增搜尋與縮圖世代、
  清除 busy 狀態及等待中縮圖，並說明舊結果已忽略。背景 provider 呼叫不做
  不安全的 thread 強制終止；晚到回應只因世代不符而被丟棄。
- Regression-first 證據：延遲 worker 的 offscreen 測試在搜尋期間停用來源；
  修正前 generation 不變且測試為 `1 failed`，修正後 generation 失效、UI 解除
  busy，舊結果與游標皆不回寫，相同回歸為 `1 passed`。
- 搜尋、分頁、offscreen UI 與版本定向回歸為 `100 passed`；完整 repository
  runner 為 `1412 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only`
  與 `git diff --check` 均通過。
- 此修正不增加 provider、網路 fallback、網站權限、Cookie 或下載能力；
  Testing `1.2.1` 保持不可變。本輪尚未取得 build、Testing `1.2.2`、stage、
  commit、push 或發布授權。

## 39.0.28（外部 MOD 搜尋狀態失效）

- 修正由 MOD 管理介面發布 `builtin_mod.changed` 時，可信 UI 以阻斷 QAction
  signal 的方式同步勾選狀態，因而略過本頁 QAction 原有的搜尋快取與游標
  失效流程；重新啟用 provider 後可能沿用停用前的過期搜尋頁面。
- 搜尋 provider 或其父 MOD 的外部狀態事件現在會在重建來源清單後統一呼叫
  `invalidate_search_cursor`；既有 39.0.27 的搜尋世代保護也同時涵蓋此事件路徑。
- Regression-first 證據：測試由事件匯流排停用 `youtube-search`，修正前 provider
  雖已停用但舊聯合結果與游標仍存在，結果為 `1 failed`；修正後相同回歸為
  `1 passed`。
- 搜尋、分頁、offscreen UI 與版本定向回歸為 `101 passed`；完整 repository
  runner 為 `1413 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only`
  與 `git diff --check` 均通過。
- 此修正不增加 provider、網路 fallback、網站權限、Cookie 或下載能力；
  Testing `1.2.1` 保持不可變。本輪尚未取得 build、Testing `1.2.2`、stage、
  commit、push 或發布授權。

## 39.0.29（聚合分頁無遺失配額）

- 修正聚合搜尋把完整頁面大小交給每個來源、卻只在合併後套用總量上限的
  資料遺失：兩個來源各回傳 20 筆而 UI 只取 20 筆時，舊流程顯示各前 10 筆，
  下一頁游標卻已前移 20，導致各自第 10～19 筆永久跳過。
- Search v2 registry 現在依本次實際查詢來源公平分配有界頁面配額；外部 MOD
  若回傳超過要求配額的頁面，會被隔離為 `invalid-response`，而不是靜默截斷
  並接受已前移的游標。若結果上限小於所選來源數，則明確拒絕無法無損分配的
  請求。
- Regression-first 證據：兩個 cursor provider 連續載入兩頁；修正前集合跳過
  各自第 10～19 筆並得到 `1 failed`，修正後兩頁完整涵蓋各自第 0～19 筆，
  相同回歸為 `1 passed`。Search v2 契約套件為 `14 passed`。
- 搜尋、分頁、offscreen UI 與版本定向回歸為 `104 passed`；完整 repository
  runner 為 `1416 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only`
  與 `git diff --check` 均通過。
- 此修正不增加 provider、網路 fallback、網站權限、Cookie 或下載能力；
  Testing `1.2.1` 保持不可變。本輪尚未取得 build、Testing `1.2.2`、stage、
  commit、push 或發布授權。

## 39.0.30（官方搜尋身分路由一致性）

- 修正 canonical 搜尋去重只檢查 URL 解析後 hostname 的身分污染；帶 userinfo
  或顯式連接埠的 URL 雖會被 exact-host 路由拒絕，舊邏輯仍把它視為官方
  YouTube，若外部 MOD 結果先到便會排擠同 ID 的合法官方項目。
- canonical 去重現在重用 `classify_site_url`；只有完整通過 HTTPS、無認證資訊、
  無顯式連接埠、官方 host 與合法資源路徑檢查的 YouTube URL，才可共用
  `site:youtube` 身分。其他 URL 使用完整 netloc 隔離，不放寬下載或開啟權限。
- Regression-first 證據：userinfo 與 `:443` 兩個外部結果先於合法官方結果；
  修正前兩個案例都錯誤合併為單項並得到 `2 failed`，修正後保留兩個不同身分，
  同時既有官方 host alias 去重仍通過，合計 `3 passed`。
- 搜尋、分頁、offscreen UI 與版本定向回歸為 `106 passed`；完整 repository
  runner 為 `1418 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染掃描 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only`
  與 `git diff --check` 均通過。
- 此修正不增加 provider、網路 fallback、網站權限、Cookie 或下載能力；
  Testing `1.2.1` 保持不可變。本輪尚未取得 build、Testing `1.2.2`、stage、
  commit、push 或發布授權。

## 39.0.31（Discovery URL 契約隔離）

- 修正 `DiscoveryItemV1` 只檢查 `https://` 字首的契約缺口；無主機、畸形 IPv6、
  超範圍 port、URL credentials、換行或過長 URL 可穿過 `from_dict()`，直接建構
  更可完全繞過檢查，之後在 canonical 去重的 `urlsplit()` 中拋錯並中斷所有來源。
- 既有文字、身分、標題、縮圖與片長規則現在統一由 `__post_init__` 執行；結果
  URL 必須是最長 4096 字元、含主機、無 credentials 與空白控制字元的 HTTPS URL，
  縮圖沿用 1000 字元上限及相同 URL 邊界。外部壞結果會在各 provider 的隔離區
  被分類為 `invalid-response`，正常來源仍可返回。
- Regression-first 證據：6 種畸形 URL、直接建構繞過及聚合中斷共得到
  `8 failed`；修正後同組為 `8 passed`。Discovery、Search v2、分頁、歷史、
  recovery、similar、YouTube／Bilibili 工作區與 Unicode IPC 相關套件為
  `138 passed`。
- 完整 repository runner 為 `1426 passed, 7 skipped`；Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案。MOD 群組 `7 / 4`、網站
  矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 均通過。
- 此修正不增加 provider、網站權限、網路 fallback、Cookie 或下載能力；Testing
  `1.2.1` 保持不可變，也未授權 build、Testing `1.2.2`、stage、commit、push 或發布。

## 39.0.32（搜尋來源選擇唯一性）

- 修正 `DiscoveryService` 已拒絕重複 provider ID，但下層 `SearchAdapterRegistry`
  仍接受相同來源多次的分層不一致；直接呼叫 registry 會重複派送同一 MOD，並把
  顯示上限除以重複項數，造成外部請求與每來源配額失真。
- registry 現在於任何 adapter 呼叫前驗證 provider 選擇；來源 ID 必須是非空字串
  且不得重複。未知但格式有效的來源仍沿用既有 failure isolation，不改變可診斷性。
- Regression-first 證據：重複 ID、空字串及非字串 ID 共得到 `3 failed`；修正後
  同組為 `3 passed`，且 adapter 在拒絕重複來源時未被呼叫。Search registry、
  Discovery service、分頁與可信 UI 相關套件為 `75 passed`。
- 完整 repository runner 為 `1429 passed, 7 skipped`；Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案。MOD 群組 `7 / 4`、網站
  矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 均通過。
- 此修正不增加 provider、網站權限、網路 fallback、Cookie 或下載能力；Testing
  `1.2.1` 保持不可變，也未授權 build、Testing `1.2.2`、stage、commit、push 或發布。

## 39.0.33（搜尋來源 iterable 有界化）

- 修正 `SearchAdapterRegistry.search()` 直接將 `provider_ids` 轉成 tuple 的無界
  展開問題；字串會被拆成單字元來源，不可迭代輸入會洩漏 `TypeError`，超長或
  無限 generator 也會在來源上限檢查前被完整消耗。
- registry 現在明確拒絕字串與 bytes，將不可迭代輸入統一映射為既有 validation
  error，並只讀取最多 `_MAX_SEARCH_SOURCES + 1`（17）項便判定是否超過 16 個
  搜尋來源；既有唯一性、來源隔離與配額行為保持不變。
- Regression-first 證據：字串、不可迭代輸入與 1000 項 generator 共得到
  `3 failed`；修正後同組為 `3 passed`，且 generator 只消耗前 17 項。Search
  registry、Discovery service、分頁與可信 UI 相關套件為 `78 passed`。
- 完整 repository runner 為 `1432 passed, 7 skipped`；Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案。MOD 群組 `7 / 4`、網站
  矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 均通過。
- 此修正不增加 provider、網站權限、網路 fallback、Cookie 或下載能力；Testing
  `1.2.1` 保持不可變，也未授權 build、Testing `1.2.2`、stage、commit、push 或發布。

## 39.0.34（服務層來源選擇契約統一）

- 修正底層 registry 已有有界 provider iterable 防護，但公開
  `DiscoveryService.federated_search()` 仍先完整轉成 tuple 的分層落差；服務路徑
  仍會拆解字串、洩漏 `TypeError`，或在來源查找前耗盡超長／無限 generator。
- `SearchAdapterRegistry.normalize_provider_selection()` 現在是共用的單一入口；
  服務層先建立已啟用來源的惰性 iterable，再於任何可用性與啟用狀態查找前套用
  同一個型別、唯一性與 16 項上限契約，registry 派送時亦重用該入口。
- Regression-first 證據：服務層字串、不可迭代輸入與 1000 項 generator 共得到
  `3 failed`；修正後同組為 `3 passed`，generator 只消耗前 17 項。Search registry、
  Discovery service、分頁與可信 UI 相關套件為 `81 passed`。
- 完整 repository runner 為 `1435 passed, 7 skipped`；Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案。MOD 群組 `7 / 4`、網站
  矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 均通過。
- 此修正不增加 provider、網站權限、網路 fallback、Cookie 或下載能力；Testing
  `1.2.1` 保持不可變，也未授權 build、Testing `1.2.2`、stage、commit、push 或發布。

## 39.0.35（搜尋結果上限型別契約統一）

- 修正 `SearchAdapterRegistry.search()` 直接呼叫 `int(limit)` 的輸入契約缺口；
  `True`、`"12"` 與 `1.5` 原本會分別被靜默轉成 1、12 與 1，造成不符合
  Search v2 公開型別的請求仍被派送給外部搜尋 MOD。
- `SearchAdapterRegistry.normalize_result_limit()` 現在是服務層與 registry 共用的
  單一入口，只接受非布林的實際整數；`DiscoveryService.federated_search()` 在
  建立查詢前即套用同一規則。合法整數仍維持 1～50 的既有有界相容行為，包含
  0→1 與超過 50→50。
- Regression-first 證據：registry 與公開 Discovery service 的三種非整數輸入共
  得到 `6 failed`，且能觀察到提供者被錯誤呼叫；修正後連同兩個 clamp 相容案例
  為 `8 passed`。Search registry、Discovery service、分頁與可信 UI 相關套件為
  `89 passed`。
- 完整 repository runner 為 `1443 passed, 7 skipped`；Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案。MOD 群組 `7 / 4`、網站
  矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 均通過；`Version/` 內 `.pyc` 為 `0`。
- 此修正不增加 provider、網站權限、網路 fallback、Cookie 或下載能力；Testing
  `1.2.1` 保持不可變，也未授權 build、Testing `1.2.2`、stage、commit、push 或發布。

## 39.0.36（Federated cursor mapping 有界驗證）

- 修正 `SearchAdapterRegistry.search()` 在驗證前直接 `dict(provider_cursors)` 的
  無界物化缺口；過長或自訂 Mapping 原本會被完整消耗後才回報未知來源，tuple-list
  也會繞過 Mapping 契約，空白、超長或非字串游標則被降級成單一 provider failure。
- `SearchAdapterRegistry.normalize_provider_cursors()` 現在只接受 Mapping，最多讀取
  `_MAX_SEARCH_SOURCES + 1`（17）組便判定超過 16 個來源上限；每組必須具有唯一
  非空 provider ID，以及 1～500 字元的字串游標，所有錯誤都在外部 MOD 派送前拒絕。
- Regression-first 證據：1000 組自訂 Mapping、tuple-list 與三種無效游標值共得到
  `5 failed`；修正後為 `5 passed`，超長 Mapping 只消耗前 17 組。Search registry、
  Discovery service、分頁與可信 UI 相關套件為 `94 passed`。
- 完整 repository runner 為 `1448 passed, 7 skipped`；Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案。MOD 群組 `7 / 4`、網站
  矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 均通過；`Version/` 內 `.pyc` 為 `0`。
- 此修正不增加 provider、網站權限、網路 fallback、Cookie 或下載能力；Testing
  `1.2.1` 保持不可變，也未授權 build、Testing `1.2.2`、stage、commit、push 或發布。

## 39.0.37（Search v2 查詢入口驗證）

- 修正 Search v2 查詢欄位只在每個 provider 的 `normalized()` 路徑驗證的契約
  缺口；沒有註冊或啟用來源時，空白／非字串查詢及無效內容類型原本會靜默
  回傳空結果，有來源時則會被錯誤分類為 provider failure，非查詢物件還會洩漏
  `AttributeError`。
- `SearchQueryV2.validated()` 現在集中驗證與正規化呼叫端欄位；Discovery service
  與 Search registry 都在來源選擇、可用性檢查及外部 MOD 派送前使用同一入口。
  Provider-specific 的內容類型、分頁能力與最大頁面大小仍由 `normalized()` 驗證。
- Regression-first 證據：無來源、有來源、非查詢物件及公開服務入口的無效輸入
  共得到 `14 failed`；修正後同組為 `14 passed`。Search registry、Discovery
  service、分頁、排序、相似搜尋與可信 UI 相關套件為 `123 passed`。
- 完整 repository runner 為 `1462 passed, 7 skipped`；Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案。MOD 群組 `7 / 4`、網站
  矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 均通過；`Version/` 內 `.pyc` 為 `0`。
- 此修正不增加 provider、網站權限、網路 fallback、Cookie 或下載能力；已公開
  Testing `1.2.1` 保持不可變。新的 Testing 修正必須使用 `1.2.2` 目錄與附件名稱。

## 39.0.38（外層搜尋游標型別驗證）

- 修正 `DiscoveryService.federated_search()` 只在 `if cursor` 為真時才進入游標
  解碼的輸入缺口；`None`、`False`、`0` 與空容器原本會被當成沒有游標，重新
  呼叫 provider 第一頁並可能改寫來源健康狀態。
- 公開服務入口現在只接受字串型游標；非字串值會在來源選擇、可用性查找及任何
  provider 派送前以穩定的 `search cursor invalid` 錯誤拒絕。空字串仍是唯一合法的
  「沒有游標」表示法，既有單來源及 federated 簽署 token 解碼規則不變。
- Regression-first 證據：四種假值非字串游標共得到 `4 failed`，且 provider 被
  錯誤呼叫；修正後同組為 `4 passed`。Discovery service、Search registry、分頁與
  可信 UI 相關套件為 `112 passed`。
- 完整 repository runner 為 `1466 passed, 7 skipped`；Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案。MOD 群組 `7 / 4`、網站
  矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 均通過；`Version/` 內 `.pyc` 為 `0`。
- 此修正不增加 provider、網站權限、網路 fallback、Cookie 或下載能力；已公開
  Testing `1.2.1` 保持不可變。新的 Testing 修正必須使用 `1.2.2`。

## 39.0.39（搜尋 MOD 註冊失敗原子性）

- 修正 `DiscoveryService.register()` 在核對搜尋 capability provider ID 前，已先把
  provider 寫入下載 registry 與服務索引的部分狀態缺口；mismatch 報錯後，同 ID
  的修正版 provider 原本會再被 `already registered` 永久阻擋。
- 搜尋 capability 的建構與身分核對現在先於任何 registry mutation；驗證失敗不會
  啟用、索引或保留 provider。合法 provider 的既有註冊順序、預設 capability 與
  Search v2 adapter 行為不變。
- Regression-first 證據：先註冊 capability 身分不符的 provider，再以同 ID 合法
  provider 恢復的公開流程得到 `1 failed`；修正後為 `1 passed`。Discovery、下載
  registry、外部 MOD adapter／protocol 與 Search v2 相關套件為 `137 passed`。
- 完整 repository runner 為 `1467 passed, 7 skipped`；Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案。MOD 群組 `7 / 4`、網站
  矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、本機 Testing `1.2`／`1.2.1`
  共 `2` 個保留版本、Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 均通過；`Version/` 內 `.pyc` 為 `0`。
- 此修正不增加 provider、網站權限、網路 fallback、Cookie 或下載能力；已公開
  Testing `1.2.1` 保持不可變。使用者已授權由 Development `39.0.39` 的乾淨
  source freeze 建立未簽署 Testing `1.2.2` 新目錄、tag、ZIP 與 GitHub prerelease；
  不簽署、不發布 Stable，也不覆寫 1.2.1。

## 39.0.40（Unicode 搜尋排序一致性）

- 修正搜尋查詢已做 NFKC 正規化，但 provider 回傳的標題與作者只做
  `casefold` 的不對稱路徑；同一內容若使用全形拉丁字元或 Unicode 組合／
  分解重音形式，原本會失去標題完整命中並退回 provider 原始順序。
- 查詢、標題與作者現在共用 NFKC、`casefold` 與空白收斂的比較形式；只影響
  本機排序與解釋，不改寫 provider 資料，也不增加任何網路請求。
- Regression-first 證據：全形標題與組合／分解重音標題兩條案例在修正前為
  `2 failed, 5 passed`；修正後搜尋排序套件為 `7 passed`。
- 搜尋、版本與入口點相關套件為 `28 passed`；完整 repository runner 為
  `1469 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字污染
  `474` 個受控檔案。MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、
  版本文件 `4`、本機 Testing `1.2.1`／`1.2.2` 共 `2` 個保留版本、Repository 外
  compileall 均通過。
- 此修正不增加 provider、網站權限、Cookie、下載、DRM／登入／廣告規避或
  網路 fallback。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、
  stage、commit、push 或發布。

## 39.0.41（搜尋建議有界讀取與事件分類）

- 修正 `preference_search_queries()` 先以 `list.extend()` 完整消耗所有歷史事件，
  最後才套用 2～12 筆輸出上限的不對稱路徑；偏好建議現在填滿上限後就
  停止讀取 iterable，不會為未顯示項目繼續消耗資料。
- 「最近搜尋」原本只讀取事件的 `query` 欄位，因此 query 不同的
  selection 事件也會被誤列為搜尋；現在只列出 `event_type == "search"` 的紀錄。
- Regression-first 證據：有界 generator 消耗與 selection 事件分類兩條案例在
  修正前為 `2 failed, 7 passed`；修正後搜尋建議與歷史套件為 `9 passed`。
- 搜尋、歷史、版本與入口點相關套件為 `30 passed`；完整 repository runner 為
  `1470 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字污染
  `474` 個受控檔案。MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、
  版本文件 `4` 與 Testing `1.2.1`／`1.2.2` 版本稽核均通過。
- 參考專案 `BoringMan314/aniGamerPlus`、`miyouzi/aniGamerPlus` 與 Gopeed 的任務狀態、
  重試與清單邊界；這些專案為 GPL-3.0，本修正只使用可泛化設計原則，沒有複製
  其程式碼、網站專屬解析、Cookie 或任何存取限制規避邏輯。
- Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.42（Unicode 搜尋建議去重）

- 修正 39.0.40 已將搜尋結果排序統一為 NFKC，但歷史與偏好建議仍只用
  `casefold` 當去重身分的不一致路徑；全形／半形拉丁詞或組合／預組重音詞原本
  會同時出現在建議選單。
- 兩個建議入口現在共用 NFKC 加 `casefold` 身分鍵；只用正規形判斷重複，
  回傳值仍保留最新歷史或優先偏好的原始文字。
- Regression-first 證據：全形偏好與半形歷史、組合與預組重音歷史兩條
  案例在修正前為 `2 failed, 9 passed`；修正後搜尋建議與歷史套件為
  `11 passed`。
- 建議、歷史、版本文件、版本通道與入口點的針對性套件為 `32 passed`；完整
  repository runner 為 `1472 passed, 7 skipped`。Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4` 與 Testing `1.2.1`／`1.2.2`
  版本稽核均通過。隔離的 `compileall` 亦通過。
- 此修正是純本機文字身分處理，不增加 provider、網站權限、網路請求、Cookie、
  下載或任何存取限制規避能力。Testing `1.2.1` 與 `1.2.2` 保持不可變；
  本輪不執行 build、stage、commit、push 或發布。

## 39.0.43（作者與標題跨欄位精確排序）

- 修正常見的「作者＋曲名」查詢跨在 `artist` 與 `title` 欄位時，只取得零散
  關鍵字分數，反而可能被將整串查詢放入標題的較弱結果超前。
- 本機排序現在檢查正規化後的 `artist + title` 與 `title + artist` 是否精確等於
  查詢；兩個欄位皆非空且整串相等時給予 75 分及「作者與標題完整符合」原因。
  其他結果仍沿用既有標題與作者規則，不新增模糊跨欄位匹配。
- Regression-first 證據：精確跨欄位結果原先排在標題全文命中之後，修正前為
  `1 failed, 7 passed`，修正後搜尋排序套件為 `8 passed`。
- 搜尋排序、版本文件、版本通道與入口點的針對性套件為 `29 passed`；完整
  repository runner 為 `1473 passed, 7 skipped`。Quality audit 通過 Ruff `366`
  個 Python 檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2`
  版本稽核與隔離 `compileall` 均通過。
- 此修正只調整已載入結果的本機排序，不修改 provider、網路請求、下載、Cookie
  或網站存取邊界。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、
  stage、commit、push 或發布。

## 39.0.44（偏好建議事件分類一致性）

- 修正「最近搜尋」已排除 selection，但偏好建議從原始歷史事件補位時仍直接採用
  所有 event.query 的不一致路徑；不同的 selection.query 原本會被顯示為使用者
  主動搜尋詞。
- `preference_search_queries()` 現在只從 `event_type == "search"` 的事件取得原始
  查詢；selection 仍保留給 History MOD 的作者、語言、內容類型與分類偏好統計。
- Regression-first 證據：空偏好搭配不同 selection/search 查詢的案例修正前為
  `1 failed, 4 passed`，修正後搜尋建議套件為 `5 passed`。
- 建議、歷史、版本文件、版本通道與入口點針對性套件為 `33 passed`；完整
  repository runner 為 `1474 passed, 7 skipped`。Quality audit 通過 Ruff `366`
  個 Python 檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2`
  版本稽核與隔離 `compileall` 均通過。
- 此修正不刪除歷史、不更動 History contract，也不新增 provider、網路、下載、
  Cookie 或網站存取能力。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行
  build、stage、commit、push 或發布。

## 39.0.45（作者與標題常見分隔符）

- 修正 39.0.43 只辨識單一空白連接作者與標題的限制；使用者輸入常見的
  `Artist - Title`、長短破折號、直線、冒號或間隔點時，精確跨欄位結果原本仍
  退回較低的零散關鍵字分數。
- 精確組合使用固定白名單：空白、`-`、`–`、`—`、`|`、`:`、`·`。兩個欄位必須
  非空，查詢亦須等於正向或反向完整組合；不剝除任意標點，不新增模糊匹配。
- Regression-first 證據：六種額外分隔符的同一案例修正前為 `1 failed, 8 passed`，
  修正後搜尋排序套件為 `9 passed`。
- 搜尋排序、版本文件、版本通道與入口點針對性套件為 `30 passed`；完整 repository
  runner 為 `1475 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與隔離
  `compileall` 均通過。
- 此修正只影響已載入結果的本機排序，不改寫查詢、provider 回應、網路或下載
  行為。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.46（標點包圍錯字修正）

- 修正已知 token typo 只能在空白切分後整詞相等時生效的限制；括號、逗號或
  句尾標點包圍的 `offical`、`lyrcis` 等完整錯字原本不會被修正。
- 改用固定錯字表產生的大小寫不敏感詞邊界規則，依查詢原始順序逐一取代；
  僅替換命中的單字內容，不重建空白或標點，也不在較長單字內匹配。
- 每次取代仍於寫回前驗證 Search v2 的 200 字元上限，避免 UI、歷史與 provider
  實際查詢分歧。
- Regression-first 證據：`song (OFFICAL), lyrcis!` 修正前為
  `1 failed, 9 passed`，修正後搜尋排序套件為 `10 passed`。搜尋排序、版本文件、
  版本通道與入口點針對性套件為 `31 passed`；完整 repository runner 為
  `1476 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字污染
  `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、
  版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與隔離 `compileall` 均通過。
- 此修正不新增 provider、網路、下載、Cookie 或網站存取能力。Testing `1.2.1`
  與 `1.2.2` 的目錄、tag、附件及 source freeze 保持不可變；本輪不執行 build、
  stage、commit、push 或發布。

## 39.0.47（精確跨欄位排序優先級）

- 修正 39.0.43 的精確「作者＋標題」結果只有 75 分，仍可能被「標題包含完整查詢」
  60 分加「作者關鍵字」20 分的較弱候選以 80 分反向超越。
- 僅將既有嚴格 `combined_exact` 分支調整為 100 分；作者與標題仍須同時非空，
  查詢仍須精確等於正向或反向完整組合，且只接受 39.0.45 的有限分隔符白名單。
  不新增模糊匹配，也不改動其他分數、穩定排序或原因文字。
- Regression-first 證據：包含完整查詢的標題搭配部分作者關鍵字原本排在真正的
  跨欄位精確結果之前，修正前為 `1 failed, 10 passed`，修正後搜尋排序套件為
  `11 passed`。搜尋排序、版本文件、版本通道與入口點針對性套件為 `32 passed`；
  完整 repository runner 為 `1477 passed, 7 skipped`。Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本
  稽核與隔離 `compileall` 均通過。
- 此修正只影響已載入結果的本機排序，不改寫查詢、provider 回應、網路或下載
  行為。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.48（Unicode 語言篩選一致性）

- 修正搜尋排序與建議已統一使用 Unicode NFKC，但本機語言篩選仍只對兩側做
  `strip()` 與 `casefold()` 的規則落差；全形語言代碼或組合形式不同的語言名稱
  原本會被錯誤排除。
- 語言篩選值與每筆結果的 `language` 欄位現在共用既有比較文字正規化：NFKC、
  `casefold` 與空白收斂。篩選仍要求正規化後整欄相等，不新增子字串、模糊匹配
  或 provider 請求。
- Regression-first 證據：全形 `ＪＡ` 對 `ja`、分解 `Café` 對預組 `café` 的
  兩個案例修正前為 `2 failed, 11 passed`，修正後搜尋排序與篩選套件為
  `13 passed`。搜尋排序、版本文件、版本通道與入口點針對性套件為 `34 passed`；
  完整 repository runner 為 `1479 passed, 7 skipped`。Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本
  稽核與隔離 `compileall` 均通過。
- 此修正只影響已載入結果的本機篩選，不改寫 provider 回應、歷史、網路或下載
  行為。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.49（拉丁搜尋片語單字邊界）

- 修正本機排序以任意子字串判斷「完整符合」的相關度缺口；例如查詢 `art` 時，
  `Cartoon archive` 原本會取得與 `Art documentary` 相同的 60 分，並因 provider
  順序排在真正的單字命中之前。
- 拉丁字與其他慣用單字邊界的文字現在只在片語前後不是其他單字字元時視為完整
  命中。中日韓、泰文、寮文、高棉文與緬甸文等慣用無空格文字仍沿用子字串搜尋，
  不降低既有中文與日文查詢召回。
- Regression-first 證據：`art`／`cartoon` 案例修正前為 `1 failed`；修正後新增
  無空格文字相容案例的搜尋排序套件為 `15 passed`。搜尋排序、版本文件、版本
  通道與入口點針對性套件為 `36 passed`；完整 repository runner 為
  `1481 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與隔離 `compileall`
  均通過。
- 此修正只影響已載入結果的本機排序，不改寫查詢或 provider 回應，也不新增網路、
  下載、Cookie 或網站存取能力。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪
  不執行 build、stage、commit、push 或發布。

## 39.0.50（完整標題優先級）

- 修正正規化後與查詢完全相等的標題，原本和只包含相同片語的延伸標題同為
  60 分；若 `live cover` 等延伸結果先由 provider 回傳，真正的完整標題便會排在
  後方。
- 完整標題現在取得 85 分及獨立的「標題完全相等」原因；一般標題片語維持 60 分，
  片語加作者關鍵字最多 80 分，而嚴格作者＋標題跨欄位精確結果仍維持 100 分。
- Regression-first 證據：延伸標題先於完整標題的案例修正前為 `1 failed`；更新
  兩個 Unicode 等價標題的預期後，搜尋排序套件為 `16 passed`。搜尋排序、版本
  文件、版本通道與入口點針對性套件為 `37 passed`；完整 repository runner 為
  `1482 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與隔離 `compileall`
  均通過。
- 此修正只影響已載入結果的本機排序與原因文字，不改寫查詢、provider 回應或
  網路行為。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、
  commit、push 或發布。

## 39.0.51（完整作者優先級）

- 修正以作者名稱搜尋時，標題只提及作者的內容取得 60 分，但作者欄位完全相等
  的作品只有 30 分，導致真正的作者作品排在訪談、紀錄片或其他提及內容之後。
- 作者欄位正規化後完全等於查詢時，現在取得 70 分及獨立的「作者完全相等」原因；
  一般作者片語維持 30 分、標題片語維持 60 分、完整標題與嚴格作者＋標題精確
  結果仍分別維持 85 與 100 分。
- Regression-first 證據：作者作品落後於標題提及內容的案例修正前為 `1 failed`；
  修正後搜尋排序套件為 `17 passed`。搜尋排序、版本文件、版本通道與入口點
  針對性套件為 `38 passed`；完整 repository runner 為
  `1483 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與隔離 `compileall`
  均通過。
- 此修正只影響已載入結果的本機排序與原因文字，不改寫查詢、provider 回應或
  網路行為。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、
  commit、push 或發布。

## 39.0.52（混合文字片語邊界）

- 修正 39.0.49 只要查詢含任一中日韓或其他無空格文字，就整段停用單字邊界的
  混合語言缺口；`art 音樂` 原本仍會把 `cart 音樂` 誤列為標題完整符合。
- 片語首尾現在各自依字元文字系統決定邊界：拉丁字端要求完整詞界，中文、日文、
  韓文、泰文、寮文、高棉文與緬甸文端保留無空格子字串能力。純拉丁及純中文
  查詢的 39.0.49 行為維持不變。
- Regression-first 證據：中英混合片語案例修正前為 `1 failed`；修正後搜尋排序
  套件為 `18 passed`。搜尋排序、版本文件、版本通道與入口點針對性套件為
  `39 passed`；完整 repository runner 為 `1484 passed, 7 skipped`。Quality audit
  通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、
  網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／
  `1.2.2` 版本稽核與隔離 `compileall` 均通過。
- 此修正只影響已載入結果的本機排序，不改寫查詢、provider 回應或網路行為。
  Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.53（偏好作者等價身分）

- 修正偏好統計把同一作者的全形／半形、大小寫或 Unicode 相容形式分開計數時，
  本機建議可能錯選次要作者，且相似音樂結果無法取得偏好加權的缺口。
- 搜尋建議與 `youtube-similar` 現在都以 NFKC＋casefold 身分有界合併最多 100 個
  偏好鍵；顯示仍保留第一個代表字串，不改寫歷史檔或 provider 回傳資料。
- Regression-first 證據：建議錯選與相似結果漏掉 `preference` 的兩個案例修正前為
  `2 failed`；修正後搜尋建議與相似音樂套件為 `17 passed`。搜尋、相似音樂、
  版本文件、版本通道與入口點針對性套件為 `38 passed`；完整 repository runner
  為 `1486 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核均通過。
- 此修正只影響本機偏好建議與相似音樂的查詢規劃／結果加權，不增加背景網路
  行為，也不改寫使用者歷史。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行
  build、stage、commit、push 或發布。

## 39.0.54（相似音樂 Unicode token 身分）

- 修正相似音樂偏好加權已支援 Unicode 等價作者，但標題／作者 token overlap 與
  「目前作者是否等於偏好作者」仍只做 casefold 的不一致；全形作者與半形作者
  因此不會取得 artist overlap，並浪費一個重複的偏好作者查詢槽位。
- `youtube-similar` 現在用同一個 NFKC＋casefold 身分處理 token、偏好鍵與種子
  作者比較；查詢仍維持最多 3 個、偏好鍵最多 100 個，不增加外部請求上限。
- Regression-first 證據：Unicode 等價作者案例修正前為 `1 failed`；修正後相似
  音樂套件為 `12 passed`；相似音樂、版本同步與內建雜湊針對性組合為
  `51 passed, 1 skipped`，完整 repository runner 為 `1487 passed, 7 skipped`。
  Quality audit 通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案。
- 此修正不改寫歷史、provider 回應或 Testing 產物；本輪不執行 build、stage、
  commit、push 或發布。

## 39.0.55（拉丁重音搜尋 fallback）

- 修正使用者未輸入拉丁重音時，`cafe` 無法對已載入的 `Café` 標題／作者取得
  本機排序分數，精確作品反而排在 `Cafe live cover` 等較弱結果之後的缺口。
- 排序現在先保留原始 NFKC＋casefold 精確比對，再以只移除拉丁基底組合符號的
  次級身分計算標題、作者與跨欄位 fallback；次級分數固定低於原始精確分數，
  非拉丁文字與語言篩選維持既有規則。
- Regression-first 證據：無重音查詢案例修正前為 `1 failed`；修正後搜尋排序
  套件為 `20 passed`，並覆蓋標題、作者、作者＋標題及原始重音優先順序；搜尋
  排序與版本同步針對性套件為 `41 passed`，完整 repository runner 為
  `1489 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染 `474` 個受控檔案。
- 此修正只重排已載入結果，不改寫或擴張送往 provider 的查詢，也不增加網路
  行為。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.56（相似音樂 metadata 等價身分）

- 修正相似音樂已正規化標題、作者與偏好身分，但語言與分類仍以原始字串直接
  比較的缺口；不同搜尋來源回傳 `zh-TW`／全形等價語言或 `music`／全形等價分類
  時，實際相同的候選原本會失去 10／15 分並降為低信心 fallback。
- `youtube-similar` 現在用既有的有界 NFKC＋casefold 文字身分比較候選語言與
  分類；空白值仍不計分，分數上限、候選上限、查詢數與外部請求行為均不變。
- Regression-first 證據：隔離語言／分類案例修正前為 `1 failed`，且只得到
  `search-query` 5 分；修正後取得 `language`＋`category` 25 分。相似音樂、內建
  完整性與 YouTube MOD 矩陣針對性套件為 `25 passed, 1 skipped`；完整 repository
  runner 為 `1490 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔
  與文字污染 `474` 個受控檔案；MOD 群組、網站矩陣、依賴鎖、版本文件、Testing
  版本稽核與 Repository 外隔離 `compileall` 均通過。
- 此修正只影響已取得候選的本機相似度排序，不改寫 provider 資料或歷史。
  Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.57（缺少作者時的精確曲名 fallback）

- 修正相似音樂種子有曲名、但 provider 未提供作者 metadata 時，查詢規劃會略過
  精確曲名並直接產生 `title related` 的缺口；較弱的擴展詞可能降低正式作品候選
  的召回與排序品質。
- 查詢規劃現在把曲名本身作為無作者種子的第一個查詢，再保留 related 與語言／
  分類 fallback；有作者時仍沿用作者＋曲名規則，查詢上限維持 3 個。
- Regression-first 證據：`Instrumental Track` 無作者案例修正前為 `1 failed`，
  第一個查詢錯為 `Instrumental Track related`；修正後相似音樂、內建完整性與
  YouTube MOD 矩陣針對性套件為 `26 passed, 1 skipped`；完整 repository runner
  為 `1491 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染 `474` 個受控檔案；MOD、網站、依賴、版本與隔離編譯稽核均通過。
- 此修正不增加網路請求上限、不改寫 provider 回應或歷史。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.58（無空格作者／曲名分隔符）

- 修正跨欄位精確排序只接受分隔符兩側有空白的輸入；使用者貼上常見的
  `Artist-Title`、`Artist|Title` 或 `Artist:Title` 時，分離的作者＋標題結果原本
  不會取得最高優先級，反而可能落後於把整串文字放在標題中的弱候選。
- 精確身分現在同時接受連字號、短／長破折號、直線、冒號及間隔點的有空格與
  無空格形式；比對仍要求完整作者與完整標題組合，不放寬一般子字串規則。
- Regression-first 證據：六種無空格分隔符案例修正前為 `1 failed`；修正後
  搜尋排序套件為 `21 passed`，精確分離欄位結果取得 100 分；完整 repository
  runner 為 `1492 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔
  與文字污染 `474` 個受控檔案；MOD、網站、依賴、版本與隔離編譯稽核均通過。
- 此修正只影響已載入結果的本機排序，不改寫 provider 查詢或回應，也不增加網路
  行為。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.59（偏好建議空白等價身分）

- 修正搜尋建議已合併 Unicode／大小寫等價偏好作者，但尚未折疊前後與重複空白
  的缺口；同一作者若被不同 provider 寫成 `Aimer` 與 `  Aimer  `，計數會分離並
  可能讓次要作者成為第一個建議。
- 偏好與歷史查詢身分鍵現在先套用 NFKC、折疊所有空白，再做 casefold；顯示仍
  保留第一個代表文字，建議數量與 200 字元上限不變。
- Regression-first 證據：空白等價作者合併案例修正前為 `1 failed`，錯選
  `Other Artist`；修正後搜尋建議與歷史套件為 `14 passed`，完整 repository
  runner 為 `1493 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔
  與文字污染 `474` 個受控檔案；MOD、網站、依賴、版本與隔離編譯稽核均通過。
- 此修正只影響本機歷史衍生的建議，不改寫歷史檔、不送出額外查詢。Testing
  `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.60（相似搜尋等價查詢去重）

- 修正相似音樂計畫只用原始字串去重的缺口；同一查詢若因分類 metadata 使用
  全形／半形或大小寫差異而產生等價字串，原本會重複占用最多三個查詢槽位，
  並把語言＋分類備援查詢擠出計畫。
- 查詢計畫現在以既有 NFKC＋casefold 文字身分去重，同時保留第一個原始顯示
  字串及三個查詢上限；不增加 provider 請求數，也不改寫使用者輸入或歷史。
- Regression-first 證據：`Artist music` 與 `Artist ＭＵＳＩＣ` 的等價查詢案例
  修正前為 `1 failed`，第二個槽位被重複查詢占用；修正後針對性案例為
  `1 passed`，相似搜尋、內建完整性與 YouTube MOD 矩陣為
  `27 passed, 1 skipped`；完整 repository runner 為 `1494 passed, 7 skipped`。
  Quality audit 通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案；
  MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件、
  Testing 版本與 Repository 外隔離 `compileall` 均通過。
- Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.61（YouTube 音樂訊號詞界）

- 修正 YouTube 搜尋 MOD 對所有音樂訊號採任意子字串判斷的缺口；拉丁訊號
  `mix` 原本會誤命中 `mixed media tutorial` 或 `concrete mixing tutorial`，
  導致 music 範圍漏加限定詞，或把一般教學影片分類成音樂。
- 拉丁訊號現在經 NFKC＋casefold 後以 ASCII 字母／數字詞界判斷；中文、日文
  等慣用無空格訊號仍保留子字串比對，因此不縮減既有 CJK 搜尋能力。
- Regression-first 證據：查詢限定與結果分類的雙重案例修正前為 `1 failed`，
  修正後針對性案例為 `1 passed`，YouTube scope、內建完整性與 MOD 矩陣為
  `16 passed, 1 skipped`；完整 repository runner 為 `1495 passed, 7 skipped`。
  Quality audit 通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案；
  MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件、
  Testing 版本與 Repository 外隔離 `compileall` 均通過。
- 此修正不繞過網站限制、不增加搜尋頁面大小或重試次數。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.62（常見音樂詞形召回）

- 修正拉丁音樂訊號改用完整詞界後，原本依靠 `song`、`album`、`playlist` 與
  `mix` 子字串命中的合法複數及 `remix` 詞形也一起失去辨識的召回缺口。
- 訊號詞表顯式加入 `songs`、`albums`、`playlists`、`mixes`、`remix` 與
  `remixes`，所有詞形仍使用 39.0.61 的嚴格詞界；`mixed`／`mixing` 不會重新
  被視為音樂訊號。
- Regression-first 證據：五種常見詞形修正前為 `5 failed`；修正後連同一般
  單字誤判防護為 `6 passed`，YouTube scope、內建完整性與 MOD 矩陣為
  `21 passed, 1 skipped`；完整 repository runner 為 `1500 passed, 7 skipped`。
  Quality audit 通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案；
  MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件、
  Testing 版本與 Repository 外隔離 `compileall` 均通過。
- 此修正只調整 YouTube 搜尋查詢限定與本機結果分類，不增加外部請求或放寬
  網站限制。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、
  commit、push 或發布。

## 39.0.63（History 偏好計數型別）

- 修正 `HistoryPreferencesV1.from_dict()` 以 `isinstance(value, int)` 驗證計數，
  因 Python 的 `bool` 是 `int` 子類而把 `True`／`False` 當成合法總數或 counter
  接受的共用契約缺口。
- 偏好總數與四組 counter 現在都在唯一契約入口明確排除布林值；既有合法整數
  範圍、100 組 counter 上限與下游建議／相似音樂行為保持不變。
- Regression-first 證據：布林總數與布林作者 counter 修正前為 `2 failed`，
  修正後為 `2 passed`；History、搜尋建議與相似音樂套件為 `31 passed`，完整
  repository runner 為 `1502 passed, 7 skipped`。Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件、Testing 版本與 Repository 外隔離
  `compileall` 均通過。
- 此修正只隔離外部 MOD 的畸形偏好回應，不改寫既有歷史檔。Testing `1.2.1`
  與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.64（拉丁重音搜尋身分一致性）

- 修正搜尋排序自 39.0.55 起會折疊拉丁重音，但最近搜尋、偏好建議與
  `youtube-similar` 查詢計畫仍只用 NFKC＋casefold 去重的規則落差；
  `Beyoncé`／`Beyonce` 可能被拆分計數、重複顯示，或占用三個查詢槽之一。
- 核心排序與建議現在共用同一個 Unicode 搜尋文字身分；相似音樂 subprocess
  保留等價的有界本機實作。只移除拉丁基底後的組合符號，其他文字系統的組合
  符號仍保留，不縮減原有 CJK 與其他無空格文字能力。
- Regression-first 證據：偏好計數合併、歷史建議去重及相似查詢槽三個案例在
  修正前為 `3 failed`，修正後相關搜尋建議、排序與相似計畫套件為 `32 passed`；
  定向搜尋、History、相似 MOD、內建雜湊與版本套件為 `85 passed`，完整
  repository runner 為 `1505 passed, 7 skipped`。Quality audit 通過 Ruff
  `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件、Testing 版本與 Repository 外隔離
  `compileall` 均通過。
- 此修正不增加外部請求、頁面上限、Cookie 或下載能力。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.65（相似候選拉丁重音 token）

- 修正 39.0.64 已統一查詢、偏好與計畫的拉丁重音身分，但相似候選的標題／
  作者 token 仍只做 NFKC＋casefold 的最後一處規則落差；未輸入重音的公開搜尋
  候選即使文字等價，也可能失去最多 35 分 title 或 30 分 artist 相關性。
- `youtube-similar` token 現在使用相同的拉丁重音折疊後再切詞；語言、分類、
  preference、去重、結果上限與穩定排序規則保持不變，其他文字系統的組合符號
  仍保留。
- Regression-first 證據：重音等價標題與作者案例修正前均只得語言＋分類
  `25` 分並形成 `2 failed`；修正後完整相似音樂套件為 `18 passed`。定向相似、
  搜尋身分、內建雜湊與版本套件為 `78 passed`，完整 repository runner 為
  `1507 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件、Testing 版本與 Repository 外隔離 `compileall` 均通過。
- 此修正只改善本機相似候選排序，不增加搜尋查詢、Cookie、下載或網站存取能力。
  Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.66（相似 token 欄位上限一致性）

- 修正 39.0.65 讓 `tokens()` 改用預設 200 字元的文字身分 helper，卻沒有保留
  DiscoveryItem 標題可達 300 字元的契約差異；第 201～300 字元內的標題 token
  因而不再參與相似度計算。
- 標題與作者相似度現在分別以契約上限 300／200 字元正規化與切詞；計畫查詢
  既有 160／100 字元邊界、拉丁重音折疊、分數權重與結果上限保持不變。
- Regression-first 證據：兩個 257 字元合法標題只在尾端共享 token，修正前候選
  只得語言＋分類 `25` 分並形成 `1 failed`；修正後完整相似音樂套件為
  `19 passed`。定向相似、搜尋身分、內建雜湊與版本套件為 `79 passed`，完整
  repository runner 為 `1508 passed, 7 skipped`。Quality audit 通過 Ruff
  `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件、Testing 版本與 Repository 外隔離
  `compileall` 均通過。
- 此修正復原本機相似排序的契約覆蓋，不增加外部請求或網站能力。Testing
  `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.67（YouTube 音樂詞形補充）

- 修正本機查詢清理已把 `sound track` 正規化為 `soundtrack`，但 YouTube
  搜尋 scope 尚未辨識 `soundtrack`／`OST`／`karaoke` 的跨模組詞彙落差；
  明確音樂查詢會被重複附加 `music`，all scope 結果也可能誤標為 video。
- 音樂訊號加入 `soundtrack`、`soundtracks`、`ost` 與 `karaoke`，沿用 39.0.61
  的拉丁完整詞界；`post production` 與 `cloud cost` 不會因內含 `ost` 而誤判。
- Regression-first 證據：四個明確詞形修正前為 `4 failed`，兩個內含字負例
  保持通過；修正後完整 YouTube scope 套件為 `13 passed`。定向 YouTube scope、
  內建雜湊、搜尋排序與版本套件為 `64 passed`，完整 repository runner 為
  `1512 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件、Testing 版本與 Repository 外隔離 `compileall` 均通過。
- 此修正只改善查詢限定與本機分類，不增加結果上限、重試、Cookie、下載或網站
  權限。Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、
  commit、push 或發布。

## 39.0.68（YouTube music scope 查詢上限）

- 修正顯式 music scope 在查詢未含音樂詞形時無條件附加 ` music`，使原本合法的
  195–200 字元查詢超過 Search v2 既有 200 字元上限的契約落差。
- 只有補上提示後仍不超過上限的查詢才會附加；194 字元查詢可補至剛好 200
  字元，195 與 200 字元查詢保持原文，不截斷或靜默改寫使用者輸入。
- Regression-first 證據：新增邊界案例修正前為 `1 failed`；修正後完整 YouTube
  scope 套件為 `14 passed`。定向 scope、內建雜湊、YouTube MOD 矩陣、搜尋排序
  與版本套件為 `65 passed`，完整 repository runner 為 `1513 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 此修正不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.69（搜尋智慧撇號身分）

- 修正 YouTube metadata 常見的直撇號與 U+2018／U+2019 智慧撇號未使用同一
  本機搜尋身分，造成同名作品排序落後、歷史建議重複及相似音樂有限查詢槽
  被同一作者的標點變體占用。
- 共用搜尋身分只在本機比較時正規化撇號；UI 顯示、歷史代表值與送往 provider
  的查詢仍保留原始文字。隔離的 `youtube-similar` MOD 同步相同規則。
- Regression-first 證據：排序、建議與相似計畫三條案例修正前為 `3 failed`，
  修正後為 `3 passed`；搜尋排序、建議、歷史與相似音樂相關套件為 `61 passed`。
  定向搜尋、歷史、相似、內建雜湊、YouTube MOD 矩陣與版本套件為 `91 passed`，
  完整 repository runner 為 `1516 passed, 7 skipped`。Quality audit 通過 Ruff
  `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing 版本與 Repository 外隔離
  `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 此修正不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.70（搜尋排版破折號身分）

- 修正 ASCII `-` 與常見排版連字號／破折號未使用同一本機搜尋身分，造成
  同名作品排序落後、歷史建議重複及相似音樂有限查詢槽被同一作者占用。
- 共用搜尋身分將 U+2010～U+2015 折疊為 ASCII `-`；UI 顯示、歷史代表值與
  送往 provider 的查詢仍保留原始文字。隔離的 `youtube-similar` MOD 同步規則。
- Regression-first 證據：排序、建議與相似計畫三條案例修正前為 `3 failed`，
  修正後為 `3 passed`。定向搜尋、歷史、相似、內建雜湊、YouTube MOD 矩陣
  與版本套件為 `94 passed`，完整 repository runner 為 `1519 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 此修正不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.71（YouTube Topic 頻道音樂分類）

- 修正 all scope 只檢查查詢、標題、曲目、專輯、類型與分類，忽略 yt-dlp 已
  回傳的 channel／uploader，導致一般標題的 YouTube 自動音樂頻道被誤標為
  video，削弱後續相似音樂分類。
- 新增嚴格的 `Artist - Topic` 頻道後綴訊號，同時支援 U+2010～U+2015 排版
  連字號／破折號；只有前方具空白分隔且以 `Topic` 結尾才成立，`Topic World`、
  `off-topic` 與空白頻道不會誤判。
- Regression-first 證據：ASCII 與 en dash 正例修正前為 `2 failed`，同檔正負
  案例修正後為 `19 passed`。定向搜尋、歷史、相似、內建雜湊、YouTube MOD
  矩陣與版本套件為 `113 passed`，完整 repository runner 為
  `1524 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- 此變更只使用搜尋結果既有 metadata，不增加網路請求、Cookie、登入、下載、
  重試或網站權限。
- Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.72（搜尋連字號空格身分）

- 修正 39.0.70 雖已統一 ASCII 與排版破折號，仍保留破折號兩側空格差異，導致
  `Artist-Title` 與 `Artist - Title` 被視為不同搜尋身分。
- 共用搜尋比較層會先折疊破折號字元，再移除其兩側空白；隔離的
  `youtube-similar` MOD 同步相同規則。UI 顯示、歷史代表值及送往 provider 的
  原始查詢均保持不變。
- Regression-first 證據：同名排序、歷史建議與相似音樂計畫三條案例修正前為
  `3 failed`，修正後為 `3 passed`。定向搜尋、歷史、相似、內建雜湊、YouTube
  MOD 矩陣與版本套件為 `116 passed`，完整 repository runner 為
  `1527 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- 此修正不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.73（搜尋智慧雙引號身分）

- 修正直雙引號與 U+201C／U+201D 左右智慧雙引號被視為不同搜尋身分，導致
  同名結果排序失真、歷史建議重複及相似音樂浪費有限查詢槽的問題。
- 共用搜尋比較層與隔離的 `youtube-similar` MOD 只在本機比較時將智慧雙引號
  折疊為直雙引號；UI 顯示、歷史代表值及送往 provider 的原始查詢均保持不變。
- Regression-first 證據：同名排序、歷史建議與相似音樂計畫三條案例修正前為
  `3 failed`，修正後為 `3 passed`。定向搜尋、歷史、相似、內建雜湊、YouTube
  MOD 矩陣與版本套件為 `119 passed`，完整 repository runner 為
  `1530 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- 此修正不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.74（相似音樂底線詞界）

- 修正共用搜尋排序將底線視為詞界、但 `youtube-similar` 將其包含在單一 token
  的規則落差。provider 回傳 `Hello_World` 類標題時，現在可與 `Hello World`
  使用相同的兩個本機 token 計算相似度。
- 變更只套用標題與作者的本機 token 化，不改寫媒體 ID、UI 顯示、provider
  查詢或外部資料。
- Regression-first 證據：底線標題案例修正前為 `1 failed`，只得到語言與分類
  25 分；修正後為 `1 passed`，正確得到標題、語言與分類共 60 分。定向搜尋、
  歷史、相似、內建雜湊、YouTube MOD 矩陣與版本套件為 `120 passed`，完整
  repository runner 為 `1531 passed, 7 skipped`。Quality audit 通過 Ruff `367`
  個 Python 檔與文字污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing 版本與 Repository 外隔離
  `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 此修正不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.75（搜尋顯示選擇符身分）

- 修正 U+FE0E／U+FE0F 文字／Emoji 顯示選擇符被納入本機搜尋身分，導致只差
  呈現形式的文字被誤判為不同標題或作者。
- 共用搜尋比較層與隔離的 `youtube-similar` MOD 只在比較時忽略顯示選擇符；
  UI 顯示、歷史代表值及送往 provider 的原始查詢均保持不變。
- Regression-first 證據：同名排序、歷史建議與相似音樂計畫三條案例修正前為
  `3 failed`，修正後為 `3 passed`。定向搜尋、歷史、相似、內建雜湊、YouTube
  MOD 矩陣與版本套件為 `123 passed`，完整 repository runner 為
  `1534 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- 此修正不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.76（lo-fi 排版連字號別名）

- 修正查詢比較已統一排版破折號，但已知 `lo-fi → lofi` phrase alias 仍只接受
  ASCII `-` 的規則落差。從網頁複製的 `lo‑fi`、`lo–fi` 與 `lo―fi` 現在會套用
  相同的既有修正。
- alias pattern 只將已知別名內的 `-` 擴充為 U+2010～U+2015，其他查詢中的
  破折號不改寫，且保留前後完整詞界，因此 `flo–fi` 仍維持原文。
- Regression-first 證據：排版正例修正前失敗、較長單字負例通過；修正後兩條
  測試均通過。定向搜尋、歷史、相似、內建雜湊、YouTube MOD 矩陣與版本套件
  為 `125 passed`，完整 repository runner 為 `1536 passed, 7 skipped`。Quality
  audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD 群組
  `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing 版本與
  Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 此修正不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.77（搜尋 Unicode 負號身分）

- 修正常見 U+2212 Unicode 負號 `−` 未納入既有連字號身分的規則落差；從網頁
  或 metadata 複製的 `Artist − Title` 原本會失去精確排序、重複出現在搜尋建議，
  並占用相似音樂有限查詢槽。
- 共用搜尋比較層、`lo-fi` phrase alias 與隔離的 `youtube-similar` MOD 現在將
  U+2212 折疊為 ASCII `-`。YouTube 搜尋也只在嚴格的 `Artist − Topic` 頻道
  後綴接受此字元；一般負號文字不會因此被判定為 Topic 頻道。
- Regression-first 證據：排序、建議、相似查詢與 `lo−fi` 別名四條案例修正前
  為 `4 failed`；Topic 頻道參數化案例為 `1 failed, 2 passed`。修正後相同案例
  為 `7 passed`。顯示、歷史代表值及送往 provider 的原始查詢保持不變。定向
  套件為 `130 passed`，完整 repository runner 為 `1540 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 此修正不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與
  `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.78（Bilibili 查詢準備一致性）

- 修正 Bilibili 專用搜尋工作區未套用共用 `prepare_search_query` 的入口落差；
  同一個 `LO-FI offical` 查詢原本在通用／YouTube 工作區會修正為
  `lofi official`，但在 Bilibili 工作區仍以原字串派送。
- Bilibili 文字搜尋現在會回填並派送準備後的查詢，也保留修正摘要供搜尋中
  狀態顯示。官方 Bilibili URL 仍優先由既有 exact-site 路由辨識，不會被改寫。
- Regression-first 證據：新增案例修正前為 `1 failed`，修正後為 `1 passed`；
  五個相關套件為 `55 passed`，完整 repository runner 為
  `1541 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- 不新增 provider、外部 fallback、Cookie、下載、重試或網站權限。
- Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.79（Bilibili 精確標題排序）

- 修正 Bilibili 專用工作區合併結果後未套用共用本機相關性排序的入口落差；
  provider 若先回傳 `Exact Match Remix`、再回傳完全同名的 `Exact Match`，
  原本 UI 仍讓延伸標題排在前面。
- 合併與官方來源過濾後，結果現在使用既有 `rank_search_results` 穩定排序。
  完全同名可提升；相同分數仍保留 provider 原順序，追加分頁的已選 URL 也由
  既有還原流程保留。
- Regression-first 證據：新增案例修正前為 `1 failed`，修正後為 `1 passed`；
  五個相關套件為 `56 passed`，完整 repository runner 為
  `1542 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- 不新增外部請求、provider、fallback、Cookie、下載、重試或網站權限。
- Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.80（專用搜尋有界分頁終止）

- 修正共用 `merge_search_results` 已將工作區限制為 200 筆，但 YouTube 與
  Bilibili 專用工作區在達上限後仍保留 provider 下一頁游標的狀態落差；使用者
  原本可繼續按「載入更多」，送出無法增加顯示結果的請求。
- 兩個專用工作區現在於合併後共用檢查 `MAX_WORKSPACE_SEARCH_RESULTS`；達上限
  即清除游標、停用下一頁操作，並在狀態文字顯示 `已達 200 筆上限`。未達上限
  的正常分頁、失敗保留、去重、排序與選取還原行為不變。
- Regression-first 證據：YouTube／Bilibili 兩條案例修正前為 `2 failed`，
  修正後為 `2 passed`；六個相關套件為 `54 passed`，完整 repository runner
  為 `1544 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與
  文字污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall`
  均通過，`Version/` 中有 `0` 個 `.pyc`。
- 不增加 provider、Cookie、下載、重試或網站權限。
- Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.81（引號標題 by 作者精確排序）

- 修正常見的 `"標題" by 作者` 明確查詢仍只取得零散關鍵字分數的缺口；若
  provider 先回傳把整句放入標題的延伸內容，真正分離在 `title`／`artist`
  欄位的作品原本會排在後面。
- 共用本機排序只新增嚴格的 `"{title}" by {artist}` 完整候選模板；既有雙引號
  正規化同時涵蓋左右智慧引號。未加引號的 `by` 不作為欄位分隔符，
  `Stand by Me` 等正式作品名稱不會被拆分；provider 查詢原文、外部請求與
  其他分數保持不變。
- Regression-first 證據：正例修正前為 `1 failed`，未加引號負例為 `1 passed`；
  修正後兩條案例為 `2 passed`。七個相關套件為 `102 passed`，完整 repository
  runner 為 `1546 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python
  檔與文字污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing 版本與 Repository 外
  隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 不增加 provider、Cookie、下載、重試或網站權限。Testing `1.2.1` 與 `1.2.2`
  保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.82（完整引號標題精確排序）

- 修正使用者以成對雙引號搜尋完整曲名時，本機排序仍把引號視為標題內容的
  缺口。`“Midnight Echo”` 原本無法讓未帶引號的正式 `Midnight Echo` 取得
  完全相等順位，可能落在將引號整句放入標題的 `live cover` 後方。
- 共用排序只在整個正規化查詢由成對雙引號包住時，額外建立去除最外層引號的
  標題比較候選；既有智慧雙引號折疊與拉丁重音 fallback 同樣適用。未閉合引號、
  查詢內部引號、UI 顯示及送往 provider 的原始查詢均不改寫。
- Regression-first 證據：成對引號正例修正前為 `1 failed`，未閉合引號負例為
  `1 passed`；修正後正負例、既有智慧引號與重音案例共 `4 passed`。七個相關
  套件為 `104 passed`，完整 repository runner 為 `1548 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 不增加 provider、Cookie、下載、重試或網站權限。Testing `1.2.1` 與 `1.2.2`
  保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.83（引號曲名搭配作者精確排序）

- 修正 39.0.81～82 只涵蓋整句引號標題及 `"標題" by 作者`，但常見的
  `"標題" 作者`、`作者 "標題"`、`"標題" - 作者` 與反向破折號形式仍退回
  零散關鍵字分數的缺口。
- 嚴格跨欄位候選現在會同時使用原始完整標題及其成對引號形式，再套入既有
  有限分隔符白名單與正向／反向排列。查詢仍必須完整等於 metadata 作者與完整
  標題組合；`"Midnight" Nora Vale` 不會誤升為完整 `Midnight Echo` 的 100 分。
- Regression-first 證據：四種正向／反向語法修正前形成 `1 failed`，部分曲名
  負例為 `1 passed`；修正後加上 39.0.81～82 引號案例共 `5 passed`。七個相關
  套件為 `106 passed`，完整 repository runner 為 `1550 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 不改寫 provider 查詢，不增加外部請求、Cookie、下載、重試或網站權限。
  Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.84（完整引號作者精確排序）

- 修正 39.0.82 的平衡引號候選只供標題精確比較使用，導致 `“Nora Vale”`
  這類完整引號作者查詢仍可能排在標題提及該作者的內容之後。
- 平衡引號候選改為標題／作者共用欄位候選；精確與 Unicode 折疊比較均沿用
  相同有限規則。未閉合引號保持原文，不取得作者完全相等分數；provider 查詢
  原文與外部請求行為不變。
- Regression-first 證據：作者正例修正前為 `1 failed`，未閉合引號負例為
  `1 passed`；修正後連同標題與重音案例共 `5 passed`。七個相關套件為
  `108 passed`，完整 repository runner 為 `1552 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 不增加 provider、Cookie、下載、重試或網站權限。Testing `1.2.1` 與 `1.2.2`
  保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.85（引號作者搭配曲名精確排序）

- 修正 39.0.83 的跨欄位候選只產生引號曲名，導致 39.0.84 雖可辨識單獨的
  完整引號作者，`“Nora Vale” Midnight Echo` 等作者＋曲名查詢仍退回零散
  關鍵字分數的缺口。
- 完整 metadata 作者現在與完整標題一樣可產生成對引號候選，再套入既有有限
  分隔符白名單與正向／反向排列；`“Nora Vale” “Midnight Echo”` 及
  `“Midnight Echo” by “Nora Vale”` 亦維持嚴格完整欄位比較。部分作者不會被
  誤升為完整匹配。
- Regression-first 證據：多種完整引號作者語法修正前形成 `1 failed`，部分作者
  負例為 `1 passed`；修正後連同既有引號欄位案例共 `6 passed`。七個相關套件
  為 `110 passed`，完整 repository runner 為 `1554 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 不改寫 provider 查詢，不增加外部請求、Cookie、下載、重試或網站權限。
  Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.86（東亞成對引號搜尋身分）

- 修正 `「」`、`『』`、`《》`、`〈〉` 在共用排序、歷史建議及隔離的
  `youtube-similar` MOD 中仍被視為不同文字身分，導致 `《曲名》` 無法提升
  未加標記的正式標題，等價偏好也可能產生重複查詢的缺口。
- 共用正規化只將完整配對且不含同型巢狀標記的內容轉為本機雙引號身分；錯配
  `「曲名』` 維持原文。原始顯示、歷史代表值與送往 provider 的查詢均不改寫。
  隔離 MOD 保留自含實作，並同步更新其 pinned SHA-256。
- Regression-first 證據：排序、建議、相似搜尋正例修正前為 `3 failed`，錯配
  標記負例為 `1 passed`；修正後共 `4 passed`。九個相關套件為
  `126 passed, 1 skipped`，完整 repository runner 為
  `1558 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- 不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與 `1.2.2`
  保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.87（補齊作者／標題有限分隔符）

- 修正跨欄位候選重複列出已被共用正規化折疊為 `-` 的排版破折號，卻未涵蓋
  常見 `/`、全形 `／`、日文中點 `・`，以及 `|`／`:` 單側空白形式的落差。
- 候選改為正規化後的空白與連字號，加上 `|`、`:`、`·`、`・`、`/` 各四種
  有限空白排列。只有完整 metadata 作者與完整標題的正向／反向組合能取得
  跨欄位精確分數；不新增一般模糊切詞。
- Regression-first 證據：新增分隔符正例修正前為 `1 failed`，部分作者負例為
  `1 passed`；修正後連同舊分隔符與引號欄位案例共 `6 passed`。七個相關套件
  為 `116 passed`，完整 repository runner 為 `1560 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 不改寫 provider 查詢，不增加外部請求、Cookie、下載、重試或網站權限。
  Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、
  push 或發布。

## 39.0.88（有限分隔符空白等價身分）

- 修正 39.0.87 僅讓精確排序接受 `/`、`|`、`:`、`·`、`・` 的空白變體，
  但共用歷史／偏好建議及隔離的 `youtube-similar` MOD 仍將
  `Artist/Title`、`Artist / Title` 視為不同搜尋身分的跨模組落差。
- 共用與隔離正規化只移除上述有限分隔符兩側的空白，保留分隔符本身；
  `Artist Title` 仍是不同身分。排序候選改為只列出正規化後的七種分隔符，
  不改寫 UI 顯示、歷史代表值或送往 provider 的查詢原文。
- Regression-first 證據：搜尋建議、最近歷史及相似音樂三條案例修正前為
  `3 failed`，修正後為 `3 passed`；搜尋排序、建議、歷史與相似音樂四個相關
  套件為 `98 passed`，八個定向套件為 `126 passed`；完整 repository runner 為
  `1563 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- 不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與 `1.2.2`
  保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.89（lo-fi 空白破折號別名）

- 修正共用搜尋身分已將連字號兩側空白視為同一排版，但送往 provider 前的既有
  `lo-fi → lofi` 詞組修正仍只接受無空白連字號，造成 `lo - fi playlist` 沒有
  套用既有別名的落差。
- 詞組別名只在既有連字號位置接受零或多個空白，並沿用 ASCII、U+2010～U+2015
  與 U+2212 白名單；完整詞界及 200 字元上限不變，`flo - fi`、
  `lo - fighter` 等較長單字不會被改寫。
- Regression-first 證據：四個空白連字號正例修正前為 `1 failed`，兩個較長單字
  負例為 `1 passed`；最小修正後兩項為 `2 passed`。搜尋排序、YouTube／
  Bilibili 工作區與版本定向回歸為 `92 passed`；完整 repository runner 為
  `1565 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- 不增加外部請求、Cookie、下載、重試或網站權限。Testing `1.2.1` 與 `1.2.2`
  保持不可變；本輪不執行 build、stage、commit、push 或發布。

## 39.0.11 Validation Baseline

- 完整 repository runner：`1364 passed, 7 skipped`。
- Quality audit：Ruff `364` 個 Python 檔案、文字污染 `471` 個受控文字檔。
- MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`。
- 本機保留版本稽核：`3` 個版本通過。
- source freeze 文件稽核涵蓋 `21` 份 Markdown，本機連結 `0` 失效。
- 精準清除 `32` 個可再生的 pytest、Ruff 與 Python cache 目錄；未刪除
  `.venv`、`Version`、`UserData` 或使用者檔案。
- source freeze 已通過 Repository 外 compileall、source-only `--verify-only`
  與 `git diff --check`；`Version/` 中有 `0` 個 `.pyc`。

## Testing 1.1 Gate

使用者已授權 Development 39.0.10 的 stage、commit、source freeze，以及由同一
乾淨 revision 建立、上傳未簽署 `SAFE_MODE` Testing `1.1.0`。GitHub Release
使用唯一 tag `test-v1.1.0-r2`，精確指向 `09b3a86e00938241d27050088583ebf81d9fb182`；
9 個附件的 GitHub digest 與本機 SHA-256 一致。遠端 metadata 目前誤設為非
prerelease 並被視為 Latest，需另行授權修正；Testing 1.0 與既有 tags 不覆寫。
Authenticode 與 production signed release manifest 仍未成立，因此 Stable Gate
保持阻擋。

## Testing 1.2 Gate

Development `39.0.11` 已於 revision
`fab5cb9333274e54f65a35b2f44a86699f0f349f` source freeze，並由同一 revision
完成 build、建立未簽署 EXE、stage Testing `1.2.0` 與產生自包含 ZIP；
`Version/Testing/1.2/release-info.json` 已記錄相同來源。push、簽署與發布
當時未獲授權，且公開 GitHub API 查核顯示沒有 Testing `1.2.0` Release 或 tag。
此本機候選保留為不可覆寫歷史，Development `39.0.12` 不回寫該目錄。

Testing `1.2.1` 使用新的 patch 目錄 `Version/Testing/1.2.1`，來源為
Development `39.0.12` revision
`05442d7875da5367cd23babc2ce4e2e3e0cb87a2`。唯一 tag `test-v1.2.1` 已建立，
[GitHub Release](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.1)
已發布為 prerelease，遠端共有 9 個附件。主要附件
`MediaManager-Testing-1.2.1.zip` 的 SHA-256 為
`c633586d974fb77ba8041533cf7f7fd5378ab651d2b8f86126ccceb6b070f148`，
並與 `MediaManager-Testing-1.2.1.zip.sha256` 閉合。Testing 維持未簽署
`SAFE_MODE`、不是 Stable，也未覆寫 Testing `1.2.0` 歷史。

Testing `1.2.2` 已由 Development `39.0.39` 的乾淨 source freeze
`f7c65ee1a8e92828ede299bcbdff5e66d16f6810` 建立於新的
`Version/Testing/1.2.2`。tag `test-v1.2.2` 與
[GitHub prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)
已發布；遠端共有 9 個 `uploaded` 附件。`MediaManager-Testing-1.2.2.zip`
為 196,925,239 bytes，SHA-256
`2dd688ceb6a3af9c3e100dca1c61a326ac8be2a19237b217bd2f8a21b6a7e2c4`，
已與 sidecar 及 GitHub asset digest 閉合。build receipt、source revision、runtime
audit、copied-folder current／previous／current smoke、deterministic ZIP、tag、
prerelease 與全部附件 digest 均已驗證；Testing 1.2.1 的目錄、tag 與公開附件
維持不可變。

## 39.0.90（格式工廠本機影像浮水印）

- 補齊格式工廠參考需求中的影片浮水印缺口；新增 `watermark-h264` preset 與
  可信 UI 影像選擇欄，輸出 H.264／AAC 的 `.mp4` 或 `.mkv` 新檔。
- 浮水印只接受使用者選取的單一 PNG／JPEG／WebP／BMP／TIFF 一般本機檔，
  固定縮放上限與右下位置；不接受連結檔、網址、自訂 FFmpeg filter 或覆寫來源。
- Regression-first 命令契約在修正前因 `ConversionRequest` 沒有 watermark 欄位而
  `1 failed`；修正後命令契約、offscreen UI 與本機 FFmpeg smoke 為 `3 passed`；
  五個定向套件為 `69 passed, 1 skipped`，完整 repository runner 為
  `1567 passed, 7 skipped`。
- 文件、DVD 與 CD 不屬於目前 FFmpeg 媒體工作區，不宣稱為已支援。Testing
  `1.2.1` 與 `1.2.2` 保持不可變；本輪不執行 build、stage、commit、push 或發布。
- Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、兩個
  Testing 版本、Repository 外隔離 `compileall` 與 `git diff --check` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。

## 39.0.91（YouTube flat-search 片長契約隔離）

- Root Cause：`youtube-search` 直接對 yt-dlp flat metadata 的任意數值執行
  `int()`；`NaN` 會中止整頁搜尋，而布林、負值與超過 86400 秒的值會違反
  `DiscoveryItemV1` 契約。
- 在 MOD 邊界新增有界片長正規化；只接受有限的 `int`／`float` 0～86400 秒，
  其餘值降為 `None`。不改查詢、結果順序、URL、下載或 Cookie 行為。
- Regression-first 案例修正前為 `1 failed`，修正後為 `1 passed`；七個定向
  套件為 `127 passed`，完整 repository runner 為 `1568 passed, 7 skipped`。
- `youtube-search/provider.py` 的內建 pinned SHA-256 已同步；Testing `1.2.1` 與
  `1.2.2` 保持不可變。本輪不執行 build、stage、commit、push 或發布。
- Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `476` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、兩個
  Testing 版本、Repository 外隔離 `compileall` 與 `git diff --check` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。

## 39.0.92（YouTube Music songs scope）

- Root Cause：顯式 `music` scope 與相似音樂查詢雖已正確標為音樂，底層仍只把
  `music` 文字加到一般 YouTube `ytsearch`，未使用目前鎖定 yt-dlp 已提供的
  YouTube Music songs extractor。
- `music` scope 現在以標準 URL 編碼建立
  `https://music.youtube.com/search?...#songs` 目標；`playlistend`、offset 與
  200 筆上限不變。`all`／`video` 仍使用原本的 bounded `ytsearch`。
- 已移除被 songs extractor 吸收的 query-hint helper 與其測試，保留音樂訊號在
  `all` scope 的本機分類用途；沒有新增 API key、Cookie、登入、下載或 fallback。
- Regression-first 路由案例修正前為 `1 failed`，修正後 YouTube scope／MOD
  matrix 為 `29 passed`；七個呼叫鏈定向套件為 `119 passed`，完整 repository
  runner 為 `1569 passed, 7 skipped`。
- `youtube-search/provider.py` 的內建 pinned SHA-256 已同步；Testing `1.2.1` 與
  `1.2.2` 保持不可變。本輪不執行 build、stage、commit、push 或發布。
- Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `476` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、兩個
  Testing 版本、Repository 外隔離 `compileall` 與 `git diff --check` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。

## 39.0.93（H.265 Main10 NVENC／Opus Passthru MKV）

- 新增 `hevc10-nvenc-opus-copy` 格式工廠 preset，固定輸出 `.mkv`；影片使用
  `hevc_nvenc` Main10／`p010le`、p7 Slowest、HQ、VBR 平均 300 kbps、完整解析度
  multipass、32-frame lookahead、Spatial／Temporal AQ，音訊使用 `copy`。
- 不指定輸出解析度或固定 FPS，並明確不加入縮放、裁切、`-vf`、`-af` 或
  filter graph；1920×1080／24 FPS 來源因此保持原尺寸與時間戳。
- UI 只有在本機能力偵測到 `hevc_nvenc` 後才允許加入；服務層再以 ffprobe 確認
  第一條來源音訊是 Opus。非 Opus、無音訊或缺少 NVENC 時明確拒絕，不做 CPU
  fallback，也不以其他音訊編碼冒充 Passthru。
- Regression-first 四條定向案例在實作前為 `4 failed`；完成後的相關套件為
  `76 passed, 2 skipped`，完整 Repository runner 為 `1571 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `476` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、兩個
  Testing 版本、Repository 外隔離 `compileall` 與 `git diff --check` 均通過。
- 本機 FFmpeg 實測的短片輸出為 HEVC Main 10／`yuv420p10le`、Opus、Matroska，
  來源與輸出 Opus packet SHA-256 相同；另以 1920x1080／24 FPS 樣本確認輸出仍為
  1920x1080／24 FPS。這些測試只驗證目前機器的 NVIDIA／FFmpeg 路徑，不代表所有
  GPU 與驅動組合均相容。
- Testing `1.2.1` 與 `1.2.2` 保持不可變；本輪未獲授權 build、stage、commit、
  push 或發布。

## 39.0.94（H.265 Main10 輸出契約與量測式優化）

- 以同一份 4 秒 1920x1080／24 FPS 樣本、相同 FFmpeg／GPU 路徑比較候選參數。
  既有 p7／HQ 組合為 VMAF `62.479828`、SSIM `0.954483`；加入 B-reference、
  UHQ、lookahead level 3 或改變 AQ strength 都降低其中一項或兩項品質指標，
  lookahead 64 則與既有輸出完全相同，因此保留 39.0.93 的編碼參數。額外加入
  300 kbps maxrate／600 kbps buffer 後，同一樣本由 `227806` 增為 `229185`
  bytes，而 VMAF 只增加 `0.044476`，沒有檔案大小效益，因此不採用硬上限。
- `hevc10-nvenc-opus-copy` 新增資料驅動 `output_contract`。FFmpeg 成功後、原子
  提交前必須由 ffprobe 確認 Matroska、HEVC、Main 10、10-bit pixel format、
  Opus、來源解析度與固定影格率，且來源／輸出 Opus 壓縮封包 SHA-256 必須
  相同；欄位缺漏、規格偏離或封包雜湊改變都視為失敗並移除 `.part`。
- 契約 schema 只接受有限已知欄位與型別，其他格式日後可重用相同機制；一般
  preset 沒有宣告契約時維持原本「非空且至少一條可讀 stream」驗證。
- ffprobe 與 Opus 封包雜湊沿用背景工作的取消事件；驗證中取消會終止子程序、
  移除 `.part`，不會等候最長 300 秒雜湊 timeout 或留下半成品。
- Regression-first 案例實作前為 `1 failed`；輸出契約定向案例為 `11 passed`，
  完整轉換服務為 `59 passed, 1 skipped`，完整 Repository runner 為
  `1592 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與
  文字污染 `476` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、兩個 Testing 版本、Repository 外隔離
  `compileall` 與 `git diff --check` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- 實機服務以 1920x1080／24 FPS／Opus 樣本再次產生 `227806` bytes 的 HEVC
  Main 10／`yuv420p10le`／Opus Matroska，並由新增 Gate 完成來源／輸出 Opus
  封包 SHA-256 比對；這是目前機器的本機證據，不代表所有 GPU／驅動組合。
- Testing `1.2.1` 與 `1.2.2` 保持不可變；Testing `1.2.3` 保留給此 source
  freeze 的本機未簽署 `SAFE_MODE` 候選。本輪不 push、不簽署、不發布。

## 39.0.95（啟動流程取消自動彈出視窗）

- Root Cause：可信主視窗在建立前無條件呼叫首次 MOD 設定模態視窗，建立後又在
  YouTube 核心工具未就緒時排程依賴環境模態視窗；即使主畫面已有 MOD 管理與
  環境狀態入口，啟動仍可能連續出現額外視窗。
- 啟動現在直接顯示主畫面，不再自動開啟上述兩種視窗。MOD 與依賴狀態仍完整
  顯示，使用者可從主畫面按鈕明確開啟；既有設定、MOD 狀態與工具安裝皆不會被
  靜默修改。
- Regression-first 案例修正前捕捉到「首次啟動：選擇要啟用的 MOD」並為
  `1 failed`；移除自動開窗路徑後為 `1 passed`。六個相關套件為 `44 passed`，
  完整 Repository runner 為 `1593 passed, 7 skipped`。
- Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `476` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、兩個
  Testing 版本、Repository 外隔離 `compileall` 與 `git diff --check` 均通過。
- Testing `1.2.1`、`1.2.2` 與本機 Testing `1.2.3` 產物保持不可變；本輪已獲
  授權 stage、commit 與 push 原始碼，不執行 build、簽署或發布。

## 40.0

沒有獨立 material delta，狀態為 `ABSORBED / NO RELEASE / NO PLAN`。不得為維持
版本號建立空版本；若日後出現可重現缺口，需另建計畫並重新取得相應授權。
