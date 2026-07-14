# MediaManager 協作規範

本文件適用於整個儲存庫，提供開發者、第三方 MOD 作者與自動化工具一致的
修改界線。若子目錄日後加入更具體的 `AGENTS.md`，以較接近目標檔案者優先。

## 專案目標

- 免費、無廣告、本機優先，預設不遙測、不強制帳號。
- 核心保持精簡；網站解析、轉換、轉錄及自動化等重功能以可停用 MOD 提供。
- 不繞過 DRM、付費、登入、地區、廣告或網站存取限制。
- 未取得正式簽署身分時必須維持 `SAFE_MODE`，不可偽稱正式安全發行版。

## 主要路徑

- `main.py`：唯一正式入口；`desktop.py` 僅為相容轉接。
- `core/`：安全、下載、媒體庫、設定、儲存與 MOD 生命週期。
- `trusted_ui/`：PySide6 可信 UI，不執行外部 MOD 提供的任意 UI 程式碼。
- `contracts/`：核心與 MOD 共用的版本化資料契約。
- `mod/builtin/`：內建但可個別啟用或停用的功能模組。
- `plugin_host/`：外部可執行 MOD 的受控程序入口。
- `tests/`：功能、安全與回歸測試。
- `docs/`：發行紀錄、架構、安全界線與路線圖。
- `Version/<major>.<minor>/`：已完成版本；補丁版只交易式替換同一資料夾。

## 修改原則

1. 先讀取相關測試與契約，再修改實作；不要把網站專屬邏輯放入核心。
2. 保留現有使用者資料、未追蹤檔案與無關修改；禁止使用破壞性的 Git 重設。
3. 檔案、設定、佇列與資料庫更新應採原子寫入或可恢復交易。
4. 網路內容、ZIP、路徑、manifest 與 IPC 輸入一律視為不可信並設定大小上限。
5. 新增背景工作必須預設關閉、可取消、有清楚狀態且不在乾淨啟動時開程序。
6. UI 應維持深色一致性、鍵盤操作、可存取名稱及 940×620 最小視窗可用性。
7. 不在儲存庫加入私鑰、權杖、Cookie、帳號資料、正式憑證或本機絕對路徑。

## MOD 規範

- 新的可執行 MOD 使用 manifest schema v2、`python-subprocess` 與 runtime
  protocol `1.0`，只申請必要 capability。
- 安裝前驗證結構、SHA-256、發布者與 Ed25519 簽章；新安裝與更新後預設停用。
- 外部 MOD UI 僅能使用受簽署的宣告式 `ui.json`，不可注入 HTML、Qt 物件或
  任意腳本。
- 第三方流程與檢查命令記錄於 `docs/mod-developer-guide.md`。

## 驗證命令

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.work\pytest-agent
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
```

建立版本前，還需執行相符的 provider smoke、一次性簽署演練與 copied-folder
啟動測試。正式發行 preflight 若因缺少生產 Ed25519／Authenticode 身分而失敗，
應明確記錄為發行阻擋，不能降低驗證條件。

## 版本與文件

- 同步更新 `core/version.py`、`pyproject.toml`、README 與對應 release 文件。
- 新功能必須有測試；安全或資料格式變更必須補充失敗案例與遷移說明。
- 不修改已保留歷史版本內容；每次發行重新產生 `release-info.json` 與
  `SHA256SUMS.txt`。
- 日常本機只保留目前版與上一版，並使用預設稽核；大版本封版、資安事件或
  定期維護才還原 GitHub 歷史附件並執行 `--full-history`。
- GitHub Releases 上已公開的 EXE、`SHA256SUMS.txt` 與 `release-info.json`
  不得刪除；即將公開的附件在上傳前後都必須驗證 SHA-256。
