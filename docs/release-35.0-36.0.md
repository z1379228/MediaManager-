# Development 35.0–36.0 更新紀錄

狀態：Development 35.0 與 36.0 來源 Exit Gate 已完成；該 Gate 完成時核心相容版本為 `36.0.0`。
這些來源後續納入 Development 38.0 source freeze，未建立 35.0／36.0 候選包，且維持
`SAFE_MODE`。本文不是發行附件、Testing／Stable 宣告或正式簽署證據。

## 35.0｜外部 MOD 資料與生命週期一致性

- 新增有界、唯讀的 dependency graph snapshot／candidate overlay，對 missing、tampered、cycle、
  fanout 與 root escape 採穩定的 fail-closed 結果。
- plugin lifecycle 使用共用 lock 與 compare-and-set journal 協調 enable／disable、Supervisor
  handle ownership、capability 撤銷、transaction recovery 與 dependency-safe startup／stop。
- install／update／rollback／restore 在 mutation 前驗證 candidate graph；updater、cleanup、purge
  recovery 等 mutation path 共用 junction／reparse／root-escape Gate。
- 不自動安裝或啟用 dependency，不 cascade 改變 dependent 的使用者設定；executable plugin
  仍預設關閉。

## Compatibility、Migration 與 Rollback

- manifest schema v2、runtime protocol 1.0、TrustStore 格式與 capability payload 不變；dependency
  仍只表示 plugin ID，沒有新增版本約束。
- 無 UserData schema migration。既有不一致 graph 會在 enable／update 時被可診斷地拒絕，屬安全收緊。
- 回退只還原 35.0 來源與測試；不得刪除 registry、MOD、backup、quarantine 或使用者資料。
  降回不支援 lifecycle journal 的來源前，需先用 35.0 recovery 收斂為 disabled／`NONE`。

## 驗證與限制

- 完整 Repository：`1212 passed, 7 skipped`；G35-02D 相關 15 檔：`175 passed`；直接
  updater／cleanup／recovery path：`40 passed`。
- Ruff／文字污染 `360 / 563`、compileall、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、
  版本文件 `4`、保留版本 `5` 與 `git diff --check` 均通過。
- 非阻擋 P2 保留於 canonical roadmap，必須在重新開啟 executable plugin 或調整 publisher trust
  協調前處理。
- 未取得 build、EXE、Testing／Stable、簽署、發布、push 或外部／人工操作授權；維持 `SAFE_MODE`。

## 36.0｜非特權 result DTO 的有界加法相容

- `DiscoveryItemV1`、`HistoryEventV1`、`HistoryPreferencesV1`、`RecoveryPlanV1`、
  `RecoveryCandidateV1` 與 `ProviderFailureV1` 現可讀取不超過 8 個 benign extra fields。
- extra key 僅接受最長 64 bytes 的 ASCII lower snake case；`schema`、`schema_version`、
  `contract_version`、`api_version`、`version` 與非公開命名均拒絕，避免把未知 major 當成加法欄位。
- 每個 extra value 必須是深度、節點與 compact JSON UTF-8 大小均有界的 JSON；單值最多 4 KiB、
  extras 合計最多 32 KiB、整個 DTO 最多 1 MiB。missing required、non-finite、non-JSON 與 oversize
  仍 fail closed。
- reader 驗證後只建立 current-schema dataclass，extra 不寫回、不記錄、不持久化；history selection
  與 recovery candidate 內嵌的 discovery item 採相同政策。
- capability token claims 補上 exact-key 驗證；Provider／Download capability、plugin manifest、
  UI descriptor、路徑、簽章與其他特權 payload 不套用 additive helper，繼續 strict。

## 36.0 Compatibility、Risk 與 Rollback

- 這是 current-schema result reader 的前向加法相容；沒有 UserData、manifest、runtime protocol、
  API 或資料 migration。既有 provider IPC 原有約 1 MiB 訊息邊界，direct decoder 現在也明確
  fail closed；超過界線的非契約輸入不再接受。
- 主要風險是 helper 被誤套到特權契約或 extras 影響 current fields；以六 DTO allowlist、required-field
  驗證、current-only construction 與特權 strict controls 限制。
- 回退可逐一還原六個 parser 與共用 helper，並還原 capability claims exact-key check；不需轉換、
  刪除或重寫使用者資料。

## 36.0 驗證與限制

- failing regression 先固定六 DTO additive reader、1 MiB payload、巢狀 discovery、provider retry
  semantics 與 signed capability claims strict 缺口：`12 failed, 30 passed`；修正後核心 targeted
  契約組為 `87 passed`，allowlist／strict-control 組為 `73 passed`。
- 升版前與 36.0.0 同步後的完整 Repository 均為 `1255 passed, 7 skipped`；Ruff／文字污染
  `363 / 566`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  scoped compileall、Version `.pyc` 零污染與 `git diff --check` 均通過。
- 未取得 stage、commit、source freeze、build、EXE、Testing／Stable、簽署、發布、push 或
  外部／人工操作授權；維持 `SAFE_MODE`。
