# MediaManager 正式版 1.0 候選狀態

目前結論為 `ready: false`。本文件是候選評估，不是 Stable 發布宣告；所有正式版門檻
通過且使用者明確確認前，不建立、簽署、包裝或上傳 `Version/Stable/1.0`。

## 目前可確認的 Development 基線

- 核心版本為 Development 9.1.0，成品位於 `Version/Development/9.1`，沒有覆寫 9.0。
- Ruff 全專案檢查通過；Pytest 629 項通過，另有 2 項 Windows symlink 測試因帳戶權限
  跳過。
- YouTube 與 Bilibili 下載工作區、網址路由及搜尋交接已分離；網站主 MOD 關閉時不顯示
  子 MOD，停用主 MOD 會級聯停用子 MOD。
- 核心四語言會讀取網站 MOD 的對應 locale；群組稽核通過 2 個網站群組與每組 4 個
  語言檔。
- copied-folder smoke 已通過 `--version`、`--verify-only`、`--headless`、凍結後 MOD 載入
  及 YouTube Music 播放清單網址解析。
- 9.1 共 58 項 SHA-256 稽核通過；`MediaManager.exe` SHA-256 為
  `3FF76A1E278E0C0C791941CECE16F1A8003CF51D1F5B1BB535513F1778B74393`。

## 仍然阻擋 Stable 1.0 的項目

1. 目前工作樹尚未提交，亦沒有對應最終 revision 的 GitHub CI 證據。
2. 程式內沒有可用的 production Ed25519 release key id 與 public key。
3. `MediaManager.exe` 的 Windows Authenticode 狀態仍為 `NotSigned`。
4. 正式候選 evidence 尚須綁定最終來源 revision、成品 digest、產生時間與發布工具版本，
   並完成升級、回退、MOD 接線與完整 copied-folder 驗證。
5. `generic-ytdlp` 仍是預設停用的舊 Beta 多網域相容 provider；它不影響 YouTube／
   Bilibili 工作區隔離，但正式版前仍應評估是否保留或逐站遷移。

因此目前必須維持 Development 與 `SAFE_MODE`。production Ed25519 私鑰及 Windows
code-signing 身分是外部發布條件，不得用測試金鑰、略過檢查或手動改狀態取代。

## 重新評估流程

1. 提交 9.1 最終原始碼並讓 GitHub CI 全部通過。
2. 以該 revision 重建 Development 9.1，重新產生 `release-info.json` 與
   `SHA256SUMS.txt`。
3. 重新執行 Ruff、Pytest、copied-folder、MOD 群組、升級、回退及完整版本稽核。
4. 取得 production Ed25519 與 Authenticode 發布身分，依正式簽署順序處理成品。
5. `tools.release_preflight` 必須回傳 `READY`。
6. 由使用者明確確認後，才可建立或上傳 Stable 1.0。

目前診斷指令：

```powershell
.\.venv\Scripts\python.exe -m tools.release_preflight --root Version\Development\9.1 --json
.\.venv\Scripts\python.exe -m tools.release_candidate --root Version\Development\9.1 --evidence .work\stable-1.0-evidence.json --suggest-stable 1.0.0
```
