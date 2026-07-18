# Development 32.1 工作樹與計畫基線

狀態：`FIX-34-02 DONE / 34.0 SOURCE-FROZEN`。本文件保存 32.1 後續工作樹與
31.0～43.0 計畫在 source freeze 前的唯一清冊。使用者已於 2026-07-18 回覆「繼續更新」，核准當時全部 90 個路徑進入
Development 34.0 review scope；後續 source-freeze 審查新增設定併行安全、降版回復、
MOD 交易回復、build ownership、pytest 暫存根目錄隔離與相符回歸／文件，形成 106 個路徑的
freeze 前快照。使用者於 2026-07-19 另行授權 stage、本機 commit 與 source freeze；
仍未授權 push、建立 EXE／Testing／Stable 或覆寫歷史版本。

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
| 動畫瘋播放器／封存 | 自動化與單一 live smoke 完成 | 本機／manifest 回歸及使用者完成官方流程後的單集播放證據；其他影片、帳號、地區與 UI 矩陣仍受外部 Gate 限制 |
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
| 35.0 | `ACTIVE / G35-02 READY` | G35-01 已吸收到 34 freeze；下一工作為 G35-02A failing regressions。 |
| 36.0 | `PLANNED / WAITING` | P1 非特權 result DTO 加法相容；特權安全契約維持 strict。 |
| 37.0 | `EVIDENCE GATED / WAITING` | 原生崩潰／provider 證據；重現時升 P0，無重現不宣稱已修復。 |
| 38.0 | `PLANNED / MANUAL BLOCKED` | 自動化基線已完成，只關閉 940×620、四語、鍵盤與讀屏人工缺口。 |
| 39.0 | `PLANNED / MEASUREMENT GATED` | 先固定 workload／baseline；無可證瓶頸即 `MEASURED / NO CHANGE`。 |
| 40.0 | `PLANNED / EXTERNAL GATED` | 精確 SAFE_MODE copied-folder 證據；Stable operator／正式簽署仍條件式阻擋。 |
| 41.0 | `DONE BASELINE` | 安全測試與品質入口已完成；歷史清理仍不在授權範圍。 |
| 42.0 | `SUPERSEDED BY FIX-34-02` | 本清冊即其缺少的收斂結果。 |
| 43.0 | `HISTORICAL / PARTIALLY ABSORBED` | capability self-check、播放器／manifest 已有實作；外部／人工／候選證據分別由 G37／G38／G40 管理，未接線的 capability-to-button routing 留在 deferred backlog。 |

## 唯一後續方向

1. 原始 90 個路徑的 34.0 review scope 與後續 source-freeze 安全修正／證據形成 106 路徑
   freeze 前快照；VUP-34-01、VUP-34-02 與兩個 commit intents 均已完成。
2. 後續唯一版本順序與優先度由 `docs/roadmap-development-34.0-40.0.md` 管理；
   35.0 現為 `ACTIVE`、G35-02 為 `READY`；36.0～40.0 在前版 Exit Gate 前保持 `WAITING`。
   既有 41.0～43.0 只保留歷史，
   不自動新增 41.0、44.0 或重複規劃已完成基線。
3. FIX-34-05～07 已標為 transferred；缺少外部 runtime、production signing 或人工環境時，
   對應 G37／G38／G40 維持 `WAITING`／`BLOCKED` 與 `SAFE_MODE`。
