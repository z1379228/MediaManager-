# 執行環境健康檢查

MediaManager 不需要額外的顯示卡、音效卡或下載器驅動。主介面的「環境」按鈕
提供完整 YouTube 支援的就緒數量與手動重新檢查。

乾淨啟動不執行 FFmpeg、ffprobe 或 JavaScript runtime 的外部版本命令；尚無本次
程序內快照時，按鈕顯示「環境尚未檢查」。使用者點擊後，詳細視窗會先顯示
「正在背景檢查」，再於非 GUI thread 執行完整檢查；使用者可以關閉視窗，主介面
不會等待外部版本命令。完成結果保存為本次程序內快照，也可在詳細視窗手動重新
檢查。程式不會在未經使用者確認時自動下載或改寫系統。

品質稽核會掃描正式執行期 Python 來源中的 `subprocess.run` 與
`subprocess.Popen`。每個呼叫都必須可靜態追蹤到 Windows
`CREATE_NO_WINDOW`；沒有隱藏視窗政策的新增呼叫會阻擋品質驗證，避免啟動、
分析、轉檔或 MOD 操作再次出現空白命令視窗。

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
自身放在使用者資料位置，不會寫回唯讀的版本目錄。因為此路徑的執行檔身分已由
發行清單固定，Bootstrap 不再額外執行 `deno --version`；PATH 提供的 Deno、Node.js
或 QuickJS 仍須經版本命令驗證。

目前健康檢查不只確認套件名稱是否存在：yt-dlp 需為 2026.7.4 以上、
yt-dlp-ejs 需為 0.8.0 以上且必須包含兩個 solver 資源，系統提供的
FFmpeg 與 ffprobe 則需為 6.0 以上。版本不足會顯示為未就緒，避免表面
4/4、實際執行時才失敗。

同一資料夾也攜帶固定版本且通過雜湊驗證的 `ffmpeg.exe` 與 `ffprobe.exe`。
採用 GyanD 的 FFmpeg 8.1.2 essentials build，並附上 GPL v3 LICENSE、建置設定與
對應來源 commit 資訊。未包含不需要的 ffplay 與 HTML 文件。

缺少任一項不會封鎖媒體庫與其他不相依功能；UI 只會顯示影響範圍。YouTube 完整支援需四項全部就緒。
