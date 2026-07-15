# MediaManager 正式版 1.0 候選狀態

目前結論為 `ready: false`。本文件是候選評估，不是 Stable 發布宣告；所有正式版門檻
通過且使用者明確確認前，不建立、簽署、包裝或上傳 `Version/Stable/1.0`。

## 目前可確認的來源基線

- 目前來源顯示為測試版 1.0，核心相容版本 11.0.0；開發與測試流程仍維持
  `SAFE_MODE`。
- GitHub 的 `test-v1.0.0` 是較早 revision 的不可覆寫測試附件。目前來源新增動畫瘋
  目錄、封面與集數導覽後尚未重新封裝，因此來源與已發布附件不能視為同一候選成品。
- 網站父子生命週期、工作區、網址路由與搜尋來源分離；目前共有 19 個內建 MOD、
  5 個網站群組及每組 4 個語言檔。
- Ruff、MOD 群組稽核與文字污染檢查通過；Pytest 719 項通過，另有 2 項 Windows
  symlink 測試因帳戶權限跳過。
- 目前沒有可供 Stable 評估的最新 revision 對應 EXE、`release-info.json`、
  `SHA256SUMS.txt`、copied-folder smoke 與發布後雜湊證據。

## 仍然阻擋 Stable 1.0 的項目

1. 程式內沒有可用的 production Ed25519 release key id 與 public key。
2. `MediaManager.exe` 的 Windows Authenticode 狀態仍為 `NotSigned`。
3. 必須從最終來源 revision 重建新的 Testing 候選，並讓 evidence 綁定成品 digest、
   產生時間與發布工具版本；既有 `test-v1.0.0` 不可覆寫或冒充新候選。
4. 尚未完成最新候選的升級、回退、MOD 接線、網址 smoke、完整 copied-folder 驗證及
   上傳前後 SHA-256 比對。
5. `generic-ytdlp` 仍是預設停用的舊 Beta 多網域相容 provider；它不影響 YouTube／
   Bilibili 工作區隔離，但正式版前仍應評估是否保留或逐站遷移。

因此目前必須維持 Development 與 `SAFE_MODE`。production Ed25519 私鑰及 Windows
code-signing 身分是外部發布條件，不得用測試金鑰、略過檢查或手動改狀態取代。

## 重新評估流程

1. 提交目前最終原始碼並讓 GitHub CI 全部通過。
2. 以該 revision 建立新的 Testing 版本號，重新產生 `release-info.json` 與
   `SHA256SUMS.txt`；不得覆寫 `test-v1.0.0`。
3. 重新執行 Ruff、Pytest、copied-folder、MOD 群組、升級、回退及完整版本稽核。
4. 取得 production Ed25519 與 Authenticode 發布身分，依正式簽署順序處理成品。
5. `tools.release_preflight` 必須回傳 `READY`。
6. 由使用者明確確認後，才可建立或上傳 Stable 1.0。

新的 Testing 候選建立後，使用其實際資料夾執行診斷；下列 `<版本>` 必須替換成新版本，
不可對舊附件回填新證據：

```powershell
.\.venv\Scripts\python.exe -m tools.release_preflight --root Version\Testing\<版本> --json
.\.venv\Scripts\python.exe -m tools.release_candidate --root Version\Testing\<版本> --evidence .work\stable-1.0-evidence.json --suggest-stable 1.0.0
```
