# 安裝與啟動

目前沒有可供一般使用者下載的已簽署 Stable 套件。本文件只說明從 Repository
執行目前來源；不要把自行建置的 Development EXE 標示為正式發行版。

## 必要條件

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
.\.venv\Scripts\python.exe -m tools.dependency_health
.\.venv\Scripts\python.exe -B .\main.py --verify-only
```

若 UI 套件未安裝，重新執行 `pip install -e ".[ui]"`。外部工具未就緒時，
與其無關的媒體庫及 MOD 仍可使用；不要以關閉完整性或信任檢查作為修復方式。

## 更新與移除

- 更新前先備份使用者資料，然後更新來源並重新安裝 editable package。
- 移除程式時分開處理 `.venv`、來源與使用者資料；不要讓清理腳本推測或遞迴
  刪除不明路徑。
- `Version/` 是保留產物，不是一般執行或暫存目錄。
