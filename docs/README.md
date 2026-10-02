# MediaManager 文件索引

此目錄只保留目前有效的規格、狀態與維護文件。已結案 roadmap、過期候選、
逐版重複日誌與退役功能說明已從目前樹移除；必要時由 Git 歷史或 GitHub Releases
追查，不另建第二份歷史索引。

- 目前來源版本為開發版 39.0（核心相容版本 39.0.119）。
- [下一次 Development 資源與 MOD 效能計畫](performance-mod-optimization-plan.md)
  已開始執行；39.0.106 已完成階段 A 至 D 及 onefile／onedir 隔離比較，
  39.0.107 開始階段 E 的下載工作流與 UI 改善，39.0.108 完成稽核修正，
  39.0.109 加入手動拖放、輸出試轉與快速健康檢查，39.0.110 增加明確的
  Intel／AMD／AV1 硬體轉檔 preset 並把 FFmpeg 能力偵測移至背景；39.0.111
  加入兩階段目標容量與明確非 Passthru 的音量標準化；39.0.112 完成只由
  本機媒體庫手動觸發、只更新本機資料庫的 MusicBrainz 中繼資料 MOD；39.0.113
  修正 PyInstaller 外部 ICU 污染並新增 Qt runtime 發行 gate；39.0.114 加入
  可搜尋且不改變設定的功能簡介；39.0.115 開始擴充其他適合網域，先完成
  無網路、具 XML 資源上限的 Podcast / RSS 本機匯入與 Direct HTTP 手動交接；
  39.0.116 再加入使用者指定公開 HTTPS 實例、只查本機公開影片且不混入聚合
  搜尋的 PeerTube 官方 API MOD；39.0.117 將完整 FFmpeg／ffprobe／runtime
  健康檢查延後到使用者開啟「環境」視窗時執行，發行資料夾內已固定 SHA-256
  身分的 Deno 也不再重複啟動版本探測，避免 GUI 啟動時連續建立短命 CLI 視窗；
  39.0.118 再把該檢查移出 GUI thread，並以品質稽核阻擋任何未套用 Windows
  隱藏視窗政策的正式執行期子程序；39.0.119 完成搜尋失敗來源手動重試、
  下載工作中心與系統匣控制、明確 CPU 重試、媒體庫增量重掃、外部 MOD 健康摘要，
  以及 Podcast 本機匯出與資源預覽。
  原先無效的本機 Testing `1.2.4` 已清除並由
  39.0.113 重建，但仍未簽署、push 或發布。Development 40.0 仍是
  `NO RELEASE`，不因規劃文件建立空版本。
- Testing `1.2.0` 已由 Development `39.0.11` 建立本機歷史封存，保留於
  `Version/Testing/1.2`，未建立 GitHub Release。
- [Testing `1.2.2`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)
  已由 Development `39.0.39` 的乾淨 source freeze
  `f7c65ee1a8e92828ede299bcbdff5e66d16f6810` 建立並發布，納入
  `39.0.13`～`39.0.39` 的搜尋修正並維持未簽署 Testing 身分；既有
  [Testing `1.2.1`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.1)
  目錄、tag 與附件保持不可變。
- `MediaManager v1.0` 是產品顯示名稱，不改變 Development／Testing／Stable 的
  信任與發布判斷。

## 使用與狀態

- [專案首頁](../README.md)
- [安裝與啟動](../INSTALL.md)
- [目前專案狀態](project-status.md)
- [執行環境健康檢查](dependency-health.md)

## 架構與能力邊界

- [下一次 Development 資源與 MOD 效能計畫](performance-mod-optimization-plan.md)
- [下載工作契約](downloads-v1.md)
- [網站主機與路徑清冊](site-host-inventory.md)
- [Direct HTTP 能力邊界](direct-http-boundary.md)
- [MEGA 能力邊界](mega-boundary.md)
- [PeerTube 公開實例搜尋邊界](peertube-search-boundary.md)
- [社群平台官方工具邊界](social-platform-boundaries.md)
- [網站父／子 MOD 與語言契約](site-mod-group-format.md)

## 第三方 MOD

- [第三方 MOD 開發指南](mod-developer-guide.md)
- [MOD 套件格式](mod-package-v1.md)
- [Search／Download Adapter SDK](adapter-sdk.md)
- [YouTube 搜尋 MOD 強化計畫](youtube-search-mod-plan.md)
- [Repository 根目錄快速入口](../MOD-DEVELOPMENT.md)

## 維護與發行

- [版本資料夾與三軌政策](version-layout.md)
- [GitHub 免安裝自包含 ZIP](self-contained-zip.md)
- [Development 39.0–40.0 更新紀錄](release-39.0-40.0.md)
- [Testing 1.2.4 候選與 1.2.x 發行紀錄](release-testing-1.2.md)
- [Testing 1.1 說明](release-testing-1.1.md)
- [簽章與發行 Gate](release-signing.md)
- [GitHub 自動檢查與合併](github-auto-merge.md)
- [原生崩潰證據 Runbook](native-crash-evidence-runbook.md)

文件描述與程式、manifest 或測試不一致時，以可重現工具輸出為準並修正文件；
不可藉由改文字降低安全、簽章或發布條件。
