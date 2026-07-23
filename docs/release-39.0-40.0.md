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

## Validation

- 完整 repository runner：`1317 passed, 7 skipped`。
- Quality audit：Ruff `364` 個 Python 檔案、文字污染 `471` 個受控文字檔。
- MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`。
- 本機保留版本稽核：`3` 個版本通過。
- source freeze 前仍須重跑文件／品質、compileall、`--verify-only` 與
  `git diff --check`。

## Testing 1.1 Gate

使用者已授權 Development 39.0.10 的 stage、commit、source freeze，以及由同一
乾淨 revision 建立、上傳未簽署 `SAFE_MODE` Testing `1.1.0`。GitHub prerelease
使用唯一 tag `test-v1.1.0-r2`，精確指向 `09b3a86e00938241d27050088583ebf81d9fb182`；
9 個附件的 GitHub digest 與本機 SHA-256 一致。Testing 1.0 與既有 tags 不覆寫。
Authenticode 與 production signed release manifest 仍未成立，因此 Stable Gate
保持阻擋。

## 40.0

沒有獨立 material delta，狀態為 `ABSORBED / NO RELEASE / NO PLAN`。不得為維持
版本號建立空版本；若日後出現可重現缺口，需另建計畫並重新取得相應授權。
