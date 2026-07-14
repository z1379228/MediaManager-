# 安裝與執行需求

## 支援環境

- Windows 10 或 Windows 11，64 位元。
- 建議至少 4 GB RAM；格式轉換、語音辨識或大型佇列建議 8 GB 以上。
- 足夠的下載與暫存空間。轉檔時建議保留來源檔案大小兩倍以上的可用空間。
- 需要線上搜尋或下載時必須有網路連線；本機媒體庫可離線使用。
- 不需要特殊驅動。若選用 NVIDIA NVENC，需安裝支援該功能的 NVIDIA 顯示驅動。

## 建議安裝：Portable ZIP

最新版 `MediaManager-2.7-portable.zip` 已包含：

- `MediaManager.exe`
- Deno JavaScript runtime
- FFmpeg 與 ffprobe
- 內建 MOD、授權說明、版本資訊及 SHA-256 清單

安裝步驟：

1. 從本倉庫 Releases 下載 Portable ZIP。
2. 完整解壓縮，不要直接在 ZIP 內執行。
3. 建議放在 `C:\Apps\MediaManager-2.7` 或使用者文件資料夾；避免唯讀目錄。
4. 執行 `MediaManager.exe`。
5. 啟動後點選環境狀態，確認 yt-dlp、JavaScript runtime、FFmpeg 與 ffprobe。

Portable 模式會在程式旁建立 `UserData`。要搬移軟體時，請先關閉程式，再搬移整個資料夾。

## 使用單獨 EXE

單獨 EXE 已包含 MediaManager、PySide6 與 yt-dlp，但完整下載/轉檔功能仍需要 FFmpeg、ffprobe 與 JavaScript runtime。可使用 winget 安裝：

```powershell
winget install --id Gyan.FFmpeg
winget install --id DenoLand.Deno
```

安裝後重新開啟 PowerShell及 MediaManager，確認：

```powershell
ffmpeg -version
ffprobe -version
deno --version
```

若指令已安裝但 MediaManager 尚未偵測到，重新登入 Windows 或重新啟動程式以刷新 PATH。

## 選用功能

- 語音轉文字需要 `whisper-cli`，並由使用者自行匯入已核對 SHA-256 的 whisper.cpp 模型；程式不會自動下載模型。
- NVIDIA 硬體編碼是選用功能；無可用 NVENC 時會回退到 CPU 路徑。
- 網站需要登入、會員、地區授權或 DRM 時，MediaManager 不會繞過限制。

## 驗證下載

每個 Release 都附有 `SHA256SUMS.txt`。PowerShell 可核對檔案：

```powershell
Get-FileHash .\MediaManager.exe -Algorithm SHA256
```

將輸出與 Release 內的清單比較。雜湊不同時不要執行。

## 移除

1. 關閉 MediaManager，確認沒有下載或轉檔工作。
2. 如需保留設定，先備份 `UserData`。
3. 刪除解壓縮後的 MediaManager 資料夾。

MediaManager Portable 版不會安裝系統驅動或廣告元件。

