# MediaManager 開發版更新紀錄 6.0～7.0

## 6.0

- YouTube 探索拆成 Search、History、Recovery、Similar、Player 與 Auto Split 等
  可獨立停用的內建 MOD。
- 搜尋、歷史、失效影片替代、相似內容與長影片音訊切割流程完成第一版整合。
- 開發版與正式版目錄分離為 `Version/Development`、`Version/Stable`；正式版
  必須通過簽章與發布 preflight。
- 固定 MOD UI 語言上限為 `en`、`ja`、`zh-CN`、`zh-TW`，不加入外部翻譯服務。

## 7.0

- provider 原始分頁游標改由核心包成不透明 HMAC token。
- token 綁定標準化查詢、provider 與內容類型，拒絕跨查詢重用、竄改及非標準
  Base64 表示。
- provider cursor 上限 500 字元，完整 token 上限 2048 字元。
- 搜尋來源新增連續失敗、成功次數與復原狀態，保留 Search v2 相容性。
- Ruff、完整測試、copied-folder smoke 與 43 項版本 SHA-256 稽核通過。

下一區間詳見 [`release-7.0-8.0.md`](release-7.0-8.0.md)。
