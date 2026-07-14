# MediaManager 正式版 1.1 規劃

## 1.1：第三方可自行完成 MOD 開發

正式版 1.1 必須讓沒有專案內部知識的第三方依公開文件完成 MOD，不以「已有範本」
作為完成判定。

- 提供中文開發指南、schema v2 manifest、宣告式四語 UI、runtime contract 與
  可直接複製的最小範例。
- `adapter_sdk create`、`validate`、`catalog` 可完成建立、靜態驗證與多專案相容
  檢查，全程不執行未信任程式碼。
- 文件完整說明 publisher、簽章、打包、安裝、啟用、更新、回退、停用、移除及
  常見錯誤定位，不提供繞過 SAFE_MODE 或信任鏈的捷徑。
- 建立一個獨立 sample MOD，在乾淨資料夾實測「建立 → 打包 → 驗證 → 安裝 →
  顯示 UI → 停用／回退／移除」。
- CI 加入 sample MOD 的契約與生命週期驗證；不把第三方 private key、cookie、
  token 或本機絕對路徑寫入範例與報告。

完成條件：由全新目錄照公開中文流程可重現完整生命週期，且所有安全失敗均為
fail-closed、錯誤訊息可定位。
