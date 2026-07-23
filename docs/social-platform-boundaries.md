# 社群平台官方工具邊界

Facebook、Instagram、Threads 與 X／Twitter 各自擁有獨立 MOD 與主機權限，
不會因同屬社群平台而共用 Cookie、session、下載 provider 或網址 allowlist。

## Facebook

- 獨立下載 MOD 只接受使用者提供的有界公開影片／Reel URL。
- 使用隔離 provider 讀取公開 metadata 與有界縮圖，再由使用者明確加入共用佇列。
- 不接受登入內容、Cookie、帳密、個人檔案、feed、留言、限時動態或私人頁面。
- extractor 存在不代表 Meta 官方支援，網站變更後可能失效。

## Instagram 與 Threads

- 父 MOD 只提供官方頁面與使用者自行取得的官方資料匯出 ZIP。
- URL 只在使用者點擊後交給系統瀏覽器；登入及匯出留在 Meta 官方網站。
- 本機 ZIP 檢查有大小、路徑、項目與媒體類型上限；不匯入腳本、Cookie、
  session 或帳號 metadata。
- 不提供第三方內容下載、profile/feed 抓取或媒體端點解析。

Threads 的舊 `threads.net` 官方 post URL 可正規化到 `www.threads.com`；
不接受 lookalike host、HTTP、自訂連接埠、帳密、任意 query 或 profile 路徑。

## X／Twitter

- `twitter-page` 只驗證並開啟有界的官方 status URL。
- `twitter-export` 只開啟官方帳號資料匯出說明，並檢查使用者另行下載的本機 ZIP。
- 不執行 X 網站 scripting、scraping、Cookie 匯入、媒體解析或下載。

## 共通規則

- 乾淨啟動不連線；每個外部動作都需要使用者明確點擊。
- 父 MOD 停用時子 MOD 不顯示、不可啟用，也不保留執行程序。
- URL 只接受 exact official host、HTTPS、無帳密、無自訂連接埠與有界路徑。
- 不繞過隱私、登入、rate、region、付費、DRM、廣告或其他存取限制。

未來若加入官方 API，必須另有應用程式權限、使用者 OAuth 授權、最小 scope、
獨立 MOD 與測試；不得把官方工具橋接靜默升級成 generic downloader。
