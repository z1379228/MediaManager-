# MediaManager 4.5 發行候選

狀態：工程候選完成，正式發布阻擋。缺少正式 Ed25519 與
Windows Authenticode 身分時只能作為 `SAFE_MODE Preview`，不得標示 stable。

## 已完成的來源門檻

- 根目錄加入 MIT `LICENSE`，與 `pyproject.toml` 授權宣告一致。
- `requirements-lock.txt` 精確鎖定 runtime、UI、測試、lint、PyInstaller 與
  setuptools；離線 audit 驗證專案宣告、鎖檔及目前環境版本一致。
- staging 自動產生 `dependency-inventory.json` 與 CycloneDX 1.6
  `sbom.cdx.json`，兩者都納入 `SHA256SUMS.txt` 與簽署檔案清單。
- 診斷與日誌額外移除敏感 URL query、MEGA 公開連結 key，以及 Windows 使用者
  路徑中的帳戶名稱。
- release preflight 同時要求有效 Ed25519 manifest 與 Authenticode；不再只憑
  其中一種簽章判定可公開。
- 既有佇列遷移、執行中工作重排、暫停狀態保存、超過一千筆工作復原及原子
  寫入回滾測試保持通過。

## 封裝驗收結果

- `Version/4.5` 建置與 43 項 staged checksum inventory 通過。
- copied-folder `--version`、Portable `--verify-only`、headless 均回傳 0；GUI
  啟動後保持運作，測試完成時只終止複製資料夾內的 one-file 程序。
- 測試副本的 SQLite、日誌與 `UserData` 全部留在副本內，程序結束後可清理。
- 本機只保留 `Version/4.5` 與上一版 `Version/4.0`，符合 current + previous。
- Authenticode 實測為 `NotSigned`，且沒有 production Ed25519 identity；因此
  正式 preflight 必須 BLOCKED，本候選只能作為 SAFE_MODE Preview。
