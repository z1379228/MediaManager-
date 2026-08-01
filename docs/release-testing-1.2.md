# MediaManager Testing 1.2.2 發行紀錄

## 發行身分

- 軌道：Testing
- Testing 身分：`1.2.2`
- 來源：Development `39.0.39` 的乾淨 source freeze
- 資料夾：`Version/Testing/1.2.2`
- tag：`test-v1.2.2`
- 主要附件：`MediaManager-Testing-1.2.2.zip` 與
  `MediaManager-Testing-1.2.2.zip.sha256`
- 信任狀態：未簽署、`SAFE_MODE`、非 Stable
- 發布狀態：已取得 build、stage、tag、GitHub prerelease 與附件上傳授權；
  最終 revision、附件數與 SHA-256 由完成後的遠端回讀證據記錄。

Testing `1.2.0` 是 Development `39.0.11` 的本機歷史候選，保留於
`Version/Testing/1.2`，沒有 GitHub Release。Testing `1.2.1` 由 Development
`39.0.12` revision `05442d7875da5367cd23babc2ce4e2e3e0cb87a2` 建立，
以 tag `test-v1.2.1` 發布為具有 9 個附件的 GitHub prerelease；其目錄、tag、
附件與 SHA-256 `c633586d974fb77ba8041533cf7f7fd5378ab651d2b8f86126ccceb6b070f148`
保持不可變。

## Goal

由單一、乾淨且可追蹤的 Development `39.0.39` revision 建立 Windows x64
Testing 1.2.2，納入 39.0.13～39.0.39 的搜尋精度、分頁、失敗隔離、輸入驗證與
第三方搜尋 MOD 原子註冊修正。一般使用者下載 ZIP、驗證 SHA-256、解壓後即可
雙擊 `MediaManager.exe`，不需要另外安裝 Python。

## Scope 與 Priority

1. 將 Testing 身分由 1.2.1 增加為 1.2.2，不修改任何既有 Testing 產物。
2. 從完整通過驗證的 Development 39.0.39 source freeze 建立 receipt-bound
   build-only 未簽署 EXE 與 wheel。
3. 以 `--stage-built` 重驗 revision、wheel 與 EXE，建立不可覆寫的
   `Version/Testing/1.2.2`。
4. 驗證 staged runtime、版本內容、copied-folder 啟動與 deterministic ZIP。
5. 建立唯一 tag `test-v1.2.2`、GitHub prerelease，並上傳完整附件與 checksum。

不在本次範圍：Authenticode、production Ed25519、Stable、覆寫 Testing 1.2.1、
新增網站權限、Cookie、登入、付費、地區、廣告或 DRM 規避。

## Dependencies 與 Approach

- 使用 Repository 既有 Python、PyInstaller、Deno、FFmpeg／ffprobe 與鎖定依賴。
- `tools.build_version --channel testing --build-only` 綁定乾淨 revision 與 wheel。
- `tools.build_version --channel testing --stage-built` 只接受相同 source freeze 的
  receipt-bound 工作目錄；Testing 不要求 Authenticode，但維持未簽署狀態。
- `tools.package_self_contained_zip` 只封裝通過版本及 runtime 稽核的 staged folder，
  並要求呼叫端提供獨立確認的 source revision。

## Compatibility

- `MediaManager v1.0` 仍是 channel-neutral 產品顯示名稱。
- Stable 身分維持 `1.0.0`；Testing `1.2.2` 不代表或取代 Stable。
- `Version/Testing/1.1`、`1.2`、`1.2.1` 及既有 tags、Release、附件皆不變。
- Testing 1.2.2 保留既有 Search v2、Discovery v1、MOD protocol 與資料格式相容性。

## Risk 與 Rollback

- Dirty source、revision 不一致、既有輸出、link-like 路徑、runtime policy 不符、
  checksum 或 copied-folder smoke 失敗時一律停止。
- build 失敗只清理由本輪建立且已驗證位於安全父目錄的 attempt／temporary 路徑；
  不做 broad delete，不刪除 UserData 或既有版本。
- 發布前失敗可移除本輪尚未公開且精確識別的 1.2.2 candidate；公開後不得覆寫，
  後續修正必須增加 Testing patch 版本。
- 程式回復使用新的 revert commit，不 reset、不 rewrite history。

## Validation

source freeze 前：

- `tools.quality_audit`
- `tools.run_tests`
- Ruff、MOD 群組、網站矩陣、依賴鎖、版本文件與文字污染稽核
- Repository 外 `compileall`
- source-only `main.py --verify-only`
- `git diff --check`

Development `39.0.39` 的實際 source-freeze 前置證據：版本／build／stage／ZIP
針對性回歸 `94 passed`；完整 repository runner `1467 passed, 7 skipped`；
Quality audit 通過 Ruff `366` 個 Python 檔與文字污染掃描 `474` 個受控檔案；
MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`；
本機不可變 Testing `1.2` 與 `1.2.1` 共 2 個版本稽核通過。Repository 外
compileall、source-only `--verify-only` 與 `git diff --check` 通過，`Version/`
內 `.pyc` 為 `0`。

建置後：

- `tools.audit_versions --root Version`
- `tools.audit_staged_runtime --root Version\Testing\1.2.2`
- copied-folder current／previous／current smoke
- 兩個獨立輸出目錄的 deterministic ZIP SHA-256 比對
- ZIP 展開後的版本、runtime、檔案與 secret／UserData 排除檢查
- GitHub tag、prerelease、附件數、asset digest 與 sidecar 的遠端回讀驗證

截圖只能證明可見版面；不以自動 GUI 互動取代人工鍵盤、UIA／讀屏、Windows
高對比或真實外部網站驗證。Testing 1.2.2 維持未簽署 `SAFE_MODE`，不是 Stable。
