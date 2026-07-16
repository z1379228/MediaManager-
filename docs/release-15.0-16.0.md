# 開發版 15.0～16.0 實際更新紀錄

本區間採單一整檔記錄。15.1～15.9 是整合進度節點，沒有建立或上傳可被誤認為完整
成品的獨立附件；已完成內容全部由新的 `Version/Development/16.0` 驗證與承載。
既有 `Version/Development/15.0` 未覆寫、未刪除。Development 仍維持 `SAFE_MODE`，
不是 Stable 正式版。

## 15.1

- provider smoke 改為從指定版本資料夾的 `mod/builtin/<provider>` 載入，避免來源樹
  假通過而封裝內容未被驗證。
- TikTok 固定案例更新為仍公開的測試網址；smoke JSON 改用 schema 2 的通過、暫時性
  上游失敗與永久失敗分類。
- 動畫瘋集數遇到 Cloudflare／HTTP 403 時顯示可操作的官方作品頁與標準單集網址
  備援卡，不再把原始 provider 例外直接顯示給使用者。

## 15.2

- 動畫瘋作品切換時會清除舊集數、舊官方單集網址與 403 備援狀態，禁止把前一作品的
  單集誤加入新作品。
- Self Check 新增動畫瘋搜尋、作品選取、顯示集數、官方單集網址、403 備援及開啟
  集數按鈕狀態檢查；不為自檢啟動網路或 provider。
- 作品／集數區維持 940×620 最小視窗可操作，狀態與錯誤訊息不借用 YouTube 工作區。

## 15.3

- YouTube 與 `music.youtube.com` 維持同一父 MOD，單片與播放清單使用同一工作區但
  依內容類型切換按鈕；單片不可展開播放清單。
- 播放清單展開後保留縮圖、試聽／停止、選用影片預覽及格式資訊，預設不勾選項目。
- 暫停、取消、停止預覽與重啟恢復狀態由回歸測試覆蓋，乾淨啟動不會自動開始下載。

## 15.4

- Bilibili 搜尋與下載維持獨立父 MOD 工作區，提供 UP 主篩選、分 P 名稱、縮圖與
  批量選取；不再以「未命名分段」代替已知標題。
- 彈幕 XML、ASS 與選用 MKV 封裝仍由 `bilibili-danmaku` 子 MOD 控制，停用彈幕不
  影響一般影片下載。

## 15.5

- Facebook 公開影片維持只貼網址的獨立下載 provider；Instagram、Threads 與 X
  各自維持官方頁及官方資料匯出父／子 MOD，不跨站搜尋、不讀取 Cookie。
- 官方封存 ZIP 只在本機進行有界安全匯入，拒絕路徑穿越、符號連結與超量項目。

## 15.6

- MEGA 工作區依公開分享資訊顯示檔案／資料夾、類型、大小、樹狀項目與 transfer
  狀態；不混入影片格式、試聽或字幕控制。
- `mega-get`、配額、取消與完成驗證保留分層錯誤；未知檔案類型不會強制當成影片。

## 15.7

- 搜尋契約統一縮圖、來源、作者、長度、內容類型、游標與部分失敗；載入更多採有界
  去重並保留目前選取。
- 0 筆結果與來源失敗分開顯示；指定缺失或停用來源時 fail closed，不回退到其他網域。

## 15.8

- 下載工作支援多選、全選／全不選、批次取消、清除已結束項目、優先級、暫停／繼續、
  原子輸出與取消後 `.part` 清理。
- 新增預設關閉的 `media-ad-trim`，作為 `media-convert` 的本機子 MOD。它只接受使用者
  選取的本機媒體與最多 50 個手動時間區間，提供第一切點前後 5 秒預覽、再次確認、
  H.264/AAC 新檔輸出及個別工作取消；不覆寫原檔。
- 本機剪除不接受網站網址，不處理網站播放器或廣告，也不規避 DRM、登入、付費、
  地區、Cloudflare 或其他存取限制。

## 15.9

- 內建 MOD 編目擴充為 31 個；父／子關係改為通用契約，網站 MOD 與本機功能 MOD
  共用相同的顯示、啟用門檻、停用連動與 Self Check。
- `Media Convert → Local Ad Segment Trim` 只有在父 MOD 啟用後才顯示；父 MOD 停用時
  只取消該父系工作並連帶停用子 MOD。
- 四語言維持 `en`、`ja`、`zh-CN`、`zh-TW`；第三方網站 MOD 仍使用 schema v2、
  最小權限、host ownership、宣告式 UI 與受控程序契約。

## 16.0

- 核心相容版本升為 `16.0.0`，建立新的 `Version/Development/16.0`，不覆寫 15.0。
- 整合動畫瘋 403 安全備援、網域專屬搜尋、YouTube／Bilibili 批量與預覽、社群及
  MEGA 分流、通用父子 MOD 與本機廣告段落剪除。
- Ruff 通過；Pytest 為 844 passed、2 skipped，兩項略過均是 Windows 帳號不能建立
  symlink。文字污染掃描 499 檔、8 組 × 4 語言 MOD 群組、13 個網站能力、39 項功能／
  56 個流程、9 項依賴鎖及 current + previous 版本稽核通過。
- 成品共有 116 個檔案、115 筆 checksum。`MediaManager.exe` SHA-256 為
  `88db3df3bc0aa82006ae81105210ac19c3fcf855c3e8855a1aacb14e141fb5e6`；wheel SHA-256
  為 `91bbf874b3582bfedf65ab3c4db694198b384a1f06c7f55afef751b4fab94110`。
- 封裝 provider smoke 為 7/7；copied-folder 的 `--version`、`--portable --verify-only`、
  `--portable --headless` 均為 exit 0，隱藏 GUI 啟動 5 秒仍存活。一次性 Ed25519 演練
  核對 113 個發行檔、成功偵測竄改且未保留私鑰。
- 發行 preflight 僅因 production Ed25519 key id／public key 尚未設定及 EXE
  Authenticode `NotSigned` 而保持 `ready: false`；16.0 因此維持 `SAFE_MODE`，未建立
  Testing 或 Stable，也尚未上傳。
