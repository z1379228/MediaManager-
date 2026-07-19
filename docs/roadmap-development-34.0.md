# Development 34.0 版本計畫

狀態：`SOURCE-FROZEN / DONE`。來源身分為 34.0.0，尚未封裝。
34.0～40.0 的跨版本排序與唯一後續 ownership 以
[34.0～40.0 主計畫](roadmap-development-34.0-40.0.md) 為準；本文件只保存已完成的
34.0 工作與其既有證據。
`ANI-34-01` 動畫瘋影片讀取診斷已取得合法官方單集正片實播證據，`ANI-34-03`
本機播放器最小修正亦已完成。原始 90 個路徑與後續 16 項 source-freeze 安全修正／證據
形成 freeze 前 106 路徑快照；使用者於 2026-07-19 明確授權 stage、本機 commit 與
source freeze，兩個 intent 已依序固定。此授權不包含 build、EXE、push、Testing／Stable、
簽署或發布；正式 runtime、外部網站與手動 UI 驗證仍受 SAFE_MODE 門檻限制。

## P0：穩定性與安全

- **增量更新**：下載佇列、搜尋結果、縮圖與 MOD 狀態只在資料變更時刷新，避免重複重繪與背景工作。
- **取消與恢復**：取消、停止、重試與重啟後狀態保持明確，不自動恢復未授權工作，不覆寫既有輸出。
- **輸入界線**：URL、路徑、封面與匯入檔案維持大小、格式、路徑與原子寫入限制。
- **稽核證據**：維持 Ruff、回歸測試、網站／MOD／版本／文字污染稽核；UserData 不納入版本雜湊。

## P1：UI 與工作區

- 940×620 最小視窗下維持深色主題、鍵盤操作、可存取名稱與清楚的父／子 MOD 狀態。
- 大量 YouTube／Bilibili／動畫瘋結果使用虛擬化或分頁式更新，縮圖與預覽受數量及大小上限保護。
- 下載工作區統一等待、處理中、完成、失敗、取消與暫停狀態，顯示可操作的下一步。
- 依賴與安全阻擋在同一 UI 元件呈現，不以白色原生視窗或誤導性啟用按鈕取代。

## P2：條件式候選

- 低資源搜尋歷史、診斷匯出與失效項目替代搜尋僅在使用者觸發時執行。
- 新網站、Gopeed、P2P／Torrent 與通用解析器維持候選，不進入核心或預設啟用。
- 參考軟體的併發、佇列與快取功能僅先記錄差異，不自動放寬限制。

## 每輪純規劃驗收

1. 唯讀掃描工作樹、文件、參考清單、版本與 MOD 狀態。
2. 建立或補充下一個未完成版本計畫；若沒有新差異，記錄原因與下一輪候選。
3. 只記錄唯讀稽核結果，不修改程式碼、使用者資料或版本產物。
4. 外部網站限制、正式簽章缺失與歷史 UserData 項目維持為阻擋項。

34.0 不建立 Stable 或 Testing 產物；發布需另行取得使用者明確決定。

## 本輪建立的唯一執行計畫（34.0-P0，2026-07-18）

- **Goal**：在不改變既有資料契約與安全邊界的前提下，降低低資源環境與大量工作項目造成的重複 UI 刷新，並維持佇列、搜尋、縮圖與 MOD 狀態的一致性。
- **Scope**：先涵蓋下載佇列快照、搜尋結果、縮圖索引與 MOD 狀態的變更判定；不新增網站、背景服務、資料庫 Schema、外部 MOD capability 或新的發行產物。
- **Priority**：P0；先於 34.0 的 P1 UI 虛擬化與 P2 候選功能，因為它是穩定性與可驗證性的共同基礎。
- **Dependencies**：既有 queue snapshot／狀態模型、render 或 refresh helper、MOD status snapshot、目前非 UI 回歸測試與 SAFE_MODE 規則。
- **Approach**：先建立唯讀 baseline 與最小回歸案例，證明資料簽章未變更時不重繪、變更時只更新必要區塊；只有測試揭露缺口時才做最小程式修正，並保持背景工作預設關閉、可取消與可恢復。
- **Compatibility**：維持 Development 32.1 既有行為、manifest/provider contract、輸出路徑與使用者資料；不修改已發布歷史版本，不放寬 DRM、登入、Cookie、Cloudflare、廣告或付費限制。
- **Risk**：低。主要風險是簽章判定遺漏變更、狀態轉換顯示延遲或測試對 UI 時序過度耦合；不涉及 Schema、格式或破壞性 API 變更。
- **Rollback**：只回復本計畫新增的測試／程式差異與本節文件；不刪除 UserData、不調整 ACL、不覆寫歷史雜湊，必要時維持既有完整刷新路徑。
- **Validation**：執行 Ruff、相關非 UI 測試、compileall、MOD／網站／依賴／版本／文字污染稽核與 `git diff --check`；缺少正式簽章、Deno、FFmpeg 或外部網站驗證時維持 SAFE_MODE 並記錄阻擋。
- **Status**：P0 驗收完成；增量刷新、取消／恢復、輸入界線與稽核證據均有測試或稽核支持，未新增核心程式修改。下一步轉入 P1 可存取性盤點。不得建立 Stable／Testing／EXE 或推送 Git。

### 34.0-P0 基線驗證（2026-07-18）

- **範圍**：`table_refresh`、下載工作區增量簽章、下載通知／佇列與內建 MOD snapshot 的非 UI 回歸測試。
- **結果**：`48 passed`；使用新的使用者本機暫存目錄並授權後執行，未再觸發 AppData 廣域收集或 WinError 5。
- **阻擋記錄**：第一次嘗試因既有 `%LOCALAPPDATA%\MediaManager` 暫存目錄 ACL 造成 `PermissionError`；未修改專案 ACL 或使用者資料，改用隔離目錄完成驗證。
- **判定**：目前已有可重用的 `visible_rows_signature`、`download_render_signature` 與快照測試，尚無足夠證據要求立即改動核心程式；下一輪優先盤點搜尋與各網站工作區是否缺少同等變更判定。
- **稽核**：Ruff、compileall、MOD group、網站品質、依賴鎖定、版本與文字污染稽核均通過；
  當時的暫存 ACL 觀察已由固定收集根與 invocation-owned LocalAppData runner 隔離，
  最新 `git status`／品質入口不再輸出 ACL 警告。

### 34.0-P0 搜尋／網站工作區盤點（2026-07-18）

- **結果**：搜尋面板與 YouTube／Bilibili／動畫瘋工作區目前以搜尋完成事件、分頁追加與明確操作觸發更新，未發現會在無資料變更時持續背景重繪的計時器路徑。
- **判定**：現有程式已有 generation／結果比對與分頁合併保護；本輪沒有足夠證據進行低風險核心修改，避免為 UI 時序引入不必要回歸。
- **下一方向**：若後續出現重複 `show_results` 或大量結果重繪的可重現證據，再針對單一工作區補 `render_signature` 回歸測試與最小修正；否則維持目前實作並轉入 P1 可存取性盤點。
- **驗證**：YouTube／Bilibili／動畫瘋工作區回歸測試 `17 passed`；本輪 Ruff、MOD／網站／依賴／版本／文字污染稽核與 `git diff --check` 均通過。

### 34.0-P0 取消／恢復與輸入界線盤點（2026-07-18）

- **結果**：下載佇列與工作區已有取消、暫停、恢復、重啟後不自動執行、重試與輸出路徑界線的回歸覆蓋；目前未發現未授權自動恢復或覆寫輸出的缺口。
- **驗證**：`tests/test_download_queue.py` 與 `tests/test_download_task_detail.py` 共 `40 passed`。
- **判定**：34.0-P0 的取消／恢復與輸入界線已有明確測試證據；本輪不修改核心程式，避免重複實作。P0 僅剩持續稽核證據與必要的真實缺口回歸測試。

## 34.0-P1 可存取性與最小視窗基線（2026-07-18）

- **範圍**：940×620 最小視窗、深色主題對比、鍵盤／快捷鍵、主要控制項 accessible name，以及父／子 MOD 樹狀狀態。
- **結果**：相關 UI 回歸測試 `31 passed`；未發現缺少最小尺寸、深色表面、主要控制項名稱或 MOD 樹可存取名稱的明確缺口。
- **判定**：目前實作已符合 34.0-P1 的基線條件；暫不修改 UI，下一輪可盤點大量結果的分頁／虛擬化候選，仍以測試證據為前提。

### 34.0-P1 大量結果與縮圖資源盤點（2026-07-18）

- **結果**：搜尋分頁已綁定來源游標並限制合併結果數；YouTube／Bilibili 工作區支援追加載入，縮圖載入具取消、世代檢查與大小／網域限制。
- **驗證**：搜尋分頁、搜尋縮圖、縮圖載入與 YouTube／Bilibili 工作區回歸測試共 `24 passed`。
- **判定**：已有分頁與資源上限的低風險基礎，未發現必須立即引入虛擬化元件的證據；下一輪轉向下載工作區狀態一致性與依賴阻擋呈現。

### 34.0-P1 下載狀態與依賴阻擋呈現盤點（2026-07-18）

- **結果**：下載工作區已有等待、下載中、等待重試、暫停、完成、失敗與取消的明確文字／按鈕狀態；主視窗環境按鈕與依賴對話框共用快照與阻擋原因，不以啟用按鈕掩蓋缺少依賴。
- **驗證**：下載細節／通知、依賴快照、自我檢查與主視窗呈現回歸測試共 `29 passed`。
- **判定**：未發現狀態遺漏或依賴阻擋呈現缺口；34.0-P1 目前僅剩跨 UI 手動可用性檢查，受限於本輪不建立發行產物與 SAFE_MODE，暫不修改程式。

### 34.0-P1 自動化驗收與手動阻擋（2026-07-18）

- **自動化結果**：UI 尺寸／可存取性、搜尋分頁／縮圖、下載狀態與依賴快照合併回歸測試 `73 passed`。
- **手動阻擋**：940×620 真實視窗操作、讀屏與跨 UI 焦點巡覽需在可啟動的發行環境驗證；目前缺少正式簽章且維持 SAFE_MODE，不建立 Stable／Testing／EXE，因此不宣稱手動驗收完成。
- **判定**：P1 自動化基線完成，剩餘項目為受控環境手動驗證；下一輪僅在有安全且實質的新證據時處理，否則維持阻擋記錄。

### 阻擋修正紀錄（2026-07-18）

- **已修正**：簽章乾跑不再使用受 ACL 影響的 Repository 暫存位置；改用隔離的使用者本機暫存目錄後，2 個測試檔案乾跑結果為 `PASS`，且成功偵測竄改、未保留私鑰。
- **仍然阻擋**：正式 preflight 仍回報 production Ed25519 身分未配置、Deno／FFmpeg 發行檔缺失及 Authenticode `NotSigned`。這些是正式發行權限／外部工具條件，不能由本機自動偽造或繞過；SAFE_MODE 與手動 UI 驗證限制維持不變。

### 打包暫存 ACL 針對性修正（2026-07-18）

- **Root Cause**：`tools.build_version` 固定把 Python／pip 的 `TEMP`、`TMP`、build tracker 與 cache 放在 Repository `.work`；本機 ACL 會使 Python 建立的暫存子目錄出現 `WinError 5`。
- **修正**：新增 `--temp-root`，將每次建置隔離至唯一的 `mediamanager-build-<attempt-id>` 子目錄；只有本輪成功建立的子目錄才可清理，碰撞時 fail closed 並保留既有內容，`--keep-work` 仍保留診斷現場。
- **相容性／範圍**：未指定參數時維持既有 `.work` 行為；PyInstaller work、wheel 與 staging 位置不變。沒有修改 ACL、建立 EXE 或建立 Stable／Testing 版本。
- **驗證**：`tests/test_build_version.py` 當次共 `14 passed`；相關與全域 Ruff、compileall、CLI `--help`、`git diff --check` 均通過。當時完整 pytest 由安全入口重跑為 `915 passed, 4 skipped`；最新完整證據見「完整修復驗證紀錄」。
- **剩餘阻擋**：乾淨 Git 來源、production Ed25519、Deno／FFmpeg 正式發行檔與 Authenticode 簽章仍是正式打包前置條件；維持 SAFE_MODE。

### pytest 收集與暫存邊界修正（2026-07-18）

- **Root Cause**：從使用者主目錄啟動未限定 target 的 pytest 會把該目錄當作收集根並掃描 `AppData`；另外 pytest `--basetemp` 不會隔離測試內直接使用的 Python／原生暫存檔，受 ACL 限制時仍可能觸發 `WinError 5`。
- **修正**：新增 `tools.run_tests`，固定以 Repository 為 `cwd`／`rootdir` 並只接受 `tests` 下的 target；每輪建立唯一 attempt，分離 `runtime` 與 pytest basetemp，設定 `TEMP`／`TMP`／`TMPDIR`，移除可注入額外 target 的 `PYTEST_ADDOPTS`，並以有界重試清理本輪擁有的目錄。
- **安全／回復**：不修改 ACL、不清除其他 attempt 或使用者資料；無法安全建立或清理時回傳失敗，`--keep-temp` 僅保留本輪診斷目錄。此入口限制收集與暫存範圍，不是測試程式碼沙箱。
- **驗證**：入口回歸測試當次 `10 passed, 1 skipped`（Windows 目錄 symlink 權限不可用時略過）；當時完整 suite `915 passed, 4 skipped`，未重現 AppData 廣域收集、`WinError 5` 或先前 self-check assertion failure。
- **最新稽核**：Ruff、compileall 與 `git diff --check` 通過；MOD group `8 groups / 4 locales`、網站 `13 sites / 42 features / 56 workflows`、依賴鎖定 `10`、版本 `5`、文字污染 `557 files` 均為 PASS。受控入口及最新 `git status` 不再列出 ACL 警告；沒有刪除使用者資料或廣域放寬 ACL。
- **剩餘阻擋**：production Ed25519、Deno／FFmpeg 發行檔、Authenticode 簽章、外部網站與真實 UI 驗證仍未具備；維持 SAFE_MODE，未建立 EXE／Stable／Testing。

## 唯一問題修正序列（2026-07-18）

- **Goal**：以單一、可驗證的順序收斂目前版本事實、計畫基線、驗證警告與發行阻擋；自動循環不得為同一問題建立新的版本計畫。
- **Scope**：包含目前入口文件、31.0～43.0 計畫狀態、工作樹變更清冊、品質稽核遍歷邊界、copied-folder／回退證據與發行前置條件；不包含新功能、刪除舊暫存、修改 ACL、下載外部工具、建立 EXE／Testing／Stable、提交或推送 Git。
- **Priority**：先修正會使後續判定失真的 P0 文件與計畫基線，再處理可重現的品質警告；需要外部權限、檔案或使用者範圍決定的項目保持 `NEEDS_CONFIRMATION`／`BLOCKED`。
- **Dependencies**：`core/version.py` 與 `pyproject.toml` 為目前版本來源；Git 工作樹與 31.0～43.0 roadmap 提供變更來源；正式發行另依賴 production Ed25519、Authenticode、Deno／FFmpeg 正式檔及手動／外部驗證。
- **Approach**：每輪只執行序列中最前面的 `READY` 項目；完成並留下驗證證據後才前進。`NEEDS_CONFIRMATION` 不自動改變 Git 或外部狀態，`BLOCKED` 不以 placeholder、自簽或降低條件繞過。
- **Compatibility**：VUP-34-01 將目前來源身分同步為 34.0.0；既有 provider／manifest
  契約與歷史版本內容不變。設定 JSON 以加法 schema 1 安全演進，legacy exact bytes
  先備份、future／invalid／corrupt 保持唯讀。第三方 manifest 若把核心上限固定在 32.1.0 或
  33.x，會依既有 fail-closed 相容性規則拒絕載入，不會靜默放寬。
- **Risk**：主要風險是把使用者既有修改誤納入發行、以忽略規則隱藏真實污染、刪除不可讀暫存資料，或把缺少正式簽章誤報為完成；所有項目均以 fail closed 與最小變更處理。
- **Rollback**：文件與稽核入口採獨立小變更，可逐項回復；不使用 reset、history rewrite、ACL 變更或廣域清理，因此不需要資料回復。
- **Validation**：每項使用其下方驗收條件；序列完成前持續執行安全 pytest 入口、Ruff、compileall、MOD／網站／依賴／版本／文字污染稽核及 `git diff --check`。

### 執行規則

1. 同一時間只允許一個 `READY` 項目進入 `IN_PROGRESS`；freeze 前 106 路徑快照已由
   VUP-34-02 的本機 commits 固定。G35-01 已因資料風險納入 34.0 freeze 並結案；
   35.0～37.0 source-only Exit Gate 已依序完成；G38-01 的無頭自動基線已重驗，兩個 P1 也已紅→綠修正；
   現為唯一 `ACTIVE / MANUAL REVALIDATION BLOCKED / SAFE_MODE` 項目，尚無另一個 `IN_PROGRESS` 工作。
   34.0 不建立 EXE，
   已驗證的 runtime 不需重新下載。
2. 不新增 34.0～40.0 主計畫以外的活動 roadmap，也不重複規劃已由 33.0／34.0
   驗收的搜尋歷史、佇列、資源上限或 pytest 暫存修正。
3. `NEEDS_CONFIRMATION` 必須取得使用者對變更範圍或外部下載的明確決定；`BLOCKED` 只記錄最低成本驗證，不進入自動執行。
4. 任一驗證失敗時停在原項目，記錄 Root Cause 與回復方式，不跳到後續功能或發行工作。

### FIX-34-01｜P0｜DONE｜目前版本與文件事實收斂

- **Problem／Evidence**：`core/version.py` 與 `pyproject.toml` 均為 `32.1.0`，但 `README.md` 同時宣稱 32.1 與 29.3，`docs/README.md` 仍宣稱 29.3；43.0 也仍把已解除的 pytest `WinError 5` 列為阻擋。
- **Fix boundary**：只修正目前入口與計畫狀態，不改歷史 release；加入離線一致性稽核，使 core、pyproject、README 與文件入口再次分歧時回傳非零。
- **Acceptance（當時 32.1 基線）**：入口文件只有一個目前來源版本且為 32.1；43.0 不再宣稱完整 `tmp_path` 回歸受阻；一致性稽核、相關測試、版本與文字污染稽核通過。
- **Evidence**：`tools.audit_version_docs` 離線比對 core、pyproject 與兩份入口文件，實際結果 `valid=true / checked=4`；UTF-8、重複宣告與版本分歧回歸均通過。

### FIX-34-02｜P0｜DONE｜計畫與變更來源基線

- **Problem／Evidence**：掃描時有 `52 modified/staged`、`25 untracked`；35.0～42.0 全為未追蹤的「規劃中」，42.0 的 31.0～42.0 彙整尚無結果，43.0 已記部分實作但狀態落後現況。
- **Fix boundary**：建立唯讀變更清冊，將每個變更對應至既有需求、版本或使用者修改；彙整 31.0～43.0 為完成／候選／重複／阻擋，不刪除 roadmap、不 reset、不 stage、不 commit。
- **Acceptance**：只有一份下一步可執行計畫；已完成與重複項不再回到待辦；所有工作樹項目有來源或明確標為未知，未知項不進發行範圍。
- **Evidence（當時基線）**：`docs/change-inventory-development-32.1.md` 最初將 57 modified、0 staged、33 untracked 共 90 個路徑分類，並把 31.0～43.0 收斂為完成、重複、候選或阻擋；清冊最終保存 freeze 前 106 路徑快照，兩個 intent 已分開提交，未 reset 或刪除檔案。

### FIX-34-03｜P1｜DONE｜品質稽核遍歷邊界

- **Problem／Evidence**：Ruff、文字掃描與 `git status` 雖成功，仍因舊 Repository 暫存目錄不可讀而輸出 `Permission denied`；安全 pytest 入口已阻止新增同類目錄，但舊資料未授權刪除。
- **Fix boundary**：建立受控品質入口，只遍歷明確來源／文件／測試路徑並拒絕 symlink／越界；不得以廣泛 `tmp*` 忽略、刪除資料、take ownership 或修改 ACL 隱藏問題。
- **Acceptance**：Ruff 與文字污染稽核無 ACL 警告且仍能抓到測試夾具中的真實污染；舊暫存內容、其他 attempt 與使用者資料保持不變。
- **Evidence**：`tools.quality_audit` 使用 fail-closed 白名單、symlink／junction／越界拒絕與 24K Ruff 分批；當次 `350` 個 Python、`549` 個文字檔均 PASS，最新為 `355 / 557`。CI 已接入版本文件稽核；PowerShell wrapper 以 trusted absolute script 與 isolated Python 執行，不從待掃 checkout import 程式。

### FIX-34-04｜P1｜DONE / SOURCE-FROZEN｜乾淨來源與 copied-folder／回退證據

- **Problem／Evidence**：大量既有修改使 clean-source preflight 無法通過；40.0 要求的 copied-folder 啟動與目前版／上一版安全回退尚無實際完成證據，wheel 建置不等於這兩項驗收。
- **Decision**：使用者已確認原始 90 個路徑進入 review scope；後續安全審查與回歸使
  freeze 前清冊增至 106 個路徑，並於 2026-07-19 明確允許 stage、本機 commit 與
  source freeze。未授權 reset、丟棄、build、push 或發行。
- **Acceptance**：核准範圍必須由 clean、可追蹤 commit 固定，source fingerprint 只作附加證據且兩者指向同一 revision；copied-folder headless smoke 與回退測試證明 UserData 不污染版本目錄且失敗可回復；clean-source preflight 對同一來源通過。
- **Completed evidence**：新增 fail-closed copied-folder 工具，拒絕 temp-root 重疊、跨發行軌與反向版本，使用 Windows Job Object 限制程序樹，並將同一份 owned portable `UserData` 原子搬移為 32.1→32.0→32.1。實際 9 個 `--version`／`--portable --verify-only`／`--headless --portable` 命令全為 exit 0，`rollback=true`、`source_unchanged=true`，本輪 attempt 已清除。
- **Completed delivery**：15 份 historical／superseded 文件先以獨立 intent 保存；其餘
  91 個目前有效路徑由最終 34.0 freeze commit 固定。最終 commit hash 與 source fingerprint
  在 clean commit 後由交付回報，不寫回同一 commit 造成自我參照；未 reset 或丟棄修改。
- **Related fix**：`release_candidate` 已嚴格支援舊 evidence/release-info `2/2` 與目前 `3/3`，並拒絕混用或未知 schema；這只解除工具相容性缺口，不代表候選已就緒。

### FIX-34-05｜P1｜TRANSFERRED TO G40-01｜Deno／FFmpeg 正式 runtime

- **Problem／Evidence**：目前 `Version/Development/32.1/tools` 缺少正式 Deno、FFmpeg／ffprobe、授權與說明檔，因此 preflight 仍失敗；省略 runtime 不能作為正式完成證據。
- **Available material**：本機 `.tool-cache` 已有政策固定的 Deno 2.9.2 與 FFmpeg／ffprobe 8.1.2，四個 FFmpeg 檔案、Deno 執行檔及 `third_party/deno/LICENSE.md` 均通過既有 SHA-256／存在性檢查。阻擋是尚未以核准來源重建新產物，不是需要重新下載。
- **Required decision**：本項不再由 34.0 啟動；G40-01 需使用者確認採用這份既有
  快取與授權來源，並另行明確允許建立新的 Development EXE。不得覆寫 32.1、不得把
  `--without-portable-runtime` 降級建置誤報為完成。
- **Acceptance**：新產物的 `tools/` 含六個固定工具／授權檔，`release-info.json` 的 `portable_tools` 非空，離線 runtime 稽核與對應 preflight 項目全部通過。

### FIX-34-06｜P0｜TRANSFERRED TO G40-02 / BLOCKED｜production Ed25519／Authenticode

- **Blocker**：需要外部正式簽署身分與憑證；禁止自簽、偽造、降低條件或將私鑰放入 Repository。
- **Acceptance**：一次性簽署演練成功且私鑰未進產物，Authenticode 為 `Valid`，manifest／signature 驗證與正式 preflight 全部通過。達成前維持 SAFE_MODE 且不得建立 Stable。

### FIX-34-07｜P1｜G37 EVIDENCE READY / TRANSFERRED TO G38 / MANUAL BLOCKED｜外部網站與真實 UI 驗證

- **Blocker**：G37 去識別 provider／原生證據邊界已完成；動畫瘋單一官方單集 live smoke 已完成，
  940×620 真實視窗、鍵盤焦點、讀屏、高對比與四語仍需受控人工環境；不得繞過登入、Cookie、
  Cloudflare、DRM、廣告或付費限制。
- **Acceptance**：只以官方公開且合法可驗證的路徑完成 smoke；人工 UI 結果記錄環境、步驟與失敗證據。未完成前不宣稱 34.0 手動驗收或正式發布就緒。

### ANI-34-01｜P0｜DONE｜動畫瘋影片讀取與安全回退

- **Trigger**：使用者回報動畫瘋仍無法讀取影片；此新證據推翻「內部可安全修正均已完成」的舊判定，優先於版本身分同步與打包。
- **Goal**：在不接觸 Cookie、登入狀態或媒體串流的前提下，消除「頁面載入即代表影片可播放」的錯誤狀態，並提供可回復、使用者明示觸發且不誤報成功的官方播放入口。成功條件是本機診斷與 handoff 行為可離線驗證；實際影片播放只能由合法官方頁人工證據確認。
- **Priority**：P0；使用者無法進入官方播放流程，且舊狀態會提供錯誤成功訊號，因此先於版本打包與一般 UI 改善。
- **Dependencies**：既有 AniGamer URL allowlist、`QDesktopServices`、Qt WebEngine capability probe、四語系 MOD UI、built-in integrity pin、LOCALAPPDATA 隔離測試入口，以及使用者自行控制的合法瀏覽器工作階段。外部完成門檻另依賴官方網站當時的登入、廣告、地區與 DRM 條件。
- **Verified facts**：本機 URL、MOD wiring、公開目錄／集數與離線資料契約未失敗。舊實作卻在 WebEngine `loadFinished(true)` 後直接顯示官方頁已載入；該事件只能證明 HTML 文件載入，不能證明影片 codec、MSE、音訊或播放狀態。PySide6／Qt 6.11.1 的離線 ApplicationWorld probe 已實測回傳 `html5Video=true`、`mse=true`，但 H.264、AAC、HLS 與 MSE H.264/AAC 路徑均為 `false`；Qt WebEngine／Qt Multimedia 模組存在不等於此內嵌引擎可播放動畫瘋常用媒體。獨立的官方公開頁 HTTP 唯讀探測曾回傳 403，未嘗試繞過；其後合法瀏覽器 live smoke 已證明官方單集 HTML、播放器外框與正片皆可在官方流程後正常載入及播放。
- **Legal live smoke／第一階段（2026-07-18）**：以 Codex in-app browser 正常開啟 `https://ani.gamer.com.tw/animeVideo.php?sn=49944`，頁面標題為「幼女戰記 2 [2] 線上看 - 巴哈姆特動畫瘋」，沒有先遇到 WinError 5、Cloudflare 或 HTTP 403。官方播放器隨即顯示「未滿12歲之兒童不宜觀賞。」及「同意／不同意」控制；依安全界線未代替使用者完成年齡確認、未點擊廣告、未讀取 Cookie／登入狀態／媒體 URL，也未嘗試繞過地區、DRM 或網站流程。分頁已保留並交接給使用者，因此此階段只確認 `official-page-loaded / playback-unverified`；後續證據見下方 Playback proof。
- **Live continuation／第二階段（2026-07-18）**：使用者自行完成官方年齡選擇後，年齡提示消失，官方播放器顯示正常廣告倒數（由 14 秒降至 4 秒），且可見 video elements 沒有媒體錯誤碼。倒數結束後頁面顯示官方「點此跳過廣告」操作；自動化依既定限制未啟用該控制，也未點擊廣告。因此此階段已排除年齡提示未生效，但當時正片仍未驗證，分類為 `official-ad-flow / user-action-required`；後續已由 Playback proof 收斂為實播成功。
- **Playback proof（2026-07-18）**：使用者自行完成官方廣告後續流程後，播放器呈現唯一「播放」控制；正片媒體總長約 `1420.044` 秒、`readyState=4`、無 media error。使用該官方播放控制短暫實播，`currentTime` 由 `6.521` 秒前進至 `10.128` 秒，且觀察點為 `paused=false / error=null`，因此具有實際正片播放證據。未讀取 Cookie、登入狀態、媒體 URL，未操作廣告或繞過網站限制。
- **Root Cause**：已確認兩層原因：程式把「頁面載入成功」誤當成「媒體可播放」，且這台電腦的 Qt WebEngine 缺少探測所需 H.264/AAC/HLS 播放路徑。前者已修正；後者不可用下載 codec、匯入 Cookie 或繞過網站限制處理。本次合法 live smoke 證明系統瀏覽器可在使用者自行完成官方年齡與廣告流程後播放該單集，因此此案例沒有新的登入、地區或 DRM 阻擋證據；其他影片或環境仍不得由單一 smoke 推廣保證。
- **Scope**：區分三條路徑：公開搜尋／集數資料、官方頁面播放入口、使用者本機媒體播放。只修正診斷、狀態、能力探測、官方系統瀏覽器 fallback 與相符回歸測試；不擷取／解析串流，不匯入 Cookie／登入，不偽裝 UA，不繞過 Cloudflare、廣告、付費、地區或 DRM。
- **Approach**：已加入失敗回歸與三態純分類；`loadFinished(true)` 改為 `document-loaded/playback-unverified`，另處理 load failure、renderer failure、capability unsupported／unknown。ApplicationWorld probe 以固定 JSON 字串回傳並由 Python bounded parser 驗證，不讀站台 DOM、Cookie、登入或媒體 URL。作品、集數、瀏覽器驗證 fallback 與開啟紀錄均以 exact-host 官方 HTTPS URL 的系統瀏覽器 handoff 作主要、明示且僅由使用者觸發的動作；內嵌 WebEngine 保留為次要的相容性預覽，載入／probe／renderer／WebEngine unavailable 都不會自動啟動外部程式。`openUrl(true)` 只記為 OS 接受 dispatch，明確不宣稱頁面載入或影片播放成功；OS 拒絕時保留可選取的官方 URL，且不寫入新的開啟紀錄。本機 QMediaPlayer 的 Qt Multimedia 能力與錯誤分類已拆分為 `ANI-34-03`；兩者共用安全邊界，但不以本機檔案播放結果取代官方網站播放驗收。
- **Alternative assessment／local static evidence**：本機唯讀盤點顯示 HTTPS 預設處理器為 `MSEdgeHTM`，已安裝 Edge `150.0.4078.65`、Chrome `150.0.7871.128` 與 WebView2 Runtime `150.0.4078.65`；Repository UI 依賴仍只有 PySide6，沒有 WebView2 host／SDK wiring。這些只證明執行檔、版本與預設關聯存在，不證明動畫瘋頁面、登入、廣告、地區條件、codec 或 DRM 可播放。34.0 不新增 Edge `--app`／profile 參數，不建立 WebView2 UDF／helper，也不以 Qt runtime flags、外部 CDM 或 codec 下載補洞；這些是本輪評估後暫緩的非最小方案，只有日後具備明確 in-app 需求、獨立依賴／更新／renderer／UDF 威脅模型與合法 live 證據時才重新評估。
- **Breaking Change**：無。provider protocol、manifest schema、官方 URL、離線封存格式與 UserData 均不變；「觀看紀錄」只調整成較準確的「開啟紀錄」顯示名稱，既有 JSON 內容可直接沿用。
- **Migration**：無 Schema 或資料 migration；不複製、轉換或刪除既有 Cookie、瀏覽器 profile、歷史版本與使用者媒體。
- **Risk**：系統瀏覽器接受 dispatch 仍可能因網站驗證、未登入、廣告流程、地區、DRM 或瀏覽器 codec 而無法播放；另一風險是 UI 再次把 handoff、HTML 載入或 capability 靜態存在誤報為播放成功。以明確未驗證文案、零自動外部啟動、exact-host allowlist 與回歸測試限制風險。
- **Compatibility／Rollback**：不改 provider protocol、manifest schema、UserData 或官方 URL；失敗時可只回復本項新增的狀態分類、UI wiring、四語字串與測試，不影響 32.1 歷史產物。
- **Validation**：擴充後的 AniGamer／網站契約／built-in MOD／品質回歸為 `203 passed, 2 skipped`，系統瀏覽器 allowlist、dispatch accepted／rejected、開啟紀錄外開、WebEngine unavailable 零外部副作用與主要／次要按鈕均由離線 mock 驗證；JSON probe 與真實 QtWebEngine ApplicationWorld 離線 smoke 以 `unsupported` 正確分類；最新完整 suite 為 `1092 passed, 7 skipped`。Ruff 與 compileall 已通過；第一次直接使用工作區 `.work` basetemp 只在 pytest session cleanup 遇到既有 `WinError 5`，未修改使用者資料，改用既有 LOCALAPPDATA 隔離測試入口後通過。合法瀏覽器 live smoke 已確認使用者自行完成官方年齡與廣告流程後，正片 `currentTime` 由 `6.521` 秒前進至 `10.128` 秒，觀察點為 `paused=false / readyState=4 / error=null`；登入／廣告／地區／DRM 流程仍不得由自動化代替或繞過，整體版本維持 SAFE_MODE。
- **Acceptance**：本項已達成：`loadFinished(true)` 不再宣稱影片可播放；unsupported／unknown／renderer failure 可離線重現並提供官方瀏覽器下一步；測試不需要真實 Cookie 或串流；合法官方流程也已取得單一單集正片實播證據。此證據只驗收本次案例，不保證其他影片、帳號、地區或環境，亦不解除版本簽署與其他 provider／UI 的 SAFE_MODE 門檻。

#### ANI-34-01 唯一修正序列

| 順序 | 狀態 | 動作與完成條件 |
|---:|---|---|
| 1 | `DONE` | 修正頁面載入、capability 與實際播放的狀態語意；只有可證明的事件能顯示對應結果。 |
| 2 | `DONE` | 將 exact-host 官方 HTTPS 系統瀏覽器 handoff 設為主要入口；拒絕 credentials、非官方 host 與非 HTTPS URL。 |
| 3 | `DONE` | 覆蓋 dispatch true／false、開啟紀錄、WebEngine unavailable 零外部副作用、四語系完整性與最小寬度主要／次要動作。 |
| 4 | `DONE` | 使用者自行完成官方年齡與廣告流程後，以頁面唯一「播放」控制驗證正片；`currentTime` 由 `6.521` 秒前進至 `10.128` 秒，且為 `paused=false / readyState=4 / error=null`。未讀取 Cookie、Token、登入狀態或媒體 URL，亦未操作廣告或繞過網站限制。 |
| 5 | `NOT_TRIGGERED` | 本次單集已播放成功，未觸發失敗分流。若其他案例日後失敗，只收集瀏覽器名稱／版本、時間、官方頁可見錯誤分類與是否通過官方驗證；依證據決定是產品 regression、網站條件或瀏覽器環境，不在無證據時新增 codec／WebView2 工作。 |

第 4 項已完成且沒有新的產品 regression，`ANI-34-01` 已改為 `DONE`。整體版本仍因簽署、runtime、其他 provider／UI 與 scope gate 維持 `SAFE_MODE`，不重複建立動畫瘋修正計畫。

### ANI-34-02｜P0｜MONITORING / NOT_REPRODUCED｜Windows 原生 breakpoint 例外

- **Trigger**：使用者於 2026-07-18 13:53 提供 `python.exe`「unknown software exception (0x80000003)」截圖；沒有 Python traceback、模組名稱或 dump。
- **Verified facts**：截圖後未發現存活的 `python.exe`；現存 `QtWebEngineProcess.exe` 的 parent 是另一個 `Games` 程序。Windows Application log 沒有同時段的 python crash 1000/1001，`CrashDumps` 也沒有本次新 dump。使用 `SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX)` 與 faulthandler 受控執行動畫瘋 UI 啟閉、QtWebEngine 建立／probe／關閉及完整 suite，全部 exit 0，例外未重現。
- **Current diagnosis**：`0x80000003` 是原生 breakpoint，不足以從截圖歸因到 Python、QtCore、WebEngine、Multimedia 或其他 DLL。因沒有同時段 WER／dump，不將它寫成已確認產品 Root Cause，也不以關閉驗證或吞掉例外處理。
- **Minimum-cost next validation**：若再次出現，先記錄精確時間與當時操作，按「確定」讓程序結束後依 [去識別採證 Runbook](native-crash-evidence-runbook.md) 人工抄錄 Event 1000/1001 的 allowlisted module basename／offset／exit code；不要匯出 Event XML／EVTX，也不要按「取消」進入未配置的除錯器。dump 不自動搜尋、解析、保存或上傳；只有使用者明確選定本次新 dump 時才在本機計算並抄錄 SHA-256。取得可重現模組證據後才建立對應 regression／修正。

### ANI-34-03｜P1｜DONE｜本機播放器 Qt Multimedia 能力與穩定錯誤分類

- **Root Cause**：離線封存的副檔名白名單只定義可安全匯入的使用者本機媒體，不代表目前作業系統與 Qt Multimedia backend 一定具備對應 container／codec。舊播放器也把非同步 `play()` 要求直接顯示成正在播放，且 backend 原始錯誤沒有穩定、可測試的 UI 分類。
- **Fix**：依 `QMediaFormat` 的 Decode file format／audio codec 回報，將完整既有媒體白名單分為 supported／unsupported／unknown。只有 codec-specific 的 FLAC／MP3／Opus 可在 container 與 codec 同時存在時預判 supported；MP4、Matroska、AVI、MOV、Ogg、Wave 與 WebM 等可變 codec container 即使 runtime 支援也保守維持 unknown。選檔器分開顯示 supported 與 unknown；已知 unsupported 在播放前阻擋，unknown 允許嘗試但明確標示未驗證。只有 `PlayingState` 才顯示播放成功；錯誤事件另比對目前 error／source，並映射為固定代碼，不輸出 backend `errorString`。
- **Privacy／UI**：狀態 `QLabel` 固定為 PlainText；使用者檔名只取有界 basename，移除 C0／C1 與 bidi formatting controls。上一個／下一個圖示按鈕已有可存取名稱，不將絕對路徑放入狀態或錯誤。
- **Compatibility／Rollback**：`ALLOWED_LOCAL_MEDIA_SUFFIXES`、封存／匯入規則、provider protocol、manifest schema 與 UserData 均不變；沒有新增網路、codec 下載或外部依賴。可只回復能力 helper、播放器 wiring、四語字串／完整性 hash 與相符測試。
- **Validation**：三集合完整覆蓋且互斥、混合佇列採最嚴格狀態、可變 codec container、Ogg／Opus、WebM 封存與播放邊界、Qt adapter failure、非同步播放狀態、穩定錯誤代碼、純文字與 bidi 檔名均有回歸。此機器實測為 supported `.flac/.mp3`、unknown `.avi/.m4a/.m4v/.mkv/.mov/.mp4/.mpeg/.mpg/.ogg/.ts/.wav`、unsupported `.opus/.webm`；這是本機 backend 能力，不是跨平台保證。相關回歸 `75 passed, 1 skipped`，最新完整 suite `1092 passed, 7 skipped`。
- **Acceptance**：不再把「允許封存」、container 可解碼或非同步 `play()` 呼叫誤報為特定檔案已可播放；已知不支援、未知 codec 相容性、準備中、已進入 PlayingState 與實際播放錯誤可區分，且不洩漏原始 backend 詳情。

## 完整修復驗證紀錄（2026-07-18）

- **Regression**：最新完整 suite `1092 passed, 7 skipped`；略過項維持其既有平台／symlink 條件，不偽裝為通過。擴充後的動畫瘋／網站契約／built-in MOD／品質回歸另為 `203 passed, 2 skipped`，built-in integrity 包含在該次驗證。
- **Transient observation**：較早一次完整 run 曾有 3 個非動畫瘋 provider 子程序無結果退出（其餘
  `1002 passed, 5 skipped`），沒有 stderr、WER 1000／1001 或原生對話框。當時移除的固定 1 秒上限
  實際只限制 EOF 後 stderr drain，不能證明 result handoff root cause。G37 後續壓力取證曾重現
  `stdout_eof / exit_code=1 / reader_complete=true`，但 direct subprocess 與相同 Job Object 各 300 輪
  均通過，故維持 `TRANSIENT / REPRODUCED INTERMITTENT / ROOT CAUSE UNKNOWN`；只保留有界 metadata，
  不加入自動 retry 或宣稱已修復。
- **Quality**：Ruff `355 files / 1 batch`、文字污染 `557 files`、compileall 與 `git diff --check` 通過；`git diff --check` 只有 LF→CRLF 提示，沒有 whitespace error。
- **獨立 P0／P1 re-review**：修正後的唯讀 freeze review 未在設定回復鎖或 feature MOD
  不可逆狀態範圍發現剩餘 P0／P1。rollback 與 `SettingsService` 共用鎖，並在鎖內
  重讀、驗證、備份及原子替換；feature registry 以鎖內最新狀態、UUID 暫存檔及保守的
  `irreversible_side_effect_unknown` 語意避免誤報完整回復。剩餘限制為非合作式外部直接
  改檔、獨立程序崩潰／斷電 fault-injection 尚未驗證，以及 provider 失敗後只能將取消數量
  標為未知；均不降低 SAFE_MODE，設定回復仍要求先關閉應用程式。
- **本輪狀態收斂驗證（2026-07-18）**：動畫瘋、built-in integrity、release preflight、版本文件、品質稽核與安全測試入口的針對性回歸歷史快照為 `90 passed, 3 skipped`；最新 Ruff `355 files / 1 batch`、文字污染 `557 files`、compileall、MOD group `8 / 4`、網站 `13 / 42 / 56`、依賴鎖定 `10`、版本文件 `checked=4`、保留版本 `5` 與 `git diff --check` 均通過。測試改用既有 LOCALAPPDATA 安全入口後未再廣域收集 AppData 或觸發 `WinError 5`；只清理本輪擁有且已核對絕對路徑的 attempt。
- **Domain audits**：MOD group `8 groups / 4 locales`；網站 `13 sites / 42 features / 56 workflows`；依賴鎖定 `10`；版本文件 `checked=4`；保留版本 `5` 均 PASS，32.0／32.1 各驗證 110 個 checksum。
- **Copied-folder／rollback**：32.1→32.0→32.1 的 3 phases／9 commands 全部通過；共用 owned `UserData` sentinel 經每階段驗證，retained source 未變，本輪 attempt 清理通過。
- **Formal preflight（歷史基線）**：先前以當時 32.1 來源檢查歷史成品為 `ready=false / checked=108 / exit 1`，阻擋為 production Ed25519 未配置、缺 Deno、FFmpeg／ffprobe 與對應 license／README、以及 Authenticode `NotSigned`。2026-07-18 以目前未封版工作樹再次交叉檢查不可變的 `Version/Development/32.1` 時，除上述阻擋外另回報四個 AniGamer 語系雜湊不符；唯讀比對確認目前來源檔與 32.1 歷史副本的 SHA-256 確實不同，而 `release_preflight` 會載入目前工作樹的 built-in pin。這不是可藉由覆寫歷史 32.1 消除的錯誤；新 34.0 候選必須在 scope／版本凍結後重建，再以同一候選來源執行正式 preflight。未下載 placeholder、未自簽、未降低條件。
- **Final decision**：`ANI-34-01` 的可安全本機修正與合法官方單集正片實播驗收均已完成；`ANI-34-02` 原生 breakpoint 未重現且缺模組證據，保持監測；`ANI-34-03` 的本機播放器分類與狀態修正已完成。單一動畫瘋案例不解除其他 provider／UI、正式 runtime 與簽署 gate。VUP-34-02 已完成 source freeze；FIX-34-05～07 已移交 G37／G38／G40。維持 `SAFE_MODE`，未建立 EXE／Testing／Stable、未推送 Git。

### G35-01 提前納入 G34 source-freeze review（2026-07-18）

- **Root Cause**：舊設定 reader 對 corrupt／future／錯誤型別缺少可寫狀態，整份 `save()`
  也可能以 stale 記憶體覆寫另一 writer 的不相關欄位；升級安裝若重跑首次 MOD 精靈，
  可能停用既有 MOD 或取消不可復原的工作。
- **Fix**：加入 schema 1 typed state、64 KiB 上限、深層 JSON 防護、unknown key 保留、
  跨程序鎖與鎖內 reread-and-merge `patch()`；legacy 首次寫入先保存 exact SHA-256
  backup，future／invalid／corrupt 只讀。既有／來源不明安裝只保存首次設定完成旗標，
  不切換 MOD 或取消工作。
- **Rollback**：`tools.settings_rollback` 預設 dry-run；apply 要求 current SHA、共用跨程序鎖、
  verified legacy backup、不可覆寫的 current owned backup 與原子替換。操作見
  [35→34 設定回復 Runbook](settings-pre35-rollback.md)。
- **Scope decision**：此資料安全工作已納入 34.0 freeze，不代表 G35-02 外部 MOD dependency
  graph 已完成；本次 Git 授權也不包含 build 或發行。

## Development 34.0 source-freeze 執行計畫（2026-07-18）

狀態：`SOURCE-FROZEN / VUP-34-02 DONE`。本節保存已完成的 34.0 證據；跨版唯一排序
見 34.0～40.0 主計畫。目前來源身分為 34.0.0，已建立本機 source-freeze commits，
但未打包、簽署、建立 Testing／Stable 或推送 Git。

### 計畫定義

- **Goal**：將已驗證的 32.1 後續修改收斂為可追蹤、可回復的 Development 34.0
  clean source revision；本版本不建立產物。
- **Scope**：包含 freeze 前 106 個核准路徑的最終 review、34.0 版本身分、clean Git
  revision 與 source fingerprint。排除 build、copied-folder 新候選、人工 UI、簽署、
  新網站、新核心服務、P2 候選、ACL 清理、UserData 刪除及歷史版本覆寫。
- **Priority**：P0；已完成最終 review、獨立 commit／freeze 授權與乾淨 revision。
- **Dependencies**：使用者已於 2026-07-19 明確授權最終 Git 交付範圍及本機 commit／source freeze。
- **Approach**：已完成最終 diff review、Shared DoD、兩個 intent commits，並在提交後確認
  clean revision 與 source fingerprint 指向同一 HEAD。
- **Compatibility**：保留 `Version/Development/32.1` 及其雜湊不變；Development、Testing、Stable 編號維持獨立。34.0 不改 provider runtime protocol 1.0、manifest schema v2 或既有公開 API；設定 JSON 以加法 schema 1 演進並保留 unknown keys。
- **Breaking Change**：無公開 API／provider Breaking Change；future／invalid／corrupt 設定由模糊 fallback 改為可診斷 read-only，屬安全收緊。
- **Migration**：legacy 設定首次寫入前保存 exact-hash backup，再原子寫入 schema 1；future schema 不寫回。這不是 DB Schema migration，回退依設定 Runbook，禁止以 retained version 或真實使用者資料試跑未驗證遷移。
- **Risk**：主要風險為把未核准修改混入 commit、以 fingerprint 取代 clean Git，或把
  review scope 誤報為 release 授權。
- **Rollback**：只以獨立 revert 回復核准 commit；不 reset、rewrite history、刪除 UserData
  或覆寫 32.1／其他歷史產物。
- **Validation**：34.0 Exit Gate 只要求 Ruff／文字污染、完整 Repository tests、完整 Python
  compileall、MOD／網站離線契約／依賴／版本文件／保留版本稽核與 `git diff --check`。
  staged runtime、copied-folder、人工 UI 與簽署 operator 已移交 34.0～40.0 主計畫的
  G37～G40，不再阻擋 34.0 source-freeze Exit Gate。

### 版本策略取捨

- **採用：Development 34.0 source freeze**。Canonical inventory 已將 33.0 的 P0／P1
  標為完成；34.0 目前只負責收斂 clean source，後續經證實的缺口依 34.0～40.0
  主計畫逐版啟動，不要求每個里程碑都建立產物。
- **不採用：32.2 或重開 33.0**。這會讓已收斂 roadmap 分叉，增加版本、文件與產物身分錯配風險。
- **不自動擴張到 40.0 以後**。35.0～40.0 已由唯一主計畫重新排序；既有
  41.0～43.0 文件只保留歷史，不構成目前活動計畫，也不支持新增平行版本。
- Testing／Stable 不由 Development 34.0 直接改名或升格；若使用者選擇其他通道，必須使用各自編號與 metadata 重新 build／validate。

### 執行序列

| 順序 | Priority | 狀態 | 工作與完成條件 |
|---|---|---|---|
| ANI-34-01 | P0 | `DONE` | 頁面載入／播放狀態、WebEngine capability／renderer 診斷與 exact-host 系統瀏覽器 handoff 已完成；合法 live smoke 在使用者自行完成官方年齡與廣告流程後取得正片時間前進、`paused=false / readyState=4 / error=null` 的單集播放證據。此證據不推廣為其他影片或環境保證。 |
| ANI-34-02 | P0 | `MONITORING / NOT_REPRODUCED` | 保存 0x80000003 截圖證據；受控 UI、WebEngine lifecycle 與完整 suite 未重現。若再次發生，只依去識別 runbook 抄錄同時段 WER module basename／offset／exit code，選用 dump 只記本機 SHA-256，不保存內容或路徑；再做最小 regression／修正。 |
| ANI-34-03 | P1 | `DONE` | 本機媒體封存白名單保持不變；Qt Multimedia runtime 能力已分為 supported／unsupported／unknown，只有 PlayingState 才確認播放，錯誤改為穩定且不洩漏本機細節的代碼。 |
| VUP-34-00 | P0 | `DONE` | 使用者於 2026-07-18 回覆「繼續更新」，核准清冊中的 90 個工作樹路徑進入 34.0 review scope；這只允許 review 與 VUP-34-01 的低風險同步，不授權全部 commit、release、reset 或丟棄修改。 |
| VUP-34-01 | P0 | `DONE` | 已同步 `core/version.py`、`pyproject.toml`、README 與 33.0～34.0 release 文件；staged runtime policy audit 以精確六檔集合、五項固定 hash、canonical Deno license、bounded／duplicate-safe metadata 及 reparse fail-closed 回歸驗證。最新完整 suite `1092 passed, 7 skipped`，品質與版本稽核通過。 |
| VUP-34-02 | P0 | `DONE / SOURCE-FROZEN` | 核准內容以兩個本機 commits 固定；最終 clean worktree、有效 HEAD 與 source fingerprint 指向同一 revision。Fingerprint 只作附加證據，不取代 clean Git。 |
| VUP-34-03 | P1 | `TRANSFERRED TO G40-01 / BUILD AUTH REQUIRED` | 34.0 不再建立 EXE；固定 runtime、unsigned Development candidate 與 build 授權由 40.0 唯一管理，不得覆寫 32.1。 |
| VUP-34-04 | P1 | `BASELINE DONE / REMAINDER TO G40-01` | 既有 copied-folder／rollback 基線保留；新候選的 runtime audit 與 verify-only／headless 精確 `MediaManager security mode: SAFE_MODE` 證據由 G40-01 唯一管理。 |
| VUP-34-05 | P1 | `G37 EVIDENCE READY / G38 MANUAL BLOCKED` | G37-01 已完成去識別 provider／原生證據；940×620、鍵盤、四語與讀屏人工驗證由 G38-01 管理。CLI exit 0 不得代替人工證據。 |
| VUP-34-06 | P0 | `TRANSFERRED TO G40-02 / WAITING` | 通道決定、發行完整性與條件式 Stable operator 由 G40-02 唯一管理；未選 Stable 時不得進入 production signing。 |

### Stable 條件式分支（歷史要求；execution ownership 已移交 40.0）

下表保留當時的安全要求供追溯，但不得再由 34.0 直接啟動。只有使用者明確選擇
Stable 後，才可依 [34.0～40.0 主計畫](roadmap-development-34.0-40.0.md) 的 G40-02
進入條件式 Stable operator；它們不是 Development 34.0 的完成條件。

| 順序 | Priority | 狀態 | 工作與完成條件 |
|---|---|---|---|
| VUP-34-S1 | P0 | `HISTORICAL / TRANSFERRED TO G40-02` | 先實作並以離線／模擬簽署測試 sign-before-stage operator：build work EXE → 檢查 Authenticode → stage／產生最終 release-info、SBOM、SHA256SUMS → Ed25519；憑證缺少或狀態不是 `Valid` 時必須在 stage 前 fail closed。此項只驗證流程與失敗邊界，不宣稱已取得正式 `Valid` 簽章；現有 build+stage 單一步驟不得直接用於 Stable。 |
| VUP-34-S2 | P0 | `HISTORICAL / TRANSFERRED TO G40-02` | 讓 signing CLI／preflight 使用 channel/version-aware Stable signed set，明確涵蓋 wheel、`release-info.json` 與 `SHA256SUMS.txt`；未知、遺漏或額外檔案一律 fail closed。 |
| VUP-34-S3 | P0 | `HISTORICAL / TRANSFERRED TO G40-02` | 取得 production Ed25519 公開身分／外部私鑰及 Authenticode 憑證；私鑰不進 Repository／Log，簽署後不得再修改產物。只有完成此項後才可執行真實 Authenticode `Valid` 門檻。 |
| VUP-34-S4 | P0 | `HISTORICAL / TRANSFERRED TO G40-02` | 以 S3 的正式身分對新的獨立 Stable 版本執行 S1 operator、全部稽核與正式 preflight，要求 Authenticode `Valid` 且 `ready=true / exit 0`；完成後仍需使用者最終發布確認。 |

### 驗證命令與成功門檻

```powershell
.\.venv\Scripts\python.exe -m tools.quality_audit
.\.venv\Scripts\python.exe -m tools.run_tests
.\.venv\Scripts\python.exe -m compileall -q `
  main.py desktop.py core contracts mod plugin_host tools trusted_ui tests
.\.venv\Scripts\python.exe -m tools.audit_mod_groups --json
.\.venv\Scripts\python.exe -m tools.site_quality_audit
.\.venv\Scripts\python.exe -m tools.dependency_lock_audit
.\.venv\Scripts\python.exe -m tools.audit_version_docs
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
git diff --check
```

VUP-34-01 已新增離線 staged runtime policy audit；其隔離回歸為
`19 passed, 1 skipped`。該稽核驗證六個 staging 檔集合精確、Deno／FFmpeg 五個固定
binary／notice hash 與政策一致、Deno license 來源可追蹤，並拒絕 reparse point、
過大或重複 key metadata。只有未來 34.0 成品 hash 通過後，才可在 owned
copied-folder 執行 runtime `--version`；目前未建立或宣稱成品通過。

建立完整且經授權的 unsigned Development 34.0 後，才可執行：

```powershell
.\.venv\Scripts\python.exe -m tools.audit_staged_runtime `
  --root Version\Development\34.0
.\.venv\Scripts\python.exe -m tools.copied_folder_smoke `
  --current Version\Development\34.0 `
  --previous Version\Development\32.1 `
  --retained-root Version
.\.venv\Scripts\python.exe -m tools.release_preflight `
  --root Version\Development\34.0 --json
```

Development 成功門檻為所有適用自動稽核 exit 0、完整 tests 無 failure/error、
runtime policy audit 通過、copied-folder 與 rollback 為 true、來源與 retained 版本
雜湊不變，且外部／人工驗證缺口如實記錄。copied-folder 的結構化報告必須保存並
斷言 verify-only 與 headless 的 stdout 均精確包含
`MediaManager security mode: SAFE_MODE`；僅有 exit 0 不構成 SAFE_MODE 證據。

Development preflight 可保持 `ready=false`，但 JSON `errors` 僅可包含目前實作的兩個
production signing blocker：`compiled release key id or Ed25519 public key is invalid` 與
`Authenticode signature is not valid: NotSigned`。兩者以外的任何錯誤（包括 runtime
缺檔、unsafe required path、required release file 缺失、built-in MOD hash mismatch、
integrity／signed-file coverage 錯誤或 Authenticode 無法檢查）都阻擋 Development
驗收；不得把任意 preflight failure 當成允許的 unsigned 狀態，也不得宣稱正式發行就緒。

若啟動 Stable 分支，則必須額外完成 VUP-34-S1～S4、對獨立 Stable 編號重建產物，
並取得正式 preflight `ready=true / exit 0`。Development／Testing 產物不得直接改名、
搬移或升格為 Stable。
