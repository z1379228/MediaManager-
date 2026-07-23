# MediaManager 文件索引

此目錄只保留目前有效的規格、狀態與維護文件。已結案 roadmap、過期候選、
逐版重複日誌與退役功能說明已從目前樹移除；必要時由 Git 歷史或 GitHub Releases
追查，不另建第二份歷史索引。

- 目前來源版本為開發版 39.0（核心相容版本 39.0.10）。
- Development 40.0 仍是 `NO PLAN / NO RELEASE`；未簽署 `SAFE_MODE`
  Testing 1.1 已以 `test-v1.1.0-r2` prerelease 發布，但不是 Stable 套件。
- `MediaManager v1.0` 是產品顯示名稱，不改變 Development／Testing／Stable 的
  信任與發布判斷。

## 使用與狀態

- [專案首頁](../README.md)
- [安裝與啟動](../INSTALL.md)
- [目前專案狀態](project-status.md)
- [最新來源更新](latest-update.md)
- [執行環境健康檢查](dependency-health.md)

## 架構與能力邊界

- [下載工作契約](downloads-v1.md)
- [網站主機與路徑清冊](site-host-inventory.md)
- [Direct HTTP 能力邊界](direct-http-boundary.md)
- [MEGA 能力邊界](mega-boundary.md)
- [社群平台官方工具邊界](social-platform-boundaries.md)
- [網站父／子 MOD 與語言契約](site-mod-group-format.md)

## 第三方 MOD

- [第三方 MOD 開發指南](mod-developer-guide.md)
- [MOD 套件格式](mod-package-v1.md)
- [Search／Download Adapter SDK](adapter-sdk.md)
- [Repository 根目錄快速入口](../MOD-DEVELOPMENT.md)

## 維護與發行

- [版本資料夾與三軌政策](version-layout.md)
- [Development 39.0–40.0 更新紀錄](release-39.0-40.0.md)
- [Testing 1.1 說明](release-testing-1.1.md)
- [簽章與發行 Gate](release-signing.md)
- [GitHub 自動檢查與合併](github-auto-merge.md)
- [原生崩潰證據 Runbook](native-crash-evidence-runbook.md)

文件描述與程式、manifest 或測試不一致時，以可重現工具輸出為準並修正文件；
不可藉由改文字降低安全、簽章或發布條件。
