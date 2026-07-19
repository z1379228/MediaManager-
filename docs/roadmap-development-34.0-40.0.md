# Development 34.0～40.0 唯一版本更新計畫

狀態：`CANONICAL / 34.0 SOURCE-FROZEN / 35.0～37.0 EXIT GATE DONE / SOURCE ONLY / 38.0 ACTIVE / G38-01 P1 FIXES VALIDATED / MANUAL REVALIDATION BLOCKED / SAFE_MODE / 39.0～40.0 WAITING`
規劃基線：2026-07-18；Development 34.0／核心相容版本 34.0.0 已完成來源凍結，尚未封裝。

本文件重新設計 34.0～40.0 的唯一執行順序，取代 35.0～40.0 單版草案的執行權；
單版文件只保留歷史背景。建立本計畫本身不等於授權修改版本號、stage、commit、build、建立
EXE／Testing／Stable、簽署、推送 Git 或覆寫任何歷史版本。缺少正式簽署身分、正式 runtime、
外部網站或人工 UI 證據時，必須保持 `SAFE_MODE` 與 `BLOCKED`。

本次「建立新計劃」經去重後保留本文件為唯一 canonical，決策為
`EXISTING CANONICAL RETAINED / NO NEW FILE / NO NEW VERSION ID`。新增的實質內容是細化
既有 G35-02 執行工作包；34.0 source freeze 已於 2026-07-19 取得 stage／本機 commit／freeze
授權並完成。這不包含 build 或發行授權；G35-02A～E 與 35.0 Exit Gate 已於 2026-07-19
完成；G36-01 與 36.0 Exit Gate 亦已完成。G37-01 的 material privacy delta 已使來源身分同步為
37.0.0，且 source-only Exit Gate 已完成。G38-01 的無頭自動基線已重驗，並用 failing
regression 證實、修正焦點指示與安全 badge 讀屏名稱兩個 material P1；現為唯一
`ACTIVE / MANUAL REVALIDATION BLOCKED` 項目。2026-07-19 使用者另行授權同步來源身分為
38.0.0，並明確授權將目前 35.0～38.0 核准變更 stage、本機 commit、固定為 Development 38.0
source freeze，再建立一次 Development 38.0 SAFE_MODE 未簽署候選包；這不包含 Testing／Stable、
簽署、發布、push 或覆寫歷史版本授權。打包只可使用該 source-freeze revision，其他版本不得平行啟動。
source freeze `6534e3f5ebcc3e3c459a34a335e2b176b2cd1107` 與唯一一次 Development 38.0
打包現已完成；產物位於 `Version/Development/38.0`，但 G38 人工 Exit Gate 與 G39／G40 順序不變。

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
- G35-02A～D 已關閉外部 MOD graph、toggle journal、candidate transaction、Supervisor ownership
  與 startup／recovery 的可重現 P0／P1 缺口；目前 executable plugin 仍預設關閉。
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
- G37 完整驗證曾間歇性重現 history provider 空 stdout／stderr 退出；壓力取證為
  `phase=stdout_eof / exit_code=1 / reader_complete=true`，且 state 尚未建立。單一 stdout producer
  的 FIFO 排除 EOF 超車 result；直接 subprocess 與相同 Job Object 各 300 輪均通過，因此 exit 1
  的成因仍為 `TRANSIENT / REPRODUCED INTERMITTENT / ROOT CAUSE UNKNOWN`。不加入自動重試隱藏
  可能的副作用；後續只依 G37 證據格式記錄 sanitized metadata。
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
| 3 | G35-02 | 35.0-P0 | `DONE / SOURCE ONLY / SAFE_MODE` | graph、bounded lifecycle journal、candidate transaction、Supervisor ownership、topological recovery、文件、完整 Repository tests 與 Shared DoD 均完成；後續納入 Development 38.0 source freeze，未建立 35.0 候選包。 |
| 4 | G36-01 | 36.0-P1 | `DONE / SOURCE ONLY / SAFE_MODE` | 六個非特權 result DTO 使用一致、有界且丟棄 extras 的加法 reader；安全契約繼續 strict。 |
| 5 | G37-01 | 37.0-P1 | `DONE / EVIDENCE READY / NO CLAIM / SOURCE ONLY / SAFE_MODE` | 去識別證據契約、provider exit metadata、queue／self-check 邊界與 runbook 已完成；未宣稱原生 crash 或未知 exit 1 已修復。 |
| 6 | G38-01 | 38.0-P1 | `ACTIVE / PACKAGE BUILT / P1 FIXES VALIDATED / MANUAL REVALIDATION BLOCKED / SAFE_MODE` | source freeze `6534e3f…1107` 與未簽署 Development 38.0 包已完成；runtime 6/6、116 筆 checksum 與 copied-folder 回退通過。940×620 全工作區、NVDA／UIA、OS 高對比與四語人工矩陣仍需人工環境。 |
| 7 | G39-01 | 39.0-P1 | `WAITING / MEASUREMENT GATED / READ-ONLY INVENTORY DONE` | 純本機 constraint preflight `7 passed, 1 skipped`；尚無 p50／p95、memory、handle 或 temp baseline，G38 完成前不啟動。 |
| 8 | G40-01 | 40.0-P0 | `WAITING / PRIOR GATES + EXACT SAFE_MODE OUTPUT REQUIRED` | 38.0 runtime/checksum 與 copied-folder 回退基線已通過，但報告未保存精確 `SAFE_MODE` stdout；本次單一 38.0 打包不啟動 G40。 |

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
- **Scope**：已提前完成的 `SettingsService` typed decode／狀態回報／原子遷移，以及已由
  G35-02A～D 完成的外部 MOD dependency graph 與可恢復生命週期；不變更內建父子 MOD
  已完成的交易基線，不重新開啟 executable plugin。
- **Priority**：P0。設定檔資料遺失風險先於 G35-02；G35-01 完成後才處理 dependency graph。
- **Verified gap／Unknown**：設定 parser、併行 writer 與回退缺口已有回歸並提前關閉；
  external dependency graph、recovery、operator 文件與完整 Gate 已由 G35-02A～E 關閉。
  executable plugin 仍預設關閉，三項非阻擋 P2 留待重新啟用前處理。
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
  missing／pending／disabled、dependent disable、cycle、candidate transaction 與 recovery 已由
  G35-02A～D targeted regressions 覆蓋；G35-02E 的文件同步、完整 Repository tests 與 Shared DoD
  亦已完成。

### G35-02 詳細執行計劃｜外部 MOD dependency graph 與可恢復生命週期

狀態：`G35-02A-E DONE / 35.0 EXIT GATE DONE / SOURCE ONLY / SAFE_MODE`。本節是 35.0 的唯一
實質工作包；34.0 已完成 source freeze。後續 G36-01 亦已依序完成，未與本節平行執行。

**初始 gap baseline 與目前狀態**：

- **CLOSED by B／C**：`PluginManager.set_enabled()` 已在共用 lifecycle lock 內拒絕 target pending，
  enable 會驗證所有 transitive dependency installed／`NONE`／enabled／verified；有效 graph 的
  disable 會拒絕 enabled transitive dependents，無效 graph 則先寫入 `DISABLE` journal、contain
  target runtime，並由 D 的 dependent-first recovery 安全收斂，不把未知 dependency safety 誤報為成功。
- **CLOSED by B／C**：enable／disable 已使用 compare-and-set `ENABLE`／`DISABLE` journal；
  supervisor handshake 前先提交 claim。registry finalize 或 stop 失敗不會被誤報為完成；已知保留
  與 SQLite／CAS 後未確認的 journal state 會分開描述，並回報 complete／incomplete rollback。
  舊 `set_enabled()` 不再用於 toggle。
- **CLOSED by A／D**：installed snapshot 與 candidate overlay 拒絕 missing node、tampered manifest
  與間接 cycle；installer／updater／rollback／restore 已在檔案 transaction 前接入 bounded candidate
  graph，rollback／restore 另含 core compatibility、trust refresh 與 post-move reverify。
- **CLOSED by C／D**：Supervisor 在 launch 後立即擁有 handle，initialize／stop 失敗不會遺失
  ownership，短期 capability 可即時撤銷；正常 startup 與 transaction recovery 採 dependency-first，
  dependency failure 會阻擋 downstream，toggle recovery 則採 dependent-first containment。
- **CLOSED by D／E**：未完成 `ENABLE`／`DISABLE` 只有在確認 runtime 已停止後才收斂為
  disabled／`NONE`；restore 補償失敗的 stranded candidate 會在下次啟動回到 quarantine 並保留
  `REMOVE`。operator 文件、完整 Repository tests、Shared DoD 與 G35 Exit Gate 均已完成。

**方案取捨**：

| 方案 | 成本 | 一致性／Recovery | 決定 |
|---|---|---|---|
| 只在 enable 前做 dependency preflight | 低 | 仍保留 start／stop 與 registry 寫入失敗後的分歧 | 不採用 |
| graph preflight + pending journal + startup recovery | 中；沿用既有 enum、SQLite registry 與 recovery | 可在 crash／失敗後收斂為 disabled 安全狀態 | **採用** |
| 自動 enable dependency 或 cascade disable dependent | 高，且會改變使用者選擇 | 回復順序與不可逆副作用擴大 | 不納入本版 |

**依序工作包**：

| 順序 | Priority | 工作與成功條件 |
|---:|---|---|
| G35-02A | P0 | **DONE**：已加入 failing regressions 與唯讀 dependency graph snapshot／candidate overlay／cycle validator；錯誤或被竄改 manifest、missing node 與間接 cycle 使用穩定結果 fail closed。 |
| G35-02B | P0 | **DONE**：共用且有界的 plugin lifecycle lock 在鎖內重讀 registry／manifest／trust；registry compare-and-set transition 實際使用 `ENABLE`／`DISABLE` journal。target 有任何既有 pending action 時拒絕 toggle 且不得清除 journal；SQLite transaction 不跨 process handshake。 |
| G35-02C | P0 | **DONE**：以共同 `RLock` 序列化 supervisor process／token／ready ownership；handshake cleanup 失敗攜回 exact handle。enable 僅允許 dependency installed、pending=`NONE`、enabled 且 verified；有效 graph 的 disable 拒絕 enabled transitive dependents，無效 graph 會 journal-first contain runtime。supervisor 或 registry 失敗會補償並明列 complete／incomplete rollback，不自動安裝、啟用或 cascade。 |
| G35-02D | P1 | **DONE**：install／update／rollback／restore 在檔案 transaction 前以 candidate overlay 驗證完整 graph；startup／transaction recovery 以 dependency-first topological order 處理，toggle recovery dependent-first containment；updater、cleanup 與 purge recovery mutation path 共用 junction／reparse root-escape Gate。 |
| G35-02E | P1 | **DONE**：已同步 MOD developer guide、release／roadmap 與 recovery 行為，完成 targeted plugin suites、完整 Repository tests 及 Shared DoD。 |

**G35-02A 驗證證據（2026-07-19）**：

- 新回歸最初因 `core.plugins.dependency_graph` 不存在而在 collection 明確失敗；新增純唯讀、
  immutable 且有 `512 nodes / 64 dependencies / 256 KiB manifest` 上限的 snapshot 後轉綠。
- 覆蓋 dependency-first 穩定順序、canonical missing node、manifest hash／identity／JSON 錯誤、
  manifest hard-read limit、installed-root escape、removed node／tombstone 不占 bounded SQL graph
  query 上限、fanout 上限，以及三節點 candidate overlay 間接 cycle；同 ID overlay 保留
  installed source integrity issue，且不寫 registry 或檔案。
- 新模組回歸 `12 passed`、相關 plugin suites `52 passed`、完整 Repository `1104 passed,
  7 skipped`。Ruff／文字污染 `357 / 559`、compileall、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5` 與 `git diff --check` 均通過。
- Installer／updater／rollback／restore 的 candidate graph 接線當時留在 G35-02D，現已完成；
  lifecycle journal 與 enable／disable readiness 分別由 B／C 完成。本項沒有啟動外部程序、修改
  SQLite schema 或移動 MOD 目錄。

**G35-02B 驗證證據（2026-07-19）**：

- failing regressions 先證明 pending journal 被 toggle 清除、缺少 compare-and-set transition、
  process handshake 跨 SQLite transaction、檔案 swap 未受共用鎖保護，以及 TrustStore stale／malformed
  與 publisher reconciliation 失敗；最後一批安全回歸在修正前為 `7 failed, 17 passed`。
- bootstrap 現在只建立一個 bounded、reentrant、跨程序 plugin lifecycle lock，Installer、Manager、
  Publisher、Cleanup、Recovery、Maintenance、Updater 與 Rollback 共用同一 instance；install／update
  在鎖內重讀 trust，registry／manifest／檔案 swap 亦留在同一 lifecycle boundary。
- `ENABLE`／`DISABLE` 使用 identity／version／hash／enabled／pending compare-and-set journal；start／stop
  handshake 前先 commit claim，完成後再 finalize，SQLite transaction 不跨外部程序呼叫。既有
  UPDATE／ROLLBACK／REMOVE／PURGE pending 不會被 toggle 清除。
- TrustStore writer 在獨立 file lock 內重讀、先保存 candidate 再提交記憶體；malformed root／欄位型別、
  stale cache 與寫入失敗均 fail closed。publisher 撤銷後若 registry 無法 reconciliation，保留撤銷並
  best-effort 停止所有外部 MOD；無法確認停止時回報明確 incomplete error。
- 核心 targeted suite `90 passed`、G35-02A/B 相關非 UI suite `105 passed`；完整 Repository 首輪
  `1144 passed, 7 skipped, 1 failed` 的 history provider EOF 失敗無法隔離重現，單例與整個
  history suite 分別 `1 passed`／`6 passed`，第二輪完整 Repository 為 `1145 passed, 7 skipped`。
  Ruff／文字污染 `360 / 562`、compileall、MOD、網站、依賴、版本與 diff 稽核均通過。
- G35-02C 的 supervisor handle ownership／dependency readiness 已完成；當時留給 G35-02D 的
  candidate graph／topological recovery 現亦已完成。B 本身不宣稱完成 G35，也未啟動 production
  MOD、修改 SQLite schema／runtime protocol／版本號、stage、commit、build、封裝、簽署、發布或 push。

**G35-02C 驗證證據（2026-07-19）**：

- 先以 `2 failed` 固定 graph 缺少 transitive dependency／dependent closure，再以 `4 failed,
  1 passed` 固定 initialize 後 orphan、stop 遺失 handle、stop-all 未 best-effort 及 capability token
  無法撤銷；Manager 新節點為 `8 failed, 1 passed`，涵蓋 missing／disabled／pending／tampered
  transitive dependency、enabled dependent 經 disabled 中介仍須阻擋，以及 complete／incomplete rollback。
  最終 review 再固定 concurrent start／stop ownership 分裂、handshake cleanup 後未追蹤 handle、
  graph 異常阻止 disable containment，以及三條 SQLite compensation 分支。
- bounded snapshot 新增穩定 closure；enable 在 lifecycle claim 前驗證所有 transitive dependency
  已安裝、`NONE`、enabled、簽章／manifest／file hash 完整，disable 反向穿越所有節點後只阻擋
  enabled transitive dependents。沒有自動 install、enable 或 cascade。
- Supervisor 以共同 `RLock` 序列化完整 start／stop／stop-all transition；Popen 後的 handshake
  cleanup 若無法確認，例外會保留 primary／cleanup error 與 exact handle，由 Supervisor 接管且
  不標為 ready。initialize／stop 會撤銷 PID-bound capability，只有 launcher 確認完成才移除 handle。
  graph 無效的 disable 仍會 journal-first 嘗試停止 target，保留 `DISABLE` journal 與明確 recovery
  訊息；registry finalize／runtime stop 失敗會區分已知保留與 state unconfirmed，並明列
  complete／incomplete rollback。
- 精準 manager suite `32 passed`、三個 ownership／manager 聚焦檔 `45 passed`、A～C 相關非 UI
  suite `136 passed`；完整 Repository 為 `1173 passed, 7 skipped`。Ruff／文字污染
  `360 / 562`、compileall、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5` 與 `git diff --check` 均通過。
- executable plugin 預設仍關閉，沒有啟動 production MOD、修改 SQLite schema／runtime protocol／
  版本號、stage、commit、build、封裝、簽署、發布或 push；35.0 保持未提交且 `SAFE_MODE`。

**G35-02D 驗證證據（2026-07-19）**：

- Installer／updater／rollback／restore 在 mutation 前使用 bounded candidate graph，dependency fanout
  超過 `64` 時先於逐 ID registry query 拒絕；rollback／restore／recovery 使用 `256 KiB` bounded
  manifest、core compatibility／fresh trust Gate、post-move signed-directory reverify 與可回復補償。
- Lifecycle path 共同 Gate 已在 updater／maintenance／rollback／cleanup／recovery mutation 前拒絕 traversal、symlink、junction／reparse point 與 MOD root
  escape。restore 若 post-move 驗證與即時補償皆失敗，下次 startup 會把 exact stranded candidate
  移回 quarantine 並保留 `REMOVE`；post-move／registry failure、swap-back fail-once 均有二次收斂回歸。
- 正常 startup 與 UPDATE／ROLLBACK transaction recovery 採 dependency-first；未完成 toggle 採
  dependent-first stop，無法確認 dependent 已停止時阻擋 dependency。Supervisor 只接受 Manager 已提交
  且 identity 完全一致的 `ENABLE` claim，沒有公開 start 入口。
- Publisher trust revoke 先 `stop_all`，再以 exact record 停用被撤銷 publisher 的 plugin；跨 publisher
  dependent 不自動改設定，後續 startup 會因 dependency disabled 而阻擋。最終相關 15 檔非 UI
  targeted suite `175 passed`；新 path fix 的直接 updater／cleanup／recovery suite `40 passed`，其中
  cleanup／recovery 4 個 regression 修正前為 `4 failed`、修正後轉綠。原發現者重審相同 mutation
  邊界後明確判定 `NO UNRESOLVED P0/P1`。
- 非阻擋 P2：全域 `stop_all` 後其他 publisher 的 enabled registry 狀態不代表 runtime 仍在執行；
  install／update 的 disabled candidate 尚未比照 rollback／restore 做立即 post-move reverify；Supervisor
  仍在 executable plugin 預設關閉的 dormant 路徑重新讀取 manifest。這些限制不降低 fail-closed enable
  Gate，但須在日後重新開啟 executable plugin 或調整信任協調前處理。
- 本項未 stage、commit、build、建立 EXE／Testing／Stable、簽署、發布或 push；35.0 保持未提交且
  維持 `SAFE_MODE`。

**G35-02E 驗證證據（2026-07-19）**：

- MOD developer guide、README、ownership、change inventory 與 release 邊界已同步；目前來源身分
  依 material delta 規則更新為 Development 35.0／核心 35.0.0，但未建立版本資料夾或產物。
- 最新完整 Repository 安全測試入口為 `1212 passed, 7 skipped`；G35-02D 相關 15 檔 targeted
  suite `175 passed`，直接 updater／cleanup／recovery path suite `40 passed`。
- Ruff／文字污染 `360 / 563`、compileall、MOD group `8 / 4`、網站 `13 / 42 / 56`、依賴鎖
  `10`、版本文件 `4`、保留版本 `5` 與 `git diff --check` 均通過。
- 一次誤用廣域 compileall 在 `Version/` 產生 607 個 CPython 3.14 快取；確認全部為同輪、
  無 reparse、未列入 checksum 後，只移除精確快取與 566 個空 `__pycache__`，再以 scoped
  compileall 及保留版本稽核證明 `Version` 快取為 0、5 個保留版本全數通過。
- executable plugin 仍預設關閉；沒有啟動 production MOD、stage、commit、source freeze、build、
  建立 EXE／Testing／Stable、簽署、發布或 push。35.0 保持 `SOURCE ONLY / SAFE_MODE`。

**Compatibility／Migration**：manifest schema v2、runtime protocol 1.0、簽章、TrustStore 檔案格式與
capability payload／permission 規則不變；Supervisor 發出的短期 token 現在會在 stop／補償時立即撤銷。
malformed TrustStore 型別與 stale cache 改為 fail closed。dependency 仍只表示
plugin ID，不新增版本約束。沒有 UserData schema migration；既有
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
依賴／版本稽核與 `git diff --check` 後，才可完成 G35-02。G35-02A～D 已完成上述相符 targeted
驗證；G35-02E 的完整 Repository tests、文件同步與 Shared DoD 亦已完成。

- **Exit Gate**：`DONE / SOURCE ONLY / SAFE_MODE`。上述可重現資料／生命週期 P0／P1 缺口均關閉，
  離線 operator 測試與完整 Gate 已完成；executable plugin 仍預設關閉，不宣稱已啟用外掛執行。

## 36.0｜非特權契約的加法相容

**Status**：`DONE / SOURCE ONLY / SAFE_MODE`。六個列名 DTO 的 exact-key compatibility 缺口已
由 failing regression 重現並完成最小修正；特權契約 strict boundary 亦完成獨立重審。

- **Goal**：舊 core 可安全讀取含 benign 新欄位的 discovery／history／recovery／provider failure
  結果，不因精確 key set 拒絕整筆資料。
- **Scope**：只限非特權 result DTO；manifest、capability、路徑、簽章與其他安全 payload 保持 strict。
- **Priority**：P1；必須在 UI 或跨 provider 擴充前完成。
- **Verified gap／Unknown**：六個 V1 DTO 加一個 benign field 均會因 exact key set 拒絕；
  `ProviderFailureV1` 因解析失敗還會把明確 `RATE_LIMITED / retryable=true` 降級為不可重試的
  `PROVIDER_ERROR`。另發現已簽章 capability token claims 會忽略未知特權欄位。沒有已發布
  predecessor 的 DTO，因此沒有捏造 v0 fixture。
- **Dependencies**：G35 完成、現有 schema v1 fixture 與 payload 大小上限。
- **Approach**：比較兩案：A）維持 exact key 並每次升 schema；B）只對逐一列名的
  `DiscoveryItemV1`、`HistoryEventV1`、`HistoryPreferencesV1`、`RecoveryPlanV1`、
  `RecoveryCandidateV1` 與 `ProviderFailureV1` 接受有界 extra keys。採 B，以取得前向加法相容；
  共用 helper 限最多 8 個 extras、64-byte ASCII lower-snake key、單值 4 KiB、合計 32 KiB、
  深度 4、節點 64 與整體 compact JSON UTF-8 1 MiB。`schema`／各版本名稱與非公開命名保留；
  extras 驗證後丟棄。相容矩陣只涵蓋 current／additive／unknown major，沒有不存在的 predecessor。
- **Compatibility**：missing required、unknown schema、non-JSON、non-finite 與 oversize 仍 fail closed；
  writer 只輸出 current schema。history／recovery 內嵌 discovery item 使用相同 reader。
- **Breaking Change／Migration**：無 UserData、manifest、runtime protocol 或 API migration。既有 provider
  IPC 已有約 1 MiB 外框；direct decoder 現同步 fail closed，超過界線的非契約輸入不再接受。
- **Risk**：加法政策擴張到特權契約，或 extras 影響 current fields。helper 只由六個列名 DTO 匯入，
  dataclass 使用 current-only construction；capability claims 改為 exact key，其他特權 parser 不變。
- **Rollback**：逐 DTO 回復 parser policy；資料格式與 UserData 不需遷移。
- **Validation**：新回歸先得到 `12 failed, 30 passed`，固定六 DTO additive、巢狀 discovery、
  1 MiB payload、provider retry semantics 與 signed capability claims strict 缺口；修正後相關核心組
  `87 passed`，allowlist／strict-control 組 `73 passed`。升版前完整 Repository 為
  `1255 passed, 7 skipped`；最終 Shared DoD 證據記於下方 Exit Gate。
- **Exit Gate**：`DONE / SOURCE ONLY / SAFE_MODE`。六個列名 DTO 有一致政策與 regression，特權
  capability／manifest unknown field 仍拒絕；material delta 已同步為 Development 36.0／核心
  `36.0.0`，未建立版本資料夾、stage、commit、source freeze、build、EXE、簽署、發布或 push。

**G36-01 驗證證據（2026-07-19）**：

- 回歸先得到 `12 failed, 30 passed`，最小修正後核心 targeted 契約組為 `87 passed`，allowlist 與
  capability／manifest strict-control 組為 `73 passed`；兩次獨立重審均未發現 runtime P0／P1。
- 36.0.0 同步後完整 Repository 為 `1255 passed, 7 skipped`；Ruff／文字污染 `363 / 566`、
  MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall、
  Version `.pyc` 零污染與 `git diff --check` 均通過。
- 所有測試使用 `tools.run_tests` 與 Repository 外的 invocation-unique temp root；沒有 raw pytest、
  broad `tmp*` ignore、外部網站、production 身分、使用者資料刪除或歷史版本寫入。

## 37.0｜條件式原生崩潰與 provider 失敗證據

**Status**：`DONE / EVIDENCE READY / NO CLAIM / SOURCE ONLY / SAFE_MODE`。既有 run ID、error code、
redaction、原子匯出、provider exit 與 WER runbook 已完成 source-only Gate；沒有可重現 native crash，
不得宣稱 root cause 或修復。

- **Goal**：不蒐集敏感資料的前提下，取得足以定位 ANI／provider／runtime 原生失敗的證據。
- **Scope**：沿用既有 self-check `run_id`、ProviderFailure 穩定 error code 與 redaction；只補
  WER module／offset 手動採證 runbook，以及與既有 run ID 對應的有界證據欄位。
  不建立第二套診斷匯出系統，也不重新實作已存在的 correlation／error code。
- **Priority**：P1；若 `0x80000003` 或同類 native crash 再現，該重現與回歸立即升為 P0。
- **Verified gap／Unknown**：run ID 與 ProviderFailure error code 已 `ABSORBED`；failing regressions
  證實 Authorization／Cookie（含 quoted key）、URL userinfo、私人 absolute path、structured provider
  failure 與 legacy queue error 可穿透舊 redaction，固定 sibling `.tmp` 不具唯一 ownership，且 no-result
  error 缺 exit metadata。另一次 full-suite queue restart 空 snapshot 與 transient open/read OSError 路徑
  高度相符，已用 deterministic PermissionError regression 關閉；provider `exit_code=1` 的間歇成因與
  native crash root cause 仍未知。
- **Dependencies**：G36 契約政策、既有去識別 self-check、合法且使用者控制的重現環境。
- **Approach**：先保存 symptom／trigger／module／offset／run ID，再依證據修 root cause；沒有重現時
  只完成 runbook 與格式，不猜測已修復。
- **Compatibility**：診斷欄位採 additive schema 或明確升版，舊 consumer 仍可讀必要欄位。
- **Breaking Change／Migration**：無；診斷資料只採 additive output，不遷移 UserData。
- **Risk**：本機路徑、Cookie、token、媒體內容或 dump 外洩；過度脫敏亦可能失去診斷價值。
- **Rollback**：停用新增證據欄位與入口；不變更或刪除原始 UserData。
- **Validation**：secret corpus、私人 Windows 路徑、大小上限、原子輸出、無網路／無背景程序副作用。
- **Implementation evidence**：新增 strict `DiagnosticEvidenceV1` 並以 additive
  `diagnostic_evidence` 附加於既有 schema 1 self-check；provider stderr／structured failure 與 queue
  error 採 UTF-8 有界 redaction，no-result error只增加 phase／exit code／reader state，不改 retry 或
  失敗語意；queue restore 以單一 bounded binary open 讀取並對 transient OSError 有界重試；唯一 owned
  temp 原子匯出與 [WER runbook](native-crash-evidence-runbook.md) 已完成。修正前核心組為
  `4 failed, 78 passed`，contract／writer 入口為 collection error；獨立審查再重現並關閉 exact-type、
  quoted／structured secret、URL userinfo、queue restore 與 provider stderr drain regressions。最終 G37
  targeted 為 `112 passed`，完整 Repository 為 `1278 passed, 7 skipped`；Ruff／文字污染
  `365 / 570`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  scoped compileall、Version `.pyc` 零污染與 `git diff --check` 均通過。
- **Exit Gate**：`DONE / EVIDENCE READY / NO CLAIM / SOURCE ONLY / SAFE_MODE`。runbook、證據契約、
  redaction／persistence regressions 與 Shared DoD 已完成；不宣稱 0x80000003 或未知 provider exit 1
  已修復，未 stage、commit、source freeze、build 或封裝。

## 38.0｜四語與人工可存取性 Gate

**Status**：`ACTIVE / G38-01 P1 FIXES VALIDATED / MANUAL REVALIDATION BLOCKED / SAFE_MODE`。
無頭自動基線已重驗；後續 source review 找到並紅→綠修正兩個 deterministic P1。真實焦點、
讀屏、高對比與四語人工矩陣沒有授權或環境；UI 證據採截圖優先且禁止自動互動，因此保持
`MANUAL REVALIDATION BLOCKED`。

來源身分已同步為 `38.0.0`；目前 35.0～38.0 核准變更已由
`6534e3f5ebcc3e3c459a34a335e2b176b2cd1107` 完成 Development 38.0 source freeze，且唯一一次
SAFE_MODE 未簽署候選包已建立於 `Version/Development/38.0`。這不解除本節人工 Exit Gate。

- **Goal**：關閉目前自動化完成、人工阻擋的可用性缺口，再固定近最終 UI 供後續量測。
- **Scope**：940×620 全工作區、Tab order／focus、accessible name、NVDA／讀屏、高對比、深色表面、
  zh-TW／zh-CN／en／ja 與 SAFE_MODE／provider blocker 呈現；不做無關視覺重設計。
- **Priority**：P1；Development candidate 前轉為 P0 Gate。
- **Verified gap／Unknown**：`QTreeView` 既可 `StrongFocus` 聚焦又被 `outline: none` 移除預設
  指示，且無替代 focus 樣式；安全 badge 的 explicit accessible name 也固定為「安全狀態」，
  沒有包含實際 NORMAL／SAFE_MODE／BLOCKED 狀態，原因只在 tooltip。兩項已修正；仍未知
  真實 Tab order／visible focus、UIA／NVDA 朗讀、OS 高對比與四語全頁結果。使用者提供的
  Development 37.0 截圖另固定為 AniGamer pre-fix baseline：內嵌 Qt WebEngine 缺少本機
  H.264／AAC 或可用 HLS／MSE 播放路徑，而集數 provider 遇到官方 403／瀏覽器驗證時按既有
  安全政策降級到手動官方單集網址；這兩者是獨立限制。
- **Dependencies**：可啟動的 Qt 環境與人工讀屏／四語驗收者。
- **Approach**：固定人工矩陣；UI 驗證採「截圖優先、禁止自動互動」，只修可重現失敗項並為
  每個修正補最小自動 regression。截圖只驗證可見版面、裁切、文字、色彩與可見焦點，不替代
  Tab／Shift+Tab 行為、UIA／NVDA／讀屏或 Windows OS 高對比人工證據。
- **Compatibility**：action／object ID 不變；翻譯鍵 additive 且有安全 fallback。
- **Breaking Change／Migration**：無；UI 修正不得改公開 action ID 或資料格式。
- **Risk**：人工判定不一致，或四語文字長度造成版面裁切。
- **Rollback**：逐項回復 UI 差異；不回退資料 schema。
- **Automated evidence（2026-07-19）**：兩組精準 `tools.run_tests` 目標合計 `58 passed, 0 skipped`；
  quality audit `ruff_files=366 / text_files=571`、MOD group audit `8 groups / 4 locales`、site audit
  `13 sites / 42 features / 56 workflows` 均 PASS。未啟動可見 GUI、瀏覽器或外部網站。
- **P1 regression evidence（2026-07-19）**：舊樣式在 tree focus contract 得到 `1 failed`；
  舊 badge 在實際 offscreen widget 得到 `1 failed`（「安全狀態」不等於「安全狀態：安全模式」）。
  修正後 tree 使用 `2px #6f8dff` focus border，badge 名稱包含狀態且 description 包含
  有界原因；`test_ui_scale.py` 與 `test_main_window_presentation.py` 合計 `12 passed`，
  post-fix 完整 Repository 為 `1279 passed, 7 skipped`。
- **AniGamer evidence（2026-07-19）**：新增「選取作品→集數 provider 回報
  `ani-gamer-browser-verification-required`→空表與官方網址 fallback→貼上 canonical
  `animeVideo.php?sn=49944`→建立一筆單集與作品 context」完整回歸；既有 production path 無需
  修改即通過，判定 `EXPECTED LIMITATION / NO NETWORK POLICY CHANGE`。另以 fake WebEngine 的
  offscreen regression 固定系統瀏覽器 fallback 位於 WebView 上方，保留 primary、stable control ID
  與 accessible name；AniGamer targeted suite 為 `60 passed, 1 skipped`，本輪完整 Repository
  Gate 為 `1281 passed, 7 skipped`。
- **AniGamer safety boundary**：本輪沒有實作 Cookie 匯入、播放串流／媒體端點攔截、codec 下載，
  或 DRM、廣告、登入、Cloudflare／瀏覽器驗證、付費與地區限制繞過。系統瀏覽器主操作可見性
  修正不構成內嵌 H.264／AAC／HLS／MSE 播放已修復的宣稱。
- **Automated coverage boundary**：已覆蓋 940×620 宣告基線、部分核心面板 accessible name、
  深色 palette／文字對比、四語資源契約與 SAFE_MODE／provider blocker 純呈現；不代表實際
  focused widget、Tab 行為、UIA／NVDA 朗讀、OS 高對比或四語全頁裁切已驗證。Development 37.0
  使用者截圖不是 G38 post-fix 證據。
- **Package evidence（2026-07-19）**：runtime policy `valid=true / checked=6`，Development 38.0
  的 116 筆 checksum 全部通過；copied-folder `38.0 → 32.1 → 38.0` 的 9 個 CLI/headless 命令
  皆 exit 0，`rollback=true / source_unchanged=true / process_tree_safe=true`。EXE 為
  `NotSigned`；報告未保存精確 SAFE_MODE stdout，因此不啟動或完成 G40，也不替代人工 UI。
- **Validation**：既有 UI tests 加實際尺寸、鍵盤、focused widget、讀屏、高對比與四語證據。
- **Exit Gate**：人工矩陣實際完成；環境缺失時保持 `MANUAL BLOCKED`，headless 測試不能代替。

## 39.0｜量測式效能與資源預算

**Status**：`WAITING / MEASUREMENT GATED / READ-ONLY INVENTORY DONE`。G38 人工 Gate 未完成，
因此本輪只盤點既有上限與可重現 workload，並執行不產生效能宣稱的純本機 constraint
preflight；未轉為 `ACTIVE`，未實作 benchmark 或最佳化。

- **Goal**：用固定 workload 找出真正瓶頸；沒有量測證據時不以複雜度換取推測性最佳化。
- **Scope**：大量搜尋結果、縮圖 cache／pending、佇列刷新、取消後 thread／handle 與本機暫存；
  不加入遙測、背景預取或無上限並行。
- **Priority**：P1；排在 UI 結構與人工 Gate 穩定之後，避免量測重做。
- **Verified gap／Unknown**：既有資源上限與取消清理列為 `ABSORBED`；目前尚無量測證據證明
  特定 bottleneck，先做 baseline，不承諾最佳化或效益。
- **Read-only inventory（2026-07-19）**：已有可重用 workload 包含 250 筆搜尋結果上限、
  1,001 筆 queue persist／restore、queue shutdown／thread cleanup、有界本機掃描／artwork cache，
  以及縮圖 1 MiB response、16 MP、40 cache／32 pending／8 s timeout 上限。正式 queue 上限為
  10,000 tasks／16 MiB state，但現有 tests 尚未 exact 斷言這兩個上限。
- **Constraint preflight（2026-07-19）**：精準 `tools.run_tests` 目標驗證搜尋分頁上限、
  1,001-task round-trip、shutdown／requeue、本機掃描／cache 與縮圖常數，結果
  `7 passed, 1 skipped`；skip 為既有 symlink 平台條件。這只是功能／資源界線證據，不是
  performance baseline。
- **Instrumentation gap**：Repository 內無 benchmark CLI／psutil／pyperf／pytest-benchmark，
  `tools.run_tests` 也不收集 p50／p95、RSS／tracemalloc peak、Windows handle／thread delta 或 temp peak；
  現有 suite duration 與 pass count 不得當作效能 baseline。
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
- **Verified gap／Unknown**：Development 38.0 的 pinned runtime、checksum 與 copied-folder
  current→previous→current 已實測通過；仍缺精確 SAFE_MODE stdout 證據與 Stable CLI wiring。
  EXE 為 `NotSigned`，正式簽署身分仍未知。
- **Dependencies**：G34～G39 與正式 runtime；本次單一 Development 38.0 打包授權不啟動 G40，
  也不跨越 G38／G39。Stable-only G40-02 另依賴
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
