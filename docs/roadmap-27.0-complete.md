# 27.0 完整方案與 P0／P1／P2 重新分配

本文件以目前程式、MOD manifest、路由表、UI 自檢與離線稽核結果為準；
「已通過稽核」不等同於已通過所有網站的即時網路 smoke。

## P0：發布前不可缺少

- 下載佇列：暫停、取消、重試、重啟後保持暫停，不自動重跑。
- 輸出安全：路徑邊界、原子提交、磁碟保留、重複任務與 `.part` 清理。
- MOD 安全：manifest v2、完整性雜湊、父子啟用限制、最小權限、SAFE_MODE。
- UI 自檢：registry、父子狀態、四語言、路由、網站能力矩陣與依賴快照。
- 發布證據：Ruff、pytest、MOD／網站／依賴／版本稽核與 copied-folder smoke。

狀態：已完成離線驗證；Testing 候選仍需正式簽章身分與實際 provider smoke 證據。

## P1：目前主要功能

- YouTube／Music：`youtube.com`、`www.youtube.com`、`m.youtube.com`、
  `music.youtube.com`、`youtu.be`、`youtube-nocookie.com`。
- Bilibili：主站、`www`、`m`、`space`、`search`、`b23.tv`；搜尋、影片、UP 主、
  分段與彈幕功能分屬不同子 MOD。
- 動畫瘋：`ani.gamer.com.tw`；作品搜尋、分類、集數、離線紀錄與嵌入式官方頁。
- MEGA：`mega.nz`／`www.mega.nz` 分享檔案與資料夾；`mega.io` 僅為官方入口。
- Facebook：主站、`www`、`m`、`fb.watch`；僅支援合法明確網址流程。
- Instagram、Threads、X：官方頁與資料匯出說明，不宣稱自動下載。

狀態：內建 MOD 群組稽核 8 組／4 語言通過；網站能力矩陣 13 網站／39 功能／
56 工作流程通過。

## P2：延後與候選

- Gopeed 橋接：需外部程序、API 權限與 token 生命週期，預設關閉。
- P2P／Torrent：另建傳輸與檔案安全模型，不進入網站下載核心。
- `bilibili.tv`：視為不同網站，待建立獨立 provider、manifest、路由與 smoke 後再納入。
- 瀏覽器擴充、剪貼簿監控、雲端同步、遠端控制：維持候選。
- 廣告、登入、DRM、地區限制繞過：明確排除。

## MOD／子網域自檢結論

| 父 MOD | 已接入子網域／主機 | 狀態 |
| --- | --- | --- |
| YouTube | standard、Music、mobile、short link、no-cookie | 已支援 |
| Bilibili | main、www、m、space、search、b23.tv | 已支援；`bilibili.tv` 延後 |
| AniGamer | `ani.gamer.com.tw` | 已支援 |
| MEGA | `mega.nz`、`www.mega.nz` | 分享下載已支援；`mega.io` 僅為入口 |
| Facebook | main、www、m、fb.watch | 已支援 |
| Instagram／Threads／X | 官方頁與匯出頁 | 頁面／匯出支援，不含自動下載 |

自檢方法：路由精確主機比對、manifest `url_hosts`、父子 group manifest、四語言
locale、網站能力矩陣與 provider registry 交叉檢查；不以網域猜測或萬用子網域放行。
