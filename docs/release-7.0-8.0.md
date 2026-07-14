# MediaManager 開發版更新紀錄 7.0～8.0

## 7.0

- 搜尋分頁游標改為核心簽章的不透明 token，並與查詢、provider、內容類型綁定。
- 搜尋來源健康資訊加入失敗、成功與恢復狀態，避免 UI 只顯示無法定位的錯誤。

## 8.0

- Adapter SDK 產生的相容上限改用目前 `CORE_VERSION`，不再硬編碼舊版本。
- 新增有界 adapter catalog 驗證，一次最多檢查 100 個專案。
- catalog 會驗證 manifest、runtime、相容版本、重複 adapter ID、不安全根目錄與
  symlink，遇到異常採 fail-closed。
- 新增 `python -m tools.adapter_sdk catalog <目錄> --json`，只做靜態檢查，
  不安裝、不信任、不簽章，也不執行外部程式碼。
- 宣告式 MOD UI schema v2 固定只接受英文、日文、簡體中文與繁體中文。
- Ruff、完整測試與 43 項版本 SHA-256 稽核通過。

下一區間詳見 [`release-8.0-9.0.md`](release-8.0-9.0.md)。
