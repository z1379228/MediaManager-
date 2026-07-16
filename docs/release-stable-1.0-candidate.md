# MediaManager 正式版 1.0 候選狀態

目前結論為 `ready: false`。本文件是候選評估，不是 Stable 發布宣告；所有正式版門檻
通過且使用者明確確認前，不建立、簽署、包裝或上傳 `Version/Stable/1.0`。

## 目前可確認的來源基線

- 目前來源顯示為開發版 16.1，核心相容版本 16.1.0；最新完整成品仍是
  `Version/Development/16.0`，16.1 尚未封裝，開發與測試流程維持 `SAFE_MODE`。
- GitHub 的 `test-v1.0.0` 是較早 revision 的不可覆寫測試附件。目前來源已再新增
  其後的網站父子 MOD、樹狀管理與動畫瘋番劇儲存，因此來源與已發布附件不能
  視為同一候選成品。
- 網站父子生命週期、工作區、網址路由與搜尋來源分離；目前共有 31 個內建 MOD、
  8 個網站群組及每組 4 個語言檔。
- Ruff、MOD 群組稽核與文字污染檢查通過；Pytest 848 項通過，另有 2 項 Windows
  symlink 測試因帳戶權限跳過。
- 開發版 16.0 已建立 EXE、`release-info.json` 與 `SHA256SUMS.txt`，copied-folder
  三種 CLI 與 GUI smoke 通過；封裝 provider smoke 為 7/7。這些仍只證明 Development
  成品一致，不能取代 Stable 的 production 簽章及候選證據。動畫瘋官方頁目前可能要求
  Cloudflare 瀏覽器驗證，14.2 已提供不繞過驗證的官方作品／單集網址貼入降級流程。

## 仍然阻擋 Stable 1.0 的項目

1. 程式內沒有可用的 production Ed25519 release key id 與 public key。
2. `MediaManager.exe` 的 Windows Authenticode 狀態仍為 `NotSigned`。
3. 必須從最終來源 revision 重建新的 Testing 候選，並讓 evidence 綁定成品 digest、
   產生時間與發布工具版本；既有 `test-v1.0.0` 不可覆寫或冒充新候選。
4. 16.0 Development 已完成成品驗證；16.1 必須先從最終提交 revision 建立可重現
   Development 成品，之後才可建立新的 Testing 候選。Development 的 copied-folder
   與本機 SHA-256 不能取代該候選的升級、
   回退、全綠網址 smoke 與上傳前後 SHA-256 比對。
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
