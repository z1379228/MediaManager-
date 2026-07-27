# MediaManager Testing 1.2.1 候選計畫

- 通道：Testing
- 預定 Testing 身分：`1.2.1`
- 候選來源：Development `39.0.12`
- 預定資料夾：`Version/Testing/1.2.1`
- 預定 tag：`test-v1.2.1`
- 預定附件：`MediaManager-Testing-1.2.1.zip` 與
  `MediaManager-Testing-1.2.1.zip.sha256`
- 信任狀態：未簽署、`SAFE_MODE`、非 Stable
- 目前狀態：`AUTHORIZED / PENDING / NOT PUBLISHED`

Testing `1.2.0` 是 Development `39.0.11` 於 revision
`fab5cb9333274e54f65a35b2f44a86699f0f349f` 建立的本機歷史候選，保留於
`Version/Testing/1.2`；它未建立 GitHub Release，也不得被覆寫、改名或冒用成
Testing `1.2.1`。

## Goal

建立一個由單一乾淨 source revision 產生、可稽核且可重現封裝的 Windows x64
Testing 1.2.1。一般使用者下載 ZIP、驗證 SHA-256、解壓後即可雙擊
`MediaManager.exe`；不需要系統 Python。

## Scope 與 Priority

1. 納入 Testing 1.2.0 的 YouTube 搜尋內容類型、數量／頁面、時長、排序、
   來源、顯示欄位、取消、歷史與選取回歸。
2. 納入 Development `39.0.12` 的單一 YouTube 搜尋結果相似音樂入口；只使用
   公開搜尋與既有本機排序，不使用 Cookie、私人推薦或觀看紀錄。
3. 納入 deterministic 自包含 ZIP 工具、失敗關閉規則及 regression。
4. 同步 Development `39.0.12`、Testing `1.2.1`、README 與發行文件。
5. 完成乾淨 source freeze 後才建置、stage、稽核及產生 ZIP。

本次已授權 source freeze、未簽署 EXE、自包含 ZIP、建立唯一 tag
`test-v1.2.1`、GitHub Release 與上傳；各步驟仍須依序通過工具驗證，不能因
授權而提前標示完成。Authenticode、production Ed25519、Stable 發布及覆寫
既有附件不在範圍內。也不新增或繞過網站的 DRM、登入、付費、地區、廣告或
存取限制。

## Dependencies 與 Approach

- 使用 Repository 鎖定的 Python、PyInstaller、Deno、FFmpeg／ffprobe 及授權檔。
- `tools.build_version --channel testing --build-only` 綁定乾淨 revision 與 wheel。
- `--stage-built` 重驗 receipt 後建立不可覆寫的 `Version/Testing/1.2.1`。
- `tools.package_self_contained_zip` 只接受已通過版本與 runtime audit 的 staged
  folder，並要求獨立提供相同 source revision。

## Compatibility

- `MediaManager v1.0` 仍是 channel-neutral 產品顯示名稱。
- Stable 身分維持 `1.0.0`；Testing `1.2.1` 不代表或取代 Stable。
- 既有 `Version/Testing/1.1`、`Version/Testing/1.2`、tag、雜湊與公開附件
  保持不可變。
- 雙擊 EXE 使用標準 Windows 使用者資料位置；ZIP 自包含不等於
  `--portable` 資料模式。

## Risk 與 Rollback

- Dirty source、revision 不一致、既有輸出、link-like／衝突路徑、UserData、
  秘密或 runtime policy 不符時一律停止。
- build 前失敗只清理由工具建立且可證明擁有的唯一 attempt；不 broad delete。
- `Version/Testing/1.2` 不覆寫；新 patch 建立於 `Version/Testing/1.2.1`。
  若 1.2.1 在公開前失敗，只移除該輪工具擁有的唯一 attempt 並重新 source
  freeze；若已公開則新增版本，不覆寫附件。
- Git 變更以新的 revert commit 回復，不 reset、rewrite history 或刪除 1.1。

## Validation

Development `39.0.12` 工作來源目前已有下列基線證據；1.2.1 source freeze 後
仍須在乾淨 revision 重跑，不能把基線當成最終發行證據：

- 完整 Repository runner：`1388 passed, 7 skipped`
- Quality audit：Ruff `366` 個 Python 檔案、文字污染 `474` 個受控文字檔
- MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`
- 版本文件 `4` 個 canonical 宣告一致；既有 Testing 版本稽核通過
- Repository 外 compileall、source-only `--verify-only` 與 `git diff --check`

source freeze 前仍需在最終 diff 上重跑：

- `tools.quality_audit`
- `tools.run_tests`
- 版本文件、MOD 群組、網站矩陣、依賴鎖與 `git diff --check`
- Repository 外 `compileall`

建置後：

- `tools.audit_versions --root Version`
- `tools.audit_staged_runtime --root Version\Testing\1.2.1`
- copied-folder current／previous／current smoke
- 兩個獨立輸出目錄的 deterministic ZIP SHA-256 比對
- 使用者提供截圖的 UI 驗證；不自動控制 GUI
- GitHub 上傳前後再次核對 ZIP、sidecar、`SHA256SUMS.txt`、`release-info.json`
  與遠端 asset digest；tag 必須為 `test-v1.2.1`

source revision 與 artifact digest 只能由本次凍結、建置與封裝工具的實際輸出
記錄，不預填在來源文件。本次雖已獲授權建立 tag、GitHub Release 與上傳，但在
遠端 API 證明 Release 與完整附件存在前，本文件不提供下載 URL，也不宣稱
Testing 1.2.1 已發布。
