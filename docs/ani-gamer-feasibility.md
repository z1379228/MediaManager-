# 巴哈姆特動畫瘋整合可行性檢視

檢視日期：2026-07-15

目前決策：開發版 9.x 提供獨立、使用者觸發的官方作品搜尋與官方播放入口。

## 依據

- [官方服務條款](https://ani.gamer.com.tw/animeRule.php) 說明應透過服務提供的觀看
  功能使用內容，並限制重製及規避廣告、播放或串流限制的行為。
- [官方搜尋頁](https://ani.gamer.com.tw/search.php) 提供公開作品目錄搜尋；
  MediaManager 只解析它回傳的官方作品連結，不存取私有介面。
- [官方動畫頁](https://ani.gamer.com.tw/animeVideo.php?sn=44866) 使用網站自己的播放器與
  彈幕控制；這不代表第三方程式獲准匯出或下載內容。
- [官方播放疑難排解頁](https://ani.gamer.com.tw/anime403info.php) 說明支援環境、IP、代理、
  VPN 與瀏覽器元件等限制；MediaManager 不會規避這些檢查。

## 已提供範圍

動畫瘋功能與 YouTube、Bilibili 完全分開，預設關閉：

- `ani-gamer-search` 只在使用者按下搜尋後，向官方搜尋頁提交有界關鍵字。
- 搜尋結果只接受精確 `ani.gamer.com.tw/animeRef.php?sn=<數字>` 作品網址，並在系統
  瀏覽器開啟；不會回退到 YouTube。
- 官方播放入口只接受精確動畫瘋 HTTPS 網域與允許的作品／集數路徑。
- 不在背景連線，不讀取或儲存登入 Cookie，也不啟動下載 provider。

## 明確排除

MediaManager 不檢查私有端點、不擷取串流網址、不匯入動畫瘋 Cookie、不下載影片、
不匯出彈幕、不移除廣告，也不規避登入、地區、IP、播放器或其他存取控制。

只有在服務公開授權 API、匯出功能或允許第三方離線使用的授權後，才會重新評估下載或
彈幕整合；官方目錄搜尋不會被解讀成下載授權。
