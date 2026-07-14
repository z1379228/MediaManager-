# MediaManager 正式版 1.0 候選狀態

本文件記錄由開發版 9.0 升格為正式版 1.0 的候選結果。它是版本資訊，
不是已發布的 Stable 宣告；所有正式版門檻通過前，不建立或上傳正式版二進位檔。

## 已通過

- Ruff 通過。
- Pytest 完整回歸通過：538 passed、2 skipped。
- 9.0 copied-folder 的 `--version`、Portable verify、headless 與 GUI smoke 通過。
- 升級與回退相關測試通過。
- 9.0 版本資料夾 43 項 SHA-256 稽核通過。
- GitHub 目前沒有開放的 P0 或 P1 issue。

## 目前阻擋

1. 程式內尚未設定有效的 production Ed25519 release key id 與 public key。
2. `MediaManager.exe` 的 Windows Authenticode 狀態是 `NotSigned`。

因此候選評估結果為 `ready: false`，目前必須維持開發版 9.0，不能包裝或
上傳 `Version/Stable/1.0`。待外部簽章身分備妥後，需重新建置、簽署並讓
`tools.release_preflight` 回傳 `READY`，才可由使用者確認正式封版。

## 重新評估指令

```powershell
.\.venv\Scripts\python.exe -m tools.release_preflight --root Version\Development\9.0 --json
.\.venv\Scripts\python.exe -m tools.release_candidate --root Version\Development\9.0 --evidence .work\stable-1.0-evidence.json --suggest-stable 1.0.0
```
