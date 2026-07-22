# MediaManager 文件入口

這個頁面是儲存庫文件的單一入口。請先依「目前有效文件」判斷現況；舊版發行紀錄
只保存當時事實，不代表目前功能、安裝方式或正式版狀態。

## 目前狀態

- 目前來源版本為開發版 39.0（核心相容版本 39.0.6），狀態
  `G39-08 SOURCE-FROZEN / NO PACKAGE / SAFE_MODE`。`38.1.14` 已
  `SOURCE VALIDATED / SUPERSEDED BY 38.1.15 / NO PACKAGE`；G38-02 已依使用者範圍決定
  `CLOSED / CANCELLED BY USER SCOPE DECISION / REMOVED / NO RELEASE`。既有 UserData、歷史紀錄、
  38.1.0～38.1.14 證據與不可變 Development 38.0 產物保留。G38-01 人工可存取性矩陣仍
  `MANUAL REVALIDATION BLOCKED`。G39-01 已完成為
  `MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE`；G39-02 因本機影像 preset 的 failing
  regression 啟動 Development 39.0.0，完整來源 Gate 已通過。使用者於 2026-07-23 已授權
  stage、本機 commit 與 Development 39.0.5 source freeze；同日也已明確授權 G39-08／39.0.6
  的 stage、本機 commit 與 source freeze，因此 G40-01 恢復為
  `BUILD WAITING / STAGED CANDIDATE + HEADLESS EVIDENCE REQUIRED`。push、build、EXE、
  Testing／Stable、簽署、發布與上傳仍未授權。
- 39.0.0 將既有、預設停用的 Media Convert 擴充為「本機格式工廠」第一工作包：增加
  PNG／JPEG／WebP 靜態影像轉檔與有界、去識別的 FFmpeg stderr 診斷；不自動安裝第三方
  執行檔、不上傳 CloudConvert，也不處理 DRM 或受保護光碟。既有影音、壓縮、修剪、佇列、
  取消、原子另存及 H.264 NVENC→CPU 回退保持相容。
- G39-02 完整 runner `1222 passed, 7 skipped`；最終 conversion security 組
  `21 passed, 1 skipped`。Ruff／文字污染 `357 / 552`、MOD `7 / 4`、網站 `12 / 33 / 49`、
  依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall、SAFE_MODE
  verify-only 與 diff check 均通過。
- G39-03／39.0.1 接續補足本機 FFmpeg build／format／encoder／filter／hwaccel 能力探測、
  轉檔磁碟 reserve preflight 與 atomic commit 前 ffprobe stream 驗證。未取得 capability 證據前
  UI 只使用 CPU；不新增或下載第三方 binary，也不將 CloudConvert 當 fallback。該工作包已完成
  來源驗證，沒有 stage、commit、freeze、build 或 package。
- G39-04／39.0.2 將 Gopeed／P2P policy 候選接成 localhost-only、explicit-action runtime MOD；
  feature 預設啟用與外部 bridge 設定分離，因此乾淨啟動不會連線或啟動程序。Token 只在記憶體，
  P2P 需合法用途與上傳確認。Speech to Text 的 `whisper-cli`／模型是選用執行相依；格式工廠新增
  WebM／AVI、AAC／Opus／WAV、BMP／TIFF。Automation、Speech to Text 維持新 profile 預設停用，
  其餘內建 MOD 新 profile 預設啟用；既有保存狀態不被覆寫。
  114 個非 UI 測試檔為 `1007 passed, 6 skipped`；最終安全邊界精準組 `43 passed`，品質、MOD、
  網站、依賴、版本、保留版本、Repository 外 compileall、SAFE_MODE verify-only 與 diff Gate 通過。
  25 個含 PySide／GUI 操作的測試檔依 UI 截圖優先政策未執行。
- G39-05／39.0.3 將 Gopeed create／resolve payload 收斂到官方 OpenAPI `Request` schema：
  移除未被接受的 `rawUrl`，保留 `url`／`labels` 與既有 localhost、token、容量、legal-use、
  non-force-delete Gate。精準非 UI 組 `108 passed, 1 skipped`；114 個非 UI 測試檔
  `1011 passed, 6 skipped`，品質與來源 Gate 通過。這不代表已連線外部 Gopeed 或建立套件。
- G39-06／39.0.4 依人工截圖將 Gopeed／P2P 頁面改成垂直可捲動的可信工作區，並以 layout
  minimum-size 契約避免設定 card 在 940×620 等有限高度下被壓扁重疊。這是純版面修正，沒有
  網路、task、設定或 UserData migration；114 個非 UI 測試檔為 `1012 passed, 6 skipped`，
  品質與來源 Gate 通過，實際修正版截圖仍須由使用者確認。
- G39-07／39.0.5 將 Stable 公開身分與 UI display 固定為獨立的 1.0.0／「正式版 1.0」，並新增 receipt-bound build-only／
  stage-built operator；receipt 綁定 source revision 與 wheel SHA-256，Stable stage 只有在
  Authenticode 為 `Valid` 時才可繼續。display RED `1 failed, 3 passed`；封裝／版本 GREEN
  `45 passed`，完整非 UI `1019 passed, 6 skipped`，其餘來源 Gate 均通過；尚未建立或發布 Stable 成品。
- G39-08／39.0.6 新增 `tools.prune_local_history` 與失敗優先回歸：默認 dry-run，要求
  保留至少兩個精確版本、其中至少一個是 audit／preflight 通過的 Stable，並對候選內
  UserData 或 link-like 內容 fail closed。精準 `9 passed`，116 個非 UI 測試檔
  `1029 passed, 6 skipped`；本輪尚未刪除任何版本、使用者資料或已公開附件。
- 38.1.16 以完整性釘選清冊逐檔建立 PyInstaller data inputs；純展開證據為
  `87 pinned / 87 expanded / 0 unexpected / 0 missing / 0 contaminating`。未執行 build，
  因此尚未宣稱新 EXE 內容已驗證。
- 2026-07-22 source-only `python -B main.py --verify-only` 已實測 exit 0 並精確輸出
  `MediaManager security mode: SAFE_MODE`；尚未證明 staged candidate／copied-folder／headless，
  也不構成任何 G40 發行操作授權。
- G39 `queue-roundtrip-v1` baseline 使用 1,001 tasks／4 workers、2 warmups／20 iterations；
  persist／restore／total p95 為 `219.921 / 240.687 / 482.475 ms`，tracemalloc peak 最大
  `20,146,560 bytes`、temp `912,806 bytes`、handle／thread delta 最大 `0`、殘留 download
  threads `0`、cleanup `true`，擴充 G39／queue regression `47 passed`；post-G39 完整 runner
  `1212 passed, 6 skipped`，quality audit Ruff `357`／文字 `551`。沒有可證 material bottleneck，
  未最佳化或升版。
- 38.1.15 驗證：完整 repository runner `1201 passed, 6 skipped`；quality audit、MOD 群組、
  網站矩陣、依賴鎖、版本文件、保留版本、Repository 外 compileall 與來源零註冊檢查通過。
  live provider smoke 因缺少 bundled Deno／FFmpeg 維持 `WAITING`，不宣稱外部網站成功。
- 以下 38.1.0～38.1.14 條目保留為歷史工程證據；其中舊的「目前」與 `ACTIVE` 字樣不再代表
  現行執行權，也不得用來重新接回已退役動畫瘋功能。

- 歷史 38.1.0～38.1.14 來源序列曾服務 G38-02；不可覆寫的封裝基線仍是 Development 38.0，
  34.0 source freeze 保持不變，35.0～37.0 source-only Exit Gate 已完成。38.0／G38-01 為
  `BASELINE FROZEN / PACKAGE BUILT / MANUAL REVALIDATION BLOCKED / SAFE_MODE`。38.1.0 是首次來源基線；
  38.1.1 是不支援／未知內嵌媒體能力 fail-closed 的第一個 material 修正；38.1.2 將 fallback
  改為緊湊提示並區分作品／單集相容性操作；38.1.3 同步四語資源的內建完整性釘選，修復
  動畫瘋主 MOD 初始化失敗；38.1.4 在本機分流 canonical 官方單集網址；38.1.5 在瀏覽器驗證
  後顯示獨立的官方目錄確認操作；38.1.6 收合 direct episode 上方的空作品區、於填表後重新
  定位單集列，並把官方目錄操作改為 system-browser allowlist handoff；38.1.7 將手動官方單集
  網址改為 `video_id`／URL 去重後附加，並在集數驗證 fallback 內提供相同的重試操作；38.1.8
  在搜尋回應只有 failure 時保留上一批有效狀態，並明示這些不是本次查詢結果；38.1.9 在作品
  切換後丟棄前一作品尚未完成的集數成功或失敗回應，避免錯集數污染播放與離線紀錄；38.1.10
  只接受原始 query 精確為 `sn=<ASCII digits>` 的動畫瘋作品／單集網址，拒絕額外、重複、大小寫或
  percent-encoded alias；38.1.11 要求 canonical `DiscoveryItemV1.video_id` 與 URL `sn` 一致，
  並在 busy／closing 時拒絕舊單集列 handoff，集中保護 provider、handoff、history 與 offline
  的寫入及讀取邊界；38.1.12 讓四語 `episode_opened` 顯示 exact URL，並由選取單集／
  history handoff 傳入實際送交 OS 的 canonical URL，同時明示頁面載入與播放未確認；38.1.13
  讓相容性彈窗依 exact route 選用作品／單集訊息，並把 OS 接受、拒絕或 opener 例外的結果同步顯示在彈窗內；38.1.14
  將 `dispatch_official_url` 的 transport positional `url` 改名為 `official_url`，避免與 message
  placeholder `url=` 發生 Python 綁定衝突。後續修正依序增加
  patch，純文件或證據更新不升版。這些已退役行為只作工程追溯，不構成現行功能或執行權；
  38.1.15 的移除不刪除使用者資料，也不將舊路徑轉接至 Direct HTTP。
  歷史 Development 產物只作回退與稽核用途，不覆寫既有內容。
- 歷史上 G38-02／38.1.14 曾是 `ACTIVE / IN_PROGRESS / SOURCE VALIDATED / LIVE WAITING / SAFE_MODE`
  來源工作；該判定現已由 38.1.15 的移除與 G39-01 ownership 取代。38.1.13 當時為
  `SOURCE VALIDATED / SUPERSEDED BY 38.1.14 / NO PACKAGE`。38.1.6 畫面證明介面
  篩選後「重試」可重新取得 20 筆官方作品；這是單一來源安全上限而非 stale 結果。集數驗證
  fallback 的手動網址則每次覆寫前一列，官方頁可見四集但工作區只保留一列。38.1.7 改用 lossless
  append＋`video_id`／URL dedupe，並在 fallback 內加入同一操作的 Retry。回退不碰使用者資料或
  既有 38.0 產物；截圖仍不能證明所有集數完成、播放或下載。
- 38.1.5 的兩項主 regression 在修正前為 `2 failed`，OS opener 失敗後遺失確認操作的恢復性
  regression 另為 `1 failed`；修正後擴充非 GUI 組為 `47 passed`。該輪 Ruff／文字污染
  `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  scoped compileall、CLI 版本與 diff check 均通過；沒有執行 GUI 自動互動或官方網路請求。
- 38.1.6 的兩項 direct episode 可見性 regression 先為 `2 failed`；目錄 media-routing、成功後
  state cleanup、armed exact-target 與重複同名操作各另為 `1 failed`。修正後六項為 `6 passed`，
  擴充非 GUI 組為 `105 passed`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、
  依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall、CLI 38.1.6 與 diff check 均通過；
  38.1.6 當輪的實際單集列位置與 OS handoff 仍為人工 `LIVE WAITING`。後續畫面只證明單一集數
  列可見及舊流程覆寫，不足以證明 OS handoff 或播放。
- 38.1.7 的新 merge helper 在實作前以 import／collection `1 error` 取得 RED；最小修正初次兩項
  為 `2 passed in 0.89s`，加入 wiring 後為 `3 passed in 0.97s`。review 再以 `2 failed`／`1 failed`
  鎖定 append failure 游標、malformed URL 與同系列分頁游標；最終精準組 `6 passed in 1.10s`，擴大
  非 UI 組 `111 passed in 1.85s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、
  依賴鎖 `10`、版本文件 `4`、保留版本 `5`、compileall、CLI 38.1.7、Version bytecode 零污染與
  diff check 均通過。
  修正不推算相鄰 SN、不讀 browser DOM／Cookie、不繞過驗證。Video.js `CODE:4` 與 `setVolume`
  TypeError 仍分類為本機 codec／站方次生錯誤；播放維持 system-browser 主路徑，未修成內嵌播放。
- 先前四張 38.1.7 post-fix 截圖確認可見版本、fallback Retry 入口與 `sn=49945` 單一集數列，分別
  記為 `version_visible=PASS`、`episode_retry_visible=PASS`、`manual_single_add=PASS`。畫面沒有
  同時呈現兩個不同官方單集或重貼結果，亦未顯示 Retry 觸發、OS handoff 或系統瀏覽器播放，故
  append、dedupe、Retry trigger、episode handoff 與播放仍為 `NOT_RUN / LIVE WAITING`。這組純證據
  更新當時沒有升版或建立候選包；完整雜湊保存在 canonical 38.x roadmap。
- 後續兩張 38.1.7 畫面顯示輸入關鍵字後進入瀏覽器驗證狀態且作品表清空；按鈕仍啟用，故不是
  click wiring 證據。來源追蹤確認 federation 把官方拒絕包成 structured failure，而工作區先提交
  空結果、清除選取與集數，之後才顯示失敗。38.1.8 新 reducer 在 production 尚不存在時先得到
  import／collection `1 error`；修正後精準非 UI 回歸 `2 passed`，擴大組
  `103 passed, 1 skipped`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、
  依賴鎖 `10`、版本文件 `4`、保留版本 `5`、compileall、CLI 38.1.8、Version bytecode 零污染與
  diff check 均通過。上一批資料只在「failure 且沒有有效 item」時保留，四語狀態明示它們不是
  本次查詢結果；首次搜尋受阻仍保持安全 fallback，未繞過驗證。人工 38.1.8 複驗仍為
  `LIVE WAITING`，未建立套件。
- 2026-07-22 的兩張 38.1.8 畫面可見三筆作品、`盜墓王` 的選取 context、兩筆集數列，以及
  codec／HLS／MSE 不支援時的緊湊系統瀏覽器 fallback；上述可見項目記為 `PASS`，但不能證明
  38.1.8 搜尋失敗保留舊狀態、OS handoff、系統瀏覽器播放或下載，故仍為 `LIVE WAITING`。
  同日複核動畫瘋官方服務條款後，沒有找到允許第三方保存影片的公開契約，條款反而禁止重製、
  廣告規避與串流破解；P2 因而維持 `BLOCKED / NO AUTHORIZED MEDIA SOURCE`。完整檔名、SHA-256
  與逐項判定只保存在 canonical 38.x roadmap；本輪不升版或建立套件。
- 38.1.9 的來源稽核重現集數 async race：A 的集數請求進行中切換到 B，舊 A 回應仍可在
  generation 未變時回填 B，並可能被後續播放歷史／離線索引配到錯作品。新增純 ownership guard，
  只有請求作品 URL 仍等於目前選取作品 URL 才套用成功或失敗回應。修正前兩項精準測試為
  `2 failed in 1.25s`；修正後為 `2 passed in 0.24s`。本輪 AniGamer 搜尋、集數、session、純
  workspace 與版本組合計 `85 passed in 1.77s`；Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外 pycache compileall、
  CLI 38.1.9 與 diff check 均通過。這不改 provider、網路、Cookie、codec 或系統瀏覽器 handoff；
  未啟動或控制 GUI，人工競態與播放仍為 `LIVE WAITING`。
- 38.1.10 修正 canonical query 邊界：舊 routing 接受 `sn` 外的額外／重複參數及大小寫、
  percent-encoded alias，使 provider 過濾、系統瀏覽器 handoff、history 與 offline 可能接收非精確
  官方網址。額外／重複 query regression 先為 `1 failed in 0.46s`；加入 alias 案例後再為
  `1 failed in 0.41s`；精確 route node 最小修正後為 `1 passed in 0.17s`。風險低、沒有資料遷移；
  Rollback 只回復 `core/site_routing.py` 條件、regressions、版本與文件。相關非 UI 組
  `205 passed, 1 skipped in 1.66s`，版本／文件組 `19 passed in 1.00s`；Ruff／文字污染
  `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  Repository 外 pycache compileall、CLI 38.1.10、Version bytecode 零污染與 diff check 均通過。
  不宣稱 UI、網路、OS handoff、播放或下載完成。
- 38.1.11 修正 canonical item identity 與 episode handoff 狀態邊界：舊 consumer 只驗 URL route，
  因而可能讓 `video_id` 與 URL `sn` 不一致的作品／單集進入 provider results、handoff、history 或
  offline；busy 期間雙擊舊單集列也缺少 fail-closed guard。共用純 validator 現要求作品 ID 為
  `ani-{sn}`、單集 ID 為 `ani-episode-{sn}`，並套用至作品／集數過濾、handoff、history 寫入及
  讀取與 offline 寫入及 metadata 讀取；episode handoff 在 busy／closing 時拒絕執行，current-series
  與 direct-episode context 保持原語意。初始 RED／GREEN 為 `4 failed in 1.80s`／
  `6 passed in 1.26s`；read-side RED／GREEN 為 `2 failed in 0.52s`／`3 passed in 0.98s`，最終相關
  非 GUI 組為 `129 passed, 1 skipped in 7.23s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall、CLI
  38.1.11、Version bytecode 零污染與 diff check 均通過。內建 provider 已使用 canonical ID，沒有
  migration／deletion 或既有檔案改寫；Rollback 為一起回復 validator、wiring、read-side checks、
  guards、regressions、版本與文件。人工 system-browser 播放仍為 `LIVE WAITING`，內嵌 codec
  不支援為預期限制；下載 P2 繼續 `BLOCKED / NO AUTHORIZED MEDIA SOURCE`。
- 兩張後續 38.1.11 截圖確認版本、`盜墓王 [1]`／`[2]`、選取第 2 集、單集 system-browser／
  compatibility 操作、緊湊 fail-closed 提示及有效 offline metadata index 可見；離線區同時明示
  尚未連結影片或字幕。這是 evidence-only 更新，不升版；內嵌播放仍為 `EXPECTED_UNSUPPORTED`，
  成功訊息也沒有 exact URL，所以無法把 OS handoff 與選取單集對應；system-browser handoff／頁面
  載入／播放與下載仍為 `NOT_RUN / LIVE WAITING`。舊截圖不是 38.1.12 live evidence。
- 38.1.12 只改單集 OS handoff 後的可觀察訊息：四語 `episode_opened` 加入 `{url}`，
  `open_selected_episode` 與 `open_history_entry` 傳入 exact canonical URL，文案明示 OS 已接受
  開啟請求但不代表官方頁載入或播放成功。修正前 `1 failed in 0.42s`，修正後
  `2 passed in 0.94s`，精準相關來源組 `9 passed in 1.04s`，擴大非 UI 回歸組
  `143 passed, 2 skipped in 1.60s`。最終 Gate 通過：Ruff／文字污染 `368 / 573`、MOD `8 / 4`、
  網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、版本文件測試
  `6 passed in 0.33s`、Repository 外 compileall、CLI 38.1.12、Version `.pyc` 零污染及 diff check。
  不碰 Cookie、串流或下載。
- 38.1.13 修正相容性彈窗的訊息與可見狀態。舊路徑對作品／單集 URL 都誤用
  `catalog_opened`，而 OS opener 拒絕或拋出 `RuntimeError` 時，失敗訊息只寫入被 modal dialog
  遮住的主狀態。新路徑依 exact route 使用 `series_opened`／`episode_opened`，單集保留 exact URL，
  並把成功／失敗訊息鏡像到 dialog-local status。精準 RED／GREEN 為
  `1 failed in 1.27s`／`1 passed in 0.71s`；相關精準組 `3 passed in 1.28s`、擴大非 GUI 組
  `115 passed, 1 skipped in 3.77s`、版本／文件組 `19 passed in 1.21s` 與來源 Gate 已通過。
  人工 38.1.13 截圖仍待，因此標記 `SOURCE VALIDATED / LIVE WAITING / SAFE_MODE`。不改 provider、network、Cookie、
  download 或 stream，未 stage、commit、freeze、build、package 或 push。
- 38.1.14 修正官方 handoff 的參數綁定錯誤。舊 helper 同時以 positional `url` 接收 transport
  target，又由 `url=` 提供 `episode_opened` message placeholder，會在 helper body 前拋出
  multiple-values `TypeError`；修正將前者改名為 `official_url` 並同步內部引用，保留後者。
  runtime 擴大組修正前 `1 failed, 162 passed, 1 skipped in 8.99s`，新增純回歸 RED
  `1 failed in 1.20s`，純 handoff GREEN `4 passed in 1.08s`。後續相關非 UI＋版本組在文件未同步時
  `134 passed, 1 skipped, 1 failed in 6.79s`，唯一失敗只因 README 與 docs README 仍為 38.1.13；
  同步後重跑為 `135 passed, 1 skipped in 1.87s`，其餘來源 Gate 亦通過，故為
  `SOURCE VALIDATED / LIVE WAITING / SAFE_MODE`。不改 provider、
  network、Cookie、download 或 stream，未 stage、commit、freeze、build、package 或 push。
- 38.1.14 的單張 evidence-only 截圖
  `codex-clipboard-5687e504-c306-4d3a-86b0-cc79cf9d8567.png`（SHA-256
  `5C52283BACEB1EECB5E55F92A1301D1E6240239D0F2BD6CDA1C1BEEB05DE5E42`）可見從 Repository
  啟動 `main.py`、標題「盜墓王 [1]」、緊湊 codec fallback、H.264／AAC／HLS／MSE 缺失提示、
  system-browser 建議操作與取消按鈕；終端可見 Video.js `CODE:4` 與 `setVolume` TypeError。CLI
  另核對當時來源 38.1.14。判定只包含 `embedded_fail_closed_presentation=PASS`、
  `episode_context_visible=PASS`、`system_browser_action_visible=PASS` 與
  `embedded_playback=EXPECTED_UNSUPPORTED`；按鈕點擊、OS handoff、
  官方頁載入、廣告與播放均未證明，仍為 `LIVE WAITING / SAFE_MODE`，不升版。
- BoringMan314/aniGamerPlus V24.9.10（`ce7a6d5`）的唯讀差異複核沒有找到新的 G38 material
  delta：通用安全能力已吸收，GPL 程式碼未複製；遠端服務與本機 MP4 `faststart` 跨 Gate
  延後；Cookie／Cloudflare／代理／串流分段／金鑰／解密與廣告規避排除。此掃描為
  `ABSORBED / NO RELEASE`，該輪維持 38.1.14 且沒有建立下一修正號；後續 38.1.15 是獨立的移除差異。相關非 UI／版本／文件組為
  `173 passed, 1 skipped`，其餘來源 Gate 通過。
- 開發與測試成品仍維持 `SAFE_MODE`；目前沒有可宣告的 Stable 正式版。
- G37 source-only Exit Gate 的最新完整 pytest 已透過固定 Repository 根目錄及隔離使用者暫存的
  安全入口完成：`1278 passed, 7 skipped`；未廣域收集 `AppData`，測試 basetemp 位於
  Repository 外。G38 無頭 UI／四語精準基線另計 `58 passed, 0 skipped`；焦點指示與
  安全 badge 讀屏名稱兩項 P1 修正後相關 UI 組 `12 passed`，post-fix 完整
  Repository `1279 passed, 7 skipped`。AniGamer targeted suite 為 `60 passed, 1 skipped`，加入
  canonical 單集 URL 回歸後的完整 Repository 為 `1281 passed, 7 skipped`；最新 G38 Shared DoD 的
  Ruff／文字污染 `366 / 571`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、
  保留版本 `5`、compileall、Version `.pyc` 零污染與 diff check 均通過；人工矩陣仍阻擋。
- G36-01 只對 `DiscoveryItemV1`、history、recovery 與 provider failure 的六個列名 result DTO
  接受最多 8 個有界 JSON extra；保留版本欄位、遺失必填、超深／超大內容仍拒絕，writer 不保留 extras。
  capability token claims、Download／Provider capability、plugin manifest 與 UI descriptor 的 unknown field
  仍由 strict regression 拒絕。
- G36-01 最終 Shared DoD：完整 Repository `1255 passed, 7 skipped`；Ruff／文字污染
  `363 / 566`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  scoped compileall、Version `.pyc` 零污染與 `git diff --check` 均通過。
- G37-01 已以 `EVIDENCE READY / NO CLAIM / SOURCE ONLY / SAFE_MODE` 完成；strict evidence v1、provider
  exit metadata、UTF-8 有界 redaction、queue restore、原子 self-check 匯出與 WER runbook 已完成。
  最終 G37 targeted `112 passed`，完整 Repository `1278 passed, 7 skipped`；Shared DoD 的
  Ruff／文字污染 `365 / 570`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、
  保留版本 `5`、scoped compileall、Version `.pyc` 零污染與 diff check 均通過。沒有重現 native crash，
  provider 間歇 exit 1 的 root cause 仍未知；不宣稱已修復。
- G35-02A 新增唯讀、immutable 且有界的外部 MOD dependency graph snapshot、candidate
  overlay 與間接 cycle validator。
- G35-02B 新增共用且有界的跨程序 lifecycle lock、compare-and-set `ENABLE`／`DISABLE`
  journal、鎖內狀態重讀及 fail-closed TrustStore／publisher reconciliation。
- G35-02C 完成序列化 supervisor handle ownership、handshake cleanup failure 的 exact-handle
  接管、短期 capability 即時撤銷、transitive dependency readiness／dependent-safe disable，
  以及 graph 異常時 journal-first 的 runtime containment。
- G35-02D 完成 bounded candidate transaction、fail-closed lifecycle path、dependency-first
  startup／transaction recovery、dependent-first toggle recovery 與補償失敗後的下次啟動收斂；
  最終相關 15 檔 targeted suite `175 passed`，原發現者重審未發現未解 P0／P1。
- G35-02E 已同步 operator／release／roadmap 文件；Ruff／文字污染 `360 / 563`、MOD `8 / 4`、
  網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、compileall 與 diff 均通過。
- 34.0 已完成本機 source freeze；35.0～37.0 Exit Gate 證據本身不構成操作授權。使用者已於
  2026-07-19 明確授權將目前 35.0～38.0 核准變更 stage、本機 commit、固定為 Development 38.0
  source freeze，並建立一次 SAFE_MODE 未簽署 Development 38.0 包；push、Testing／Stable、
  簽署與發布仍未授權。
- Development 38.0 已從 freeze revision
  `6534e3f5ebcc3e3c459a34a335e2b176b2cd1107` 建立於 `Version/Development/38.0`；
  runtime policy 6/6、116 筆 checksum 與 copied-folder `38.0 → 32.1 → 38.0` 均通過，
  `rollback=true / source_unchanged=true / process_tree_safe=true`。EXE 為 `NotSigned`；這項
  封裝證據不替代 G38 人工 UI 矩陣，也沒有保存 G40 所需的精確 SAFE_MODE stdout。
- `tools.audit_version_docs` 會離線比對 `core/version.py`、`pyproject.toml` 與目前文件；
  版本分歧時以非零狀態結束。
- 目前內建 MOD 與網站父群組數量以 `tools.audit_mod_groups --json` 及
  `tools.site_quality_audit` 的本輪輸出為準；文件不手動保存可能過期的計數。
- Self Check 可匯入最近一次手動 provider smoke schema 2 JSON，但不啟動下載器或外部媒體工具。
- 動畫瘋父 MOD、目錄／搜尋、集數導覽、相容性播放器與離線索引入口已於 38.1.15 退役。
  舊設定與既有 UserData 保留但不重新註冊；動畫瘋網址不得轉送到 Direct HTTP 或其他通用 adapter。
- `media-convert` 在全新 profile 預設啟用，工作區名稱為「格式工廠」；除 39.0.0 的
  PNG／JPEG／WebP 外，39.0.2 再加入 WebM／AVI、AAC／Opus／WAV、BMP／TIFF，並沿用既有影音、
  壓縮、修剪、佇列、取消、atomic no-overwrite 與 H.264 NVENC→CPU fallback。
  文件、受保護光碟、CloudConvert 自動 fallback 與第三方安裝程式不在目前 scope。
- `media-ad-trim` 是 `media-convert` 下全新 profile 預設啟用的本機子 MOD，只依手動時間區間
  重新編碼並另存新檔；可預覽第一切點，不覆寫原檔，也不接受網站網址。
- GitHub 的 [`test-v1.1.0`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.1.0)
  是不可覆寫的既有測試附件。開發版 11.1 使用獨立版本資料夾及 Pre-release，
  不能讓文件假稱舊附件已包含後續功能。

## 目前有效文件

- [專案首頁與執行方式](../README.md)
- [Development 34.0～40.0 唯一版本更新計畫與優先度](roadmap-development-34.0-40.0.md)
- [Development 34.0 目前執行證據與阻擋](roadmap-development-34.0.md)
- [Development 35.0～36.0 更新紀錄](release-35.0-36.0.md)
- [Development 37.0～38.0 更新紀錄](release-37.0-38.0.md)
- [Development 39.0～40.0 更新紀錄](release-39.0-40.0.md)
- [原生崩潰去識別證據 Runbook](native-crash-evidence-runbook.md)
- [Development 35→34 設定回復 Runbook](settings-pre35-rollback.md)
- [網站父 MOD、子 MOD 與四語言契約](site-mod-group-format.md)
- [動畫瘋整合退役說明（歷史）](ani-gamer-feasibility.md)
- [第三方 MOD 開發流程](mod-developer-guide.md)
- [Search／Download Adapter SDK](adapter-sdk.md)
- [下載工作契約](downloads-v1.md)
- [MOD 套件格式](mod-package-v1.md)
- [執行環境與依賴檢查](dependency-health.md)
- [MEGA MOD 能力邊界](mega-feasibility.md)
- [Direct HTTP MOD 能力邊界](direct-http-boundary.md)
- [Facebook／Instagram 能力邊界](meta-social-feasibility.md)
- [X／Twitter 能力邊界](x-twitter-feasibility.md)
- [Threads 能力邊界](threads-feasibility.md)
- [同類軟體參考與取捨](comparable-software-options.md)
- [GitHub 自動檢查與合併](github-auto-merge.md)
- [正式簽章流程](release-signing.md)
- [版本資料夾與三軌發布政策](version-layout.md)
- [開發版 33.0～34.0 更新紀錄（34.0 尚未封裝）](release-33.0-34.0.md)
- [開發版 12.x 實際更新紀錄](release-12.0-13.0.md)
- [開發版 13.x 實際更新紀錄](release-13.0-14.0.md)
- [開發版 14.x 實際更新紀錄](release-14.0-15.0.md)
- [開發版 15.x 實際更新紀錄](release-15.0-16.0.md)
- [開發版 16.x 實際更新紀錄（規劃中）](release-16.0-17.0.md)
- [測試版 1.1 發布附件紀錄](release-testing-1.1.md)
- [正式版 1.0 候選狀態](release-stable-1.0-candidate.md)

## 歷史發行紀錄

下列文件是唯讀歷史，用來追查當時變更與雜湊。它們不是目前安裝指引，也不應改寫
成新版本內容：

- [開發版 3.0～4.0](release-3.0-4.0.md)
- [開發版 4.0～5.0](release-4.0-5.0.md)
- [開發版 5.0～6.0](release-5.0-6.0.md)
- [開發版 6.0～7.0](release-6.0-7.0.md)
- [開發版 7.0～8.0](release-7.0-8.0.md)
- [開發版 8.0～9.0](release-8.0-9.0.md)
- [開發版 9.0～10.0](release-9.0-10.0.md)
- [開發版 10.0～11.0](release-10.0-11.0.md)
- [開發版 11.0～12.0](release-11.0-12.0.md)

`release-1.x.md`、`release-2.x.md` 及舊 roadmap 同樣屬於歷史資料。GitHub Releases
上已公開的 EXE、`SHA256SUMS.txt`、`release-info.json` 與其對應版本文件不得刪除或
覆寫；日常介面與 README 只連到本入口，避免舊內容被誤認為最新版本。

## 後續候選方案

下列 roadmap 是尚未全部完成的候選設計，不是目前功能承諾：

- [多網站下載與彈幕](multisite-danmaku-roadmap.md)
- [YouTube 自動切割](youtube-auto-split-roadmap.md)
- [YouTube 搜尋、歷史、替代與相似內容](youtube-discovery-roadmap.md)
- [選用 YouTube 影片預覽](youtube-player-roadmap.md)
- [正式版 1.1 第三方 MOD 目標](roadmap-stable-1.1.md)
- [開發版 15.0 網站工作流可靠性計畫](roadmap-development-15.0.md)
- [開發版 16.0 網域搜尋、MOD 適配與下載可靠性計畫](roadmap-development-16.0.md)
- [開發版 17.0 可重現發行、分站可靠性與第三方 MOD 計畫](roadmap-development-17.0.md)
- [開發版 28.0～29.0 更新紀錄](release-28.0-29.0.md)
- [開發版 29.0 可重現性、Self Check 與 MOD 維護計畫](roadmap-development-29.0.md)

## 文件更新規則

1. 功能、數量、版本與測試結果只寫入目前文件及所屬大版本區間。
2. 尚未重新封裝的來源變更必須標示「尚未封裝」，不可回填到既有發布附件紀錄。
3. 開發次版本附加在同一大版本區間文件，不新增零散 release 文件。
4. Stable 文件只記錄候選評估；未取得簽署身分、完整驗證與使用者確認前，不宣告正式版。
5. 文件一律使用 UTF-8，提交前檢查合併標記、工具殘留、無效連結與版本事實衝突。
