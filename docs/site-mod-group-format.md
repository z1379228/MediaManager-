# 網站父 MOD、子 MOD 與語言契約

可信 UI 中的網站功能共用父子生命週期、exact-host ownership 與四語言來源。
網站專屬邏輯不得放入核心或借用另一個網站的 provider。

## 群組與語言

- 每個網站父 MOD 使用唯一英文 `group_id`。
- 父目錄提供 `group.json` 與 `locales/en.json`、`ja.json`、`zh-CN.json`、
  `zh-TW.json`；四份檔案必須完整覆蓋所有可見子 MOD。
- `settings.language` 是唯一語言來源。未知語言回退 `zh-TW`。
- 字串鍵、長度與 schema 都受驗證；不得注入 HTML、Qt 物件、URL callback
  或可執行腳本。
- 缺檔、少翻譯、額外欄位、無效 UTF-8 或 hash 不符會使群組 fail closed。

## 父子生命週期

- 父 MOD 永遠是群組入口；子 MOD 只在父 MOD 已啟用時顯示並允許開關。
- 停用父 MOD 會停用其子 MOD、取消群組工作並停止 runtime。
- 舊設定若出現「父關閉、子開啟」，Bootstrap 在建立 UI 前收斂為關閉。
- YouTube 的搜尋、預覽、歷史、恢復、相似內容與自動切割是 `youtube` 子 MOD。
- Bilibili 搜尋與彈幕是 `bilibili` 子 MOD；停用彈幕不影響主下載。
- Instagram、Threads 與 X／Twitter 的官方頁／資料匯出是各自父 MOD 的子 MOD。
- MEGA、Direct HTTP、Facebook、格式工廠、Gopeed、Speech to Text 與
  Automation 保持各自能力邊界；不得因 UI 分頁相鄰而共享權限。

已退役的 `ani-gamer*` 只作未知舊設定處理，不能重新建立群組、網路權限或
工作區。

## Site matrix

每個內建網站父 MOD 提供 schema v2 `site-matrix.json`，逐一宣告辨識、發現、
分析、預覽、排隊、取消與完成階段，狀態只允許：

- `supported`
- `conditional`
- `browser-mediated`
- `not-applicable`

`ui_capabilities` 決定可信 UI 可顯示的控制；`features` 必須使用有界唯一 ID；
`boundaries` 必須明列 Cookie、登入、地區、付費、DRM、廣告與私人內容限制。

```powershell
.\.venv\Scripts\python.exe -m tools.audit_mod_groups --root .
.\.venv\Scripts\python.exe -m tools.site_quality_audit --root .
```

這些稽核只讀取固定檔案，不連網、不啟動 provider，也不建立 Repository 內暫存。

## 主機與路由

- 一個 executable provider 只屬於一個網站群組，`provider_id` 不可跨群組重複。
- `network.<site>`、搜尋 `sites`、manifest host 與 site matrix 必須一致。
- 只接受已驗證的 exact host 與窄路徑，不使用 wildcard 子網域。
- HTTP、內嵌帳密、自訂連接埠、相似字主機、任意 query、fragment 與
  open redirect 一律拒絕。
- API、CDN、官方說明頁與 localhost 服務不因出現在程式中就成為媒體輸入主機。
- 新主機必須同時具備官方 URL、provider／extractor 證據、最小路徑契約、
  manifest／matrix 更新與成功／失敗 regression。

完整分類見 [網站主機清冊](site-host-inventory.md)。
