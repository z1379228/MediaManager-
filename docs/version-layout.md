# 版本資料夾與三軌政策

Development、Testing 與 Stable 是互相獨立的發行軌，數字不可跨軌比較新舊。

## 目錄

- `Version/Development/<major>.<minor>/`
- `Version/Testing/<major>.<minor>/`
- `Version/Stable/<major>.<minor>/`

5.0 以前的歷史產物可能仍位於 `Version/<major>.<minor>/`。它們是保留證據，
不得為了統一目錄而搬移或改寫。

每個完整版本資料夾可包含 EXE、wheel、portable tools、內建 MOD、
`release-info.json`、`SHA256SUMS.txt`、SBOM 與簽章資料。檔案清單與 hash
必須閉合；未列檔案、缺檔、路徑逃逸或 staging residue 都使稽核失敗。

## 版本身分

- Development 使用完整核心版本 `X.Y.Z`；material 程式修正增加 `Z`。
- 純文件、證據或不改變執行行為的更新不增加修正號。
- Testing 與 Stable 各有自己的公開版本，不從 Development 數字推導。
- UI 產品名稱可使用 `MediaManager v1.0`，但不取代核心版本、channel、
  checksum、簽章與 release metadata。

## 不可變與保留

- 已存在的版本資料夾不得覆寫；同一候選必須由同一 source revision 產生。
- 已公開 tag、EXE、`SHA256SUMS.txt` 與 `release-info.json` 不得刪除或替換。
- 日常本機可只保留 current＋previous，但必須使用受控 dry-run 工具，且不得
  刪除 UserData、含 link-like 項目的目錄或唯一可用的回復版本。
- 完整歷史稽核前，先從 GitHub Releases 還原公開附件，再執行
  `--full-history`；不要以空資料夾或假 manifest 補數。

```powershell
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version --full-history
```

## 建置與發布授權

stage、commit、source freeze、build、建立 EXE、Testing／Stable、Authenticode、
Ed25519 簽署、stage-built、push、發布與上傳都是分開的外部狀態變更，必須逐項
取得明確授權。授權其中一項不自動授權下一項。

目前沒有 Development 40.0 或 Stable 發布計畫；Testing 1.1 僅取得本機未簽署
打包授權。下列完整發布流程仍只是保留契約，不因 Testing 打包而自動獲得授權：

1. 建立乾淨、不可變的 source-freeze revision。
2. 在 Repository 外的唯一工作目錄執行 receipt-bound build-only。
3. 由外部安全環境對同一 EXE 套用 Authenticode，並獨立確認 `Valid`。
4. `stage-built` 重驗 receipt、revision、wheel 與 EXE 後建立不可覆寫候選。
5. 產生 final checksum、SBOM 與 release metadata。
6. 使用 Repository 外的 production Ed25519 私鑰簽署 final staged set。
7. 執行 preflight、版本稽核、copied-folder smoke 與必要人工驗證。
8. 只有全部證據指向同一 digest，且另有發布授權時才能上傳。

詳細秘密管理與順序見 [簽章與發行 Gate](release-signing.md)。

## 測試版本

不要直接在保留版資料夾執行會寫入 `UserData` 的 GUI 或 headless smoke。應複製
完整資料夾到 Repository 外或 `.work/smoke-<version>`，測試完成後確認沒有程序
存活，再只移除該 smoke 副本並重新執行版本稽核。
