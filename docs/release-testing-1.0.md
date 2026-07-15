# MediaManager 測試版 1.0

測試版 1.0 將開發版 11.0 已驗證的功能提供給使用者回饋。它是 GitHub
Pre-release，不是正式版，也不代表正式安全簽署已完成。

## 版本識別

- 使用者顯示版本：測試版 1.0
- 核心／MOD 相容版本：11.0.0
- 本機路徑：`Version/Testing/1.0`
- GitHub 標籤：`test-v1.0.0`
- 安全模式：`SAFE_MODE`

## 主要範圍

- YouTube／YouTube Music 使用同一父 MOD，搜尋、歷史、替代、相似內容、預覽與
  自動切割維持可個別控制的子 MOD。
- Bilibili 搜尋與彈幕分別是子 MOD；主 MOD 保留影片、番劇與分 P 下載能力。
- Facebook 限於使用者提供的公開影片網址，不提供音訊、字幕、分段或播放清單選項。
- MEGA 使用獨立公開檔案下載介面，不混入影片網站格式或試聽控制。
- 動畫瘋提供官方近期熱播、新上架、分類、搜尋與官方播放入口，不下載串流、
  不跳過廣告，也不規避登入、地區或播放器限制。
- 四種核心語言為繁體中文、簡體中文、英文與日文，父 MOD 啟用後才顯示其子 MOD。

## 安裝與回報

請完整保留資料夾內容後執行 `MediaManager.exe`；缺少外部工具時可執行
`安裝必備軟體.bat`。建議與問題可透過
[MediaManager 建議表單](https://forms.gle/iUMyEDojsASoFyY16) 回報。

本測試版不得改標成正式版。正式版仍需要生產 Ed25519、Authenticode、完整 preflight
及使用者明確放行。
