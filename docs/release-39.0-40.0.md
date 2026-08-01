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

## 40.0

沒有獨立 material delta，狀態為 `ABSORBED / NO RELEASE / NO PLAN`。不得為維持
版本號建立空版本；若日後出現可重現缺口，需另建計畫並重新取得相應授權。
