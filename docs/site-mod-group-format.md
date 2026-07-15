# 網站父 MOD／子 MOD 與語言契約

Development 9.1 起，完成度足以顯示在可信 UI 的網站功能必須遵守下列規則；
Development 11.0 將規則套用到下載、搜尋與宣告式功能三種內建登錄表。

## 資料與語言

- 每個網站主 MOD 使用一個英文 `group_id`，例如 `youtube`、`bilibili`。
- 主目錄提供受核心雜湊保護的 `group.json` 與 `locales/`；只允許 `en`、`ja`、
  `zh-CN`、`zh-TW` 四個檔案，且每個檔案必須完整覆蓋該群組所有可見子 MOD。
- 核心 `settings.language` 是唯一語言來源。MOD 不保存第二份語言選擇；核心切換語言後
  發布 `ui.language.changed`，工作區、MOD 管理與搜尋來源同步重新讀取同一語言檔。
- 未知語言回退到 `zh-TW`；缺檔、少翻譯、額外欄位或無效 UTF-8 均視為群組驗證失敗，
  不可用空白頁或其他語言假裝成功。

## 父子生命週期

- 主 MOD 永遠可見；子 MOD 只有在主 MOD 已啟用時才顯示並允許開關。
- 停用主 MOD 會同步停用已啟用的子 MOD，取消主 MOD 擁有的工作，並發布每個狀態事件。
- 舊設定若出現「主 MOD 關閉、子 MOD 開啟」，Bootstrap 在建立 UI 前自動改為關閉子 MOD。
- YouTube 的主 MOD 是 `youtube`，子 MOD 為搜尋、影片試看、歷史、失效替代、相似內容
  與自動切割；YouTube Music 是同一網站家族，不另建重複主 MOD。
- Bilibili 的主 MOD 是 `bilibili`，子 MOD 是 `bilibili-search` 與
  `bilibili-danmaku`。停用彈幕子 MOD 時，下載仍可使用，但 XML、ASS 與 MKV
  控制會隱藏並清除，避免把額外能力誤當成主下載必要條件。
- 動畫瘋的主 MOD 是 `ani-gamer`，`ani-gamer-search` 是子 MOD。主工作區只開啟
  經允許的官方目錄、分類、作品及播放頁；搜尋子 MOD 關閉時仍可使用官方分類入口。
- Development 9.2 的 `facebook` 與 `mega` 是沒有子 MOD 的獨立主 MOD；兩者預設
  停用，啟用後才建立各自下載工作區。Facebook 不與 Instagram／Threads 共用下載
  provider；MEGA 也不經 `generic-ytdlp`。

## 各網域能力邊界

- YouTube／YouTube Music：影片、播放清單、格式、字幕、試聽／預覽及選用子功能。
- Bilibili：影片、番劇、分 P 與字幕；彈幕下載及轉換由獨立子 MOD 管理。
- Facebook：只處理使用者提供的公開影片頁，無音訊格式、字幕、分段或播放清單控制。
- MEGA：只處理公開檔案傳輸與檔案種類辨識，不顯示影音格式、字幕、試聽或播放清單。
- 動畫瘋：官方目錄、分類、搜尋與官方播放入口；不提供下載、廣告處理或串流擷取。

## 網域隔離

- 一個可執行 provider 只能屬於一個網站群組；`provider_id` 不可跨群組重複。
- `network.<site>` 權限與搜尋 `sites` 必須等於父群組，不得用 YouTube 代查 Bilibili
  或動畫瘋，也不得在 YouTube 工作區顯示其他網站選項。
- 每個群組與四語言資源都納入內建 MOD SHA-256；執行
  `python -m tools.audit_mod_groups --root .` 可快速檢查群組、語言與 provider 邊界。
- `generic-ytdlp` 是 9.1 暫留且預設停用的舊 Beta 相容 provider，沒有 YouTube／
  Bilibili 工作區入口。其網站必須逐站遷移成獨立主 MOD；新網站禁止加入此聚合 provider。
