# MediaManager

平台無關的桌面媒體管理器。平台功能將由受隔離、具最小權限的 MOD 提供；核心負責安全、工作、儲存、網路與憑證代理。

目前開發基準為 3.5.0，核心與網站功能分離。GitHub 對外下載的大版本為
3.0.0；3.1～3.5 僅提供更新簡介，不另外發布重複的大型安裝檔：

- Windows EXE、主視窗與通知區使用專用多尺寸圖示，小尺寸仍保持清楚辨識
- 外觀選單提供精簡、標準與大字三種介面大小，下載工作區在小視窗可安全捲動
- 插件管理預設顯示九個內建 MOD，可直接啟用或停用並同步下載與搜尋工作區
- 下載工作可暫停／繼續、批次控制，並可選擇 1–4 個同時工作
- 下載封存與播放清單 ID 可經預覽後安全匯入／匯出
- 外部 MOD manifest v2、簽章／權限生命週期與側邊離線更新基礎
- 八個公開網站家族的可重複 smoke matrix 與一致錯誤分類
- Bilibili bangumi、分 P、字幕資訊與彈幕處理契約

- 依序初始化的 Bootstrap 與 AppContext
- 一般／Portable 路徑服務
- 乾淨的 PySide6 媒體庫、搜尋、下載佇列與 MOD 管理介面
- 可關閉的 YouTube 搜尋／下載 MOD，含搜尋範圍、歷史、縮圖、試聽與選用影片預覽
- 預設關閉的 Bilibili MOD，含分段、彈幕 XML、ASS 與可選 MKV 封裝
- 動畫瘋官方播放入口，只開啟經驗證的官方頁面，不擷取影片或彈幕
- Facebook／Instagram／Threads 官方媒體頁與資料匯出說明入口，不啟用自動擷取
- 播放清單選取，以及具預覽與檢查結果的 TXT／CSV 批量匯入
- 格式、字幕、優先級、時間區段、重試、取消與完成通知
- 可選取的任務詳情、失敗原因複製與安全輸出位置開啟
- 可攜 Deno、FFmpeg、ffprobe 與本機依賴健康提示
- 原子寫入的設定、佇列、歷史與下載封存
- Trust Store、SHA-256 完整性驗證與 fail-closed 簽章介面
- `NORMAL`、`SAFE_MODE`、`BLOCKED` 安全狀態
- 可自選背景，以及不依賴圖片資源的低負載漸層預設背景
- 下載表格增量更新與依工作狀態調整的低負載刷新
- 加入下載前輸出路徑與 256 MiB 磁碟保留空間預檢
- 第三方 MOD schema v2 範本、安裝前驗證工具與中文開發流程
- YouTube 最近搜尋選單可依本機偏好提供有界、需手動觸發的搜尋建議
- 長音訊切割確認會提示過短、低信心、預設名稱與時間間隙並預覽輸出名稱
- 內建網站能力與 Bilibili 彈幕政策具有不連網、可重複的品質稽核

## 執行

```powershell
python main.py
python main.py --portable --headless
python main.py --portable --verify-only
```

`main.py` 是唯一的正式入口；直接執行、安裝後的 `mediamanager` 指令與
PyInstaller 桌面程式都使用相同的參數解析、Bootstrap 與主視窗啟動流程。
`desktop.py` 僅保留為舊版啟動方式的相容轉接。

本機開發封裝依版本號位於 `Version/<major>.<minor>`；GitHub 下載頁只發布
3.0、4.0 等大版本完整檔案，次版本改以中文更新簡介說明。整個版本資料夾可
移動到其他位置
執行；不要只移動 EXE，因為同層的 MOD、工具與 checksum 檔案也是版本
的一部分。

## 路徑架構

- 核心與正式入口：應用程式根目錄
- 待安裝插件：`mod/packages/*.modpkg`
- 已安裝插件：`mod/installed/<plugin-id>`
- 隔離插件：`mod/quarantine`
- 插件登錄資料庫：`mod/registry.sqlite3`

插件根目錄固定置於核心旁的 `mod`，不因一般或 Portable 模式而改變。
插件套件會先驗證結構、檔案雜湊、發布者信任與 Ed25519 簽章，再以暫存目錄交易式安裝；新安裝插件預設停用。公鑰使用 Base64 編碼的 32-byte Ed25519 公鑰（可加上 `ed25519:` 前綴），簽章可使用原始 64-byte 或 Base64 格式。

開發版本沒有簽署的 `security/release-manifest.json`，因此會刻意以 `SAFE_MODE` 啟動。正式版本必須由發行流程產生並簽署 manifest；不可把開發用金鑰放進原始碼。

## 測試

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

建立並交易式更新目前版本資料夾：

```powershell
.\.venv\Scripts\python.exe -m tools.build_version
```

批次稽核所有保留版本的版本號、wheel 與 SHA-256 完整性：

```powershell
.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
```

## 後續版本

3.0 完成紀錄位於 [`docs/release-3.0.md`](docs/release-3.0.md)；3.1 到 4.0 的
可修改提案位於 [`docs/roadmap-3.1-to-4.0.md`](docs/roadmap-3.1-to-4.0.md)。

3.1～3.5 已完成項目的精簡說明位於
[`docs/release-3.1-to-3.5-summary.md`](docs/release-3.1-to-3.5-summary.md)。
