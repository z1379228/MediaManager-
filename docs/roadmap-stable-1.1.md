# MediaManager 正式版 1.1 規劃

正式版 1.1 的目標不是再增加一份範本，而是讓第三方作者能在乾淨資料夾中，使用公開、
可安裝的工具完成真正可驗證的 MOD 生命週期。Stable 1.0 尚未通過 production
Ed25519 與 Authenticode 門檻前，不得跳號發布 Stable 1.1。

## 已有基線

- schema v2 manifest、API 1.0 與 runtime protocol 1.0 驗證。
- `en`、`ja`、`zh-CN`、`zh-TW` 四語宣告式 UI schema v2。
- Adapter SDK 的 Search／Download v2 `create`、`validate` 與 `catalog` 離線流程。
- 使用者端的發布者信任、安裝、停用、更新、回退、移除及隔離清理介面。

以上能力仍不得被描述為「第三方作者已可完整自行發布」；目前作者端工具與乾淨環境
證據尚不完整。

## 必須完成

- 將 MOD SDK 納入 wheel／Portable 可用範圍，不要求作者持有 MediaManager 原始碼。
- 提供安全的 `create`、inventory／hash、離線 `sign`、`pack`、`validate` 與 lifecycle
  指令；私鑰永遠由作者外部保存，不自動建立或上傳。
- 修正範本硬編的舊核心版本，產生最小四語 `ui.json`，並同步更新
  `MOD-DEVELOPMENT.md`、MOD 開發指南與 runtime request／response、初始化、錯誤及
  shutdown 契約。
- 提供一個獨立 sample MOD，在乾淨資料夾完成：建立 → inventory → 簽署 → 打包 →
  驗證 → 信任 → 安裝 → 顯示四語 UI → 更新 → 回退 → 停用 → 移除。
- CI 執行上述生命週期，不使用 production private key、Cookie 或 token；測試金鑰只限
  隔離測試資料且不得被正式版信任。
- Search／Download adapter 正式 runtime 需另外具備逾時、取消、程序樹終止、訊息與
  資源上限、權限 token、host ownership 衝突檢查及動態 capability UI。

## 完成條件

未接觸核心原始碼的新作者可依中文指南，在乾淨環境中建立、封裝、驗證及安裝 sample
MOD；CI 可重現完整生命週期；任何未簽署、未信任、權限超界或 protocol 不相容的套件
均 fail closed，且不會降低 `SAFE_MODE`。
