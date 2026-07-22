# Development 32.1 工作樹與計畫基線

狀態：`FIX-34-02 DONE / 34.0 SOURCE-FROZEN`。本文件保存 32.1 後續工作樹與
31.0～43.0 計畫在 source freeze 前的唯一清冊。使用者已於 2026-07-18 回覆「繼續更新」，核准當時全部 90 個路徑進入
Development 34.0 review scope；後續 source-freeze 審查新增設定併行安全、降版回復、
MOD 交易回復、build ownership、pytest 暫存根目錄隔離與相符回歸／文件，形成 106 個路徑的
freeze 前快照。使用者於 2026-07-19 先授權 34.0 stage、本機 commit 與 source freeze，後續再明確
授權將目前 35.0～38.0 核准變更 stage、本機 commit、固定為 Development 38.0 source freeze，
並建立一次 SAFE_MODE 未簽署 Development 38.0 包；仍未授權 push、Testing／Stable、簽署、
發布或覆寫歷史版本。

2026-07-19 後續新增的 G38-02 工作不屬於上述 freeze：它由動畫瘋作品／集數與內嵌播放失敗
證據啟動，首次來源基線為 38.1.0。使用者後續決定停止此整合；G38-02 已於 38.1.15 標記
`CLOSED / CANCELLED BY USER SCOPE DECISION / REMOVED / NO RELEASE`，38.1.14 為
`SOURCE VALIDATED / SUPERSEDED BY 38.1.15 / NO PACKAGE`。38.1.15 只固定來源移除與
SAFE_MODE 身分，未 stage、commit、source freeze、build 或建立套件，也不覆寫 38.0 產物或
刪除使用者資料。38.1.16 後續只收斂 PyInstaller 內建 MOD 的精確封裝白名單，仍未建立套件。
G39-01 已完成為 `MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE`。G39-02 由本機影像 preset
的 failing regression 啟動 Development 39.0.0；第一工作包與完整來源 Gate 已完成，
未 stage、commit、freeze、build 或建立套件。G39-03／Development 39.0.1 已
`SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`，補本機 capability、磁碟 preflight 與 ffprobe commit Gate；
G39-04／Development 39.0.2 已為 `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`，
新增 localhost-only Gopeed／P2P runtime、Speech 選用相依、格式工廠 preset 與新 profile 預設；
  G39-05／Development 39.0.3 為 `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`，修正 Gopeed
  create／resolve request 多送官方 schema 不接受的 `rawUrl`；G39-06／Development 39.0.4 現為
  `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`，依人工截圖加入 Transfer 工作區垂直捲動與
  minimum-size layout contract，修正有限高度 card 重疊；G39-07／Development 39.0.5 現為
  `SOURCE VALIDATED / NO PACKAGE / SAFE_MODE`，將 Stable 公開身分固定為 1.0.0，並完成
  receipt-bound build-only／Authenticode 後 stage-built operator；
source-only verify-only 已有精確 SAFE_MODE stdout。使用者於 2026-07-23 明確授權將目前核准變更
stage、本機 commit 並固定為 Development 39.0.5 source freeze；不包含 push、build、EXE、
Testing／Stable、簽署、發布或上傳。G40-01 因而只前進到 source-freeze precondition，仍等待
build／candidate 授權與 staged candidate／headless 證據。

## 快照與判定界線

- 快照時間：2026-07-18（source-freeze P0／P1 修正與完整驗證後）。
- Branch：`codex/development-17`（歷史工作分支名稱，不代表目前 Development generation；
  source freeze 身分只以最終核准的 34.0 commit hash 與 fingerprint 為準）。
- Freeze 前工作樹：65 個 tracked modified、0 staged、41 個 untracked，共 106 個路徑；
  其中本文件、候選 schema 相容修正與 PowerShell wrapper 安全測試是基線盤點後的
  修正差異。
- 106 個路徑均有語意歸屬；沒有無法分類的檔案。使用者已核准原始 90 個路徑進入
  34.0 review；其後新增路徑是 source-freeze 審查發現的低風險安全修正與證據。
  最終依 91 項主要 intent 與 15 份歷史文件 intent 分開提交；這仍不構成 build 或 release 授權。
- `git status` 現在不再輸出舊 Repository 暫存目錄 ACL 警告；測試使用
  `%LOCALAPPDATA%\MediaManager-TestRuns` 的 invocation-owned 目錄，品質入口只掃明確來源。
  根目錄 `/pytest-of-*/`、`/pytest-agent-*/` 與 `/pytest-ani-agent-*/` ignore 規則只把
  已知 pytest 暫存家族排除於來源清冊，不代表已讀取、驗證或
  核准其中內容；沒有刪除使用者資料、take ownership 或廣域放寬 ACL。

## 變更清冊

| 分類 | Modified | Untracked | 合計 | 判定 |
|---|---:|---:|---:|---|
| 版本／契約 | 11 | 2 | 13 | 32.1 版本、provider capability、MOD catalog／group／manifest |
| 核心 | 8 | 1 | 9 | Bootstrap、下載狀態、通知、佇列、子程序、Feature、自檢、設定與快照 |
| UI | 14 | 1 | 15 | 工作區、播放器、下載／MOD 面板、縮圖、設定與首次設定 |
| 測試／工具／CI | 28 | 17 | 45 | `.gitignore` 測試暫存隔離、回歸測試、安全測試入口、品質／版本／runtime／copied-folder／設定回復／候選稽核與 CI |
| 文件 | 4 | 20 | 24 | 入口、版本配置、release、31.0～43.0 roadmap、34.0～40.0 主計畫、回復 runbook 與本清冊 |
| 未知 | 0 | 0 | 0 | 無；但「可解釋」不等於「已核准發行」 |
| **總計** | **65** | **41** | **106** | **freeze 前快照；已提交** |

### Source-freeze commit 分區（已完成）

- 34.0 功能、安全、測試、工具、CI、目前有效文件與 `.gitignore` 共 91 個路徑，屬主要
  source-freeze intent。
- 15 份 superseded／historical release 與 roadmap 文件另作歷史保存 intent，不混入功能
  commit：`release-29.0-30.0.md`、`roadmap-development-30.0-31.0.md`、
  `roadmap-development-31.0-32.0.md`，以及單版 31.0、32.0、33.0、35.0～43.0 roadmap。
- 兩個 intent 已依序完成；只以最終核准的 34.0 tip commit hash／fingerprint 識別 source
  freeze。hash 與 fingerprint 於 clean commit 後在交付回報，不寫回同一 commit 造成自我參照；
  本次授權不包含 build 或發行。

### 版本／契約（13）

- Modified：`core/builtin_mod_catalog.py`、`core/downloads/builtin_integrity.py`、
  `core/downloads/capabilities.py`、`core/mod_groups.py`、`core/version.py`、
  `pyproject.toml`、`mod/builtin/ani-gamer/group.json`、
  `mod/builtin/ani-gamer/locales/en.json`、`ja.json`、`zh-CN.json`、`zh-TW.json`。
- Untracked：`contracts/provider_capability_v1.py`、
  `mod/builtin/ani-gamer-player/feature.json`。

### 核心（9）

- Modified：`core/bootstrap/bootstrap.py`、`core/downloads/models.py`、
  `core/downloads/notifications.py`、`core/downloads/queue.py`、
  `core/downloads/subprocess_provider.py`、`core/features/registry.py`、
  `core/self_check.py`、`core/settings.py`。
- Untracked：`core/builtin_mod_snapshot.py`。

### UI（15）

- Modified：`trusted_ui/ani_gamer_offline.py`、`ani_gamer_workspace.py`、
  `bilibili_workspace.py`、`builtin_mod_control.py`、`builtin_mod_panel.py`、
  `direct_http_workspace.py`、`download_panel.py`、`main_window.py`、
  `mega_workspace.py`、`mod_pages.py`、`search_panel.py`、`self_check_probe.py`、
  `thumbnail_loader.py`、`youtube_workspace.py`。
- Untracked：`trusted_ui/initial_mod_setup.py`。

### 測試／工具／CI（45）

- Modified tests：`tests/test_ani_gamer_offline.py`、
  `test_ani_gamer_workspace.py`、`test_bootstrap_wiring.py`、
  `test_build_version.py`、`test_builtin_mod_catalog.py`、
  `test_builtin_mod_control.py`、`test_builtin_mod_panel.py`、
  `test_dependency_snapshot.py`、`test_download_notifications.py`、
  `test_download_queue.py`、`test_entrypoint.py`、`test_feature_mod_registry.py`、
  `test_main_window_presentation.py`、`test_plugin_ui.py`、`test_quality_workflow.py`、
  `test_release_candidate.py`、`test_release_signing_dry_run.py`、`test_self_check.py`、
  `test_subprocess_provider.py`、`test_thumbnail_loader.py`、`test_ui_action_state.py`、
  `test_version_channels.py`。
- Modified tools／CI：`tools/audit_text_pollution.ps1`、
  `tools/build_version.py`、`tools/release_signing_dry_run.py`、
  `tools/release_candidate.py`、
  `.github/workflows/quality.yml`。
- Untracked tests：`tests/test_audit_staged_runtime.py`、
  `tests/test_audit_version_docs.py`、
  `test_audit_text_pollution_wrapper.py`、`test_builtin_mod_snapshot.py`、
  `test_copied_folder_smoke.py`、
  `test_initial_mod_setup.py`、`test_provider_capability_v1.py`、
  `test_quality_audit.py`、`test_run_tests.py`、`test_settings.py`、
  `test_settings_rollback.py`。
- Untracked tools：`tools/audit_staged_runtime.py`、
  `tools/audit_version_docs.py`、
  `tools/copied_folder_smoke.py`、`tools/quality_audit.py`、
  `tools/run_tests.py`、`tools/settings_rollback.py`。

### 文件（24）

- Modified：`AGENTS.md`、`README.md`、`docs/README.md`、
  `docs/version-layout.md`。
- Untracked release／range：`docs/release-29.0-30.0.md`、
  `docs/release-33.0-34.0.md`、
  `docs/roadmap-development-30.0-31.0.md`、
  `docs/roadmap-development-31.0-32.0.md`、
  `docs/roadmap-development-34.0-40.0.md`。
- Untracked single-version roadmap：`docs/roadmap-development-31.0.md` 至
  `docs/roadmap-development-43.0.md`。
- Untracked canonical inventory：本文件。
- Untracked runbook：`docs/settings-pre35-rollback.md`。

## 語意變更束

| 變更束 | 狀態 | 主要證據 |
|---|---|---|
| 32.1 版本與入口文件 | 自動化完成 | `tools.audit_version_docs` 與回歸測試 |
| 34.0 來源身分／runtime policy audit | 自動化完成 | canonical version、release 文件、離線 audit 與回歸測試 |
| Provider capability v1／自檢 | 自動化完成 | 契約、capability、自檢與契約測試 |
| MOD 快照／父子交易回復 | 自動化完成 | snapshot、control 與回復測試 |
| 首次 MOD 選擇 | 自動化完成 | 初始設定、settings 與測試 |
| 設定併行寫入／pre-35 回復 | 自動化完成 | OS 排他鎖、typed patch、dry-run／SHA／owned backup 工具與回歸 |
| 下載 `RETRYING`／通知一致性 | 自動化完成 | queue、notifications、panel 與測試 |
| 動畫瘋播放器／封存（歷史） | `RETIRED / REMOVED IN 38.1.15 / HISTORICAL EVIDENCE ONLY` | 不再排程 live smoke；現行只驗證零 runtime／UI／provider 註冊並保留 UserData、歷史文件與不可變 38.0 產物 |
| 縮圖／工作區資源釋放 | 自動化完成 | loader、各工作區與回歸測試 |
| pytest／build／signing 暫存隔離 | 自動化完成 | `tools.run_tests`、build/signing 工具與測試 |
| 品質遍歷邊界 | 自動化完成 | `tools.quality_audit`、CI 與污染回歸測試 |
| copied-folder／回退 | 完成 | 32.1→32.0→32.1 共用 UserData，9 個既有 EXE 命令通過；來源未變且 attempt 已清除 |
| 候選 metadata schema | 自動化完成 | `release_candidate` 嚴格支援 2/2 與目前 3/3，混用／未知版本 fail closed |
| 正式 runtime／簽章／網站／UI | 阻擋 | 外部檔案、正式身分與人工環境未具備 |

## 31.0～43.0 狀態矩陣

| Roadmap | 收斂狀態 | 判定 |
|---|---|---|
| 31.0 | `DONE / SUPERSEDED` | Development 產物與 range 文件已有完成證據；單版規劃不再活動。 |
| 32.0 | `DONE / SUPERSEDED` | Development 產物完整保留；單版規劃不再活動。 |
| 33.0 | `DONE` | P0／P1 已驗收；P2 只保留 deferred 候選。 |
| 34.0 | `DONE / SOURCE-FROZEN` | VUP-34-02 已完成，本修正序列由 clean revision 固定。 |
| 35.0 | `DONE / SOURCE ONLY / SAFE_MODE` | G35-01 已吸收到 34 freeze；G35-02A～E 的 graph、bounded lifecycle journal、Supervisor ownership、candidate transaction、dependency-safe toggle、topological recovery、文件與完整 Gate 均完成；後續納入 Development 38.0 source freeze，未建立 35.0 候選包。 |
| 36.0 | `DONE / SOURCE ONLY / SAFE_MODE` | 六個列名非特權 result DTO 已使用一致、有界且不持久化 extras 的加法 reader；特權 capability／manifest 契約維持 strict，完整 Gate 已完成。 |
| 37.0 | `DONE / EVIDENCE READY / NO CLAIM / SOURCE ONLY / SAFE_MODE` | 去識別原生／provider 證據、queue／self-check 邊界、runbook 與完整 Gate 已完成；未知 crash／exit 1 不宣稱已修復。 |
| 38.0 | `BASELINE FROZEN / PACKAGE BUILT / G38-01 MANUAL REVALIDATION BLOCKED / SAFE_MODE` | 來源身分為 38.0.0；source freeze `6534e3f…1107` 與一次未簽署 Development 包已完成且不可覆寫。runtime 6/6、116 筆 checksum、copied-folder `38.0 → 32.1 → 38.0` 與回退均通過；EXE 為 `NotSigned`。 |
| 38.1.0 | `G38-02 SOURCE BASELINE / SUPERSEDED BY 38.1.1 / NO PACKAGE` | 首次來源基線；系統瀏覽器官方播放優先，動畫瘋 exact-host session Cookie 只供目錄／集數且來源回歸已通過。未 stage、freeze 或 build。 |
| 38.1.1 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.2 / NO PACKAGE` | 修正 capability 不支援／未知時仍顯示內嵌黑畫面的 fail-closed 缺口；非 GUI 與版本 Gate 已通過，未 stage、freeze 或 build。 |
| 38.1.2 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.3 / NO PACKAGE` | 收斂不支援時的大型深色 fallback，並區分作品頁與選取集數的相容性操作；未同步的 locale integrity pins 由 38.1.3 修正。未 stage、freeze 或 build。 |
| 38.1.3 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.4 / NO PACKAGE` | 同步 AniGamer 四語資源的 SHA-256 pins，恢復父 MOD 安全載入；由 38.1.4 接續。未 stage、freeze 或 build。 |
| 38.1.4 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.5 / NO PACKAGE` | canonical 官方單集網址改由本機建立獨立單集列；目錄第一擊可 arm allowlist query，但後續只能再點完全相同快捷操作，沒有獨立可見確認且受 busy／狀態清除影響。未 stage、freeze 或 build。 |
| 38.1.5 | `G38-02 SOURCE VALIDATED / LIVE PRODUCT FAIL / SUPERSEDED BY 38.1.6 / NO PACKAGE` | browser-verification 後顯示獨立官方目錄確認操作，OS opener 失敗時保留重試；後續人工畫面證明 direct episode 上方空作品區仍占 220px，且目錄相容性操作誤入 media codec gate。擴充非 GUI 組 `47 passed`；未 stage、freeze 或 build。 |
| 38.1.6 | `G38-02 SOURCE VALIDATED / LIVE PRODUCT FAIL / SUPERSEDED BY 38.1.7 / NO PACKAGE` | direct episode 與目錄 handoff 的來源 Gate 已通過；後續人工證據顯示目錄「重試」可取得單來源上限 20 筆而非 stale，但手動集數網址每次覆寫前一列，官方頁四集與工作區一列不一致。未 stage、freeze 或 build。 |
| 38.1.7 | `G38-02 SOURCE VALIDATED / LIVE PRODUCT FAIL / SUPERSEDED BY 38.1.8 / NO PACKAGE` | 手動集數 lossless append／dedupe 與 fallback Retry 的來源 Gate 通過；後續人工搜尋畫面與來源追蹤證明 structured failure 會先清空上一批作品、選取與集數。未 stage、freeze 或 build。 |
| 38.1.8 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.9 / NO PACKAGE` | 新 catalog reducer 讓 `failure + 0 accepted` 保留上一批有效狀態，partial success 與成功空結果維持原語意；四語提示明示保留列不是本次查詢結果。精準組 `2 passed`、擴大非 UI 組 `103 passed, 1 skipped` 與全部來源 Gate 通過；首次官方拒絕仍安全降級，不繞驗證。未 stage、freeze 或 build。 |
| 38.1.9 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.10 / NO PACKAGE` | 集數成功／失敗回應套用前核對請求作品與目前選取作品；切到 B 後不再讓舊 A 回應污染 B。純回歸先 `2 failed`，修正後 `2 passed`、相關純測 `6 passed`；不改 provider、網路、Cookie、codec 或 handoff。未 stage、freeze 或 build。 |
| 38.1.10 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.11 / NO PACKAGE` | canonical 動畫瘋作品／單集網址只接受原始 query 精確 `sn=<ASCII digits>`；額外、重複、大小寫與 percent-encoded alias fail closed，集中保護 provider、handoff、history 與 offline。相關非 UI 組 `205 passed, 1 skipped` 與全部來源 Gate 通過。未 stage、freeze 或 build。 |
| 38.1.11 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.12 / NO PACKAGE` | canonical item ID 必須與 URL `sn` 一致；作品／集數 filter、handoff、history 與 offline 讀寫共用 validator，busy／closing 時拒絕舊單集 handoff。最終相關非 GUI 組 `129 passed, 1 skipped in 7.23s` 與來源 Gate 通過。未 stage、freeze 或 build。 |
| 38.1.12 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.13 / NO PACKAGE` | 四語 `episode_opened` 與選取單集／history handoff 將 exact canonical URL 顯示於 OS 接受請求的訊息，並明示頁面載入／播放未確認。RED `1 failed in 0.42s`、GREEN `2 passed in 0.94s`，擴大非 UI 組 `143 passed, 2 skipped in 1.60s` 與來源 Gate 通過。未 stage、freeze 或 build。 |
| 38.1.13 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.14 / NO PACKAGE` | 相容性彈窗不再固定誤用 `catalog_opened`：依 exact route 使用 `episode_opened`／`series_opened`，單集訊息顯示 exact canonical URL，且 OS 拒絕或 `RuntimeError` 的成功／失敗結果鏡像到 dialog-local status，不再只寫入被彈窗遮住的主狀態。精準回歸 RED `1 failed in 1.27s`、GREEN `1 passed in 0.71s`；來源 Gate 已通過，38.1.13 人工截圖待補。未 stage、commit、freeze、build、package 或 push。 |
| 38.1.14 | `G38-02 SOURCE VALIDATED / SUPERSEDED BY 38.1.15 / NO PACKAGE` | `dispatch_official_url` 的 transport positional `url` 與 message placeholder `url=` 會在 helper body 前發生 Python 綁定衝突；將前者改名為 `official_url` 並同步內部引用。純回歸 RED `1 failed in 1.20s`、handoff GREEN `4 passed in 1.08s`；同步後相關非 UI／版本組 `135 passed, 1 skipped in 1.87s` 且來源 Gate 通過。部分可見畫面證據已補；後續由 38.1.15 的移除決策取代，未 stage、commit、freeze、build、package 或 push。 |
| 38.1.15 | `SOURCE VALIDATED / ANI-GAMER MOD REMOVED / NO PACKAGE / SAFE_MODE` | G38-02 依使用者範圍決定標記 `CLOSED / CANCELLED BY USER SCOPE DECISION / REMOVED / NO RELEASE`；移除目前來源註冊與執行接線，保留使用者資料、歷史文件與不可覆寫的 Development 38.0，不轉接至 Direct HTTP。完整 repository runner `1201 passed, 6 skipped`，quality／MOD／網站／依賴／版本／compileall／污染檢查通過；live provider smoke 因缺少 bundled Deno／FFmpeg 維持 `WAITING`。未 stage、commit、freeze、build、package 或 push。 |
| 38.1.16 | `SOURCE VALIDATED / PACKAGING INPUT HARDENED / NO PACKAGE / SAFE_MODE` | PyInstaller 內建 MOD data inputs 改用完整性釘選的精確 87 檔清冊，缺檔或不安全路徑 fail closed；純展開為 `87 / 87 / 0 unexpected / 0 missing / 0 contaminating`，stage-version／spec 回歸 `12 passed`。未 build，post-build EXE 仍待獨立授權與驗證。 |
| 39.0.0 | `G39-02 SOURCE VALIDATED / NO PACKAGE / SAFE_MODE` | G39-01 的量測工作保持 `MEASURED / NO CHANGE / NO RELEASE`；後續影像 preset 缺口以 RED `4 failed` 啟動 G39-02。既有 Media Convert 新增 PNG／JPEG／WebP 單幀本機轉檔、輸入副檔名限制、UI／automation wiring、本機 protocol／linklike 路徑 Gate 與 64 KiB 去識別 FFmpeg stderr。完整 runner `1222 passed, 7 skipped`，品質／MOD／網站／依賴／版本／compileall／SAFE_MODE／diff Gate 通過；未 stage、commit、freeze、build、package 或 push。 |
| 39.0.1 | `G39-03 SOURCE VALIDATED / NO PACKAGE / SAFE_MODE` | 補 FFmpeg version／build／formats／encoders／filters／hwaccels probe、256 MiB 轉檔磁碟 reserve 及 atomic commit 前 ffprobe stream 驗證。conversion `34 passed, 1 skipped`、相關非 UI `41 passed`，本機影音／影像 smoke `2 passed`，實際 capability smoke 修正 2 欄 filter flags 後 `1 passed`；quality、MOD、網站、依賴、版本、compileall 與 diff Gate 通過。 |
| 39.0.2 | `G39-04 SOURCE VALIDATED / NO PACKAGE / SAFE_MODE` | 新增 localhost-only Gopeed Bridge／P2P Transfer、Speech optional runtime dependencies、格式工廠新增 WebM／AVI、AAC／Opus／WAV、BMP／TIFF，以及除 Automation／Speech 外的新 profile 預設啟用。非 UI `1007 passed, 6 skipped`、最終安全邊界 `43 passed`，全部來源 Gate 通過；25 個含 GUI 操作的測試檔依截圖優先政策未執行。 |
| 39.0.3 | `G39-05 SOURCE VALIDATED / NO PACKAGE / SAFE_MODE` | 移除 Gopeed 官方 `Request` schema 不接受的 `rawUrl`，由 exact body regression 鎖定 direct create 與 P2P resolve；精準非 UI `108 passed, 1 skipped`、完整非 UI `1011 passed, 6 skipped`，其餘 localhost、token、P2P 與非強制刪除邊界不變。 |
| 39.0.4 | `G39-06 SOURCE VALIDATED / NO PACKAGE / SAFE_MODE` | 依 39.0.3 人工截圖，Gopeed／P2P 工作區加入 `workspaceScroll` 與 minimum-size layout contract，有限高度改用垂直捲動而不壓扁 card；非 UI `1012 passed, 6 skipped` 且來源 Gate 通過，修正版人工截圖待確認。 |
| 39.0.5 | `G39-07 SOURCE-FROZEN / NO PACKAGE / SAFE_MODE` | Stable identity 與 UI display 固定為獨立 `1.0.0`／「正式版 1.0」；正式版 operator 拆為 receipt-bound build-only 與 Authenticode `Valid` 後 stage-built，拒絕 revision／receipt／wheel mismatch。display RED `1 failed, 3 passed`、精準封裝／版本 GREEN `45 passed`、非 UI `1019 passed, 6 skipped`，其餘來源 Gate 通過；2026-07-23 已授權 stage、本機 commit 與 source freeze，未實際 build、簽署或 push。 |
| 40.0 | `SOURCE FREEZE AUTHORIZED / BUILD WAITING / STAGED CANDIDATE + HEADLESS EVIDENCE REQUIRED` | G39 prior gate 已關閉；2026-07-22 source-only `python -B main.py --verify-only` 已 exit 0 並精確輸出 `MediaManager security mode: SAFE_MODE`。39.0.5 source freeze 已於 2026-07-23 授權，但不證明 staged candidate／copied-folder／headless；build／candidate、EXE、Testing／Stable、簽署、發布、上傳與 push 仍未授權，production 身分與真實 staged Stable preflight 仍條件式阻擋。 |
| 41.0 | `DONE BASELINE` | 安全測試與品質入口已完成；歷史清理仍不在授權範圍。 |
| 42.0 | `SUPERSEDED BY FIX-34-02` | 本清冊即其缺少的收斂結果。 |
| 43.0 | `HISTORICAL / PARTIALLY ABSORBED` | capability self-check、播放器／manifest 已有實作；外部／人工／候選證據分別由 G37／G38／G40 管理，未接線的 capability-to-button routing 留在 deferred backlog。 |

2026-07-22 post-removal completion audit：目前 root 工作樹已無動畫瘋 catalog、integrity、capability、
workspace 或 route 註冊；Direct HTTP 的 `gamer.com.tw` deny rule 是必須保留的安全邊界。其餘功能
critical subset 為 `98 passed, 1 skipped`，另以不可覆寫 Development 38.0 既有 FFmpeg／ffprobe
驗證本機 conversion 與 Bilibili MKV／ASS mux，結果 `2 passed`。TODO／FIXME／HACK／
NotImplemented、xfail 與可證 material bottleneck 均為 `0`，因此本輪維持 `NO MATERIAL DELTA /
NO NEW VERSION / NO RELEASE`。刪除尚未 staged，故 Git `HEAD`、舊 `build/`／`dist/` 與
Development 38.0 仍可能含舊動畫瘋整合；它們只屬歷史或待授權候選清理邊界，不得冒充目前來源。

G38 AniGamer 歷史證據邊界：使用者提供的 Development 37.0 截圖是 pre-fix baseline，記錄內嵌
H.264／AAC／HLS／MSE 不可用與集數 403／瀏覽器驗證安全降級；現行修正只提升系統瀏覽器
主操作的可見性。G38-02 另加入使用者主動貼上、exact-host、session-only Cookie 供動畫瘋
目錄／集數 GET 使用；拒絕 Cloudflare 驗證狀態、不保存，也不攔截串流或繞過 DRM、廣告、
登入、付費、地區限制。UI 採截圖優先、禁止自動互動；截圖不能完成 Tab、UIA／NVDA／讀屏或
Windows OS 高對比 Gate，因此 G38-01 人工矩陣仍保持 `MANUAL REVALIDATION BLOCKED / SAFE_MODE`。
G38-02 的 runtime／UI 整合已在 38.1.15 移除；不得把舊 Cookie、catalog、episode 或 handoff
路徑重新接到通用 Direct HTTP，也不得以移除為由刪除既有使用者資料。

38.1.5 Root Cause／evidence boundary：38.1.4 的第一擊 wiring 已成功進入 armed 狀態，不能宣稱
四鍵 wiring 斷線；舊流程的缺口是不可見且時序脆弱的 exact-second-click，以及 direct episode row
留在 fold 下。38.1.5 以獨立明示確認操作與 populated episode-table focus 修正；Rollback 為一起
保留 OS opener 失敗後的重試，並回復操作、焦點、四語文字／完整性釘選與版本身分，不刪資料或
覆寫 38.0。使用者截圖
`9e44c01c…`（SHA-256 `1c3720949e0530d404823f6047e91c6106782af603a39ffc11ca36dc0a5f8854`）與
`24bbcaa7…`（SHA-256 `5605edd28f93048765b7890b286e1293bfc1790f3afef82e3e776e5a6e77f794`）
只支持第一擊 armed／缺少獨立完成操作；`2d13c4cf…`（SHA-256
`0db2a37d53bf0b97d34c8bcf13baf7c2c480592b34a24ee8213abd3f43f276ae`）只支持 canonical 單集已辨識
但列位於裁切下方。三圖皆不證明點擊、網路回應、OS handoff、完整集數、播放或下載。

38.1.6 Root Cause／evidence boundary：38.1.5 的 `fa442…` 畫面（SHA-256
`ECBC583EB97BAA2A8774C02627847BCB01113FEC589AE9F6931B545E1FC54CE3`）證明 browser-verification
arm 與獨立確認操作可見；`552848…`（SHA-256
`71FEEF01E3CE71D616755581E94CCE124B04AFF3982B321173B696A068AB5CBE`）證明另一個目錄入口錯走
media codec fallback；`ea3b…`（SHA-256
`CECCEF2F01CE18F4282703BB61A8E426E6C8C438500DC0F4EBEAB7902B52CFEC`）證明 canonical 單集已本機
辨識，但空作品表仍占畫面且單集列在 fold 下。38.1.6 只修 result-area visibility、post-populate
focus、目錄 system-browser routing 與 exact armed target；Rollback 逐項回復上述來源差異與版本身分，
不刪資料、不覆寫 38.0。三圖不能證明實際點擊、OS handoff、完整集數、播放或下載。

38.1.7 Root Cause／evidence boundary：38.1.6 的八張人工畫面證明介面篩選後「重試」可重新取得
20 筆官方作品，該數量是單來源安全上限；集數 provider 的驗證 fallback 則讓每次手動 URL 取代
既有清單，且與系統瀏覽器官方頁可見四集不一致。38.1.7 只加入 lossless append、`video_id`／URL
dedupe 與 fallback Retry wiring；不推算相鄰 SN、不讀 browser DOM／Cookie、不繞過驗證。終端
`CODE:4`／`setVolume` 保持本機 codec／站方次生錯誤，播放仍交給系統瀏覽器，未宣稱內嵌修復。
八圖完整 SHA-256 與逐圖判定保存在 canonical roadmap。Rollback 逐項回復 merge／wiring 與版本
身分，不刪資料、不覆寫 38.0。後續四張 post-fix 截圖只把 `version_visible`、
`episode_retry_visible`、`manual_single_add` 更新為 `PASS`；append、dedupe、Retry trigger、episode OS
handoff 與 system-browser playback 仍為 `NOT_RUN`。完整 SHA-256 同樣保存在 canonical roadmap；
這組 post-fix 截圖本身只做證據同步；其後另有搜尋狀態回退證據才形成 38.1.8，仍未建立套件。

38.1.8 Root Cause／evidence boundary：後續 `9d48…`（SHA-256
`3439213CD04B897A60BBFB7F52DDB6F3AE71712EC49C29C2CC26F192422DE78C`）與 `d97a…`
（SHA-256 `FFBEEAEF9ABE58524F26AF6C2E5BB11037D34A2051489F09D01C47F4532BEB32`）只顯示
38.1.7 關鍵字查詢進入瀏覽器驗證、按鈕啟用而表格為空。來源追蹤確認 federation 把官方 403
放入合法 response failures，舊 UI 在檢查 failure 前提交空 results 並清除選取／集數。38.1.8
只加入純 reducer、production wiring、四語精確提示與相符 integrity pins；不改 provider 網路、
不讀 browser Cookie、不自動開 GUI、不繞過驗證。首次受阻仍為空表；只有既有上一批資料時才
保留並明示不是本次結果。Rollback 一起回復上述來源差異與版本身分，不刪資料、不覆寫 38.0。

38.1.8 live evidence update（2026-07-22）：`0bff…` 與 `292f…` 的完整檔名、SHA-256 及逐項矩陣
固定於 canonical roadmap。畫面可支持 38.1.8 身分、三筆作品、`盜墓王` 選取 context、兩筆集數列、
codec fail-closed 提示與系統瀏覽器操作可見；不能支持 failure-state preservation、OS handoff、
系統瀏覽器播放或下載。官方服務條款複核亦沒有第三方可保存來源，且禁止重製、廣告規避與串流
破解，因此 P2 維持 `BLOCKED / NO AUTHORIZED MEDIA SOURCE`；離線功能仍只保存公開 metadata／
封面及匯入使用者自行取得的本機媒體。本輪是證據／決策同步，不升版、不建立套件。

38.1.9 Root Cause／validation boundary：A 的集數 worker 執行期間選取 B 時，舊 selection handler
只清除 episode state，沒有讓 operation generation 失效；A 回應仍能進入共用 dispatch，污染 B 的
集數或錯誤狀態，並可能被播放歷史／離線索引配到錯作品。新增純 URL ownership guard，只有請求
作品仍等於目前選取作品才套用成功或失敗回應。helper 與 guard 不存在時精準組 `2 failed in
1.25s`；修正後 `2 passed in 0.24s`。本輪 AniGamer 搜尋、集數、session、純 workspace 與版本組
合計 `85 passed in 1.77s`；Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖
`10`、版本文件 `4`、保留版本 `5`、Repository 外 pycache compileall、CLI 38.1.9 與 diff check
均通過。未啟動或控制 GUI、未連線動畫瘋；人工競態與系統瀏覽器播放仍為 `LIVE WAITING`。
Rollback 只回復 helper、dispatch guard、tests 與 38.1.9 身分，不刪資料或覆寫 Development 38.0。

38.1.10 Root Cause／validation boundary：共用 AniGamer route 原先只解析 query 值並檢查數字，沒有
要求原始 query 精確形式，因此 `sn` 外的額外／重複參數、大小寫或 percent-encoded alias 可穿過
分類，擴散至 provider result filter、system-browser handoff、history 與 offline。修正改為只接受
原始 query 精確 `sn=<ASCII digits>`。額外／重複 query regression 先為 `1 failed in 0.46s`；加入
alias 案例後第二階段為 `1 failed in 0.41s`；精確 route node 最小修正後為 `1 passed in 0.17s`。
相關非 UI 組 `205 passed, 1 skipped in 1.66s`，版本／文件組 `19 passed in 1.00s`；Ruff／文字
污染 `368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
Repository 外 pycache compileall、CLI 38.1.10、Version bytecode 零污染與 diff check 均通過。
未啟動或控制 GUI、未連線動畫瘋，不宣稱 OS handoff、播放或下載完成。風險低且沒有資料遷移；Rollback 只回復
`core/site_routing.py` 條件、regressions、版本與文件，不刪資料或覆寫 Development 38.0。

38.1.11 Root Cause／validation boundary：canonical AniGamer `DiscoveryItemV1.video_id` 原先可與
精確 URL `sn` 不一致後仍進入 provider results、series／episode handoff、history 或 offline 新寫入；
busy 期間雙擊舊單集列的 handler 也缺少 busy／closing guard。新增共用純 validator，作品只接受
`ani-{sn}`、單集只接受 `ani-episode-{sn}`，並在上述 consumers、history load 與 offline metadata
read fail closed；current-series 與 direct-episode context 保持原語意。精準回歸先為
`4 failed in 1.80s`，初始修正後為 `6 passed in 1.26s`；read-side review 再先得到
`2 failed in 0.52s`，修正後為 `3 passed in 0.98s`。最終相關非 GUI 組為
`129 passed, 1 skipped in 7.23s`；Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
`13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall、CLI 38.1.11、
Version bytecode 零污染與 diff check 均通過。沒有 migration／deletion 或既有檔案改寫。

38.1.11 後續人工截圖證據：`9b3bf123…`（SHA-256
`81733D7FC2DAB30DC5ED1CB257235AAFDB5E39F13DA764F5937AD6BF2B571990`）只支持 compact
fail-closed presentation 與內嵌 codec `EXPECTED_UNSUPPORTED`；`92c95b19…`（SHA-256
`E46E4C90AFBBC5028E138FDBF3AE42C89BB1201969135A07BDA841D2431CD986`）支持版本 38.1.11、兩筆
集數列、選取第 2 集、單集操作可見及 offline metadata index 有效但影片／字幕未連結。成功訊息
未包含 exact URL，無法將 OS handoff 對應到選取的 canonical episode URL；system-browser 頁面載入／播放、
完整總集數、下載與檔案完整性仍為 `NOT_RUN / LIVE WAITING`。這組截圖不是 38.1.12 live evidence。

38.1.12 Goal／Scope／Priority／Dependencies／Approach／Compatibility／Risk／Rollback／Validation：P1 目標是讓
人工證據可將 OS 接受的單集開啟請求對回 exact canonical URL。只改四語 `episode_opened`
`{url}` 文案、`open_selected_episode`／`open_history_entry` wiring、regressions、版本與文件；依賴
38.1.11 identity invariant 與現有 allowlisted OS opener。不改 Cookie、provider traffic、contract、schema、串流、
codec 或下載。文案同時明示 OS 只是接受請求，官方頁載入與播放未確認，避免誤報。
Rollback 一起回復 locale 文案，wiring、regressions、38.1.12 版本與文件；無 migration／deletion，不覆寫
Development 38.0。修正前 `1 failed in 0.42s`，修正後 `2 passed in 0.94s`，相關來源組
`9 passed in 1.04s`，擴大非 UI 組 `143 passed, 2 skipped in 1.60s`。Ruff／文字污染
`368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
版本文件測試 `6 passed in 0.33s`、Repository 外 compileall、CLI 38.1.12、Version `.pyc` 零污染與
diff check 均通過；不宣稱 GUI、system-browser 頁面載入或播放完成。stage、commit、freeze、build、
package 與 push 均未執行。

38.1.13 Goal／Scope／Priority／Dependencies／Approach／Compatibility／Risk／Rollback／Validation：P1 目標是讓
相容性彈窗在自身可見區域呈現實際 exact-route handoff 結果，避免使用者在 OS 拒絕或 opener
拋出 `RuntimeError` 時只看到未更新的彈窗。Scope 只含相容性彈窗的 route-aware 訊息選擇、
exact URL 顯示、dialog-local status 鏡像、精準 regression、版本與文件；不改 provider、network、
Cookie、download 或 stream。Priority 是 G38-02 唯一 P1；依賴既有 exact route、canonical item
identity、allowlisted OS opener 與 38.1.12 handoff 文案。Approach 是對單集 route 使用
`episode_opened` 並帶入 exact canonical URL，對作品 route 使用 `series_opened`，再把 opener 的
成功與失敗訊息同步寫入主狀態及 dialog-local status。Compatibility 維持既有官方系統瀏覽器
handoff、SAFE_MODE 與 fail-closed 邊界，不新增外部介面或資料遷移。Risk 是 route 分類錯誤、
狀態文字分歧或把 OS 接受誤報為頁面載入／播放；以 exact-route regression、同一訊息鏡像與明確
文案限制。Rollback 一起回復 route-aware dialog wiring、local-status 鏡像、regression、38.1.13
版本與文件；不刪除資料、不覆寫 Development 38.0。修正前 RED `1 failed in 1.27s`，修正後
GREEN `1 passed in 0.71s`；相關精準組 `3 passed in 1.28s`、擴大非 GUI 組
`115 passed, 1 skipped in 3.77s`、版本／文件組 `19 passed in 1.21s`。Ruff／文字污染
`368 / 573`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
Repository 外 compileall、CLI 38.1.13、Version `.pyc` 零污染與 diff check 均通過；38.1.13 人工截圖仍為 `LIVE WAITING`。
stage、commit、source freeze、build、package 與 push 均未執行。

38.1.14 Goal／Scope／Priority／Dependencies／Approach／Compatibility／Risk／Rollback／Validation：P1 目標是修正
單集官方 handoff 在進入 helper body 前即失敗的 Python 參數綁定缺口。Scope 只含
`dispatch_official_url` transport formal parameter 與內部引用、精準 regression、版本與文件；不改
provider、network、Cookie、download 或 stream。Priority 是 G38-02 唯一 P1；依賴 38.1.12
`episode_opened` 的 `url=` placeholder、38.1.13 route-aware dialog-local status、canonical identity
與 allowlisted OS opener。舊 helper 以 positional `url` 接收 transport target，呼叫端又以 keyword
`url=` 傳入 message placeholder，Python 因而在 helper 執行前拋 multiple-values `TypeError`；修正將
transport 參數改名為 `official_url`，opener 與失敗文案同步使用該名稱，並保留 `**values` 中的
`url`。Compatibility 維持呼叫順序、官方 URL、翻譯與 dialog-local 結果；無 migration 或 external
API breaking change。Risk 是內部引用漏改或只驗 AST 未覆蓋實際綁定；以 signature／opener／
failure-message regression 與 handoff 組控制。Rollback 一起回復 helper 參數與內部引用、regression、
38.1.14 版本與文件；不刪除資料或覆寫 Development 38.0。runtime 擴大組修正前
`1 failed, 162 passed, 1 skipped in 8.99s`，新增純回歸 RED `1 failed in 1.20s`，純 handoff GREEN
`4 passed in 1.08s`。後續相關非 UI＋版本組在文件未同步時
`134 passed, 1 skipped, 1 failed in 6.79s`，唯一失敗只因 README／docs README 仍為 38.1.13；
同步後重跑為 `135 passed, 1 skipped in 1.87s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
`13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall、CLI 38.1.14、
Version `.pyc` 零污染與 diff check 均已通過，故 38.1.14 當時為
`SOURCE VALIDATED / LIVE WAITING / SAFE_MODE`；此狀態已由 38.1.15 的移除結論取代。未 stage、
commit、source freeze、build、package 或 push。
38.1.14 的單張 evidence-only 截圖 `codex-clipboard-5687e504-c306-4d3a-86b0-cc79cf9d8567.png`
（SHA-256 `5C52283BACEB1EECB5E55F92A1301D1E6240239D0F2BD6CDA1C1BEEB05DE5E42`）顯示從 Repository
啟動 `main.py`、終端 Video.js `CODE:4`／`setVolume` 錯誤、標題「盜墓王 [1]」的緊湊 fallback、
codec 缺失提示與 system-browser 建議操作可見；CLI 另核對當時來源 38.1.14。判定只包含
`embedded_fail_closed_presentation=PASS`、`episode_context_visible=PASS`、
`system_browser_action_visible=PASS` 與 `embedded_playback=EXPECTED_UNSUPPORTED`；按鈕點擊、OS handoff、官方頁載入、
廣告與播放沒有證據，仍為 `LIVE WAITING / SAFE_MODE`。這是純證據同步，不升修正號。
BoringMan314/aniGamerPlus V24.9.10（`ce7a6d5`）已完成唯讀差異掃描：安全命名、批次、
SQLite 狀態、有限重試／併發、佇列／進度、日誌輪替、離線匯入與驗證均已被現有元件吸收；
FTP／Dashboard／Docker、背景排程與本機 MP4 `faststart` 跨 Gate 延後；Cookie／profile 刷新、
瀏覽器模擬、Cloudflare／代理／地區規避、M3U8／key／segment／AES／FFmpeg 串流抓取與廣告
跳過／移除排除。上游 GPL-3.0 程式碼未搬入 MIT tree。結論為 `ABSORBED / NO RELEASE`，
該輪 38.1.14 維持當時來源且沒有建立下一修正號；後續 38.1.15 是獨立的移除差異。首次外部 test-root 受 Windows ACL 阻擋且未回退
Repository；改用唯一 LOCALAPPDATA test-root 後相關非 UI／版本／文件組為
`173 passed, 1 skipped in 5.36s`。Ruff／文字污染 `368 / 573`、MOD `8 / 4`、網站
`13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、Repository 外 compileall 與 diff check
均通過。

## 唯一後續方向

1. 原始 90 個路徑的 34.0 review scope 與後續 source-freeze 安全修正／證據形成 106 路徑
   freeze 前快照；VUP-34-01、VUP-34-02 與兩個 commit intents 均已完成。
2. 後續唯一版本順序與優先度由 `docs/roadmap-development-34.0-40.0.md` 管理；
   35.0～37.0 Exit Gate 已完成且維持 `SOURCE ONLY / SAFE_MODE`；G38-01 已固定為不可覆寫基線，
   G38-02 已於 38.1.15 關閉並移除；G38-01 人工矩陣維持 `MANUAL BLOCKED / SAFE_MODE`。
   G39-01 已完成為 `MEASURED / NO CHANGE / NO RELEASE / SAFE_MODE`；G40 保持
   `WAITING / AUTHORIZATION + STAGED VERIFY/HEADLESS SAFE_MODE EVIDENCE REQUIRED`，目前沒有 `ACTIVE / IN_PROGRESS`
   或平行工作。
   既有 41.0～43.0 只保留歷史，
   不自動新增 41.0、44.0 或重複規劃已完成基線。
3. FIX-34-05～07 已標為 transferred；缺少外部 runtime、production signing 或人工環境時，
   G37 已完成 evidence-ready 邊界；G38 維持 `MANUAL BLOCKED`，G40 維持
   `WAITING / EXTERNAL BLOCKED`，且全程保持 `SAFE_MODE`。
