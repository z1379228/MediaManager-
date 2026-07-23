# 執行環境健康檢查

MediaManager 不需要額外的顯示卡、音效卡或下載器驅動。它會偵測本機執行元件，主介面的「環境」按鈕顯示完整 YouTube 支援的就緒數量，詳細視窗可手動重新檢查。

啟動時若未達 4/4，程式會主動開啟環境視窗，列出缺少項目、影響範圍及「安裝／修復方式」。不會在未經使用者確認時自動下載或改寫系統。

## 檢查項目

1. **yt-dlp**：YouTube 解析、搜尋與下載。
2. **yt-dlp EJS**：YouTube JavaScript challenge 元件。
3. **FFmpeg / ffprobe**：合併、轉檔、音訊切割與預覽；兩者都存在才視為就緒。
4. **JavaScript runtime**：依序採用 Deno、Node.js、QuickJS。

支援下限依 yt-dlp 官方 EJS 文件維護：

- Deno 2.3.0 以上（優先建議）
- Node.js 22.0.0 以上
- QuickJS 2023-12-9 以上
- Bun 不列入就緒判定，因官方已標示為 deprecated

參考：

- https://github.com/yt-dlp/yt-dlp/wiki/ejs
- https://github.com/yt-dlp/yt-dlp/blob/master/README.md

## 路徑策略

執行檔會先尋找應用程式旁的 `tools/<name>.exe`，其次是應用程式根目錄，最後才使用系統 `PATH`。因此日後可在版本資料夾內提供可攜式 runtime，而不用修改核心或污染使用者系統。

Windows 新版資料夾封裝預設攜帶固定版本、通過 SHA-256 驗證的 Deno，位置為
`Version/<channel>/<version>/tools/deno.exe`。Deno 的快取與下載資料仍由 Deno
自身放在使用者資料位置，不會寫回唯讀的版本目錄。

目前健康檢查不只確認套件名稱是否存在：yt-dlp 需為 2026.7.4 以上、
yt-dlp-ejs 需為 0.8.0 以上且必須包含兩個 solver 資源，系統提供的
FFmpeg 與 ffprobe 則需為 6.0 以上。版本不足會顯示為未就緒，避免表面
4/4、實際執行時才失敗。

同一資料夾也攜帶固定版本且通過雜湊驗證的 `ffmpeg.exe` 與 `ffprobe.exe`。
採用 GyanD 的 FFmpeg 8.1.2 essentials build，並附上 GPL v3 LICENSE、建置設定與
對應來源 commit 資訊。未包含不需要的 ffplay 與 HTML 文件。

缺少任一項不會封鎖媒體庫與其他不相依功能；UI 只會顯示影響範圍。YouTube 完整支援需四項全部就緒。
