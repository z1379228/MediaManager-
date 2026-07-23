# MEGA MOD 能力邊界

`mega` 是獨立網站 MOD，使用官方 MEGAcmd 的 `mega-get` 處理公開檔案或整個
公開資料夾；不經 yt-dlp、Direct HTTP 或其他網站 MOD。

## 接受範圍

- 只接受有界的 HTTPS `mega.nz/file/...#...` 與 `mega.nz/folder/...#...`
  公開分享連結。
- 本機分析只辨識檔案／資料夾種類並檢查 `mega-get` 是否存在。
- 只有使用者明確分析或下載時才啟動外部程序。
- 下載經共用佇列處理目的地、取消、重試、進度與完成通知。
- 完成的資料夾必須落在單一受限根目錄，最多檢查 10,000 個項目，且拒絕
  symbolic link、junction、reparse point 與路徑逃逸。

## 敏感資訊

分享連結中的解密材料不寫入一般標籤、歷史摘要或診斷包；完整連結只傳給
使用者明確啟動的 `mega-get` 程序。程式不接收 MEGA 帳號、密碼、Cookie 或
瀏覽器 session。

## 明確排除

不提供帳號同步、備份、上傳、WebDAV、遠端管理、逐檔遠端瀏覽、quota 規避、
登入自動化或第三方解密服務。舊式連結、缺少解密材料、相似主機、自訂連接埠、
query 或巢狀未授權路徑一律拒絕。

官方參考：

- [MEGA Desktop](https://mega.io/desktop)
- [MEGA SDK](https://github.com/meganz/sdk)
- [MEGAcmd](https://github.com/meganz/MEGAcmd)
