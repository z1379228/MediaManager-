# MediaManager 開發版更新紀錄 8.0～9.0

## 8.0

- Adapter SDK 加入有界目錄驗證、相容版本檢查、重複 ID 檢查與 JSON 報告。
- 宣告式外部 MOD UI schema v2 限定 `en`、`ja`、`zh-CN`、`zh-TW` 四種語言。

## 9.0

- 下載佇列整合有界自動重試：第一次等待 2 秒、第二次等待 8 秒，最多自動重試
  2 次，單次等待上限 30 秒。
- 只重試 provider 明確標示 `retryable=True` 的暫時性失敗；永久失效、需要登入、
  DRM、磁碟或權限錯誤不會盲目重試。
- 重試次數與下一次等待時間寫入佇列狀態，舊版 JSON 可安全載入；手動重試會重設
  計數，暫停、取消與關閉可中斷等待。
- Search cursor、Adapter catalog 與下載重試共同完成搜尋、MOD 適配及下載可靠性
  的大版本強化。

## 9.x 特別修正：MOD 顯示、語言與說明

- 修正 MOD 多語言資料層已完成、但 UI 沒有語言選擇器且 bootstrap 忽略設定語言
  的接線缺口。
- 外部 MOD 介面可切換英文、日文、簡體中文與繁體中文；選擇會寫回
  `settings.json`，下次啟動正確還原。
- 即使目前沒有已啟用的外部 MOD，語言選擇器仍保持可用並保存設定；不再因空白清單
  錯誤停用整個語言區塊。
- MOD 狀態區分「未啟用」「安全模式限制」與「初始化失敗」，並顯示安全原因；開發版
  不會為了讓畫面全綠而繞過外部可執行 MOD 的簽章限制。
- 外部 MOD 啟用後切換到介面頁會自動重新載入，另提供手動重新整理；SAFE_MODE
  阻擋外部可執行 MOD 時顯示明確原因，不再只呈現空白頁。
- 3 個下載 MOD、8 個探索 MOD、3 個選用功能 MOD（共 14 個）全部納入唯一啟用
  路由稽核；
  搜尋頁、下載頁與 MOD 管理器統一透過相同控制器發布跨頁同步事件。
- Media Convert、Speech to Text、Automation 在 MOD 管理頁與各自分頁補上中文
  使用順序、入口與 FFmpeg／whisper-cli／模型依賴說明。
- Portable 根目錄新增 `安裝必備軟體.bat`：雙擊後自動偵測並補齊 FFmpeg、ffprobe
  與 Deno；已安裝或內附的元件會略過，缺少 winget 或選用的 whisper-cli 時會明確提示。
- 一鍵安裝不夾帶 Git、GitHub CLI 或 Python 等開發工具，也不含任意網址下載、靜默安裝
  或繞過系統政策。
- MOD 接線稽核加入正式版候選必要證據；未通過不得封裝 Stable。
- 將原本實際綁定 YouTube 的跨站搜尋拆開：YouTube Search、Bilibili Search 與
  動畫瘋官方搜尋使用三個獨立 provider、權限與啟用開關，停用其中一個不會回退到
  YouTube。
- Bilibili Search 只查詢 Bilibili 官方公開搜尋端點；動畫瘋搜尋只解析官方搜尋頁並
  開啟官方作品頁，不提供下載、試聽或內嵌影片預覽。
- Bilibili 官方端點若回覆驗證或節流狀態，會明確提示稍後重試／使用官方瀏覽器搜尋，
  不會改查 YouTube，也不嘗試繞過驗證碼。
- 搜尋結果來源會一路保留到 UI，跨網站相同影片 ID 不再誤判為重複；YouTube 專用的
  歷史、失效替代、相似搜尋與影片預覽不會套用到其他網站。
- Ruff 與 566 項測試通過，另有 2 項 Windows symlink 測試因帳戶權限跳過。

上述搜尋拆分目前是 `codex/separate-site-search` 工作樹候選，尚未提交、合併、重建或
上傳為公開 9.x 成品。合併前仍須補上聯合搜尋的每來源公平收集，避免第一個來源吃滿
結果上限，並重新執行 CI、copied-folder、SHA-256 與 MOD 接線稽核。

## 正式版 1.0 候選

開發版 9.x 的既有功能與 MOD 接線稽核已通過，但搜尋拆分工作樹尚未成為已驗證成品；
production Ed25519 release identity 也尚未設定，`MediaManager.exe` 的 Authenticode
狀態仍是 `NotSigned`。因此目前只能保留開發版與正式版候選資訊，不能建立或上傳
Stable 1.0 二進位檔。

候選細節見 [`release-stable-1.0-candidate.md`](release-stable-1.0-candidate.md)。

> 後續註記：網站父／子 MOD、四語言資源與 YouTube／Bilibili 工作區完全隔離在
> Development 9.1 完成，驗證結果請以 [`release-9.0-10.0.md`](release-9.0-10.0.md)
> 為準；本檔保留 8.0～9.0 的歷史紀錄，不回寫成 9.1。
