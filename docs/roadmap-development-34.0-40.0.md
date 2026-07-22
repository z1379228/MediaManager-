# Development 34.0～40.0 唯一版本更新計畫

狀態：`CANONICAL / 34.0 SOURCE-FROZEN / 35.0～37.0 EXIT GATE DONE / SOURCE ONLY / G38-01 BASELINE FROZEN + MANUAL BLOCKED / G38-02 CLOSED + REMOVED / G39-01 MEASURED + NO RELEASE / G39-02～G39-06 SOURCE VALIDATED + NO PACKAGE / G39-07 39.0.5 SOURCE-FROZEN / G39-08 39.0.6 SOURCE-FROZEN / G39-09 39.0.7 SOURCE VALIDATED + SOURCE FREEZE WAITING / G40-01 BUILD BLOCKED / SAFE_MODE`
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
regression 證實、修正焦點指示與安全 badge 讀屏名稱兩個 material P1；G38-01 現已固定為
不可覆寫的 Development 38.0 基線，人工矩陣仍為 `MANUAL REVALIDATION BLOCKED`。2026-07-19
使用者另行授權同步來源身分為
38.0.0，並明確授權將目前 35.0～38.0 核准變更 stage、本機 commit、固定為 Development 38.0
source freeze，再建立一次 Development 38.0 SAFE_MODE 未簽署候選包；這不包含 Testing／Stable、
簽署、發布、push 或覆寫歷史版本授權。打包只可使用該 source-freeze revision，其他版本不得平行啟動。
source freeze `6534e3f5ebcc3e3c459a34a335e2b176b2cd1107` 與唯一一次 Development 38.0
打包現已完成；產物位於 `Version/Development/38.0`。後續 G38-02 曾以 38.1.0～38.1.14
處理動畫瘋來源缺口；使用者於 2026-07-22 決定移除該整合，38.1.15 因而成為
`SOURCE VALIDATED / ANI-GAMER MOD REMOVED / NO PACKAGE / SAFE_MODE`，G38-02 關閉且不覆寫
Development 38.0。G39-01 measurement baseline 已完成且沒有可證 bottleneck，判定為
`MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE`。後續使用者明確要求本機 Format Factory 類能力，
且 `image-png` 可重現為 unsupported preset，故啟動唯一 G39-02／Development 39.0.0 工作；第一
工作包與完整來源 Gate 已完成。2026-07-22 使用者以明確新需求取代 Gopeed／P2P 的 deferred
判定，故啟動唯一 G39-04／Development 39.0.2 工作包。後續官方 Gopeed OpenAPI 契約稽核
  證實 create／resolve request 多送未接受的 `rawUrl`，因此啟動單一 G39-05／Development 39.0.3
  相容修正。後續 39.0.3 人工截圖證實 Gopeed／P2P 設定 card 在有限高度下被壓扁重疊，故啟動
  單一 G39-06／Development 39.0.4 版面修正。正式版候選評估再證實 Stable 公開身分錯用核心號、
  build 後立即 stage 沒有 Authenticode 窗口，故啟動 G39-07／Development 39.0.5；其來源修正與
  Gate 已完成。使用者於 2026-07-23 明確授權 stage、本機 commit 與 Development 39.0.5 source
  freeze；build、EXE、Testing／Stable、簽署、發布、上傳與 push 未授權。後續唯讀整理證實
  `Version` 中存在含 UserData 的舊版本，且 Repository 沒有對應的失敗優先清理工具，
  因此啟動唯一 G39-08／Development 39.0.6。使用者於 2026-07-23 明確授權其 stage、
  本機 commit 與 source freeze；G40-01 因而恢復 build waiting，仍缺 staged candidate／
  headless SAFE_MODE 證據。後續 production Ed25519 私鑰已在 Repository 外建立，公開
  key ID／public key 則形成唯一 G39-09／Development 39.0.7 material trust-identity delta；
  39.0.7 尚未取得 stage／commit／source-freeze 授權，因此 G40-01 暫回 build blocked。

## 目標與非目標

- **Goal**：以資料安全、相容性、可診斷性、人工可用性、量測證據及發行完整性的順序，
  把目前工作樹收斂到可驗證的 Development 40.0 候選決策點。
- **Scope**：只處理下表已由程式碼或既有阻擋證明的缺口；每版先做 baseline，再做最小修正。
- **Non-goals**：35.0～40.0 不新增網站、通用解析器、雲端帳號、遙測或自動上傳，也不繞過
  DRM、登入、Cloudflare、廣告、付費或地區限制。Gopeed／P2P 只限 G39-04 明列的本機外部
  Bridge、明確使用者提交與安全邊界；動畫瘋整合已移除；
  不得把退役網址重新接到 Direct HTTP、通用 provider、Cookie／profile、串流或下載路徑。
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
  `SAFE_MODE` stdout。Stable split-phase build-only／stage-built 已完成來源與模擬失敗驗證；
  production Ed25519 公開身分已編入 39.0.7，私鑰維持 Repository 外；production
  Authenticode、實際簽署候選及正式 preflight 尚未完成。

### Assumptions

- 35.0～39.0 是 evidence milestone，不保證各自建立附件；只有 material delta 才同步版本身分。
- 先固定人工 UI，再量測近最終 UI，可避免先最佳化後因版面修正重做。

### Unknowns

- 後續 39.0.7 source-freeze／build 授權與 production Authenticode 身分尚未取得。
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
7. G38-01 人工矩陣仍個別保持 `MANUAL BLOCKED`；G38-02 已由明確 scope 決策關閉並移除。
   G39-01 已保存固定 workload measurement baseline；沒有可證瓶頸，故以
   `MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE` 完成。G39-02 只實作有 failing regression 的
   本機格式工廠工作包；參考產品本身不構成 scope。G39-08 只建立預設 dry-run，
   並對 Stable／UserData／link-like 邊界 fail closed。G39-09 只編入非秘密 production Ed25519
   公開身分；在 39.0.7 source freeze 前，G40-01 保持 `BUILD BLOCKED`，
   不得以[參考軟體功能矩陣](comparable-software-options.md)自動跨 Gate。

## 依賴執行順序與版本內 Priority

| 排名 | 工作 ID | 版本／Priority | 狀態 | 唯一成果與 Gate |
|---:|---|---|---|---|
| 1 | G34-01 | 34.0-P0 | `DONE / SOURCE-FROZEN` | VUP-34-02 已完成；核准範圍由兩個本機 commit 固定，最終 freeze revision 維持 clean。 |
| 2 | G35-01 | 35.0-P0 | `DONE / ABSORBED INTO G34 SOURCE FREEZE` | 設定檔 typed decode、future fail-safe、併行 patch 與回復工具已作為 G34 freeze blocker 完成。 |
| 3 | G35-02 | 35.0-P0 | `DONE / SOURCE ONLY / SAFE_MODE` | graph、bounded lifecycle journal、candidate transaction、Supervisor ownership、topological recovery、文件、完整 Repository tests 與 Shared DoD 均完成；後續納入 Development 38.0 source freeze，未建立 35.0 候選包。 |
| 4 | G36-01 | 36.0-P1 | `DONE / SOURCE ONLY / SAFE_MODE` | 六個非特權 result DTO 使用一致、有界且丟棄 extras 的加法 reader；安全契約繼續 strict。 |
| 5 | G37-01 | 37.0-P1 | `DONE / EVIDENCE READY / NO CLAIM / SOURCE ONLY / SAFE_MODE` | 去識別證據契約、provider exit metadata、queue／self-check 邊界與 runbook 已完成；未宣稱原生 crash 或未知 exit 1 已修復。 |
| 6 | G38-01 | 38.0-P1 | `DONE / PACKAGE BUILT / MANUAL MATRIX REMAINS BLOCKED / SAFE_MODE` | source freeze `6534e3f…1107` 與未簽署 Development 38.0 包已完成；runtime 6/6、116 筆 checksum 與 copied-folder 回退通過。此包固定為 G38-02 前基線，不得覆寫。 |
| 7 | G38-02 | 38.1.15-P1 | `CLOSED / CANCELLED BY USER SCOPE DECISION / REMOVED / NO RELEASE` | 38.1.14 為 `SOURCE VALIDATED / SUPERSEDED BY 38.1.15 / NO PACKAGE`。38.1.15 從目前來源移除動畫瘋 MOD／UI／runtime 註冊，保留 UserData 與歷史證據；不產生套件，也不重新接到通用下載路徑。 |
| 8 | G39-01 | 39.0-P1 | `MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE` | `queue-roundtrip-v1` 以 1,001 tasks／4 workers、2 warmups／20 iterations 完成；persist／restore／total p95 分別為 `219.921 / 240.687 / 482.475 ms`，tracemalloc peak 最大 `20,146,560 bytes`、temp `912,806 bytes`、handle／thread delta 最大 `0`、殘留 download threads `0`、cleanup `true`。未證明 material bottleneck。 |
| 9 | G39-02 | 39.0.0-P1 | `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE` | 既有、預設停用的 Media Convert 新增 PNG／JPEG／WebP 靜態影像 preset、輸入副檔名 Gate、UI／automation wiring、本機 protocol／linklike 路徑 Gate 與 64 KiB 去識別 FFmpeg stderr。RED `4 failed`；完整 runner `1222 passed, 7 skipped`，含實際 FFmpeg BMP→PNG smoke。文件、受保護光碟、雲端 fallback 與未知第三方 binary 排除。 |
| 10 | G39-03 | 39.0.1-P1 | `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE` | 本機格式工廠第二工作包：已補 FFmpeg build／formats／encoders／filters／hwaccels 能力探測、磁碟 preflight 與提交前 ffprobe 驗證。只處理本機工具與本機輸出，不加入新 binary、網路 fallback 或發行操作。 |
| 11 | G39-04 | 39.0.2-P1 | `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE` | 新增 localhost-only Gopeed Bridge／P2P Transfer、Speech optional runtime dependencies、格式工廠固定 preset 與新 profile MOD 預設；非 UI `1007 passed, 6 skipped`、最終安全邊界 `43 passed`，全部來源 Gate 通過。 |
| 12 | G39-05 | 39.0.3-P1 | `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE` | 移除 Gopeed 官方 `Request` schema 不接受的 `rawUrl`，以 exact request-body regression 鎖定 direct create 與 P2P resolve 共用 payload；非 UI `1011 passed, 6 skipped`，不擴張 transport scope。 |
| 13 | G39-06 | 39.0.4-P1 | `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE` | 人工截圖證實 Gopeed／P2P 工作區在有限高度下壓扁設定 card；加入 `workspaceScroll` 與 minimum-size layout contract，空間不足時垂直捲動而不重疊。非 UI `1012 passed, 6 skipped`；修正版人工截圖待確認。 |
| 14 | G39-07 | 39.0.5-P0 | `SOURCE-FROZEN / NO PACKAGE / SAFE_MODE` | Stable 公開身分與 UI display 固定為獨立 1.0.0／「正式版 1.0」；release operator 拆成 receipt-bound build-only 與 Authenticode `Valid` 後 stage-built。display RED `1 failed, 3 passed`、精準封裝／版本 GREEN `45 passed`、非 UI `1019 passed, 6 skipped`；2026-07-23 已授權 stage、本機 commit 與 source freeze，未實際 build、簽署或 push。 |
| 15 | G39-08 | 39.0.6-P0 | `SOURCE-FROZEN / NO PACKAGE / SAFE_MODE` | 建立預設 dry-run 的本機版本歷史整理計畫；至少保留兩版且包含 publish-ready Stable，UserData、link-like、意外目錄或計畫後變更均 fail closed，apply 另需 exact confirmation 並重驗完整計畫。RED 為缺少模組的 collection error，精準 GREEN `9 passed`、非 UI `1029 passed, 6 skipped`；2026-07-23 已授權 stage、本機 commit 與 source freeze，未實際刪除。 |
| 16 | G39-09 | 39.0.7-P0 | `SOURCE VALIDATED / SOURCE FREEZE WAITING / NO PACKAGE / SAFE_MODE` | production Ed25519 私鑰在 Repository 外建立；只把公開 key ID／raw public key 編入來源，並以 RED→GREEN 回歸要求合法 key ID 與 32-byte public key。精準 `27 passed`、非 UI `1030 passed, 6 skipped`，來源 Gate 通過；尚未 stage、commit、source freeze、build、Authenticode 或候選簽署。 |
| 17 | G40-01 | 40.0-P0 | `SOURCE FREEZE WAITING / BUILD BLOCKED` | source-only verify-only 已有精確 SAFE_MODE stdout；39.0.7 是目前 material trust-identity delta，必須先固定 clean revision。build／candidate、EXE、Testing／Stable、簽署、發布、上傳與 push 仍須逐項明確授權。 |

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

**Status**：`BASELINE FROZEN / PACKAGE BUILT / MANUAL REVALIDATION BLOCKED / SAFE_MODE`。
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
- **AniGamer safety boundary**：G38-01 基線沒有實作 Cookie 匯入、播放串流／媒體端點攔截、codec 下載，
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

### G38-02｜動畫瘋整合（已關閉並移除）

**Status**：`CLOSED / CANCELLED BY USER SCOPE DECISION / REMOVED IN 38.1.15 / NO RELEASE / SAFE_MODE`。
Development 38.0 是不可覆寫的 source-freeze 與套件基線；G38-02 的 38.1.0～38.1.14
內容保留為歷史來源證據。38.1.14 已標記
`SOURCE VALIDATED / SUPERSEDED BY 38.1.15 / NO PACKAGE`；38.1.15 為
`SOURCE VALIDATED / ANI-GAMER MOD REMOVED / NO PACKAGE / SAFE_MODE`。未 stage、commit、freeze、
build、package 或 push，也不得回寫 `Version/Development/38.0`。

**Closure contract（2026-07-22）**：目前來源不再註冊動畫瘋父 MOD、目錄搜尋、集數導覽、
相容性播放器、session Cookie 或離線索引 UI。既有 UserData、歷史紀錄與使用者自行選取的本機
媒體保留；舊 `ani-gamer*` 設定只作已退役未知 ID，不能使啟動失敗或重新啟用功能。動畫瘋網址
不得改接 Direct HTTP、yt-dlp、ffmpeg 或其他 generic adapter。Rollback 是回復 38.1.14 的完整
來源差異與測試／文件，不是覆寫歷史成品或刪除使用者資料。

**38.1.15 validation（2026-07-22）**：完整 repository runner
`1201 passed, 6 skipped in 78.10s`；quality audit 為 Ruff `355`／文字 `549`，MOD 群組
`7 / 4`、網站矩陣 `12 / 33 / 49`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外
compileall、來源 `.pyc` 零污染與 runtime 零動畫瘋註冊均通過。live provider smoke 因缺少
bundled Deno／FFmpeg 為 `WAITING / 0 passed, 7 failed`，不作外部網站成功宣稱；stage、commit、
freeze、build、package、sign、publish 與 push 均未執行。

**Post-removal completion audit（2026-07-22）**：目前 root 工作樹的 catalog、integrity、
capability、optional workspace 與 site routing 均無動畫瘋 runtime 註冊；Direct HTTP 保留
`gamer.com.tw` deny rule，這是防止通用下載器退化成網站 extractor 的安全邊界，不是功能殘留。
TODO／FIXME／HACK／NotImplemented 與 xfail 均為 `0`；G39／queue／recovery／subprocess critical
subset 為 `98 passed, 1 skipped`，使用不可覆寫 Development 38.0 內既有 FFmpeg／ffprobe 的純本機
conversion 與 Bilibili MKV／ASS mux smoke 為 `2 passed`。沒有可重現的 failing regression 或
material delta，故不建立新版本或 `ACTIVE / IN_PROGRESS` 工作。此結論只適用目前工作樹：刪除仍
未 staged，Git `HEAD`、忽略的舊 `build/`／`dist/` 與保留的 Development 38.0 仍可能獨立包含舊整合；
它們不得作為目前來源或新候選，也不授權刪除使用者資料、stage、commit、freeze 或 build。

下列內容只保存 38.1.0～38.1.14 的歷史 Goal、Scope、失敗證據與安全界線；不再具有執行權。

- **Goal**：先讓使用者可以穩定進入動畫瘋官方播放頁並正常播放；其後只在網站明確授權、
  不需擷取播放中串流的前提下評估離線影片；最後才評估官方公開彈幕。
- **Scope / Priority**：
  1. **P1-A 官方播放**：系統瀏覽器是主要成功路徑，使用瀏覽器自己的登入與 Cookie。內嵌
     Qt WebEngine 只作相容性選項；允許官方頁自行播放，但 MediaManager 不注入腳本讀取頁面、
     不開 DevTools、不裝 request interceptor，也不攔截或保存播放串流。缺少 H.264／AAC 或
     HLS／MSE 路徑時，明確凸顯系統瀏覽器，不把內嵌黑畫面宣稱為播放成功。
  2. **P1-B 作品／集數與 session Cookie**：只接受使用者主動貼上的 HTTP Cookie header body，
     只在本次程式工作階段記憶體保存，只送到 `https://ani.gamer.com.tw` exact host 的目錄與
     集數請求。不可匯入瀏覽器 profile／Cookie DB，不可寫入設定、佇列、歷史、離線索引、
     log、argv、環境變數或 URL；系統瀏覽器不接收這份 Cookie。`cf_clearance`、`__cf_bm`、
     `_cfuvid`、`cf_chl_*` 等 Cloudflare 驗證狀態拒絕匯入。
  3. **P2 合法離線影片**：只有官方文件或回應契約明確提供可保存的非 DRM／非廣告規避來源，
     且能以不攔截播放流的方式驗證時才實作。否則維持公開 metadata／封面與使用者自行取得
     本機媒體匯入，標記 `NO AUTHORIZED MEDIA SOURCE / BLOCKED`，不以 Cookie 或「網頁能播放」
     推論下載授權。瀏覽器、Qt WebEngine、service worker 或播放器的暫存不是下載來源，不得讀取、
     複製或重組；若日後官方契約明確提供可下載來源，只能由下載器寫入 MediaManager 自有的
     content-addressed cache，再由本機播放器讀取同一份已驗證內容。
  4. **P3 官方公開彈幕**：只接受官方公開且允許保存的 API／匯出契約；不得從 WebEngine、
     service worker 或播放 session 攔截，也不得把 Cookie 寫入 sidecar。沒有正式契約時保持
     `DEFERRED / NO AUTHORIZED PUBLIC CONTRACT`。
- **Dependencies**：可用的系統瀏覽器；動畫瘋官方頁與公開契約；Qt runtime codec 能力只影響
  選配內嵌路徑，不阻擋系統瀏覽器成功路徑。
- **Approach**：先固定「選作品→讀集數→在系統瀏覽器開啟官方單集」回歸，再加入最小、
  exact-host、session-only Cookie broker 與 provider stdin IPC；每一階段獨立紅→綠，不讓影片
  下載或彈幕需求擴張播放修正的 blast radius。
- **Compatibility**：`SearchQueryV2`、cursor、`DiscoveryItemV1`、下載佇列與離線索引格式不變；
  未設定 Cookie 時維持 Development 38.0 的公開資料與手動官方網址 fallback 行為。
- **Breaking Change / Migration**：無資料 migration；Cookie 功能預設沒有值，關閉工作區、停用
  動畫瘋 MOD、使用者清除或程式結束時撤銷。Python／Qt 的暫時記憶體副本只能承諾不持久化與
  邏輯清除，不宣稱可從 pagefile 或 crash dump 鑑識抹除。
- **Risk**：Cookie 屬敏感憑證；錯誤 scope 可能跨站洩漏。官方頁可播放仍不代表可下載，Qt codec
  缺失也不能靠 Cookie 修復。下載／彈幕若沒有官方授權契約，必須阻擋而非降低安全條件。
- **Cache architecture decision（2026-07-20，設計限定）**：播放暫存可能包含分段、廣告、短效授權、
  不完整或加密內容，且不具穩定所有權與完整性契約，因此不得轉作下載緩存。日後若官方契約
  明確提供可保存的非 DRM 來源，下載器可使用有大小上限、原子 `.part`、取消清理、內容雜湊與
  完整性驗證的應用程式自有 cache；索引、檔名與 log 不得保存 Cookie 或授權材料。這只是未來
  實作邊界，不是目前的下載授權或完成宣告，亦不觸發 38.1.1 升版。
- **Rollback**：清除記憶體 session、終止尚在執行的動畫瘋 provider、關閉相關內嵌頁並回復
  Development 38.0 的 public metadata＋system-browser fallback；不刪除使用者資料。
- **Implementation evidence（2026-07-19）**：已加入程序記憶體 Cookie store、嚴格 request-Cookie
  parser、exact-host／provider／capability 三重限制、stdin-only provider IPC、錯誤脫敏，以及停用父
  MOD／清除／關閉／shutdown 時先取消工作再撤銷。只有 `ani-gamer-search` 與
  `ani-gamer-episodes` 可取得 store；系統瀏覽器、WebEngine、下載 provider、離線保存與彈幕路徑
  均未接線。搜尋重新導向在送出前也必須仍屬官方目錄白名單。
- **Automated validation（2026-07-19）**：使用 Repository runner 與唯一、Repository 外 temp root
  執行 G38-02 相關非 UI 回歸，結果 `176 passed`。`tools.quality_audit`（Ruff 368／文字污染 573）、
  MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped
  `compileall` 與 `git diff --check` 均通過。未使用真實 Cookie、未連線官方網站，也未啟動或控制
  GUI；因此 P1-B 的來源契約已驗證，但真實連線仍為 `MANUAL WAITING`。
- **Revision validation（2026-07-20）**：來源、project metadata 與 canonical 文件已同步為 38.1.0，
  Development UI／CLI 改顯示完整三段版本；版本、entrypoint、build 與文件稽核回歸為 `37 passed`，
  CLI 實際輸出 `MediaManager 開發版 38.1.0`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall 與 diff check
  均通過；未 stage、commit、freeze 或 build，也未修改既有 Development 38.0 產物。
- **38.1.1 correction（2026-07-20）**：可重現來源路徑顯示 capability 已為 `UNSUPPORTED`／
  `UNKNOWN` 時仍只凸顯 fallback，沒有停止或隱藏 WebView；使用者截圖亦顯示內嵌黑色播放器仍
  留在畫面。純狀態回歸先因 production 缺少 presentation policy 而 collection fail，補入三態
  fail-closed mapping 後為 `3 passed`。修正後只有 `SUPPORTED` 顯示內嵌頁；其他 capability、
  load failure／timeout、probe timeout 與 renderer termination 都停止並隱藏 WebView、保留明示的
  系統瀏覽器主操作，且不呼叫 opener。Rollback 為回復此 presentation policy、callback wiring、
  相符測試與 38.1.1 身分；不影響 Cookie、provider、UserData 或既有 38.0 產物。
- **38.1.1 automated validation（2026-07-20）**：擴大 G38-02 非 GUI 回歸 `176 passed`；版本、
  entrypoint、build source 與 stage-folder 精準回歸 `28 passed`。CLI 實際輸出
  `MediaManager 開發版 38.1.1`；Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall 與
  `git diff --check` 均通過。沒有執行會建立或控制 `QApplication` 的 GUI 測試；未 stage、commit、
  freeze、build、連線官方網站或修改既有 Development 38.0 產物。
- **38.1.2 correction（2026-07-20）**：38.1.1 人工截圖證明 WebView 已隱藏，但原本
  `960×680`／minimum `700×480` 的對話框仍留下大面積深色空白，使用者合理辨識為「相容性播放
  全黑」；作品與單集按鈕又共用同一「相容性內嵌檢視」文字，無法辨識目前操作層級。純 presentation
  regression 先因 production 缺少 dialog geometry policy 而 collection fail；修正後 `SUPPORTED`
  維持 `960×680`／minimum `700×480`，`UNSUPPORTED`／`UNKNOWN` 與 load／probe／renderer fallback
  收斂為 `760×220`／minimum `560×180`，並以四語文字區分作品頁與選取單集。這不增加 codec、
  不自動開啟瀏覽器，也不攔截串流。Rollback 為回復 geometry 欄位、callback wiring、兩個新 locale
  key、相符測試與 38.1.2 身分。
- **38.1.2 automated validation（2026-07-20）**：presentation regression 在 production 尚未
  接受 geometry 欄位時先以 `TypeError` collection failure 取得 RED；修正後精準回歸
  `18 passed`，擴大搜尋／集數／session／locale／版本文件非 GUI 回歸 `80 passed`。CLI 實際輸出
  `MediaManager 開發版 38.1.2`；`tools.quality_audit`（Ruff 368／文字污染 573）、MOD `8 / 4`、
  網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped `compileall` 與
  `git diff --check` 均通過。測試使用唯一且位於 Repository 外的 temp root；未啟動或控制 GUI、
  未連線動畫瘋、未使用真實 Cookie，也未 stage、commit、freeze、build 或修改既有 38.0 產物。
  因此來源修正記為 `SOURCE VALIDATED`，但集數人工 fallback、單集 handoff 與播放仍保持
  `LIVE WAITING / NOT_RUN`。
- **38.1.3 correction（2026-07-20）**：38.1.2 新增四語作品／單集操作文字後，
  `core.downloads.builtin_integrity.BUILTIN_PROVIDER_HASHES` 仍釘選舊 locale SHA-256；bootstrap
  依安全設計拒絕 `ani-gamer` parent，截圖因此顯示 `31/32` 與「初始化失敗」。既有
  `test_pinned_builtin_integrity_matches_repository_files` 先以 stale `ani-gamer/locales/en.json`
  取得 `1 failed` RED；最小修正只同步 en、ja、zh-CN、zh-TW 四個實際 digest，不降低或停用
  完整性驗證。Rollback 為回復四個 pins 與 38.1.3 身分，但會重新安全阻擋該 MOD。
- **38.1.3 automated validation（2026-07-20）**：完整性／bootstrap／搜尋／集數／session／locale／
  版本擴大非 GUI 回歸 `91 passed, 1 skipped`；全 built-in digest 掃描 `mismatch_count=0`，直接 AniGamer verifier
  通過，bootstrap `verify_only` 回到預期 `SAFE_MODE`，唯一剩餘原因為 Development 無正式簽章。
  CLI 實際輸出 `MediaManager 開發版 38.1.3`；Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall 與 diff check
  均通過。未啟動或控制 GUI、未連線動畫瘋，也未讀取 Cookie 或敏感設定；實際 `32/32` 仍需
  完全關閉舊 38.1.2 行程、重啟 38.1.3 後以截圖確認。
- **38.1.4 correction（2026-07-20）**：兩個可重現缺口共屬 G38-02。第一，工作區 `search()`
  原本把所有非空輸入送入只接受作品／`animeRef.php` 的目錄 provider；canonical
  `https://ani.gamer.com.tw/animeVideo.php?sn=49853` 因此回報 catalog URL invalid，且單集無法進入
  下方僅限已選作品的手動流程。修正後在 provider 前只本機接受 exact-host、無 userinfo／顯式
  port／fragment／額外或重複 query、ASCII digits serial 的 canonical 單集網址，清除舊作品關聯後
  建立一筆獨立單集列；不捏造 `animeRef`，未選正式作品時作品歷史與離線保存繼續停用。第二，
  `近期熱播`、`新上架`、`所有動畫`、`人氣排序` wiring 均正常，但共同 provider 遇 Cloudflare 403
  時四者一起受阻。現在錯誤 callback 只 arm 精確 allowlist query 並提示；只有使用者再次明示點擊
  同一目錄操作才交給系統瀏覽器，點不同操作、文字搜尋、取消、成功或其他錯誤都清除狀態。
  `recent`／`new` 只安全映射官方首頁，不宣稱瀏覽器會自動定位 section。沒有自動開啟瀏覽器、
  分享 Cookie、繞過 Cloudflare 或攔截串流。Rollback 為回復 strict input helper、獨立單集列、
  second-click state、四語 keys／pins 與 38.1.4 身分；不刪使用者資料或修改既有 38.0 產物。
- **38.1.4 automated validation（2026-07-20）**：新增回歸在 production 尚無 classifier／allowlist
  helper 時先以 ImportError collection failure 取得 RED；實作後四個精準純函式／AST 回歸為
  `4 passed`，擴大且不建立 QApplication 的搜尋、集數、session、完整性、bootstrap、locale 與版本
  文件回歸為 `111 passed`。CLI 實際輸出 `MediaManager 開發版 38.1.4`；Ruff／文字污染
  `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  scoped compileall 與 `git diff --check` 均通過。原擴大清單中會建立／驅動 Qt GUI 的 layout test
  因截圖優先政策未執行；本輪也未啟動瀏覽器、連線動畫瘋或讀取 Cookie。故來源記為
  `SOURCE VALIDATED`，實際同按鈕第二擊 handoff、獨立單集列可見性、完整集數與播放均仍為
  `LIVE WAITING / NOT_RUN`。
- **38.1.5 correction（2026-07-20）**：38.1.4 的第一擊 wiring、provider error classification 與
  allowlist arm 均已執行；問題不是四個快捷按鈕同時斷線。Root Cause 是第二階段只能在非 busy
  狀態下再次點擊「完全相同 raw query」的原按鈕，介面沒有顯示哪一項已 armed 或提供獨立完成
  操作；快速第二擊會在 busy 時被忽略，改點其他快捷、重新搜尋或取消又會清除 arm，因此人工上
  不可辨識且時序脆弱。另一個可見性缺口是 canonical 單集已建立於 `episodes`，但
  `focus_episode_section()` 只捲到標題，使實際單集表留在 fold 下，看似空白。38.1.5 在
  browser-verification arm 後顯示獨立的「在系統瀏覽器開啟官方目錄」確認操作；只有使用者再點
  該明示按鈕才以原始 exact allowlist query 交給 OS，錯誤 callback 仍不自動開啟。已有單集資料時
  焦點改移到 `episode_table`，沒有單集時才回到標題。OS opener 回報失敗時仍保留明示確認操作，
  只有成功交接才清除 arm，使用者不必重跑一次 Cloudflare 失敗流程。沒有匯入瀏覽器 Cookie、繞過 Cloudflare、
  自動控制 GUI 或攔截播放串流。Rollback 為一併回復獨立確認按鈕、arm 清除／action-state wiring、
  episode-table 焦點、四語文字與完整性釘選及 38.1.5 身分；不刪使用者資料、不改寫 38.0 產物。
- **38.1.5 targeted validation（2026-07-20）**：兩個主 regression 在修正前為 `2 failed`，分別證明
  缺少明確確認操作及焦點未優先指向 populated episode table；OS opener 失敗後遺失確認操作的
  恢復性 regression 另先得到 `1 failed`。完成三項修正後，含 no-auto-open、exact allowlist、四語、
  pinned integrity、版本、entrypoint、網站與依賴契約的擴充非 GUI 組為 `47 passed`。
  `tools.quality_audit` 為 Ruff `368`／文字污染 `573`，MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖
  `10`、版本文件 `4`、保留版本 `5`、scoped compileall、CLI `MediaManager 開發版 38.1.5` 與
  `git diff --check` 均通過。這些證據不啟動或操作 GUI、不連線動畫瘋，也不證明 OS handoff、
  完整集數、播放或下載。
- **38.1.6 correction（2026-07-20）**：38.1.5 最新畫面證明快捷操作與 canonical 單集搜尋均已
  進入 handler，故不是所有按鈕 wiring 同時失效。可重現 Root Cause 有三項：direct route 清空
  上方作品表後仍保留其 220px minimum height 與三個無關作品動作，且只在 `populate_episodes()`
  前排程焦點；單集資料雖已建立，實際 row 仍在 fold 下。另「相容性檢視作品頁」把官方目錄
  送進 media WebEngine 的 H.264／AAC／HLS／MSE capability gate，產生與目錄用途無關的 fail-closed
  對話框。常駐 system-browser handoff 成功後若不清除既有 arm，介面又會殘留第二個同名確認。
  38.1.6 在 direct route 收合空作品表與三個作品動作，正常 `populate_results()` 時完整恢復；單集
  填入並選取後再排程 focus。官方目錄操作改為使用者明示點擊的 `open_official()` exact allowlist
  交接，成功才清除 arm，OS opener 失敗則保留重試。它不自動開啟瀏覽器、不讀取 browser profile
  或 Cookie、不繞過 Cloudflare／登入／廣告／DRM，也不攔截或保存串流。Rollback 為回復 result-area
  visibility、post-populate focus、catalog handoff／arm 清除與 38.1.6 身分；不刪資料、不改寫 38.0。
- **38.1.6 targeted validation（2026-07-20）**：direct visibility／post-populate focus 先為
  `2 failed`；catalog media-routing、成功 handoff state cleanup、armed exact-target 與重複同名操作
  各另為 `1 failed`。完成最小修正後六項純 AST／邏輯 regression 為 `6 passed`，擴充搜尋、集數、
  session、allowlist、locale／MOD 與版本非 GUI 組為 `105 passed`。`tools.quality_audit` 為 Ruff
  `368`／文字污染 `573`，MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本
  `5`、scoped compileall、CLI `MediaManager 開發版 38.1.6` 與 `git diff --check` 均通過。這些測試
  不建立或操作 `QApplication`、不開瀏覽器、不連線動畫瘋；實際 widget 幾何、四個快捷點擊與
  OS handoff 仍保持 screenshot-first `LIVE WAITING`。
- **38.1.7 correction（2026-07-20）**：38.1.6 人工畫面把搜尋與集數問題分離。套用介面篩選後
  「重試」重新得到 20 筆官方作品；20 是目錄 provider 的單一來源安全上限，不是先前結果未清除。
  可重現產品缺口在集數 browser-verification fallback：使用者每貼一個 canonical 官方單集網址，
  舊流程即以單元素清單取代現有集數，所以官方頁可見四個集數按鈕時，工作區仍只保留最後一列。
  38.1.7 將該操作改為 lossless append，依 `video_id` 與 canonical URL 去重；集數 fallback 內另新增
  呼叫同一操作的「重試」，讓使用者不必離開阻擋提示。它不推算相鄰 `sn`、不讀 browser DOM／
  Cookie、不從官方頁抽取資料，也不繞過 Cloudflare／登入／年齡／廣告／DRM。Rollback 為一起
  回復 merge helper、兩處 wiring 與 38.1.7 身分；不刪資料、不改寫 Development 38.0。
- **38.1.7 validation boundary（2026-07-20）**：新 helper 在 production 尚不存在時以 import／
  collection `1 error` 取得 RED；最小修正初次為 `2 passed in 0.89s`，加入 fallback wiring 後精準組
  `3 passed in 0.97s`。review 再以 `2 failed` 重現 append failure 游標遺失與 malformed URL 例外，
  並以 `1 failed` 鎖定同系列手動加入不應清除分頁游標；修正後精準組 `6 passed in 1.10s`，擴大
  非 UI 組 `111 passed in 1.85s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、
  依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall、CLI `MediaManager 開發版 38.1.7`、
  Version bytecode 零污染與 `git diff --check` 均通過。來源因此標為 `SOURCE VALIDATED`；全程未
  啟動／控制 GUI 或瀏覽器，未連線官方網站，完整集數與系統瀏覽器播放仍為 `LIVE WAITING`。
- **38.1.7 post-fix screenshot evidence（2026-07-20）**：四張使用者畫面已由檔案雜湊固定；
  只依可見內容更新人工矩陣，不以截圖推論點擊、網路回應或持續播放。
  - `codex-clipboard-ad3d55ee-8700-4eef-bad8-3b34d6f86f69.png`（SHA-256
    `E28B7B03C75B054BFDE5FB4703906F5DF614F959C0917E1A7E0CA614534B1387`）顯示可見來源
    `38.1.7`、已選「盜墓王」、集數 browser-verification fallback、可見「重試」與空集數表；因此
    `version_visible=PASS`、`episode_retry_visible=PASS`，但 `episode_retry_trigger=NOT_RUN`。
  - `codex-clipboard-6ce78fde-fb6a-4fc8-a7c5-09c8c8814422.png`（SHA-256
    `56A34B38F66521BDCC27E19D72ADE943D0CF154E5B4A7823A17C4A4062CB0E48`）顯示緊湊 codec
    fallback 與「在系統瀏覽器播放（建議）」操作可見；它不證明該操作已點擊或 OS 已收到網址。
  - `codex-clipboard-34c6109a-30ec-461f-a89f-6ca2ebcb6646.png`（SHA-256
    `639C8A5611C301AD765A5408062D43D3B41177F424E45BAD61005D71C5A63C89`）顯示 Video.js
    `CODE:4 MEDIA_ERR_SRC_NOT_SUPPORTED` 與 `setVolume` TypeError，故
    `embedded_playback=EXPECTED_UNSUPPORTED`；這不等於 system-browser 播放失敗。
  - `codex-clipboard-583c41e8-d91e-4059-bcad-10a70bc0348c.png`（SHA-256
    `94B9CF99771A5C24EAA10EA3C3D5E943ED9ED60F106C68DE21DBFDD717A5FCA1`）顯示
    `https://ani.gamer.com.tw/animeVideo.php?sn=49945` 已加入為「盜墓王 [官方單集 49945]」一列；
    因畫面只有一個網址／一列，僅記 `manual_single_add=PASS`，不得宣稱 append 或 dedupe 完成。
  - 本輪矩陣結論為 `manual_append=NOT_RUN`、`manual_dedupe=NOT_RUN`、
    `episode_OS_handoff=NOT_RUN`、`system_browser_playback=NOT_RUN`。證據更新沒有 material 程式差異，
    因此該純證據輪當時不升版；其後另有搜尋狀態回退證據才建立 38.1.8。
- **38.1.7 → 38.1.8 search-state evidence（2026-07-20）**：後續兩張 38.1.7 使用者畫面顯示
  關鍵字搜尋已進入瀏覽器驗證狀態，搜尋與重試按鈕仍為啟用，但作品表為空；因此不是 click
  wiring 失效的證據。檔案雜湊固定如下，只依畫面可見內容判定：
  - `codex-clipboard-9d48bdde-2491-4d83-a710-d74bee943be0.png`（SHA-256
    `3439213CD04B897A60BBFB7F52DDB6F3AE71712EC49C29C2CC26F192422DE78C`）顯示來源
    `38.1.7`、空作品表與官方瀏覽器驗證提示。
  - `codex-clipboard-d97ad78c-18a1-4d02-8cc6-d38f6b25e850.png`（SHA-256
    `FFBEEAEF9ABE58524F26AF6C2E5BB11037D34A2051489F09D01C47F4532BEB32`）顯示搜尋框有
    「盜墓王」、搜尋／重試仍可見且結果表為空。截圖不能證明 403 的供應者、網路封包或按鈕
    點擊次數，只能與來源追蹤共同固定 pre-fix 症狀。
- **38.1.8 correction（2026-07-20）**：provider 的 HTTP 403 會被 federation 捕捉並放入合法
  `FederatedSearchResult.failures`，因此 `show_response()` 的直接 `error` 保持空字串。38.1.7 的
  `show_search_results()` 在檢查 failures 前先把 `self.results` 換成空 tuple、清除選取作品與集數，
  形成「先前成功資料消失」的本機狀態回退；直接 exception 路徑反而會提前 return，兩條錯誤路徑
  不一致。38.1.8 加入純 catalog result reducer：`failure + 0 accepted` 保留上一批狀態，
  `failure + accepted` 仍提交 partial success，`success + 0 accepted` 仍清空並顯示找不到作品。
  瀏覽器驗證與其他 structured failure 的四語提示都會明示保留資料不是本次查詢結果；首次搜尋
  沒有上一批資料時仍顯示空表並要求使用
  系統瀏覽器取得 canonical `animeRef.php`。這不讀 browser profile／Cookie、不重送瀏覽器驗證
  狀態、不自動開啟 GUI，也不繞過官方拒絕。
- **38.1.8 validation boundary（2026-07-20）**：新 reducer 尚不存在時以 import／collection
  `1 error` 取得 RED；加入 reducer 與 production wiring 後精準非 UI 組 `2 passed in 0.43s`，
  最終 review 補上非瀏覽器 structured failure 的通用保留提示後，提示／四語／integrity 精準組
  `5 passed in 0.45s`；擴大搜尋、集數、session、MOD integrity、bootstrap、版本與文件組為
  `103 passed, 1 skipped in 3.20s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、scoped compileall、CLI
  `MediaManager 開發版 38.1.8`、Version bytecode 零污染與 `git diff --check` 均通過。沒有執行
  會建立或控制 GUI 的測試，沒有連線動畫瘋；來源標記 `SOURCE VALIDATED / LIVE WAITING`。
  Rollback 為一起回復 reducer、`show_search_results()` wiring、四語提示／integrity pins 與 38.1.8
  身分；不刪除使用者資料、不修改或覆寫 Development 38.0。
- **38.1.8 screenshot-first revalidation（MANUAL WAITING）**：先在同一行程用成功搜尋或貼入
  canonical `animeRef.php` 建立至少一筆作品並選取；再執行一筆會收到官方拒絕的關鍵字搜尋。
  預期舊作品、選取與集數仍留存，狀態明示「上一批結果不是本次查詢結果」。完全重啟後在沒有
  上一批資料時執行同一受阻查詢，預期仍為空表與 system-browser fallback。兩個畫面都只以
  使用者截圖驗證；不得自動控制 GUI 或以截圖宣稱 OS handoff／播放成功。
- **38.1.8 visible-flow evidence（2026-07-22）**：本輪兩張使用者截圖只按可見內容分級，不由
  截圖推論按鈕點擊、官方回應來源、完整總集數、持續播放或下載。
  - `codex-clipboard-0bffb46a-98ec-432c-993e-514599e69eb4.png`（SHA-256
    `1DE77504132E45AEFFB22AE357CA7B4657FE7995CCC0E20282B9FA1ABF8E671B`）顯示
    `MediaManager 開發版 38.1.8`、三筆可見作品、`盜墓王` 選取 context、狀態「已列出 2 集」及
    `盜墓王 [1]`／`[2]` 兩列。因此 `version_visible=PASS`、
    `catalog_results_visible=PASS (3 displayed)`、`series_selection_visible=PASS`、
    `episode_rows_visible=PASS (2 displayed)`；它不證明搜尋按鈕觸發、完整總集數、集數 URL、
    append／dedupe 或 38.1.8 的 failure-state preservation。
  - `codex-clipboard-292f470e-768c-491e-bcf6-4057bbe00d82.png`（SHA-256
    `03BD5EA9CE94F8E692D291D976DB2B0E0A472AB487DC4E83F202AE9D78E32655`）顯示 Video.js
    `CODE:4 MEDIA_ERR_SRC_NOT_SUPPORTED`、站方 `setVolume` TypeError，以及緊湊的本機
    codec／HLS／MSE 不支援提示與「在系統瀏覽器播放（建議）」操作。因此
    `embedded_fail_closed_presentation=PASS`、`system_browser_action_visible=PASS`、
    `embedded_playback=EXPECTED_UNSUPPORTED`；`system_browser_handoff=NOT_RUN` 與
    `system_browser_playback=NOT_RUN`。這是既知 runtime 限制，不是 38.1.8 新 regression。
  - 這兩張圖沒有顯示「受阻搜尋後仍保留上一批資料」或 fresh restart 空狀態受阻查詢，故上方
    38.1.8 專屬 revalidation 仍為 `MANUAL WAITING`；本輪純證據同步不升版或建立套件。
- **38.1.8 evidence-only verification（2026-07-22）**：一次完整 runner 誤納入 offscreen GUI
  自動互動，結果為 `1370 passed, 7 skipped, 1 failed`；唯一失敗不是 runtime regression，而是同一
  workspace 測試仍硬編碼舊的 `Cloudflare` 搜尋提示與舊的通用 `Compatibility View` 標籤。
  兩處已改為比對目前的 locale key，沒有修改 production code，因此不升修正號；依「截圖優先、
  禁止自動互動」界線不重跑該 GUI 測試，也不把完整 runner 當作本 Gate 通過證據。其後僅執行
  AniGamer session／搜尋／集數、MOD group 與純 reducer／codec policy 組，結果
  `90 passed in 1.03s`；Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖
  `10`、版本文件 `4`、保留版本 `5`、外部 pycache compileall 與 `git diff --check` 均通過。
  系統瀏覽器 handoff／正片播放仍須使用者人工截圖，完整 GUI suite 維持 `NOT RUN AFTER TEST-ONLY FIX`。
- **38.1.9 correction（2026-07-22）**：唯讀播放路徑 audit 重現一個 episode ownership race。
  A 的集數 worker 執行期間仍可把作品選取切到 B；selection handler 只清除 episode state，沒有
  取消 worker 或使 operation generation 失效。A 回應抵達後，舊 `show_response()` 因 generation
  仍相同而呼叫 `show_episode_results()`，將 A 的成功資料或失敗提示套到 B；之後播放歷史與離線
  索引可能把 A 集數配到 B。38.1.9 新增純 ownership guard：請求時的 `episode_query` 必須仍為
  非空字串且完全等於目前選取作品 URL，才可套用成功或失敗回應；否則丟棄 stale response、結束
  busy 並保留 B 的狀態。它不修改 provider、網址、Cookie、網路、codec、system-browser handoff、
  UserData、manifest 或 integrity pins。
- **38.1.9 validation boundary（2026-07-22）**：helper／dispatch guard 尚不存在時兩項純回歸先得
  `2 failed in 1.25s`；最小修正後同組 `2 passed in 0.24s`。本輪 AniGamer 搜尋、集數、session、
  純 workspace 與版本組合計 `85 passed in 1.77s`；Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外 pycache compileall、
  CLI 38.1.9 與 `git diff --check` 均通過。未啟動或控制 GUI、未連線動畫瘋；人工競態與系統瀏覽器
  播放仍為 `LIVE WAITING`。
  Rollback 為一起回復 ownership helper、episode dispatch guard、兩項 regression 與 38.1.9 身分；
  不刪除使用者資料、不修改或覆寫 Development 38.0。
- **38.1.10 correction（2026-07-22）**：唯讀 exact-handoff audit 重現 canonical query 缺口。舊
  `_ani_gamer_route()` 會解析 query 後檢查 `sn` 數字，卻未要求原始 query 精確形式，因此帶額外／
  重複參數、`SN=` 或 percent-encoded key／value 的同站網址仍可能被分類成官方作品／單集，並進入
  provider result filter、system-browser handoff、history 或 offline。38.1.10 改為只接受原始 query
  精確等於 `sn=<ASCII digits>`，其他 alias 全部 fail closed；標準 canonical URL 行為不變，也不新增
  provider traffic、Cookie、browser state、codec、UI 或下載能力。
- **38.1.10 validation boundary（2026-07-22）**：額外／重複 query regression 在修正前先得到
  `1 failed in 0.46s`；加入大小寫與 percent-encoded alias 後第二階段再得到
  `1 failed in 0.41s`；精確 route node 最小修正後為 `1 passed in 0.17s`。相關非 UI 組
  `205 passed, 1 skipped in 1.66s`，版本／文件組 `19 passed in 1.00s`；Ruff／文字污染
  `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  Repository 外 pycache compileall、CLI 38.1.10、Version bytecode 零污染與 diff check 均通過。
  未啟動或控制 GUI、未連線動畫瘋，不宣稱 system-browser handoff、播放或下載完成。風險低、
  沒有資料遷移；Rollback 只回復
  `core/site_routing.py` 精確 query 條件、相符 regressions、版本與文件，不刪資料或覆寫 Development 38.0。
- **38.1.11 correction（2026-07-22）**：來源完整性 audit 重現 canonical item identity 與 episode
  handoff 狀態缺口。舊 consumer 只驗 AniGamer URL route，沒有要求 `DiscoveryItemV1.video_id` 與
  精確 URL `sn` 一致，因此不一致 item 仍可進入 provider results、series／episode handoff、history
  或 offline 新寫入；busy 期間雙擊畫面上的舊單集列也可越過 action-state disabled 外觀觸發 handler。
  38.1.11 新增共用純 identity validator，作品只接受 `ani-{sn}`、單集只接受
  `ani-episode-{sn}`，並套用至作品／集數 filter、handoff、history 寫入及讀取與 offline 寫入及
  metadata 讀取；episode handler 在
  busy／closing 時 fail closed。current-series 與 direct-episode context 保持原語意。
- **38.1.11 validation boundary（2026-07-22）**：validator／consumer wiring／handoff guard 不存在時
  精準回歸先得到 `4 failed in 1.80s`；最小修正後初始精準組為 `6 passed in 1.26s`。read-side review
  再以 `2 failed in 0.52s` 重現 history load 與 offline metadata 讀取缺口，修正後為
  `3 passed in 0.98s`；最終相關非 GUI 組為 `129 passed, 1 skipped in 7.23s`。Ruff／文字污染
  `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  Repository 外 compileall、CLI 38.1.11、Version bytecode 零污染與 diff check 均通過。內建
  providers 原本已輸出 canonical IDs，沒有 migration／deletion 或既有檔案改寫。未啟動或控制
  GUI，也不宣稱 system-browser 播放或下載完成。Rollback 為一起回復 identity validator、consumer
  wiring、history／offline read-side checks、busy／closing guards、regressions、版本與文件，不覆寫
  Development 38.0。
- **38.1.11 live screenshot evidence（2026-07-22，evidence-only）**：本組是新的 38.1.11 人工
  可見證據，不覆寫 38.1.8 或其他歷史 hash，也不因純證據更新升修正號。
  - `codex-clipboard-9b3bf123-feeb-4f9c-95e9-13b1ec70f0ea.png`（SHA-256
    `81733D7FC2DAB30DC5ED1CB257235AAFDB5E39F13DA764F5937AD6BF2B571990`）顯示終端的
    Video.js `CODE:4 MEDIA_ERR_SRC_NOT_SUPPORTED`／`setVolume` TypeError，以及選取
    `盜墓王 [2]` 後的「內嵌檢視無法載入官方頁面，請改用系統瀏覽器」compact fallback。
    因此 `embedded_fail_closed_presentation=PASS`、`embedded_playback=EXPECTED_UNSUPPORTED`；
    不能由此推論 system-browser handoff 或播放。
  - `codex-clipboard-92c95b19-5fca-4c05-bf57-2054ba5e62ab.png`（SHA-256
    `E46E4C90AFBBC5028E138FDBF3AE42C89BB1201969135A07BDA841D2431CD986`）顯示
    `MediaManager 開發版 38.1.11`、`盜墓王 [1]`／`[2]`、選取第 2 集、可見的單集
    system-browser／compatibility 操作，以及「離線索引有效；目前尚未連結影片或字幕」。因此
    `version_visible=PASS`、`episode_rows_visible=PASS (2 displayed)`、
    `selected_episode_visible=PASS`、`episode_actions_visible=PASS`、
    `offline_metadata_index=PASS`、`video_linked=false`、`subtitle_linked=false`。
  - 截圖不能證明 ID／URL identity、busy／closing guard、按鈕互動、完整總集數、OS handoff、登入／
    年齡／廣告流程、兩個不同播放時間、播放持續前進或檔案完整性；這些仍為
    `NOT_RUN / MANUAL WAITING`。成功訊息也沒有 exact URL，因此無法把當時的 OS handoff 與
    選取的 canonical episode URL 對應；該組 38.1.11 截圖不是 38.1.12 live evidence。P2 下載繼續
    `BLOCKED / NO AUTHORIZED MEDIA SOURCE`。
- **38.1.12 Goal（P1）**：讓截圖優先的人工驗證可把 MediaManager 回報的單集 OS 開啟請求
  對回實際送出的 exact canonical URL，同時阻止「OS 接受請求」被誤報為官方頁已載入或播放。
- **38.1.12 Scope**：只包含四語 `episode_opened` 文案、`open_selected_episode`／
  `open_history_entry` 訊息 wiring、相符 regressions、版本與文件。不包含 Cookie、provider traffic、
  網頁狀態偵測、串流／codec、下載、彈幕或 GUI 自動操作。
- **38.1.12 Priority／Dependencies**：P1；38.1.11 已證明版本、兩筆集數與選取第 2 集，但沒有
  exact URL 的成功訊息不足以建立 handoff evidence。實作依賴 38.1.11 canonical item identity、現有
  allowlisted OS opener 與四語格式化資源；G39／G40 仍不得平行啟動。
- **38.1.12 Approach**：四語 `episode_opened` 加入 `{url}`；`open_selected_episode` 與
  `open_history_entry` 在現有 OS opener 回報接受後，傳入同一個已通過 38.1.11 identity
  邊界的 exact URL。訊息必須同時告知「OS 已接受開啟請求」與「頁面載入／播放未確認」。
- **38.1.12 Compatibility／Risk**：不改 provider、contract、schema、IPC、network、Cookie、資料或離線格式；
  選取單集與 history 使用的 canonical URL 語意不變。風險是 locale placeholder 遺漏／格式錯誤，
  或使用者把 OS acceptance 誤解成 playback success；四語測試與明確限制文案為對應控制。
- **38.1.12 Rollback**：一起回復四語 `episode_opened`、`{url}` wiring、regressions、38.1.12 版本
  與文件；沒有 migration／deletion，不碰使用者資料，也不覆寫 Development 38.0。
- **38.1.12 Validation／Release boundary**：修正前精準回歸 `1 failed in 0.42s`；修正後
  `2 passed in 0.94s`，精準相關來源組 `9 passed in 1.04s`，擴大非 UI 組
  `143 passed, 2 skipped in 1.60s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、版本文件測試
  `6 passed in 0.33s`、Repository 外 compileall、CLI 38.1.12、Version `.pyc` 零污染及
  diff check 均通過。未啟動或控制 GUI，也未證明 system-browser 頁面載入或播放；
  38.1.11 截圖不得充當本版 live evidence。
  stage、commit、source freeze、build、package 與 push 均未執行。
- **38.1.13 Goal（P1）**：讓使用者在相容性 modal dialog 仍開啟時即可看到 exact 官方 route 的
  system-browser handoff 結果，避免單集／作品被誤標成官方目錄，亦避免 OS 拒絕或 opener 例外只寫到
  被彈窗遮住的主狀態。
- **38.1.13 Scope**：只包含相容性彈窗的 route-aware handoff 訊息、dialog-local status 鏡像、
  regression、版本與文件；不包含 provider、network、Cookie、download、stream、codec、schema、
  IPC、離線格式、網頁狀態偵測或 GUI 自動操作。
- **38.1.13 Priority／Dependencies**：P1；依賴 38.1.10 的 exact route、38.1.11 canonical item identity、
  38.1.12 的 exact-URL `episode_opened` 與既有 allowlisted OS opener。G39／G40 仍不得平行啟動。
- **38.1.13 Approach**：舊相容性彈窗固定使用 `catalog_opened`，且
  `QDesktopServices.openUrl` 回傳拒絕或 opener 拋出 `RuntimeError` 時只更新 `self.status`。新路徑先依
  exact AniGamer route 選擇單集 `episode_opened` 或作品 `series_opened`；單集傳入實際送交 OS 的
  exact URL，並將 accepted／rejected／exception 的最終文字同時寫入主狀態與 dialog-local status。
- **38.1.13 Compatibility**：送交 OS 的 allowlisted URL、按鈕語意、provider contract、Cookie
  lifetime、資料與網路行為均不變；沒有 migration、breaking change 或歷史版本覆寫。
- **38.1.13 Risk**：route／placeholder 選錯可能再次顯示錯誤類型或遺失 exact URL；只更新主狀態則
  modal 仍會遮住結果。精準 route regression 與 dialog-local status assertion 為對應控制。來源測試
  不能取代實際 OS handoff 或頁面載入／播放證據。
- **38.1.13 Rollback**：一起回復 exact-route 訊息選擇、dialog-local status 鏡像、regression、
  38.1.13 版本與文件；不刪除或遷移資料、不覆寫 Development 38.0，也不改 provider、network、
  Cookie、download 或 stream。
- **38.1.13 Validation／Release boundary**：修正前精準回歸 `1 failed in 1.27s`；最小修正後
  `1 passed in 0.71s`；相關精準組 `3 passed in 1.28s`、擴大非 GUI 組
  `115 passed, 1 skipped in 3.77s`、版本／文件組 `19 passed in 1.21s`。Ruff／文字污染
  `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  Repository 外 compileall、CLI 38.1.13、Version `.pyc` 零污染與 diff check 已完成，故 38.1.13 當時為
  `SOURCE VALIDATED`。人工 38.1.13
  截圖仍為 `LIVE WAITING`；stage、commit、source freeze、build、package 與 push 均未執行。
- **38.1.14 Goal（P1）**：修正單集官方 handoff 在進入 helper body 前就因 positional target 與
  message placeholder 同名而失敗，恢復 38.1.12 exact URL receipt 與 38.1.13 dialog-local 結果。
- **38.1.14 Scope**：只改 `dispatch_official_url` 的 transport formal parameter 與內部引用、精準
  regression、版本與文件；不改 provider、network、Cookie、download、stream、codec、schema、
  IPC、離線格式或站點政策。
- **38.1.14 Priority／Dependencies**：P1；依賴 38.1.12 `episode_opened` 的 `url=` placeholder、
  38.1.13 route-aware dialog-local status、canonical identity 與 allowlisted OS opener。
- **38.1.14 Approach**：舊 helper 宣告 `dispatch_official_url(url, ..., **values)`，呼叫端同時傳入
  positional transport URL 與 keyword `url=`，Python 在 helper 執行前即拋 multiple-values
  `TypeError`。將 transport 參數改名為 `official_url`，opener 與失敗文案使用該名稱，並保留
  `**values` 中供 `episode_opened` 使用的 `url`。
- **38.1.14 Compatibility**：呼叫順序、allowlisted URL、翻譯 placeholder、成功／失敗訊息與
  dialog-local 鏡像不變；沒有 migration、資料格式或 external API breaking change。
- **38.1.14 Risk**：內部引用漏改可能把錯誤 target 送至 opener 或失敗文案；只驗 AST 形狀也可能
  再漏掉實際綁定。signature／opener／failure-message regression 與純 handoff 組限制此風險。
- **38.1.14 Rollback**：一起回復 helper transport 參數名稱與內部引用、regression、38.1.14 版本
  與文件；不刪除或遷移資料、不覆寫 Development 38.0，也不改 provider、network、Cookie、
  download 或 stream。
- **38.1.14 Validation／Release boundary**：runtime 擴大組修正前
  `1 failed, 162 passed, 1 skipped in 8.99s`；新增純回歸 RED `1 failed in 1.20s`；修正後純 handoff
  組 GREEN `4 passed in 1.08s`。後續相關非 UI＋版本組在文件未同步時
  `134 passed, 1 skipped, 1 failed in 6.79s`，唯一失敗只因 README／docs README 仍為 38.1.13；
  同步後重跑為 `135 passed, 1 skipped in 1.87s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
  `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall、CLI 38.1.14、
  Version `.pyc` 零污染與 diff check 均已通過，故該輪為 `SOURCE VALIDATED`。人工 38.1.14 截圖當時維持
  `LIVE WAITING`；未 stage、commit、source freeze、build、package 或 push。
- **38.1.14 partial screenshot evidence（2026-07-22）**：
  `codex-clipboard-5687e504-c306-4d3a-86b0-cc79cf9d8567.png`（SHA-256
  `5C52283BACEB1EECB5E55F92A1301D1E6240239D0F2BD6CDA1C1BEEB05DE5E42`）可見 PowerShell 從
  `C:\Dev\MediaManager` 執行 `.\.venv\Scripts\python.exe .\main.py`；終端顯示 Video.js
  `CODE:4 MEDIA_ERR_SRC_NOT_SUPPORTED` 與 `setVolume` TypeError，畫面則顯示標題「盜墓王 [1]」的
  緊湊相容性 fallback、Qt WebEngine 缺本機 H.264／AAC／HLS／MSE 路徑提示，以及「在系統瀏覽器播放
  （建議）」與取消按鈕。CLI 另核對當時來源為 38.1.14。逐項只記
  `embedded_fail_closed_presentation=PASS`、`episode_context_visible=PASS`、
  `system_browser_action_visible=PASS`、`embedded_playback=EXPECTED_UNSUPPORTED`。截圖沒有顯示按鈕
  已點、OS handoff、官方頁載入、廣告或播放；上述項目仍為 `NOT_RUN / LIVE WAITING`，版本維持
  38.1.14／`SAFE_MODE`，不因純證據同步升修正號。
- **BoringMan314 fork reference decision（2026-07-22）**：唯讀比較固定在
  [V24.9.10／`ce7a6d5`](https://github.com/BoringMan314/aniGamerPlus/commit/ce7a6d58caead87825fa2e0da0fb8c168cdb5995)。
  上游採 GPL-3.0，本專案採 MIT，未複製其程式碼。作品／集數 metadata、安全命名、批次、
  SQLite 狀態、有限重試／併發、佇列、進度、日誌輪替、離線匯入與完整性已 `ALREADY ABSORBED`；
  FTP／Dashboard／Docker、背景排程與本機 MP4 `faststart` 為跨 Gate `DEFER`。Cookie／profile
  擷取或刷新、瀏覽器模擬、Cloudflare／代理／地區規避、M3U8／key／segment／AES／FFmpeg 串流
  抓取及廣告跳過／移除維持 `REJECT`。沒有 G38 scope 內、非重複且有 failing regression 的
  material delta，故該次掃描當時標記 `ABSORBED / NO RELEASE`，未因參考 fork 建立 38.1.15。
  這項歷史判定已由後續「移除動畫瘋整合」的獨立 material delta 取代；38.1.15 並非 fork
  功能導入，也不再要求 38.1.14 handoff／播放人工證據。首次指定的外部 test-root 因
  Windows ACL 拒絕建立 `runtime` 而退出，未回退到 Repository；改用本輪唯一 LOCALAPPDATA
  test-root 後相關非 UI／版本／文件組為 `173 passed, 1 skipped in 5.36s`。Ruff／文字污染
  `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  Repository 外 compileall 與 diff check 均通過。
- **P2 official-contract recheck（2026-07-22）**：重新查閱
  [動畫瘋服務條款](https://ani.gamer.com.tw/animeRule.php)與
  [動畫瘋官方 App 說明](https://prj.gamer.com.tw/app2u/animeapp.html)。官方 App 說明只列線上觀看，
  沒有可供第三方保存的公開影片匯出契約；服務條款要求依服務提供方式觀看，並禁止重製、規避
  廣告及規避／破解串流。故 P2 明確維持 `BLOCKED / NO AUTHORIZED MEDIA SOURCE`；Cookie、
  WebView／瀏覽器／service worker／播放器暫存、播放中的分段或廣告後處理都不是下載授權，
  不得擷取、複製、重組或事後移除。現有離線區只保存公開 metadata／封面，並匯入使用者自行
  取得的本機媒體；只有日後官方提供明確的非 DRM、非廣告規避可保存契約才重新開 Gate。
- **38.1.6 → 38.1.7 screenshot boundary（2026-07-20）**：八張使用者畫面只按可見內容保存，
  支持本輪 Root Cause 與手動驗證界線，不覆寫 38.1.6 的來源驗證歷史。
  - `codex-clipboard-8e01c660-a762-4c6a-b85f-c16e85669771.png`（SHA-256
    `DA3AF3ACBABE90DD16E9127DBA67F4DB5C4D7371327D036D3DB31F318E73AEE4`）顯示 Video.js
    `CODE:4 MEDIA_ERR_SRC_NOT_SUPPORTED` 與 `setVolume` TypeError。它們分類為本機 codec／站方
    播放器次生錯誤；不證明搜尋、集數 merge 或系統瀏覽器播放失敗。
  - `codex-clipboard-2cc78b2d-15c3-4883-830f-20ace3d95eec.png`（SHA-256
    `A62CECC58389B80FFF7FED1C966A674341EE63CF1BF7670D00A4254AB8CA5A13`）顯示選取作品的緊湊
    codec fallback 與系統瀏覽器播放主操作；不證明內嵌播放成功。
  - `codex-clipboard-00e76bb9-ad9a-4c96-9ca5-bb072b394918.png`（SHA-256
    `8FB18DF1FD9DD0EF21E15F5F0F733312A324B2EB5C638493B34B3AFB6E166A70`）與
    `codex-clipboard-7dcb3966-61ed-48f2-b0b4-eb86a11d0ca5.png`（SHA-256
    `3A032FB80549A82D8DC5580BC1745743F6EDD286AB291F882D8182627512C616`）顯示介面篩選已套用、
    目錄受瀏覽器驗證阻擋且結果表為空；不能推論按鈕 wiring 失效。
  - `codex-clipboard-21ca9270-6440-4a1f-8723-e4093ed0b0bd.png`（SHA-256
    `D5B89A93543C9EC2352A8B1BB3FE84B7E959412E888AE13F15D7DE19B52665DD`）顯示「重試」後找到
    20 筆官方作品，支持重新查詢與單一來源上限，而非 stale 結果。
  - `codex-clipboard-e33db316-7773-4fb1-8b61-537456386a8f.png`（SHA-256
    `C0B84A77D9A795ABEB75A09BDB1C35E72FBF9F842CE1A119E63F0C24093395A5`）顯示已選「貓與龍」
    後工作區僅保留手動官方集數 `49789` 一列。
  - `codex-clipboard-6bed3f04-4add-4f19-83da-6e11c33ad874.png`（SHA-256
    `204130AA2A083446CD4CAFCAB755585624833B3B4AE0B190DBBC08D06BC9AAAD`）顯示使用者的系統
    瀏覽器官方作品頁可見四個集數按鈕與年齡提示；只支持官方頁可見的對照，不讀取 DOM／Cookie，
    也不證明正片播放。
  - `codex-clipboard-7fcc3997-cd31-41c3-9cb0-d7a3cd1cfba2.png`（SHA-256
    `D1B087D3EFB7CDD0FCAE73BAC793ADA63AB931029135A8DB57DEB79B4E75F407`）顯示單一手動集數列與
    codec fallback 同時存在；支持集數覆寫與內嵌播放限制是兩個獨立問題。
- **38.1.5 → 38.1.6 screenshot boundary（2026-07-20）**：最新三張使用者畫面是 38.1.5
  post-fix／38.1.6 pre-fix 證據，不覆寫 38.1.5 的 source validation 或更早歷史。
  - `codex-clipboard-fa442f06-81b7-4433-a6e8-0a7863062bb3.png`（SHA-256
    `ECBC583EB97BAA2A8774C02627847BCB01113FEC589AE9F6931B545E1FC54CE3`）顯示 browser-verification
    armed 訊息與獨立官方目錄確認操作可見；支持至少一個快捷流程已進入 callback，不能證明四鍵
    `isEnabled()`、實際點擊或 OS handoff。
  - `codex-clipboard-552848cc-69b0-4af8-b4ec-ec9d7ba515e3.png`（SHA-256
    `71FEEF01E3CE71D616755581E94CCE124B04AFF3982B321173B696A068AB5CBE`）顯示另一個官方目錄入口
    進入 media codec fail-closed 對話框；只支持 catalog routing 錯置，不證明新的明示 handoff 失敗。
  - `codex-clipboard-ea3bfea7-a0e0-4993-a119-74bf58e9db07.png`（SHA-256
    `CECCEF2F01CE18F4282703BB61A8E426E6C8C438500DC0F4EBEAB7902B52CFEC`）顯示 `sn=49853` 已在
    本機辨識，但 220px 空作品表仍占畫面且只露出「作品集數」標題；支持 direct row 未進入可見
    viewport，不證明 row 根本不存在、完整集數、播放或下載。
- **38.1.4 → 38.1.5 screenshot boundary（2026-07-20）**：三張使用者畫面保存為 38.1.5
  pre-fix 人工證據，不覆蓋下方既有 38.1.4 歷史證據。
  - `codex-clipboard-9e44c01c-54e6-4259-a5d8-3b3ba545a594.png`（SHA-256
    `1c3720949e0530d404823f6047e91c6106782af603a39ffc11ca36dc0a5f8854`）可見 38.1.4 四個快捷按鈕與
    browser-verification 訊息；它支持第一擊已完成 arm，而非四鍵 wiring 斷線，也沒有顯示可供完成
    第二階段的獨立操作。截圖不能證明實際點擊或網路回應。
  - `codex-clipboard-24bbcaa7-fec7-41dc-a000-c69c88299252.png`（SHA-256
    `5605edd28f93048765b7890b286e1293bfc1790f3afef82e3e776e5a6e77f794`）同樣可見 armed 訊息、篩選值與
    canonical 單集輸入；只支持 opaque arm 狀態持續可見，不能證明第二擊、OS handoff 或官方頁結果。
  - `codex-clipboard-2d13c4cf-abe8-4afd-9169-6ee7b0b0468d.png`（SHA-256
    `0db2a37d53bf0b97d34c8bcf13baf7c2c480592b34a24ee8213abd3f43f276ae`）可見 canonical 單集已在本機
    辨識，但上方結果表為空且畫面裁切在下方單集列之前；它支持 direct-route 與 focus/fold 的可見性
    缺口，不能證明資料列不存在、完整集數、OS handoff、播放或下載。
- **Manual validation boundary**：實際播放只由使用者提供截圖或人工結果記錄。現有截圖只證明
  Development 37.0／38.x 內嵌路徑曾顯示 codec 不相容或未載入，不能證明 header、登入、廣告流程、
  播放成功、Tab／UIA／NVDA 或串流未被攔截；P1-A 仍為 `MANUAL WAITING`。完整 Repository suite
  含 GUI 自動互動案例，依「截圖優先、禁止自動互動」指示本輪未執行，不以 targeted suite 取代。
- **Screenshot evidence（2026-07-20）**：使用者提供的
  `codex-clipboard-8556837e-e9ea-487e-929b-108999576e59.png`（SHA-256
  `4e20faf20b6019161ad96b5a2498c198be8fd2f589f96b6f24e23d18192b924f`）顯示官方頁與播放器容器
  已載入，但內嵌畫面回報 `No compatible source was found for this media.`。它只支持 Qt WebEngine
  codec／HLS／MSE 相容路徑仍失敗，不含可見來源版本，也不能證明系統瀏覽器播放或廣告流程結果。
- **38.1.1 visible-source evidence（2026-07-20）**：使用者提供的
  `codex-clipboard-03303314-63dd-419d-9c21-22e2a80c46f0.png`（SHA-256
  `5001759a5c3cc7f678feb06256feb4a53939e64f00da5917f8548a7a8d521d2a`）顯示視窗標題與底部狀態均為
  `開發版 38.1.1`，且動畫瘋主工作區、Cookie 安全界線、篩選區、provider 狀態與 Cloudflare
  人工 fallback 訊息可見。這張圖沒有開啟「相容性內嵌檢視」對話框，因此不能證明 38.1.1 已隱藏
  不支援的黑色 WebView，也不能證明作品／集數結果、系統瀏覽器 handoff、登入、廣告或正片播放。
- **38.1.1 user-run command evidence（2026-07-20）**：使用者提供的
  `codex-clipboard-1d2ecb29-031f-44d0-8143-fbe84a0f7f94.png`（SHA-256
  `d16fae87a16d392b28a94b03fd2cb0cb9d3b79b4911962f103a3c3757c606b79`）顯示
  `main.py --version` 輸出 `MediaManager 開發版 38.1.1`，以及指定的 presentation policy／wiring
  精準回歸為 `4 passed in 0.24s`。此證據與自動驗證結果一致，但不取代 GUI／官方連線人工 Gate。
- **38.1.1 unsupported-presentation evidence（2026-07-20）**：使用者提供的
  `codex-clipboard-e130d7d0-f82e-407e-96d7-153e195bdd17.png`（SHA-256
  `4f06ea7a72050dd7142f8bd3a073e68d2f3028fc8d3d653fd01ea13fb548043b`）顯示「AniGamer 官方目錄」
  對話框在本機 codec／HLS／MSE 能力不支援時沒有顯示官方頁、黑色播放器或媒體錯誤容器，只保留
  相容性說明、「在系統瀏覽器播放（建議）」與取消操作。配合同一輪 38.1.1 可見來源證據，這項
  `embedded_unsupported_presentation` 人工檢查記為 `PASS`；它不證明按鈕 handoff、系統瀏覽器、
  登入／Cloudflare／廣告或正片播放結果。
- **38.1.1 official-browser navigation evidence（2026-07-20）**：使用者提供的
  `codex-clipboard-08d71c56-62ea-412f-8fb4-186a80949c8e.png`（SHA-256
  `8ffb04ea5d27ff8317ee147ee7b56687cd67def9ece24f7733ef172192c8415d`）顯示 38.1.1 已選取
  「擅長逃跑的殿下 第二季」，而 `codex-clipboard-47df92f9-f43e-4128-8a91-8be4fca21075.png`
  （SHA-256 `a55f175a1fad96db7403d5c34c916fdf48c95b36ac1de5d3b8825a47a6b46ebf`）顯示系統瀏覽器
  最後位於同作品官方 `animeVideo.php?sn=49853` 第 13 集頁面。因對話框標題只有作品名稱且單集列
  尚未建立，證據只支持 `series_system_browser_handoff=PASS` 與使用者在官方網站導覽至第 13 集；
  `episode_system_browser_handoff` 仍為 `NOT_RUN`。官方頁也停在 15+ 人工確認，故播放階段為
  `NOT_RUN`，不能宣稱廣告完成或正片時間持續前進。
- **38.1.1 episode-list remaining gap（2026-07-20）**：同一張 38.1.1 工作區截圖的集數表仍為空，
  只能證明作品選取成功，不能證明 MediaManager 已讀取第 13 集或完整集數。此項維持
  `LIVE WAITING`；`codex-clipboard-d842ab16-2dce-46a0-ba68-0a841df350c7.png`（SHA-256
  `e437da9daabb521d9e988678b6ab3a182e1cf629da9309204ad94be25a81b12c`）再次確認作品專屬的
  unsupported presentation 已隱藏 WebView，但不補足集數清單或播放證據。
- **38.1.2 MOD-integrity failure evidence（2026-07-20）**：使用者提供的
  `codex-clipboard-74deec0a-6e07-497d-8ca6-0ad34b640791.png`（SHA-256
  `bb0e6b6844828b4ca133a8f47cf057dd241c894fc93fa3fd336aa6dc09f4b2a8`）顯示可見來源為
  `開發版 38.1.2`、內建 MOD `31/32`，且動畫瘋父群組內的 `ani-gamer` 官方目錄為「初始化失敗」。
  此證據與完整性 RED 一致，只作 38.1.3 pre-fix baseline；不能證明修正後 UI、集數或播放成功。
- **38.1.4 routing／catalog pre-fix evidence（2026-07-20）**：
  `codex-clipboard-9ee5c80f-1678-4b1a-919a-320a75bead1d.png`（SHA-256
  `9212b59912ff0898e9431a95acb101d6c49f19e6f7957f5d7c9710b32a0d2dce`）明確顯示 canonical
  `animeVideo.php?sn=49853` 被作品搜尋路徑回報 catalog invalid，判定為 pre-fix `PRODUCT_FAIL`。
  `codex-clipboard-adb27923-25c1-40e1-bc6f-e3ac0d9d3127.png`（SHA-256
  `c976966646099dea38794bb043dc9cf711ad87f609465ac6fcca1228a518be46`）只證明四個快捷按鈕可見；
  「四個按鈕都無法使用」是使用者的人工觀察，不由截圖自行證明互動。另兩張截圖 hash
  `7d0623f5e0e2de5671578f0d173f141dedf9828a295a757c0faaf9ca11eb1f78` 只支持必要模組標記與
  Cloudflare 訊息可見，`d6da7de83ec743a608ffcbfac9fdc2ae4dc4ae3dbac40ea79bc501d6d485afde`
  只支持 38.1.2 緊湊 fallback 顯示；都不證明瀏覽器 handoff、完整集數或播放。
- **38.1.4 live screenshot evidence（2026-07-20）**：本輪三張使用者截圖只依可見內容分級，
  不以截圖推論互動或網路結果。
  - `codex-clipboard-8138e5ca-4901-41bd-a9f3-5cca5bcd182a.png`（SHA-256
    `759c08d3c9dab241db269d6126e4e307a9680dbfacd3b640221cc4242f4d2622`）顯示作品結果、
    `盜墓王` 作品 context、狀態「已列出 2 集」以及 `盜墓王 [1]`、`盜墓王 [2]` 兩筆可見列；因此
    `catalog_results_visible=PASS`、`series_context_visible=PASS`、
    `episode_rows_visible=PASS (2 displayed)`。截圖未包含結果列的選取標記、完整總集數來源、
    已選單集或單集 URL，故 `selected_series_row`、`complete_episode_count`、
    `episode_system_browser_handoff` 與播放仍為 `NOT_RUN`。
  - `codex-clipboard-117a8a2c-8f02-456d-99e8-0b17f2cd6979.png`（SHA-256
    `e9f29bafd971c9e38273553382ea075ae9e9b888047413bb7bbabcd93de82e67`）顯示 38.1.4 離線區的
    「離線索引有效；目前尚未連結影片或字幕」；只支持 `offline_metadata_index=PASS` 與明確
    `video_linked=false / subtitle_linked=false`。它不證明影片／字幕匯入、下載、播放或檔案完整性。
  - `codex-clipboard-87d6364c-2d87-41bd-833b-f17e1fac5abb.png`（SHA-256
    `821ab9400db7a2b14f8d8bca9814981e1d404cc9421d9d395d8aa0afc2c42bad`）顯示 canonical
    `https://ani.gamer.com.tw/animeVideo.php?sn=49853` 已在本機辨識為獨立官方單集，且未選正式
    作品時作品關聯紀錄與離線保存仍停用；因此 `direct_episode_local_route=PASS`、
    `standalone_no_series_boundary=PASS`。畫面裁切在單集列之前，故單集列可見性、OS handoff 與
    播放均維持 `NOT_RUN`。
- **Screenshot-first live checklist（唯一人工模板）**：
  1. 完全關閉舊行程後啟動可見來源 38.1.14；先以一次成功搜尋或貼入 canonical
     `animeRef.php` 建立至少一筆作品並選取，再執行一筆收到官方拒絕的關鍵字搜尋。記錄上一批
     作品、選取與集數仍保留，且狀態明示不是本次查詢結果；完全重啟後沒有上一批資料時，
     同一受阻查詢應維持空表。不得把保留列當作本次新結果。
  2. 手動開始載入作品 A 的集數後立即切換至作品 B；A 的晚到成功或失敗回應不得在 B 的集數表、
     context 或狀態中出現。只以使用者操作及前後截圖驗證，不自動控制 GUI；若無法穩定製造延遲，
     記為 `NOT_RUN`，不得以單張靜態截圖宣稱競態通過。
  3. 套用一組介面篩選並按「重試」，記錄取得的作品數量；20 是單一來源安全上限，不要求超過
     20。若官方仍拒絕，記為 `EXPECTED_EXTERNAL_BLOCKED`，不重複自動嘗試或繞過。
  4. 使用者明示點擊該確認按鈕，只記錄 OS 收到 allowlist 內官方目錄 URL；再記錄 MediaManager
     顯示的作品查詢結果與已選作品。畫面不得包含 Cookie、帳號或其他憑證。
  5. 在集數驗證 fallback 逐一貼上同作品的兩個 canonical 單集網址，再重貼其中一個；記錄前兩筆
     皆保留、重複項未增加，並記錄 fallback 內「重試」可觸發同一操作。不得推算相鄰 SN。作品、
     集數或焦點錯置即為 `PRODUCT_FAIL`。
  6. 按現有「在系統瀏覽器播放」後，記錄 MediaManager 的成功訊息包含與選取列一致的
     exact canonical episode URL，且明示只是 OS 接受請求。從 history 開啟時也套用同一檢查；
     handoff 訊息不能單獨宣稱頁面載入或播放成功。
  7. 使用者自行在系統瀏覽器完成官方登入、年齡提示與廣告；不得自動點擊、跳過或代替驗證。
  8. 正片開始後提供兩張不同播放時間的去識別截圖，並人工記錄「播放時間有持續前進」。單張
     截圖只能證明可見畫面，不能證明持續播放。
  9. Cookie 驗證只記 `cookie_mode=none` 或 `cookie_mode=memory-session`，不得記錄值、header、帳號、
     DevTools、Network 面板或任何流量內容。「未攔截串流」只採來源／測試稽核證據，不由截圖宣稱。
- **Manual result record**：每次只建立一筆包含
  `observed_at_utc`、`source_version_or_revision`、`os`、`browser_version`、`locale`、
  `series_id_or_title`、`episode_id`、`cookie_mode`、`phase`、`result`、`visible_message`、
  `screenshot_names_or_hashes`、`manual_observation`、`blocker`、`follow_up` 的去識別紀錄。
  `result` 只允許 `PASS`、`EXPECTED_EXTERNAL_BLOCKED`（官方登入／Cloudflare／地區／廣告流程）、
  `PRODUCT_FAIL`（作品／集數／官方 URL／handoff 錯誤）或 `NOT_RUN`。
- **Exit Gate**：P1-A 與 P1-B 回歸、Shared DoD、文件與人工官方播放結果完成；P2／P3 若缺官方
  授權契約，分別標記 `BLOCKED`／`DEFERRED`，不阻擋已證實的播放修正，但不得宣稱影片或彈幕
  下載完成。

## 39.0｜量測與本機格式工廠

### G39-01｜量測式效能與資源預算

**Status**：`MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE`。G38-02 已依使用者 scope
決定關閉；G38-01 人工矩陣仍是獨立 blocker，不以截圖宣稱完成。固定可重現 workload baseline
已保存，沒有可證 bottleneck；未實作或宣稱任何最佳化，目前沒有 `ACTIVE / IN_PROGRESS` 工作。

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
- **Instrumentation gap（2026-07-22 closed for this workload）**：原有 `tools.run_tests` 不收集
  p50／p95、tracemalloc peak、Windows handle／thread delta 或 temp peak；現由純本機
  `tools.g39_baseline` 固定 workload 與輸出 schema。一般 suite duration 與 pass count 仍不得當作
  效能 baseline。
- **Measurement baseline（2026-07-22）**：量測當下（後續只同步 evidence 文件）的來源為 `38.1.15`、fingerprint
  `c86b4a75eb5210a56b56b3730ef179ec83835e1ffe128987a4000be5d020e6bf`、revision
  `3a35ab2b7c200f29920e3b25d9d0d7a8d4f7f014` 執行
  `.\.venv\Scripts\python.exe -m tools.g39_baseline --warmups 2 --iterations 20`。
  `queue-roundtrip-v1` 固定為 1,001 tasks／4 workers：persist p50／p95／max
  `198.654 / 219.921 / 229.945 ms`，restore `212.36 / 240.687 / 260.336 ms`，worker
  `1.075 / 1.402 / 1.733 ms`，total `437.495 / 482.475 / 506.929 ms`；tracemalloc peak
  `20,145,600 / 20,146,368 / 20,146,560 bytes`，temp peak 每輪均為 `912,806 bytes`，
  process handle／thread delta 最大皆為 `0`，殘留 download threads `0`，cleanup `true`。
  擴充 G39／queue regression `47 passed`；post-G39 完整 repository runner `1212 passed, 6 skipped`，
  quality audit Ruff `357`／文字 `551`。同一 workload 未顯示資源洩漏或足以啟動最佳化的
  material bottleneck，因此不建立 39.0 版本、附件或空 release。
- **Dependencies**：G38 近最終 UI、固定資料集／workload 與相同環境的 before／after 方法。
- **Approach**：baseline、workload 與 constraint 已固定；本輪沒有實測 bottleneck，不啟動修正。
- **Compatibility**：不改公開 contract；資源上限維持有界且可診斷。
- **Breaking Change／Migration**：無；若量測指向 contract／資料變更，停止並另立計畫。
- **Risk**：時間型 CI 測試不穩，或跨機器數據被錯誤比較。
- **Rollback**：移除單項最佳化，但保留安全上限、benchmark 與診斷證據。
- **Validation**：同一來源與固定 workload 完成 2 次 warmup、20 次 p50／p95／max、memory／handle／
  thread／temp 量測、`47 passed` 擴充 G39／queue regression 與完整 runner `1212 passed, 6 skipped`；CI 仍只
  檢查上限與洩漏，不硬綁硬體絕對時間。
- **Exit Gate**：baseline 已保存且無資源 regression，判定
  `MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE`；不建立空產物。

### G39-02｜本機格式工廠第一工作包

**Status**：`SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`。
本節 full source Gate 已完成，目前沒有 `ACTIVE / IN_PROGRESS` 工作；未經授權不啟動 G40 或第二個
39.x 工作包。

- **Goal**：在既有、預設停用的 Media Convert 邊界內，加入可驗證的本機影像轉檔與可支援的
  FFmpeg 失敗證據，形成不依賴專有安裝程式或雲端上傳的第一個「本機格式工廠」版本。
- **Scope**：新增 PNG／JPEG／WebP 靜態影像 preset、來源副檔名限制、UI／automation wiring、
  bounded redacted stderr；沿用現有影音轉檔、壓縮、修剪、串接／切割、字幕、單工佇列、取消、
  `.part` 與 atomic no-overwrite。文件、DVD／CD、浮水印、持久佇列、進度解析、完整 GPU capability
  probe 另列後續 evidence gate。
- **Priority**：P1；使用者已明確要求，且 `image-png` 在實作前可重現為 unsupported preset。
- **Dependencies**：既有 pinned／使用者驗證的本機 FFmpeg、Media Convert manifest、preset
  integrity pins、atomic output 與共用 diagnostic redaction。
- **Approach**：以加法 preset 擴充現有服務；只接受使用者選取的普通本機檔，靜態影像固定
  `-frames:v 1 -update 1`。FFmpeg 只允許 `file,pipe`，stderr 由 daemon reader 持續排空，最多保留
  64 KiB；截斷首個不完整行先丟棄，任務錯誤只暴露 redacted／bounded 內容。UI 只對既有 H.264
  preset 啟用 NVENC 選項，失敗仍回退 CPU。
- **Compatibility**：provider ID、manifest schema、request model、既有 preset 與輸出規則不變；
  新 preset 是加法式。沒有 UserData migration 或 API breaking change。
- **Risk**：FFmpeg build 缺 encoder、損壞／超大影像、stderr pipe 阻塞、診斷洩漏、輸出碰撞與
  誤示 GPU 能力。以固定 preset、來源大小／symlink／extension Gate、背景 drain、redaction、
  `.part`、atomic no-overwrite 與 CPU fallback 控制；未量測前不宣稱加速。
- **Rollback**：移除三個 preset、UI／automation mapping、stderr reader、integrity hash 與相符
  regressions；不刪除來源、UserData 或已產生輸出，也不覆寫 Development 38.0。
- **Validation**：RED 合計 `4 failed`；擴充精準組 `69 passed, 1 skipped`，最終 conversion security
  組 `21 passed, 1 skipped`，包含實際本機 FFmpeg 8.1.2 BMP→PNG 與 PNG signature。完整 runner
  `1222 passed, 7 skipped`；Ruff／文字 `357 / 552`、MOD `7 / 4`、網站 `12 / 33 / 49`、依賴鎖
  `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall、SAFE_MODE verify-only 與 diff check
  均通過。
- **後續 Gate**：
  - `G39-03` 候選只能先做 FFmpeg build／encoder／filter／hwaccel capability probe 與輸出
    `ffprobe` 驗證；必須另有 regression，不在本輪自動啟動。
  - 文件需獨立本機 adapter 與 macro／sandbox／檔案炸彈風險設計；CloudConvert 不得自動 fallback。
  - DVD／CD 只限使用者持有且未受保護的來源；CSS、AACS、區碼或 DRM 繞過永久排除。
  - 圖像浮水印優先於文字浮水印，但仍需獨立輸入模型、filter escaping、預覽與 rollback 證據。
- **Exit Gate**：完整來源 Gate 通過後最多標記
  `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`；stage、commit、source freeze、build、EXE、
  Testing／Stable、簽署、發布與 push 均需另行逐項明確授權。

### G39-03｜本機能力、磁碟與成品驗證

**Status**：`SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`。來源 Gate 已完成，目前沒有 ACTIVE／
IN_PROGRESS 工作；G40-01 繼續等待另行授權。

- **Goal**：讓格式工廠只顯示有本機證據的 GPU 能力，排程前拒絕明顯不足的磁碟空間，並在
  原子提交前以 ffprobe 證明暫存輸出至少含一條可讀媒體 stream。
- **Scope**：加入有 timeout 與 bounded／redacted 診斷的 FFmpeg version／buildconf／formats／
  encoders／filters／hwaccels probe；H.264 NVENC UI 只在 `h264_nvenc` 實際存在時啟用；以估算輸出
  加 256 MiB reserve 執行本機磁碟 preflight；FFmpeg exit 0 後用本機 ffprobe JSON 驗證 `.part`
  再 atomic no-overwrite。排除下載器、網路 URL、雲端 fallback、未知 binary、效能百分比宣稱、
  浮水印、文件與光碟。
- **Priority**：P1；G39-02 已留下「缺 encoder／損壞輸出／磁碟不足只能到執行期才知道」的明確
  failure boundary，且使用者要求 CPU／GPU 加速與不突然崩潰。
- **Dependencies**：既有 pinned／使用者驗證的本機 FFmpeg 與 ffprobe、Media Convert queue、
  diagnostic redaction、`.part` 與 atomic no-overwrite。
- **Approach**：能力探測只讀本機 executable 且結果快取；個別 probe 失敗記錄去識別錯誤而不假裝
  能力存在。submit 在建立 task 前執行磁碟檢查；ffprobe 只允許 `file,pipe`，限制執行時間與 JSON
  大小，必須成功解析且 `streams` 非空才提交。
- **Compatibility**：公開 provider ID、preset ID、request schema 與既有輸出命名不變；
  `ConversionService` 的 ffprobe 參數採向後相容 keyword。缺 ffprobe 時功能保持不可用而非略過驗證。
- **Risk**：probe 輸出格式差異、能力偵測阻塞、磁碟估算誤差、ffprobe 對合法字幕／靜態圖格式誤判，
  或診斷暴露路徑。以 timeout、大小限制、redaction、256 MiB reserve、最小 stream contract 與
  regression 控制；不依 probe 數據宣稱速度。
- **Rollback**：移除 capability model／UI 提示、submit preflight 與 commit 前 probe，回復 39.0.0；
  不刪除來源、UserData 或既有完成輸出。
- **Validation**：先建立 capability、low-disk、ffprobe failure／success regressions，再執行相關非 UI
  runner、實際本機 FFmpeg→ffprobe smoke、Ruff／quality、MOD／依賴／版本／compileall、污染與
  `git diff --check`。缺少正式 runtime 或人工 UI 截圖仍保持 SAFE_MODE／MANUAL WAITING。
- **Exit Gate**：只有上述來源證據通過才標記 `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`；
  stage、commit、source freeze、build、EXE、Testing／Stable、簽署、發布與 push 不在本工作授權內。
- **Evidence**：conversion regression `34 passed, 1 skipped`；相關 bootstrap／catalog／dependency／
  version／stage 非 UI suite `41 passed`；本機 FFmpeg→ffprobe smoke `2 passed`，能力 probe smoke
  `1 passed`。quality、MOD `7 / 4`、網站 `12 / 33 / 49`、dependency lock `10`、version docs `4`、
  retained versions `5`、Repository 外 compileall、SAFE_MODE verify-only 與 `git diff --check` 通過。

### G39-04｜Gopeed Bridge、P2P Transfer、選用語音相依與格式工廠擴充

**Status**：`SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`。此工作完成時沒有 IN_PROGRESS 工作；
其來源後續納入已授權的 39.0.5 source freeze，但未授權 build、EXE、Testing／Stable、簽署、
發布、上傳或 push。

- **Goal**：把既有 policy-only Gopeed／P2P 候選收斂為可執行、無乾淨啟動副作用的內建 MOD；
  將 whisper-cli 與 Speech model 明確改為 Speech to Text 的選用執行相依；把本機轉檔工作區統一
  命名為「格式工廠」並加入常用音訊、影像與影片格式。
- **Scope**：只連線至使用者已啟動且明確設定 token 的 localhost Gopeed REST API；支援本機
  health／task list／create／pause／continue 與非強制 delete，HTTPS 直接檔案交由 Gopeed Bridge，
  `magnet:`／`ed2k:` 另受 P2P legal-use、絕對 storage root、容量與明確提交 Gate 約束。新增可信
  Transfer UI；不保存 token、不啟動 Gopeed、不提供 torrent 搜尋、不自動開埠、不強制刪除資料。
  Speech to Text 維持預設停用，缺 whisper-cli 或 model 時顯示選用相依而非使 MOD 註冊失敗。
  Automation 與 Speech to Text 以外的內建 MOD，只有新安裝／無保存狀態時預設啟用；既有使用者
  的明確狀態不覆寫。
- **Priority**：P1；使用者已明確要求，且既有 Gopeed／P2P 只有 policy、格式工廠名稱與格式集合
  不完整、Speech to Text 把可後補的 adapter／model 當成硬 readiness 缺口。
- **Dependencies**：使用者另行安裝與啟動的 Gopeed、官方 `/api/v1` REST 契約與
  `X-Api-Token`；既有 FeatureModRegistry、dependency snapshot、ConversionService、FFmpeg／
  ffprobe 與 manifest integrity pins。Gopeed、whisper-cli、模型均不隨核心下載或安裝。
- **Approach**：使用標準函式庫 HTTP client、timeout、1 MiB response 上限、exact response schema
  與可替換 transport；endpoint 驗證每次請求都限制 localhost，token 只保留於記憶體並在停用時
  清除。P2P 只建立明確協定 task；Gopeed 官方目前未提供本 Bridge 可可靠設定的全域上下傳速率
  欄位，因此 UI／文件不得宣稱 MediaManager 已套用實際頻寬限制，實際網路行為由使用者的
  Gopeed 設定負責。格式以固定 FFmpeg preset 加法擴充，不接受任意參數。
- **Compatibility**：既有 provider／preset ID 與 UserData schema 不變；新增 MOD、workspace 與
  preset 為加法。Feature 預設只作用於沒有保存狀態的全新資料目錄，既有明確停用保持不變。
  開發來源身分在 material 修正完成後同步為 `39.0.2`。
- **Risk**：本機 API token 洩漏、SSRF、超大／錯誤 JSON、Gopeed 狀態與實際檔案不一致、P2P
  合法性與上傳行為誤解、預設啟用造成乾淨啟動副作用、FFmpeg build 缺 codec。以 localhost-only、
  no-log／no-persist token、bounded response、明確 legal-use、非強制 delete、feature enabled 與
  transport configured 分離、固定 preset 與 capability failure 診斷控制。
- **Rollback**：移除兩個 runtime MOD／Transfer UI／新增 preset／選用相依呈現，回復新安裝預設
  與 `39.0.1` 身分；不刪除 Gopeed task、下載資料、模型、來源檔或 UserData，不修改外部 Gopeed
  設定。
- **Validation**：先執行 Gopeed request contract／local-only／bounded response／token redaction、
  P2P explicit legal-use、feature default persistence、Speech optional dependency 與新 preset RED；
  再執行相關非 UI runner、完整 runner、Ruff／quality、compileall、MOD／網站／依賴／版本／文字
  污染與 `git diff --check`。GUI 不自動互動；人工版面只接受使用者截圖，未提供時維持 MANUAL
  WAITING／SAFE_MODE。
- **Exit Gate**：來源證據全部通過後最多標記 `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`；任何
  發行或 Git 操作仍需另行逐項授權。
- **Evidence**：更新後精準組 `120 passed, 1 skipped`；114 個非 UI 測試檔
  `1007 passed, 6 skipped`；最終 Gopeed／Direct HTTP 安全邊界 `43 passed`。quality、MOD `7 / 4`、
  網站 `12 / 33 / 49`、dependency lock `10`、version docs `4`、retained versions `5`、Repository 外
  compileall、SAFE_MODE verify-only 與 `git diff --check` 通過。25 個含 PySide／GUI 操作的測試檔
  未執行；人工 UI 截圖與互動證據維持 WAITING／SAFE_MODE。

### G39-05｜Gopeed 官方 request schema 相容修正

**Status**：`SOURCE-FROZEN / NO PACKAGE / SAFE_MODE`。2026-07-23 已授權本輪精確範圍的 stage、
本機 commit 與 Development 39.0.5 source freeze；未授權 build、EXE、Testing／Stable、簽署、
發布、上傳或 push。

- **Goal**：讓 G39-04 的 direct create 與 P2P resolve request body 精確符合 Gopeed 官方
  OpenAPI `Request` schema，避免真實 Gopeed 因 unknown field 拒絕工作。
- **Scope**：只移除 `_request_model` 的未支援 `rawUrl`；保留 `url`／`labels`、localhost-only、
  記憶體 token、explicit action、容量／磁碟／legal-use 與 `force=false` delete Gate。
- **Priority**：P1；官方 schema 使用 `additionalProperties: false`，而 mock transport 無法自行揭露
  多餘欄位，因此這是會讓實際整合失敗的 wire-contract 缺口。
- **Dependencies**：Gopeed 官方 API Integration、OpenAPI／官方 JS client、既有可替換 transport
  與 request-body regression；不安裝或啟動 Gopeed。
- **Approach**：最小移除非官方欄位，讓 direct／P2P 共用 request builder；測試以 exact JSON
  body 斷言 `req == {url, labels}`，避免再次加入未驗證 compatibility guess。
- **Compatibility**：不改 provider ID、manifest、UserData、公開 MediaManager request model 或
  Gopeed task；開發來源身分升為 `39.0.3`。
- **Risk**：官方契約未來變動、外部 runtime 尚未安裝或設定；以官方文件重掃、固定 regression、
  no-startup-network 與 SAFE_MODE 控制。不以 mock 測試宣稱 live Gopeed 已成功。
- **Rollback**：一併回復 request builder、regression、39.0.3 身分與文件；不刪除 Gopeed task、
  下載資料、模型、UserData、來源檔或格式工廠輸出。
- **Validation**：Gopeed／P2P／Direct HTTP／版本精準非 UI runner，再執行全部不含 GUI 操作的
  runner、Ruff／quality、compileall、MOD／網站／依賴／版本／文字污染、SAFE_MODE verify-only 與
  `git diff --check`。不自動互動 GUI；缺外部 Gopeed 時只標明 live runtime 未驗證。
- **Exit Gate**：上述來源證據通過後標記 `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`；發行與 Git
  操作仍需另行逐項授權。
- **Evidence**：精準非 UI 組 `108 passed, 1 skipped`；114 個非 UI 測試檔
  `1011 passed, 6 skipped`。quality audit Ruff `361`／文字 `558`、MOD `7 / 4`、網站
  `12 / 33 / 49`、dependency lock `10`、version docs `4`、retained versions `5`、Repository 外
  compileall、SAFE_MODE verify-only 與 `git diff --check` 通過。25 個含 GUI marker 的測試檔排除；
  外部 Gopeed 與人工 UI 未執行，維持 SAFE_MODE。

### G39-06｜Gopeed／P2P 有限高度捲動版面修正

**Status**：`SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`。此工作完成時沒有 IN_PROGRESS 工作；
其來源後續納入已授權的 39.0.5 source freeze，但未授權 build、EXE、Testing／Stable、簽署、
發布、上傳或 push。

- **Goal**：在 940×620 等有限可用高度下完整保留 Bridge、HTTPS、P2P 與 task controls，改由
  垂直捲動瀏覽，不再讓 card、文字與控制項互相重疊。
- **Scope**：只調整 `trusted_ui.transfer_panel` 的可信 UI shell 與 layout constraint；不改 API、
  transport policy、token、P2P acknowledgement、task 或本機檔案。
- **Priority**：P1；39.0.3 使用者截圖提供可重現視覺證據，主要操作區已無法可靠閱讀或操作。
- **Dependencies**：既有 `workspaceScroll` theme、其他可信工作區已使用的 `QScrollArea`／
  `SetMinimumSize` 模式，以及不啟動 GUI 的純來源 contract test。
- **Approach**：將頁面內容移入 widget-resizable、無 frame、禁止水平捲動的 `QScrollArea`；內容
  layout 設最小尺寸 constraint，讓垂直 scroll range 承接不足高度。
- **Compatibility**：控制項、signal、provider ID、服務、設定與 UserData schema 不變；來源身分升為
  `39.0.4`，無 migration 或 breaking change。
- **Risk**：不同 DPI／字型可能改變 scroll range；採 Qt size hints 而非固定 pixel 高度。截圖無法
  證明鍵盤／UIA／讀屏／OS 高對比，相關人工證據保持 WAITING。
- **Rollback**：一併回復 scroll shell、regression、39.0.4 身分與文件；不刪除 Gopeed task、下載
  資料、UserData 或外部 Gopeed 設定。
- **Validation**：純來源／服務 regression `12 passed`；全部 114 個非 UI 測試檔
  `1012 passed, 6 skipped`。quality audit Ruff `361`／文字 `558`、MOD `7 / 4`、網站
  `12 / 33 / 49`、dependency lock `10`、version docs `4`、retained versions `5`、Repository 外
  compileall、SAFE_MODE verify-only 與 `git diff --check` 通過。修正版視覺結果只接受使用者截圖，
  不自動啟動或控制 GUI。
- **Exit Gate**：來源 Gate 通過後保持 `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`；人工截圖可補
  視覺證據，但不能授權或取代 G40 發行 Gate。

### G39-07｜Stable 1.0 身分與 sign-before-stage operator 修正

**Status**：`SOURCE-FROZEN / NO PACKAGE / SAFE_MODE`。2026-07-23 已授權本輪精確範圍的 stage、
本機 commit 與 Development 39.0.5 source freeze；未授權 build、EXE、Testing／Stable、簽署、
發布、上傳或 push。

- **Goal**：讓 Stable 使用獨立 `1.0.0` 公開身分，並保證 Authenticode 在 stage 與最終 hash／
  Ed25519 metadata 前完成；缺簽章或 handoff 不一致時 fail closed。
- **Scope**：只修改版本通道 mapping、`tools.build_version` split-phase operator、receipt validation、
  回歸與文件；不建立真實 EXE／Stable，不處理或保存 private key／certificate。
- **Priority**：P0；錯誤公開版本會破壞通道相容性，build 後立即 stage 則使 Authenticode 後的
  SHA-256／manifest 必然失效，兩者都直接阻擋正式版。
- **Dependencies**：既有 `release_identity_version`、isolated build work、`stage_version`、
  `authenticode_status`、clean Git revision 與 channel-aware release layout。
- **Approach**：Stable identity 明確映射為 `1.0.0`；`--build-only` 產生 receipt-bound handoff，
  綁定 core／release／channel、source revision 與 wheel SHA-256；`--stage-built` 只接受同一
  release track 的合法 attempt、相符 receipt、同一 clean revision 與未變更 wheel，並在 Stable
  Authenticode `Valid` 後才 stage。兩個操作互斥。
- **Source-freeze correction**：關鍵差異審查發現 Stable `display_version()` 仍引用 Development
  `CORE_VERSION`；回歸先重現「期待正式版 1.0、實際正式版 39.0」，修正後改由 `STABLE_VERSION`
  產生公開 UI 身分。
- **Compatibility**：Development 核心升為 `39.0.5`；Testing `1.1.0` 不變，Stable 公開身分是
  `1.0.0`。無 UserData、MOD protocol、provider 或 conversion schema migration。
- **Risk**：receipt 只是本機 operator handoff，不取代 production identity；外部簽署仍可能缺失、
  過期或使用錯誤憑證，最終仍需 preflight、exact signed set、SBOM、checksum 與 copied-folder。
- **Rollback**：回復版本 mapping、split-phase operator、回歸、39.0.5 身分與文件；不刪除任何
  UserData、歷史 Version、公開附件或未發布 signing work。
- **Validation**：Stable display RED `1 failed, 3 passed`；精準封裝／版本 GREEN `45 passed`；
  114 個非 UI 檔 `1019 passed, 6 skipped`；quality
  Ruff／文字 `361 / 558`、MOD `7 / 4`、網站 `12 / 33 / 49`、依賴 `10`、版本文件 `4`、保留版本
  `5`、Repository 外 compileall、Version bytecode `0`、SAFE_MODE verify-only 與 diff check 通過。
- **Exit Gate**：來源工作標記 `SOURCE-FROZEN / NO PACKAGE / SAFE_MODE`。只有另行授權並提供
  production 身分後，才可在 G40 執行真實 build／sign／stage／preflight。

### G39-08｜本機版本歷史整理安全邊界

**Status**：`SOURCE-FROZEN / NO PACKAGE / SAFE_MODE`。39.0.5 source-freeze commit 保留不變；
使用者已於 2026-07-23 明確授權這個 material source delta 的 stage、本機 commit 與 source freeze。

- **Goal**：在 Stable 1.0 已驗證、已上傳且上傳後 digest 一致時，為本機舊版本提供一份
  先審閱、後確認的精確刪除計畫；預設永遠不刪除。
- **Scope**：只處理 `Version` 下 legacy `X.Y` 與三個 release track 的精確版本資料夾；
  不處理 Git 追蹤的 release／roadmap 文件、GitHub Releases、UserData、`.work` 或 `dist`。
- **Priority**：P0；使用者的最終目標包含清理舊檔，而唯讀盤點證實 Development 16.1
  內嵌 UserData，且 audit log 與當前 UserData 不相同，不可使用 broad delete。
- **Dependencies**：至少兩個使用者明列的保留版本，其中至少一個 Stable 必須同時通過
  `audit_versions` 與 `release_preflight`；實際清理另需上傳後 digest 證據與獨立授權。
- **Approach**：`tools.prune_local_history` 默認 dry-run，輸出精確候選、檔案數與 bytes。
  discovery 只接受版本資料夾；候選含 UserData、symlink、junction／reparse point、
  無法讀取內容或重掃結果變化即整批拒絕。apply 需要精確
  `DELETE-LOCAL-RELEASE-HISTORY` 確認，且不接受單一 keep 或自動推論。
- **Compatibility**：Development 核心升為 `39.0.6`；Stable `1.0.0`、Testing `1.1.0`、UserData
  schema、MOD protocol 與已公開附件不變。
- **Risk**：刪除後無法從本機就地 rollback；因此 dry-run 本身不將 Stable preflight 視為
  upload 證據，真正 apply 仍必須由 G40 operator 先驗證備份／上傳。
- **Protected-data evidence**：唯讀盤點確認 `Version/Development/16.1/UserData` 有 6 個檔案、
  86,566 bytes；5 個與目前 UserData 的同路徑檔案相同，舊 `Logs/audit.jsonl` 則不同且不是
  目前檔案的行前綴。它必須在 prune 前獨立保存到 `Version` 外並以逐檔 hash 驗證，不可直接
  覆寫目前 audit 或把整個版本當成一般候選刪除。
- **Capacity evidence**：2026-07-23 `Version` 快照有 42 個 release 目錄、3,983 個檔案、
  15,344,278,530 bytes；排除預計保留的 `Development/38.0` 後，41 個現有候選為
  3,866 個檔案、14,789,775,742 bytes。這只是上限估算，未滿足 Stable／UserData／upload
  Gate 前不可 apply。
- **Rollback**：apply 前可完整回復工具、regression、39.0.6 身分與文件，不影響本機歷史。
  apply 後只能從已驗證備份復原，所以目前不執行。
- **Validation**：先以缺少 `tools.prune_local_history` 得到 collection RED；實作後精準
  regression `9 passed`，包含 dry-run 後保留版失效時拒絕 apply。116 個非 UI 測試檔
  `1029 passed, 6 skipped`；quality audit `363 / 560`、MOD `7 / 4`、網站 `12 / 33 / 49`、
  依賴 `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall、SAFE_MODE verify-only
  與 diff Gate 均通過。24 個含 Qt／PySide GUI 操作的測試檔依截圖優先政策未重跑；一次誤納
  GUI 的廣泛 runner 曾以兩個 stale「預設停用」測試假設失敗，測試來源已依 canonical 內建
  MOD 預設狀態校正，但該未重跑的 GUI 組不列為通過證據。
- **Exit Gate**：已前進為 `SOURCE-FROZEN / NO PACKAGE / SAFE_MODE`；完成當時 G40-01 曾恢復
  build-waiting，後續 G39-09 的 material trust-identity delta 使其在 39.0.7 固定前再次 blocked。

### G39-09｜production Ed25519 公開信任身分

**Status**：`SOURCE VALIDATED / SOURCE FREEZE WAITING / NO PACKAGE / SAFE_MODE`。
G39-08／39.0.6 source-freeze commit 保留不變；39.0.7 尚未取得 stage、本機 commit 或
source-freeze 授權。

- **Goal**：將已在 Repository 外建立之 production Ed25519 身分的非秘密 key ID／raw public
  key 編入驗證來源，讓 Stable 候選只接受相符私鑰。
- **Scope**：`core/security/release_key.py` 公開值、39.0.7 Development 修正號、回歸與目前文件。
  私鑰、本機私鑰路徑、密碼、PIN、Token、Authenticode 憑證與候選成品不納入來源。
- **Priority**：P0；compiled identity 空白時 `release_preflight` 必然拒絕所有 Stable 候選。
- **Dependencies**：Repository 外私鑰已由既有 loader 成功重載，重新導出的 public key 與編入值
  一致；後續仍依賴本工作 source freeze、build-only 授權與 production Authenticode `Valid`。
- **Approach**：先新增 compiled identity regression，在空白設定取得 `1 failed, 6 passed`；再只
  編入公開 key ID／Base64 raw public key。回歸沿用 preflight key ID regex，且要求嚴格 Base64
  解碼結果正好 32 bytes。
- **Compatibility**：Development 核心升為 `39.0.7`；Stable `1.0.0`、Testing `1.1.0`、UserData、
  MOD protocol、release manifest 與簽署 CLI 不變。
- **Risk**：錯誤 public key 會讓正確私鑰無法簽署或讓候選啟動失敗；既有簽署工具會在寫檔前
  比對私鑰導出的 public key，正式 preflight 仍需 exact staged set。
- **Rollback**：build 前回復公開身分、39.0.7 版本、回歸與文件；不刪除或輸出外部私鑰，
  不修改 UserData、歷史版本或 39.0.6 commit。
- **Validation**：精準 release／version `27 passed`；116 個非 UI 測試檔合計
  `1030 passed, 6 skipped`。quality audit `363 / 560`、MOD `7 / 4`、網站 `12 / 33 / 49`、
  依賴 `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall `363`、SAFE_MODE
  verify-only 與 diff check 通過。歷史 Development 38.0 preflight 已不再報 compiled identity
  invalid，但仍因舊 MOD、缺 manifest 與 Authenticode `NotSigned` fail closed。沒有 Authenticode、
  build、簽署、stage、Stable 建立、發布、上傳或 push。
- **Exit Gate**：來源通過後仍為 `SOURCE FREEZE WAITING`；只有取得 39.0.7 的精確
  stage／commit／source-freeze 授權，G40-01 才可回到 build-waiting。

## 40.0｜可重現候選與發行完整性

**Status**：`SOURCE FREEZE WAITING / BUILD BLOCKED`。
G39-08／39.0.6 的 stage、本機 commit 與 source freeze 已於 2026-07-23 取得明確授權；
G39-09／39.0.7 是尚未固定的 material trust-identity delta。未取得 39.0.7 source freeze 及
build／candidate、EXE、Testing／Stable、簽署、發布、上傳或 push 的逐項明確授權前不啟動
後續操作。Stable-only
G40-02 仍受正式簽署身分與通道決定阻擋。

- **Goal**：在另行授權後，從 clean revision 產生可驗證、可回退且明確為 unsigned
  `SAFE_MODE` 的 Development candidate；Stable 只保留條件式 Gate。
- **Scope**：Development 只涵蓋固定 Deno／FFmpeg 與授權、runtime policy audit、SBOM、
  release-info、SHA-256 與 copied-folder current→previous→current。Stable-only G40-02 才涵蓋
  sign-before-stage／exact signed set operator；不建立 Testing／Stable、不推送，除非使用者
  在該步驟另行明確授權。
- **Priority**：P0，為最後 release-integrity Gate。
- **Verified gap／Unknown**：Development 38.0 的 pinned runtime、checksum 與 copied-folder
  current→previous→current 已實測通過。2026-07-22 source-only
  `python -B main.py --verify-only` 已 exit 0 並精確輸出
  `MediaManager security mode: SAFE_MODE`；此證據不代表 staged candidate、copied-folder 或 headless。
  上述 staged verify／headless 證據仍缺；Stable split-phase CLI wiring 已於 G39-07 完成來源驗證，
  但真實 EXE、production Authenticode、候選 Ed25519 簽署及正式 preflight 仍未知。
- **Dependencies**：G34～G39 與正式 runtime；本次單一 Development 38.0 打包授權不啟動 G40，
  也不跨越 G38／G39。Stable-only G40-02 另依賴
  production Ed25519 私鑰、Authenticode 憑證與使用者通道決定；私鑰不得進入來源或 Log。
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

- 新網站、P2P 搜尋／tracker 探索、通用解析器、雲端同步、帳號與自動更新；Gopeed／P2P 只限
  G39-04 的 localhost external bridge 與使用者明確提供的 magnet／ed2k，不擴張為遠端控制或搜尋。
- 需要 DRM、登入、Cloudflare、廣告、付費或地區限制繞過的功能永久排除；通用 Cookie／Header
  接管、瀏覽器 Cookie 擷取、播放串流攔截、M3U8／金鑰／分段擷取亦永久排除。已退役的動畫瘋
  exact-host／session-only Cookie 不得轉為通用能力或重新接線。
- 參考軟體差異只有在量測或明確需求證明價值後，才可另立新 scope；不得回填進本計畫。

## 完成與停止條件

40.0 的 Development Exit Gate 完成後，本計畫停止自動擴張並回報總結；不得自動建立 41.0、
Testing 或 Stable。若任一版本沒有 material delta，依規則標記 `ABSORBED / NO RELEASE` 並前進到
下一個已證明缺口；不得為維持版本數量而建立空附件。
