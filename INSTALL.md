# 安裝與啟動

目前沒有可供一般使用者下載的已簽署 Stable 套件。本文件分別說明既有 Testing
附件與從 Repository 執行來源；不要把自行建置的 Development EXE 標示為正式
發行版。

Testing `1.2.0` 是 Development `39.0.11` 的本機歷史候選，保留於
`Version/Testing/1.2`，沒有 GitHub 發布。Testing `1.2.1` 是 Development
`39.0.12` 的既有公開 prerelease，維持不可變。Testing `1.2.2` 將由 Development
`39.0.39` 的乾淨 source freeze 建立；它是未簽署 Testing 產物，不是 Stable。

## Testing 1.2.2 預發行版

若要使用已打包的未簽署測試版，請由
[Testing 1.2.2 prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)
下載
[`MediaManager-Testing-1.2.2.zip`](https://github.com/z1379228/MediaManager-/releases/download/test-v1.2.2/MediaManager-Testing-1.2.2.zip)
與
[`MediaManager-Testing-1.2.2.zip.sha256`](https://github.com/z1379228/MediaManager-/releases/download/test-v1.2.2/MediaManager-Testing-1.2.2.zip.sha256)。
它維持 `SAFE_MODE`、不是 Stable，Windows 可能顯示未簽署程式警告。下載後先
比對 `.zip.sha256`；也可用同頁的
`SHA256SUMS.txt` 與 `release-info.json` 核對內部檔案及來源 revision。解壓後
直接雙擊 `MediaManager.exe`，不需要另外安裝 Python。

雙擊 EXE 會使用 `%APPDATA%\MediaManager`、`%LOCALAPPDATA%\MediaManager` 與
`Downloads\MediaManager`，不等同於資料完全可攜；發行附件本身不包含
`UserData`。完整內容與發行者流程見
[GitHub 免安裝自包含 ZIP](docs/self-contained-zip.md)。

## 從原始碼執行的必要條件

- Windows 10／11 x64。
- Python 3.14 以上。
- Git。

YouTube 完整工作流程另需 yt-dlp EJS、FFmpeg／ffprobe 與支援的 JavaScript
runtime；程式會顯示缺少項目，但不會未經確認自動安裝。詳見
[執行環境健康檢查](docs/dependency-health.md)。

## 建立環境

```powershell
git clone https://github.com/z1379228/MediaManager-.git
Set-Location .\MediaManager-
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[ui,dev]"
```

## 啟動

```powershell
.\.venv\Scripts\python.exe .\main.py
```

可用的唯讀或隔離模式：

```powershell
.\.venv\Scripts\python.exe .\main.py --portable --headless
.\.venv\Scripts\python.exe .\main.py --portable --verify-only
```

`--portable` 會把資料放在執行根目錄旁的 `UserData/`。一般開發執行使用
Repository 既有資料路徑；刪除虛擬環境不等於刪除使用者資料。

## 初次檢查

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -B .\main.py --verify-only
```

`--verify-only` 只檢查核心完整性。啟動 UI 後，按主畫面的核心／選用 MOD
工具狀態按鈕開啟「執行環境」，再按「重新檢查」取得實際依賴狀態。目前沒有
獨立的依賴健康檢查 CLI。

若 UI 套件未安裝，重新執行 `pip install -e ".[ui]"`。外部工具未就緒時，
與其無關的媒體庫及 MOD 仍可使用；不要以關閉完整性或信任檢查作為修復方式。

## 更新與移除

- 更新前先備份使用者資料，然後更新來源並重新安裝 editable package。
- 移除程式時分開處理 `.venv`、來源與使用者資料；不要讓清理腳本推測或遞迴
  刪除不明路徑。
- `Version/` 是保留產物，不是一般執行或暫存目錄。
