# MediaManager

MediaManager 是一套免費、無廣告、Windows 優先的模組化媒體管理工具。預設介面保持簡潔，YouTube、Bilibili、通用網站下載、影片預覽、格式轉換、語音轉文字與自動化等功能可依需要啟用或停用。

目前最新公開成品：**2.7.0 開發版**。

> 目前 EXE 尚未使用正式 Windows Authenticode 與產品 Ed25519 身分簽章，因此會以 `SAFE_MODE` 啟動。請只從本倉庫 Releases 取得檔案並核對 SHA-256；正式簽章完成前不應視為正式穩定發行版。

## 主要功能

- 乾淨的深色桌面 UI，可自訂背景及字體密度。
- YouTube 搜尋、縮圖、音訊/影片預覽、批次下載、格式選擇、分段下載、相似搜尋及失效影片替換。
- Bilibili 影片資訊、字幕及 XML/ASS 彈幕工作流程。
- 通用網站下載 MOD；實際支援度取決於網站規則、地區、登入要求及 yt-dlp 支援狀態。
- 本機媒體庫、播放紀錄、標籤、播放清單與重複檔案檢查。
- 選用的 FFmpeg 格式轉換、whisper.cpp 語音轉文字及自動化 MOD。
- Portable 資料夾模式；每個已發布版本均保留在獨立 Release。

## 下載與安裝

一般使用者請到 [Releases](https://github.com/z1379228/MediaManager-/releases) 下載最新版：

1. 優先下載 `MediaManager-2.7-portable.zip`。
2. 解壓縮到可寫入的資料夾，例如 `C:\Apps\MediaManager-2.7`。
3. 執行 `MediaManager.exe`。請勿只把 EXE 從 Portable 資料夾單獨移出。
4. 若 Windows 顯示未知發行者，先核對 Release 的 SHA-256；不確定來源時不要執行。

完整需求、精簡版依賴與安裝指令請看 [INSTALL.md](INSTALL.md)。

## 版本選擇

- **最新版 Portable ZIP**：建議一般使用者使用，包含程式所需的 Deno、FFmpeg 與 ffprobe。
- **單獨 EXE**：適合已自行安裝相依工具或只使用不需要媒體處理工具的功能。
- **最新原始碼**：在 v2.7.0 Release 下載 `MediaManager-2.7.0-source.zip`，並使用同名 `.sha256` 核對；它與執行檔分開提供，不包含 Git、快取、UserData 或建置成品。
- **wheel**：供測試及 Python 環境使用，不是一般桌面使用者的首選。
- **舊版本**：只供回溯、相容性測試或復原；不會自動取得新修正。

## MOD 開發

第三方 MOD 必須遵守 manifest v2、最小權限、檔案雜湊與 Ed25519 發行者簽章流程。請先閱讀 [MOD-DEVELOPMENT.md](MOD-DEVELOPMENT.md)。

未簽章、發行者未受信任、要求禁止權限或不符合核心版本範圍的 MOD 會被拒絕。`SAFE_MODE` 可安裝套件但不能啟用可執行 MOD。

## 意見與建議

功能建議、操作問題與改善方向可填寫：

**[MediaManager 建議表單](https://forms.gle/iUMyEDojsASoFyY16)**

## 使用界線

MediaManager 不提供 DRM、付費、地區、廣告或登入驗證繞過。使用者必須遵守網站服務條款、著作權及所在地法律；受保護或未獲授權的內容不應下載或再散布。

