# Development 9.1 驗證與已知問題日誌

- 產生日期：2026-07-15
- 版本：Development 9.1.0
- 發布狀態：開發中，非 Stable／正式版

## 驗證結果

- Ruff：通過。
- Pytest：629 passed、2 skipped。
- Python compileall：通過。
- 內建網站 MOD 群組稽核：通過，2 個群組、每組 4 個語言檔。
- 版本與 SHA-256 稽核：通過；Development 9.1 共檢查 58 個檔案。
- copied-folder smoke：`--version`、`--verify-only`、`--headless`、凍結後 MOD 載入及
  YouTube Music 播放清單網址解析通過。
- 文件污染標記、Git 衝突標記與差異空白檢查：通過。
- 未發現需要阻止 Development 9.1 上傳的重大應用程式錯誤。

## 已知限制與非應用程式錯誤

1. 兩項 symlink 測試因目前 Windows 帳戶無法建立 symlink 而跳過：
   - `tests/test_builtin_download_provider.py`
   - `tests/test_library_service.py`
2. 沙盒內第一次重跑 pytest 時，測試暫存路徑回報存取遭拒；改用相同虛擬環境在沙盒外
   重跑後為 629 passed、2 skipped。這是測試環境權限問題，不是測試斷言失敗。
3. Windows UI Automation 無法直接操作 Qt 表格內嵌的 MOD 開關；實際 PySide6 元件測試
   已驗證主 MOD 關閉時隱藏子 MOD、開啟後顯示，以及停用主 MOD時級聯停用子 MOD。
4. `generic-ytdlp` 仍是預設停用的舊 Beta 多網域相容 provider，後續開發版應逐站遷移。
5. Bilibili 彈幕下載選項目前整合在 Bilibili 下載 MOD；獨立彈幕子 MOD仍標示製作中。

## 上傳前已修正

- 第一個 9.1 候選 EXE 的 windowed CLI 模式無法取得標準輸出，導致 `--version`、
  `--verify-only`、`--headless` 顯示視窗錯誤而無法結束。上傳已暫停；修正為只替 CLI
  模式還原 Windows 輸出管線，沒有主控台時回退到 null device，並在重新建置後以 ZIP
  內 copied-folder 實測三種模式。未修正的候選檔沒有上傳到 9.1 Release。

## Stable 發布阻擋

`tools.release_preflight` 檢查 56 項後回傳 `ready: false`：

- compiled release key id 或 production Ed25519 public key 無效／尚未設定。
- `MediaManager.exe` 的 Authenticode 狀態為 `NotSigned`。

以上是刻意保留的正式發布阻擋。Development 9.1 必須維持 `SAFE_MODE`，不得將測試
金鑰、略過驗證或手動改狀態當作正式簽章。此版本不建立或發布 Stable 1.0。

## 公開日誌隱私界線

本檔不包含使用者名稱、下載紀錄、媒體網址、Cookie、Token、私鑰、本機完整路徑或原始
應用程式個人日誌。若日後需要診斷特定故障，應先由核心 redaction 流程產生匿名化輸出，
再由使用者明確決定是否公開。
