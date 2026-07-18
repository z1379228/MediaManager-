# Development 34.0～40.0 唯一版本更新計畫

狀態：`CANONICAL / 34.0 SOURCE-FROZEN / 35.0 ACTIVE / G35-02 READY / 36.0～40.0 WAITING`
規劃基線：2026-07-18；Development 34.0／核心相容版本 34.0.0 已完成來源凍結，尚未封裝。

本文件重新設計 34.0～40.0 的唯一執行順序，取代 35.0～40.0 單版草案的執行權；
單版文件只保留歷史背景。建立本計畫不等於授權修改版本號、stage、commit、build、建立
EXE／Testing／Stable、簽署、推送 Git 或覆寫任何歷史版本。缺少正式簽署身分、正式 runtime、
外部網站或人工 UI 證據時，必須保持 `SAFE_MODE` 與 `BLOCKED`。

本次「建立新計劃」經去重後保留本文件為唯一 canonical，決策為
`EXISTING CANONICAL RETAINED / NO NEW FILE / NO NEW VERSION ID`。新增的實質內容是細化
既有 G35-02 執行工作包；34.0 source freeze 已於 2026-07-19 取得 stage／本機 commit／freeze
授權並完成。這不包含 build 或發行授權；G35-02 目前只轉為 `READY`，須等 G35-02A 實際開始
failing regression 工作後才可標記 `IN_PROGRESS`。

## 目標與非目標

- **Goal**：以資料安全、相容性、可診斷性、人工可用性、量測證據及發行完整性的順序，
  把目前工作樹收斂到可驗證的 Development 40.0 候選決策點。
- **Scope**：只處理下表已由程式碼或既有阻擋證明的缺口；每版先做 baseline，再做最小修正。
- **Non-goals**：35.0～40.0 不新增網站、Gopeed、P2P／Torrent、通用解析器、雲端帳號、
  遙測或自動上傳，也不繞過 DRM、登入、Cookie、Cloudflare、廣告、付費或地區限制。
- **Compatibility**：未知 major／特權安全契約一律 fail closed；允許加法相容的範圍必須明列，
  不可用廣泛忽略未知欄位取代安全驗證。
- **Breaking Change**：本計畫不預設公開 API、runtime protocol 或 UserData breaking change；
  35.0 對錯誤型別與無效 dependency 狀態的拒絕屬安全收緊，必須在 release note 明列。
- **Migration**：只有已知舊設定格式可依 35.0 計畫原子遷移；其他格式若需要轉換，必須先
  另立 Expand → Verify → Contract、備份與 rollback，不可直接併入版本。

## 決策依據

### Verified Facts

- `core/settings.py` 的損壞／非 object／錯誤型別／future schema fail-closed、未知欄位保留、
  跨程序鎖與 typed patch 已因 34.0 source-freeze 資料風險提前完成；使用歷史 `pre-35`
  檔名的 legacy／pre-schema1 回復工具也已建立。
- `core/plugins/manager.py` 的外部 MOD enable／disable 尚未完成 enabled dependency、
  dependent-safe disable 與 cycle Gate；目前 executable plugin 預設關閉。
- `DiscoveryItemV1`、`HistoryEventV1`／`HistoryPreferencesV1`、`RecoveryPlanV1`／
  `RecoveryCandidateV1` 與 `ProviderFailureV1` 目前使用 exact key set。
- 四語與多數 accessible name 已有自動化基線；940×620、鍵盤焦點、讀屏與高對比仍缺人工證據。
- copied-folder／rollback 基線已完成，但新候選尚未精確斷言 verify-only 與 headless 的
  `SAFE_MODE` stdout；Stable sign-before-stage 與 signed-set CLI wiring 尚未完成。

### Assumptions

- 35.0～39.0 是 evidence milestone，不保證各自建立附件；只有 material delta 才同步版本身分。
- 先固定人工 UI，再量測近最終 UI，可避免先最佳化後因版面修正重做。

### Unknowns

- 後續 build 授權與 production signing 身分尚未取得。
- 本次 freeze 驗證曾有一次 recovery provider 空 stdout／stderr 退出；精確案例 20 輪、前序
  組合 5 輪、250 輪額外壓力驗證與完整套件重跑均未重現，暫列 `TRANSIENT / NOT_REPRODUCED`。
  若再次發生，依 G37-01 先保存 sanitized exit code、同時段 WER 與 dump，不加入自動重試隱藏原生失敗。
- `0x80000003` 尚未穩定重現，也沒有 WER faulting module／offset。
- 可用的 NVDA／讀屏、四語人工環境與其他 provider 合法 live matrix 時程未知。

## 排序規則

1. **版本 gate 先於版本內 Priority**：只有前一版 Exit Gate 完成，下一版才可轉為 `ACTIVE`。
   後續版本的 P0 不會跨版插隊；只有可重現的安全事件、資料損失或目前原生崩潰可例外升級。
2. **P0** 阻擋該版本完成；**P1** 先以 evidence gate 判定是否存在 material delta。確認有差異後，
   該 P1 的 Exit Gate 必須完成；沒有差異則標記 `ABSORBED / NO RELEASE`。**P2** 集中在
   Deferred Backlog，不阻擋版本結束。
3. 同一時間只能有一個 `ACTIVE` 版本及一個 `IN_PROGRESS` 項目。
4. 啟動項目前必須有可重現缺口、驗證計畫、Rollback 與受影響清冊；進入修正前先加入
   可證明缺口的 failing Regression Test。若唯讀盤點證明能力已存在，標記
   `ABSORBED / NO RELEASE`，不建立空版本、不改 `CORE_VERSION`。
5. 外部權限、網站或人工環境缺失時維持 `BLOCKED`；不得用 placeholder、自簽、降低驗證條件
   或 headless exit 0 偽稱完成。
6. 無 material delta 時不升版；有 material delta 時，必須在該版 Exit Gate 前同步
   `core/version.py`、`pyproject.toml`、README 與所屬大版本 release 文件。是否 build 仍需獨立授權。
7. G38 因人工環境阻擋時，只允許 G39 做唯讀 baseline 準備；G39 不得轉為 `ACTIVE`、實作
   最佳化或完成 Exit Gate，直到 G38 已完成或另有明確 scope 決策。

## 依賴執行順序與版本內 Priority

| 排名 | 工作 ID | 版本／Priority | 狀態 | 唯一成果與 Gate |
|---:|---|---|---|---|
| 1 | G34-01 | 34.0-P0 | `DONE / SOURCE-FROZEN` | VUP-34-02 已完成；核准範圍由兩個本機 commit 固定，最終 freeze revision 維持 clean。 |
| 2 | G35-01 | 35.0-P0 | `DONE / ABSORBED INTO G34 SOURCE FREEZE` | 設定檔 typed decode、future fail-safe、併行 patch 與回復工具已作為 G34 freeze blocker 完成。 |
| 3 | G35-02 | 35.0-P0 | `READY / 35.0 ACTIVE` | 外部 MOD dependency graph、pending journal 與可恢復 enable／disable 生命週期；尚未進入 `IN_PROGRESS`。 |
| 4 | G36-01 | 36.0-P1 | `WAITING` | 非特權結果 DTO 的明確加法相容；安全契約繼續 strict。 |
| 5 | G37-01 | 37.0-P1 | `EVIDENCE GATED` | 原生崩潰／provider 失敗的去識別證據；崩潰重現時升 P0。 |
| 6 | G38-01 | 38.0-P1 | `MANUAL ENV REQUIRED` | 940×620、鍵盤、NVDA／讀屏、高對比與四語人工矩陣。 |
| 7 | G39-01 | 39.0-P1 | `MEASUREMENT GATED` | 固定 workload 的資源 baseline；無瓶頸則 `MEASURED / NO CHANGE`。 |
| 8 | G40-01 | 40.0-P0 | `WAITING / BUILD + FORMAL RUNTIME AUTH REQUIRED` | 新候選 copied-folder 的精確 `SAFE_MODE` 證據與可回退性。 |

Stable-only Gate 不屬於 Development 40.0 的執行排名；只有使用者明確選擇 Stable 後，
G40-02 才成為該獨立通道的 P0：sign-before-stage、channel-aware exact signed set、
production Ed25519／Authenticode `Valid` 與正式 preflight。

## 方案取捨

| 方案 | 成本／維護 | 安全與一致性 | 測試／Rollback | 決定 |
|---|---|---|---|---|
| 逐版 evidence gate；無差異即 `ABSORBED / NO RELEASE` | 每版範圍小，外部 Gate 可能使進度停留 | 契約、資料、UI、效能與發行依序收斂 | Regression 與回復邊界最清楚 | **採用** |
| 35.0～39.0 平行功能開發，40.0 一次整合 | 表面較快，但合併與維護成本高 | 同時變更資料、契約、UI 與發行，風險互相放大 | 回歸來源與 rollback 難隔離 | 不採用 |

採用逐版 Gate 的理由是 34.0 已提供 clean source revision，而後續仍有外部簽署／人工環境
阻擋；平行開發無法安全縮短這些外部依賴，反而會擴大 blast radius。

## 34.0｜來源基線與凍結

- **Goal**：將 34.0 工作樹收斂為單一、可追蹤、可回復的 clean source revision；已完成。
- **Scope**：目前已核准進入 review scope 的路徑、版本一致性與 blocker ledger；不打包。
- **Priority**：P0，全計畫第一順位。
- **Dependencies**：使用者已於 2026-07-19 明確授權 stage、本機 commit 與 source freeze；
  build、EXE、push、Testing／Stable、簽署與發布仍未授權。
- **Approach**：已完成最終 diff review → 歷史保存 commit → 主要 freeze commit → clean
  worktree／source fingerprint。最終 hash 與 fingerprint 在 commit 完成後由交付回報保存，
  不寫入同一 commit 造成自我參照。
- **Compatibility**：保持 manifest／runtime protocol、既有第三方 provider 介面與第三方 MOD
  fail-closed 上限；新增的 provider capability v1 目前由 core self-check 驗證，並作為可信 UI
  後續採用的加法式契約；本版不宣稱 capability-to-button routing 已完成。
- **Breaking Change／Migration**：不改公開 API／既有第三方 provider 介面；設定檔加入 schema 1，legacy
  exact bytes 先備份再原子升級，future schema 保持唯讀，並提供 legacy／pre-schema1 回復工具。
- **Risk**：髒工作樹混入無關修改，或把 review scope 誤當成交付授權。
- **Rollback**：只以獨立 revert 回復核准 commit；不 rewrite history、不刪除 UserData。
- **Validation**：Shared Definition of Done 全部通過，最終 revision 需維持 clean worktree。
- **目前證據（2026-07-19）**：完整 Repository pytest 重跑為 `1092 passed, 7 skipped`；Ruff／文字污染
  `355 / 557`、compileall、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴 `10`、版本文件 `4`、
  保留版本 `5` 與 `git diff --check` 通過；修正後獨立 freeze re-review 在設定回復鎖與
  feature MOD 不可逆狀態範圍未發現剩餘 P0／P1。一次 recovery provider EOF 未重現，
  不以 retry 或放寬 assertion 隱藏；其診斷 follow-up 由 G37-01 evidence gate 管理。
- **Exit Gate**：`DONE / VUP-34-02 COMPLETE`；無可在本機安全修復的未處理 P0，外部阻擋已列明。

## 35.0｜設定與外部 MOD 生命週期安全

- **Goal**：設定檔損壞、未知版本或 MOD dependency 狀態不再造成啟動崩潰、靜默降級後覆寫，
  或不一致的啟停順序。
- **Scope**：已提前完成的 `SettingsService` typed decode／狀態回報／原子遷移，以及尚待執行的外部 MOD dependency graph；
  不變更內建父子 MOD 已完成的交易基線，不重新開啟 executable plugin。
- **Priority**：P0。設定檔資料遺失風險先於 G35-02；G35-01 完成後才處理 dependency graph。
- **Verified gap／Unknown**：設定 parser、併行 writer 與回退缺口已有回歸並提前關閉；
  external dependency graph 仍由程式碼確認為 G35-02 缺口。不得把設定完成誤報為整個 35.0 完成。
- **Dependencies**：G34-01 clean baseline、現有 atomic write helper、manifest dependency 資料。
- **Approach**：設定端已以 corrupt、top-level list、錯誤欄位型別、future schema、unknown keys、
  stale writer 與 lock timeout fixture 驗證；runtime 只在可寫狀態持久化，否則 fail closed。
  G35-02 的 MOD enable 要求 dependency 已安裝、非 pending 且已啟用；disable 預設拒絕 enabled dependents，
  並回傳可操作原因。dependent-first cascade 會改變使用者選擇，留待另立明示操作，不在本版自動執行。
- **Compatibility**：目前 schema 1 reader／writer 保留已接受的 unknown keys；future schema 維持
  read-only。回復工具只還原經 SHA 驗證的 legacy／pre-schema1 backup，不承諾任意 future 格式可寫相容。
- **Breaking Change**：錯誤型別、損壞設定及無效 dependency ordering 會由模糊 fallback 改為
  可診斷拒絕；不改 manifest schema 或 runtime protocol。
- **Migration**：只對已知舊格式以副本、驗證、原子替換遷移；unknown／future schema 不寫回。
  第一次 schema 1 write 前保存已驗證備份；回退時使用 owned copy／read-only 或還原備份，
  不讓舊 writer 接觸唯一的新格式原檔。
- **Risk**：收緊 latent invalid MOD ordering，或 fallback 設定被誤寫為正式設定。
- **Rollback**：保留原檔備份；回退時只切換到已驗證備份或 owned copy，不刪設定或 registry，
  也不宣稱 34 能保留它不認識的 future fields。
- **降版準備（來源工作樹，尚未發行）**：`tools.settings_rollback` 預設只做 dry-run；它驗證
  歷史檔名 `settings.pre-35.<sha256>.json` 的雜湊、大小、legacy 型別與路徑邊界；該檔
  可能由 Development 34 第一次 schema 1 write 建立，不宣稱是緊鄰 35 的 snapshot。明確 `--apply`
  仍須帶入 dry-run 的 current SHA-256；重新規劃、雜湊、current owned copy 與原子替換
  全程持有與 `SettingsService.patch()` 相同的跨程序鎖；
  操作與失敗處理見 [35→34 設定回復 Runbook](settings-pre35-rollback.md)。
- **Validation**：設定端 corrupt／list／future／typed values、原 bytes、save failure、stale writer、
  lock timeout／競爭與 rollback 回歸已包含於完整 `1092 passed, 7 skipped`；dependency
  missing／pending／disabled、dependent disable 與 cycle 仍由 G35-02 驗證。

### G35-02 詳細執行計劃｜外部 MOD dependency graph 與可恢復生命週期

狀態：`READY / 35.0 ACTIVE`。本節是 35.0 的唯一實質工作包；34.0 已完成 source freeze。
目前尚未開始 G35-02A，只有實際加入 failing regressions 時才轉為 `IN_PROGRESS`。

**Verified gaps**：

- `PluginManager.set_enabled()` 尚未驗證 target 的 pending action、dependency 是否 installed／
  pending-free／enabled，也未在 disable 前拒絕 enabled dependents。
- enable 目前先啟動 supervisor 再寫 registry；disable 先停止 supervisor 再寫 registry。
  registry finalization 失敗時可能造成 runtime 與 registry 分歧，且 `sqlite3.Error` 並未完整映射
  為可診斷的補償結果。
- `PluginRegistry.set_enabled()` 會直接把 pending action 清為 `NONE`；若 UPDATE／ROLLBACK／
  REMOVE 等 transaction 誤觸 toggle，可能破壞 recovery journal。
- manifest parser 只拒絕 self／duplicate dependency；installer／updater 尚未驗證整張 installed
  graph 的間接 cycle。既有 maintenance removal 已保守拒絕 installed dependents，可沿用其
  fail-closed 原則。
- `PendingAction.ENABLE`／`DISABLE` 已存在但尚未投入 lifecycle；startup recovery 目前會把它們
  當成 unsupported action。現有 plugin manager tests 也未涵蓋上述失敗路徑。
- bootstrap／supervisor 尚未依 dependency-first topological order 啟動 enabled MOD；dependency
  啟動失敗後 downstream 仍可能被嘗試啟動。supervisor 在 initialize 失敗或 stop 結果未知時的
  process handle ownership 也需先證明不會留下 orphan 或把未終止程序誤報為已停止。
- restore 尚未重新驗證 dependency readiness；update／rollback candidate 可能改變 graph，必須
  在任何檔案 transaction 前以 candidate overlay 驗證，而不是只檢查目前 installed snapshot。

**方案取捨**：

| 方案 | 成本 | 一致性／Recovery | 決定 |
|---|---|---|---|
| 只在 enable 前做 dependency preflight | 低 | 仍保留 start／stop 與 registry 寫入失敗後的分歧 | 不採用 |
| graph preflight + pending journal + startup recovery | 中；沿用既有 enum、SQLite registry 與 recovery | 可在 crash／失敗後收斂為 disabled 安全狀態 | **採用** |
| 自動 enable dependency 或 cascade disable dependent | 高，且會改變使用者選擇 | 回復順序與不可逆副作用擴大 | 不納入本版 |

**依序工作包**：

| 順序 | Priority | 工作與成功條件 |
|---:|---|---|
| G35-02A | P0 | 先加入 failing regressions 與唯讀 dependency graph snapshot／candidate overlay／cycle validator；錯誤或被竄改 manifest、missing node 與間接 cycle 使用穩定結果 fail closed。 |
| G35-02B | P0 | 建立共用且有界的 plugin lifecycle lock，鎖內重讀 registry／manifest；提供 registry compare-and-set transition 並實際使用 `ENABLE`／`DISABLE` journal。target 有任何既有 pending action 時拒絕 toggle 且不得清除 journal；SQLite transaction 不跨 process handshake。 |
| G35-02C | P0 | 修正 supervisor process handle ownership；enable 僅允許 dependency installed、pending=`NONE`、enabled 且 verified，disable 預設拒絕 enabled transitive dependents。supervisor 或 registry 失敗需補償並回報 complete／incomplete rollback，不自動安裝、啟用或 cascade。 |
| G35-02D | P1 | install／update／rollback／restore 在檔案 transaction 前以 candidate overlay 驗證完整 graph；startup／recovery 以 dependency-first topological order 處理，未完成 enable／disable 收斂為 disabled／`NONE`，dependency failure 阻擋 downstream 且不得留下 orphan process。 |
| G35-02E | P1 | 同步 MOD developer guide、release／roadmap 與 recovery 行為，執行 targeted plugin suites、完整 Repository tests 及 Shared DoD。 |

**Compatibility／Migration**：manifest schema v2、runtime protocol 1.0、簽章、TrustStore 與 capability
規則不變；dependency 仍只表示 plugin ID，不新增版本約束。沒有 UserData schema migration；既有
不一致 graph 在 enable／update 時改為可診斷拒絕，屬安全收緊。executable plugin 預設關閉與
SAFE_MODE／BLOCKED 規則不得放寬。

**Risk／Rollback**：主要風險是 stale graph、lock ordering、補償失敗或把 disabled dependent
誤判為阻擋。操作必須在共用且有界的 lifecycle lock 內重讀狀態；失敗時保留 pending journal、
停止不應存活的 runtime，並收斂到 disabled。程式回退只 revert G35-02 來源／測試；不刪 registry、
MOD 目錄或既有 backups，也不自動改變 dependency／dependent 的使用者選擇。若曾產生
`ENABLE`／`DISABLE` journal，降回不支援該 recovery 的來源前必須先用 G35 recovery 收斂為
disabled／`NONE`；不得以直接改 SQLite 取代收斂。

**Acceptance／Validation**：missing／pending／disabled dependency 均不能 enable；間接 cycle
fail closed；enabled dependent 阻擋 disable、disabled dependent 不阻擋；任一 pending target
不得 toggle；start、stop、registry finalize 或 recovery 失敗後不得留下無法診斷的 runtime／
registry 分歧或 orphan process；startup 依拓撲順序且 dependency failure 不啟動 downstream；
restore／update／rollback 不得導入無效 graph。完成 targeted plugin tests、完整 pytest、Ruff／quality audit、compileall、MOD／
依賴／版本稽核與 `git diff --check` 後，才可完成 G35-02。此規劃輪未執行測試；不宣稱 G35 已完成。

- **Exit Gate**：上述可重現資料／生命週期缺口均關閉；若 G35-02 在 executable plugin 關閉下
  只屬未來 Gate，仍須完成離線 operator 測試但不得宣稱已啟用外掛執行。

## 36.0｜非特權契約的加法相容

- **Goal**：舊 core 可安全讀取含 benign 新欄位的 discovery／history／recovery／provider failure
  結果，不因精確 key set 拒絕整筆資料。
- **Scope**：只限非特權 result DTO；manifest、capability、路徑、簽章與其他安全 payload 保持 strict。
- **Priority**：P1；必須在 UI 或跨 provider 擴充前完成。
- **Verified gap／Unknown**：上述 V1 DTO 的 exact key set 已確認；沒有已發布 predecessor 的 DTO
  不捏造 v0，額外欄位的 threat model 與上限需在實作前逐類定義。
- **Dependencies**：G35 完成、現有 schema v1 fixture 與 payload 大小上限。
- **Approach**：比較兩案：A）維持 exact key 並每次升 schema；B）只對逐一列名的
  `DiscoveryItemV1`、`HistoryEventV1`、`HistoryPreferencesV1`、`RecoveryPlanV1`、
  `RecoveryCandidateV1` 與 `ProviderFailureV1` 接受有界 extra keys。採 B，以取得前向加法相容；
  每個 DTO 必須定義 extra field 數量、key／value 大小、保留名稱與整體 payload 上限。
  相容矩陣只涵蓋 current／additive／unknown major，以及實際存在的已發布 predecessor。
- **Compatibility**：missing required、unknown schema、oversize 仍 fail closed；writer 只輸出 current schema。
- **Breaking Change／Migration**：無；只放寬白名單 result reader 的 benign extra keys，
  不重寫既有資料。
- **Risk**：加法政策擴張到特權契約，或忽略原本應驗證的欄位。
- **Rollback**：逐 DTO 回復 parser policy；資料格式與 UserData 不需遷移。
- **Validation**：extra benign key 等價解析；missing／unknown／oversize 失敗；特權契約未知欄位仍拒絕。
- **Exit Gate**：六個列名 DTO 有一致政策與 regression；若盤點顯示無 material delta，標記
  `ABSORBED / NO RELEASE`，不得空轉升版。

## 37.0｜條件式原生崩潰與 provider 失敗證據

- **Goal**：不蒐集敏感資料的前提下，取得足以定位 ANI／provider／runtime 原生失敗的證據。
- **Scope**：沿用既有 self-check `run_id`、ProviderFailure 穩定 error code 與 redaction；只補
  WER module／offset 手動採證 runbook，以及與既有 run ID 對應的有界證據欄位。
  不建立第二套診斷匯出系統，也不重新實作已存在的 correlation／error code。
- **Priority**：P1；若 `0x80000003` 或同類 native crash 再現，該重現與回歸立即升為 P0。
- **Verified gap／Unknown**：run ID、error code 與去識別匯出列為 `ABSORBED`；缺口是 WER 採證
  與可重現 root cause。崩潰尚未重現，因此不得預先承諾程式修正。
- **Dependencies**：G36 契約政策、既有去識別 self-check、合法且使用者控制的重現環境。
- **Approach**：先保存 symptom／trigger／module／offset／run ID，再依證據修 root cause；沒有重現時
  只完成 runbook 與格式，不猜測已修復。
- **Compatibility**：診斷欄位採 additive schema 或明確升版，舊 consumer 仍可讀必要欄位。
- **Breaking Change／Migration**：無；診斷資料只採 additive output，不遷移 UserData。
- **Risk**：本機路徑、Cookie、token、媒體內容或 dump 外洩；過度脫敏亦可能失去診斷價值。
- **Rollback**：停用新增證據欄位與入口；不變更或刪除原始 UserData。
- **Validation**：secret corpus、私人 Windows 路徑、大小上限、原子輸出、無網路／無背景程序副作用。
- **Exit Gate**：runbook 與證據契約完成；沒有可重現 crash 時標記 `EVIDENCE READY / NO CLAIM`，
  不宣稱 0x80000003 已修復。

## 38.0｜四語與人工可存取性 Gate

- **Goal**：關閉目前自動化完成、人工阻擋的可用性缺口，再固定近最終 UI 供後續量測。
- **Scope**：940×620 全工作區、Tab order／focus、accessible name、NVDA／讀屏、高對比、深色表面、
  zh-TW／zh-CN／en／ja 與 SAFE_MODE／provider blocker 呈現；不做無關視覺重設計。
- **Priority**：P1；Development candidate 前轉為 P0 Gate。
- **Verified gap／Unknown**：自動化尺寸／名稱基線已完成；缺口只剩真實焦點、讀屏、高對比
  與四語人工矩陣，驗收環境時程未知。
- **Dependencies**：可啟動的 Qt 環境與人工讀屏／四語驗收者。
- **Approach**：固定人工矩陣；只修失敗項並為每個修正補最小自動 regression。
- **Compatibility**：action／object ID 不變；翻譯鍵 additive 且有安全 fallback。
- **Breaking Change／Migration**：無；UI 修正不得改公開 action ID 或資料格式。
- **Risk**：人工判定不一致，或四語文字長度造成版面裁切。
- **Rollback**：逐項回復 UI 差異；不回退資料 schema。
- **Validation**：既有 UI tests 加實際尺寸、鍵盤、focused widget、讀屏、高對比與四語證據。
- **Exit Gate**：人工矩陣實際完成；環境缺失時保持 `MANUAL BLOCKED`，headless 測試不能代替。

## 39.0｜量測式效能與資源預算

- **Goal**：用固定 workload 找出真正瓶頸；沒有量測證據時不以複雜度換取推測性最佳化。
- **Scope**：大量搜尋結果、縮圖 cache／pending、佇列刷新、取消後 thread／handle 與本機暫存；
  不加入遙測、背景預取或無上限並行。
- **Priority**：P1；排在 UI 結構與人工 Gate 穩定之後，避免量測重做。
- **Verified gap／Unknown**：既有資源上限與取消清理列為 `ABSORBED`；目前尚無量測證據證明
  特定 bottleneck，先做 baseline，不承諾最佳化或效益。
- **Dependencies**：G38 近最終 UI、固定資料集／workload 與相同環境的 before／after 方法。
- **Approach**：先記錄 baseline、target、workload、constraint，再只修實測 bottleneck。
- **Compatibility**：不改公開 contract；資源上限維持有界且可診斷。
- **Breaking Change／Migration**：無；若量測指向 contract／資料變更，停止並另立計畫。
- **Risk**：時間型 CI 測試不穩，或跨機器數據被錯誤比較。
- **Rollback**：移除單項最佳化，但保留安全上限、benchmark 與診斷證據。
- **Validation**：同環境多次 p50／p95、memory／handle／temp 量測與功能 regression；CI 只檢查
  上限與洩漏，不硬綁硬體絕對時間。
- **Exit Gate**：baseline 已保存且無資源 regression；無可證 bottleneck 時標記
  `MEASURED / NO CHANGE`，不建立空產物。

## 40.0｜可重現候選與發行完整性

- **Goal**：在另行授權後，從 clean revision 產生可驗證、可回退且明確為 unsigned
  `SAFE_MODE` 的 Development candidate；Stable 只保留條件式 Gate。
- **Scope**：Development 只涵蓋固定 Deno／FFmpeg 與授權、runtime policy audit、SBOM、
  release-info、SHA-256 與 copied-folder current→previous→current。Stable-only G40-02 才涵蓋
  sign-before-stage／exact signed set operator；不建立 Testing／Stable、不推送，除非使用者
  在該步驟另行明確授權。
- **Priority**：P0，為最後 release-integrity Gate。
- **Verified gap／Unknown**：copied-folder／rollback 本體列為 `ABSORBED`；已確認尚缺精確
  SAFE_MODE stdout 證據與 Stable CLI wiring。build 授權及正式簽署身分仍未知。
- **Dependencies**：G34～G39、build 授權與正式 runtime。Stable-only G40-02 另依賴
  production Ed25519、Authenticode 憑證與使用者通道決定。
- **Approach**：clean revision → isolated build work → staged runtime audit → 完整驗證 → copied-folder
  與 rollback。`CommandStatus` 必須保存有界且脫敏的 stdout／stderr，verify-only 與 headless 都要
  精確證明 `MediaManager security mode: SAFE_MODE`；exit 0 本身不構成安全證據。
  若另行啟動 G40-02，Stable operator 必須先驗 Authenticode `Valid`，才可 stage／產生最終
  metadata／checksum／Ed25519；signing／preflight CLI 使用 `stable_signed_files(version)` exact set。
- **Compatibility**：保留上一 Development；只有明確宣告 rollback-compatible 的格式可共用
  UserData。35 設定格式使用 owned copy／read-only／已驗證備份回退，不保證所有資料都可雙向寫入。
- **Breaking Change／Migration**：候選本身不得新增 breaking change；若前版已核准 migration，
  必須在 copied-folder 前完成獨立 upgrade／rollback 驗證。
- **Risk**：產物混入絕對路徑、runtime／license hash 不符、future settings 在回退後被舊版刪除，
  或 NotSigned 產物先被 stage。
- **Rollback**：實際回退使用保留的上一版與原子備份；刪除未發布候選工作目錄仍需另行授權。
- **Validation**：G40-01 Development Exit Gate 執行 Shared DoD、staged runtime audit、
  metadata／SBOM／checksum、copied-folder 精確 SAFE_MODE 與 rollback。只有另行啟動 G40-02，
  才執行 sign-before-stage 模擬失敗測試；Stable 另須 Authenticode `Valid`、production Ed25519
  與正式 preflight `ready=true / exit 0`。
- **Exit Gate**：最多宣告 Development candidate 驗證完成。Stable 缺正式身分時保持
  `CONDITIONAL / BLOCKED`，不得以 Development 產物改名、搬移或升格。

## Shared Definition of Done

每個實際程式變更至少執行與風險相符的相關回歸，並在版本 Exit Gate 前執行：

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

任何未執行、部分執行、略過或受外部條件阻擋的驗證都必須逐項記錄；不得以舊結果宣稱新差異通過。

## Deferred Backlog（不屬於 34.0～40.0 完成條件）

- 新網站、Gopeed、P2P／Torrent、通用解析器、雲端同步、帳號與自動更新。
- 需要 DRM、登入、Cookie、Cloudflare、廣告、付費或地區限制繞過的功能永久排除。
- 參考軟體差異只有在量測或明確需求證明價值後，才可另立新 scope；不得回填進本計畫。

## 完成與停止條件

40.0 的 Development Exit Gate 完成後，本計畫停止自動擴張並回報總結；不得自動建立 41.0、
Testing 或 Stable。若任一版本沒有 material delta，依規則標記 `ABSORBED / NO RELEASE` 並前進到
下一個已證明缺口；不得為維持版本數量而建立空附件。
