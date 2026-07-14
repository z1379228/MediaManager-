# MediaManager 開發版 7.0 至 8.0 更新紀錄

本文件以 7.0 搜尋工作階段為基線，集中記錄 8.0 的第三方 MOD 適配改進。

## 7.0 基線

- 搜尋分頁 cursor 由核心以 HMAC 不透明 token 綁定查詢、類型與 provider。
- 來源健康資訊記錄連續失敗與成功次數。

## 8.0

- Adapter SDK 新範本的最高核心版本改為目前 `CORE_VERSION`，避免新建專案立即過期。
- 新增最多 100 個 Adapter 專案的批次唯讀相容性報告；不安裝、不信任、不簽署、
  不載入或執行第三方程式碼。
- 批次報告列出每個專案的 ID、類型、錯誤、警告、外部工具與 Python 依賴。
- 重複 Adapter ID、超量目錄、危險 symlink、無效 manifest 及核心版本不相容
  都會使整體報告 fail-closed。
- `python -m tools.adapter_sdk catalog <目錄> --json` 可供作者及 CI 使用。
- 宣告式 MOD UI 仍永久只支援 `en`、`ja`、`zh-CN`、`zh-TW`；未知語言回退
  manifest 預設，不接受 HTML、Qt 物件或任意腳本。

下一階段下載與正式版候選更新記錄於 [`release-8.0-9.0.md`](release-8.0-9.0.md)。
