# 目前專案狀態

狀態日期：2026-09-12

## 結論

MediaManager 目前工作來源為 Development `39.0.119`。39.0.107 先完成三個下載工作流
基礎：手動貼入與 TXT／CSV 共用可信下載收件匣；瀏覽器交付只接受有界、已知且
可下載的公開 HTTPS 頁面，開啟對應工作區但不自動排隊；資源模式提升為所有下載
頁共用，省資源／平衡／高速分別預設 1／2／4 個全域工作，YouTube 再於核心套用
固定片段額度。自動模式在啟動時依邏輯處理器與總記憶體選取實際模式，資訊不足
採平衡，工作中不重判；本機 12 threads／63.8 GiB 的偵測結果為高速。收件匣與
共用說明元件使用一致的階層、導覽捲動、焦點與非色彩狀態文字。頂層另提供
按需建立的「工作區」分類選單，直接切換並沿用既有 lazy 工作區；它不新增背景
timer，第三方未知工作區仍保留在「其他」。
先前由 39.0.112 建立的 Testing `1.2.4` 本機 EXE／ZIP 已因外部 ICU DLL 污染
判定無效且不得散布；其後已由 39.0.113 乾淨 source freeze 在本機重建並通過
Qt runtime gate，但仍未簽署、push 或發布。Testing `1.2.3` 不覆寫。
格式工廠另完成無損軌道工作流：單一來源由背景 ffprobe 列出音訊／字幕軌，
明確選取後輸出 `.mka`／`.mks`，排隊前重查軌道與副檔名，完成前驗證 codec 及
來源／輸出封包 SHA-256；不在 GUI thread 等待探測，也不重新編碼所選軌道。
39.0.108 的真實 FFmpeg 稽核發現 `.mks` 無法穩定依副檔名推斷 muxer，現已明確
加入 `-f matroska`；實際 SubRip 軌道複製前後的封包 SHA-256 相同。
Speech to Text 亦完成預設關閉的 VAD 能力閘：語音與 VAD 模型在本機 manifest
明確分型並各自驗證 SHA-256；只有使用者要求背景偵測且 whisper-cli 同時提供
`--vad`／`--vad-model` 時，UI 才允許啟用。缺少任一依賴維持一般轉錄，不自動
下載模型，也不以可見 console window 執行 CLI。39.0.108 再把最高 8 GiB 模型
的來源雜湊與複製移出 GUI thread；關閉程式會取消工作並清除未完成暫存檔。
本機媒體庫的重複檔案檢查也改為大小、首尾指紋與完整 SHA-256 三階段確認；
完整雜湊只處理候選並快取至 SQLite。39.0.108 讓每次重複確認自行重查目前大小
與修改時間，使掃描後才被同大小改寫的檔案也會使快取失效。檢查在
背景 thread 執行、可取消且有進度，介面不會自動刪除檔案。
39.0.109 新增共用且有界的拖放分類：一般下載工作區接網址或單一 TXT／CSV，
Direct HTTP 只採用既有政策允許的公開 HTTPS 檔案網址，格式工廠只採用本機媒體；
所有拖放都只填入或開啟既有收件流程，不會自動排隊。格式工廠另提供實際
20 秒輸出試轉與 15 秒開頭健康檢查；兩者在背景執行並與正式轉換共用單一
FFmpeg 執行槽，可取消且不新增正式工作紀錄。試轉暫存檔限制於服務私有目錄，
關閉預覽或服務時清除；自我檢查只讀取功能暖狀態，不會自行啟動程序。
39.0.110 為格式工廠加入 Intel Quick Sync、AMD AMF 及 NVIDIA／Intel／AMD
AV1 的明確硬體 preset。介面只在 FFmpeg build 回報對應 encoder 時允許加入，
工作執行時仍由實際顯示卡與驅動驗證；硬體失敗不會靜默回退 CPU。原本會在
GUI thread 同步執行六個 FFmpeg 能力命令的路徑改為可取消的背景偵測，關閉頁面
會使舊世代結果失效，避免晚到結果改寫已關閉的介面。
39.0.111 新增 H.264 兩階段目標容量轉檔。單一來源時長由背景 ffprobe 提供，
核心以 3% 容器餘裕和第一音軌 AAC 192 kbps 計算影片平均位元率；第一階段只
分析影片，第二階段建立新檔，完成後仍檢查實際檔案不超過使用者上限。pass log
限制於服務暫存目錄並在成功、失敗或取消後清除。此格式與 CRF、硬體 preset
互斥，不會用 `-fs` 提前截斷影片。格式工廠另加入 EBU R128 `-16 LUFS` 的 FLAC
品質優先與 Opus 160 kbps 容量優先格式；兩者都標示會處理音訊樣本，不與串流
複製、Opus Passthru 或一般 FLAC 無損轉碼混用。
39.0.112 完成本機媒體庫的 MusicBrainz 輔助中繼資料工作流。它是預設啟用但
只能由使用者在單一音訊項目的管理選單手動觸發的隔離 MOD；`manual` 搜尋
可見性使它不出現在一般網站搜尋來源，也不參與聚合搜尋。外送只允許官方
`musicbrainz.org/ws/2/recording/` HTTPS 路徑，回應限制 512 KiB、每次最多 10 筆，
同一 provider instance 的請求起始間隔至少一秒。選取結果後只更新本機 SQLite
中的標題、歌手及單一 `musicbrainz:<MBID>` 標籤；媒體位元、檔名及內容雜湊不變。
查詢不在 GUI thread 執行，不建立背景輪詢；停止等待後不套用晚到結果，已送出
的單一請求由 15 秒 timeout 收束。
39.0.113 修正發行建置繼承外部原生工具 PATH 的問題。PyInstaller 現在只使用
Windows、目前 Python 與 venv 的受控搜尋路徑，spec 在 Analysis 前再次套用該值，
避免受管理程序宿主重新注入 Poppler／libheif 路徑。copied-folder smoke 新增
`--ui-runtime-check`，實際載入 QtCore、QtWidgets 與 offscreen platform plugin；
因此只通過 version、verify-only、headless 的 EXE 不再能進入可散布候選。
39.0.114 新增可由頁尾或 `Ctrl+I` 開啟、可搜尋且不改變設定的功能簡介。
39.0.115 新增只讀取使用者所選本機 RSS 2.0／Atom 檔案的 Podcast / RSS 匯入
MOD；它不訂閱或連線 Feed 內資源，只有符合 Direct HTTP 既有規則的附件可由
使用者明確送入下載工作區，仍不自動分析或排隊。
39.0.116 新增具 HTTPS 實例範圍的 PeerTube 官方 API 搜尋 MOD。它只搜尋指定
實例的本機公開影片，不進入聚合搜尋；DNS、TLS、重新導向、回應大小及游標均有
明確邊界，結果只供系統瀏覽器開啟，不解析串流或加入下載佇列。
39.0.117 將完整外部工具健康檢查延後到使用者開啟「環境」視窗時才執行；乾淨
主視窗先顯示尚未檢查，不再於建立 UI 時依序開啟 FFmpeg、ffprobe 與 runtime
版本探測子程序。發行資料夾內已通過固定 SHA-256 身分檢查的 Deno 由 Bootstrap
直接採用，不再重複執行版本命令；未固定身分的 PATH runtime 仍維持最低版本閘。
39.0.118 將使用者觸發的完整環境檢查移到單一背景工作；視窗立即顯示檢查中，
使用者關閉視窗只停止等待晚到結果，不會讓主介面卡在外部版本命令。依賴快取與
外部探測改用分離鎖，檢查進行中的 `peek()` 保持立即返回。品質稽核另以 AST
掃描 `main.py`、`desktop.py`、`core/`、`trusted_ui/`、`plugin_host/` 與 `mod/`
正式執行期來源；新增或修改 `subprocess.run/Popen` 若無法證明帶有 Windows
`CREATE_NO_WINDOW` 政策便失敗關閉，避免其他功能再次引入空白命令視窗。
39.0.119 完成後續工作中心改善：聚合搜尋在首次只有部分來源失敗時保留成功結果，
並可只重試失敗來源；下載清單與系統匣可依狀態檢視、暫停／繼續佇列並批次重試
provider 明確標示可恢復的失敗。格式工廠的 H.264 GPU 工作失敗後保持失敗與原始
診斷，使用者確認才會以同來源、輸出與參數建立 CPU 重試，絕不靜默改寫策略。
媒體庫增加背景手動重新掃描，未變更的已索引檔不再重寫 SQLite。外部 MOD 頁只讀
既有失敗次數與隔離原因，顯示健康摘要、需注意與已隔離篩選，沒有探測、輪詢或
自動重啟。Podcast / RSS 對已載入的本機 Feed 提供 M3U／CSV 匯出與逐字稿／章節
宣告資訊預覽；匯出 CSV 會中和試算表公式字首，所有 URL 保持未讀取狀態。
Provider 取消時先以 Windows 原生樹狀終止收束仍在執行的 host 與子程序，Job Object
的 kill-on-close 仍是後備；兩者均套用隱藏視窗政策。
完整 Repository runner 為 `1792 passed, 9 skipped`；九項 skip 均是目前 Windows
帳號缺少建立測試用 link 權限，其中兩項覆蓋拖放與試轉暫存目錄的 link 拒絕
路徑。Quality audit 通過 Ruff `392` 個 Python 檔與文字污染掃描 `503` 個受控
檔案；版本文件及 diff 格式檢查通過。
無網路 Provider Host 以 2 次 warmup、7 次樣本重測，elapsed p50／p95 為
`351.495 / 377.174 ms`，Private Bytes p50／p95 為
`18,509,824 / 18,952,192`。這只能量到固定啟動成本，尚無真實搜尋 workload
證明常駐 Host 的效益足以抵銷額外程序、記憶體與狀態風險，因此沒有導入。
背景待機基準也以每樣本 5 秒、2 次 warmup、7 次記錄比較前景與背景。乾淨 lazy
的活動重複 timer 為 `1 / 0`，全部 11 個延遲工作區物化後為 `6 / 0`，OS thread
p50 為 `9 / 8`。CPU 樣本低於目前 Windows 取樣解析度，記憶體差異只有數十至
百 KiB 且背景沒有穩定較低；因此只確認喚醒來源已停止，不宣稱 CPU 或記憶體
降幅，也不以卸載頁面犧牲輸入狀態與返回速度。
Direct HTTP 另完成不開網路 socket 的真實 provider 寫檔基準。32 MiB 合成內容
比較 256 KiB／1 MiB／4 MiB 分塊時，elapsed p50 為
`35.116 / 44.308 / 43.977 ms`，tracemalloc peak p50 為
`660,427 / 2,232,539 / 8,523,819 bytes`；256 KiB 同時把每樣本進度事件由
32 增為 128。因基準未包含真實 HTTPS、pipe flush 與 UI 消費成本，不能外推
端到端下載速度；目前保留 1 MiB 折衷，拒絕沒有速度收益且記憶體較高的 4 MiB。
另以 [W3C HTML5 media-events](https://www.w3.org/2010/05/video/mediaevents)
頁面使用的固定 Sintel HTTPS URL 執行一次真實
Direct HTTP smoke。provider 在收緊至 8 MiB 上限後成功取得 `4,372,373` bytes、
產生 5 次進度事件並記錄 SHA-256，owned 暫存下載已移除。單次觀察為
`2562.414 ms / 1.627 MiB/s`，只證明 TLS、驗證、寫檔、進度、雜湊與清理可用；
公共主機未重複取樣，不能把單點吞吐量視為效能基線或下載加速證據。
固定 200 筆搜尋結果的 offscreen 基準也已完成。填表期間停止 repaint 並延後
`ResizeToContents` 寬度掃描、完成後恢復原模式，使結果建立 elapsed p50／p95
由 `407.624 / 413.729 ms` 變為 `23.414 / 26.490 ms`，CPU time 由
`406.25 / 421.875 ms` 變為 `31.25 / 31.25 ms`。頂端／底端縮圖請求維持
`8 / 16`，沒有網路連線；Private Bytes 差異不足以宣稱記憶體改善。一次性預設
列高候選使 p50 退步至 `484.693 ms`，已撤回。
YouTube／Bilibili 專用結果表另以相同 200 筆離線 workload 實測；原路徑
p50／p95 分別為 `23.956 / 27.657 ms` 與 `31.106 / 34.020 ms`。照搬上述批次
layout 候選後 p95 退為 `34.463 / 37.354 ms`，故已撤回；撤回確認為
`23.855 / 24.438 ms` 與 `30.305 / 33.399 ms`，縮圖請求均維持 `9 / 18`。
基準 schema 現為 4，後續不應把通用搜尋的收益未經量測外推到專用工作區。
39.0.114～39.0.119 的來源修改尚未 build、stage、commit、push 或發布。39.0.119
最新完整 Repository runner 為 `1839 passed, 9 skipped`；九項 skip 均是目前
Windows 帳號缺少建立測試用 link 權限。Quality audit 通過 Ruff `402` 個
Python 檔、文字污染掃描 `516` 個受控檔案，以及 `0` 個子程序視窗政策問題。

`39.0.106` 讓配置比較器
在 build 前先拒絕 Repository 內、既存或 link-like 證據路徑，並以 Windows
kill-on-close Job Object 收容每個量測程序的完整程序樹；程序先 suspended、
成功加入 Job 後才恢復，逾時或初始化失敗也會關閉 Job 並 reap。`39.0.105` 新增隔離的
onefile／onedir PyInstaller 配置比較器；正式發行 build 仍強制 onefile。隔離實驗
已由乾淨 commit 使用 2 次 warmup、7 次樣本完成：onedir 的 version、verify-only
與 Provider Host p50 分別為 `341.116`、`523.244`、`421.681 ms`，onefile 為
`2238.396`、`2355.176`、`2257.093 ms`；兩者 SHA-256、複製資料夾 smoke 與
89 個釘選內建 MOD 的首次物化均通過。代價是 artifact 從 1 個約 93 MiB 檔案變成
445 個、約 211 MiB。onefile 資源數據目前只可靠涵蓋 launcher 父程序，因此尚不以
CPU／記憶體結果決定發行 layout；原型已清除，也沒有改動 Testing／Stable。
`39.0.104` 新增預設關閉的
YouTube 大型播放清單快速模式；只在使用者明確選取時逐筆解析前 500 項，並在
UI 說明結果不是完整總數且不套用隨機／反向排序。未選取時與非 YouTube provider
維持原 payload。`39.0.103` 新增由可信核心
驗證的 YouTube 省資源、平衡、高速與自動下載效能設定；核心會依全域工作數
配置有界片段併發並覆寫外來同名選項，所有已建立的下載頁同步顯示設定。
有未結束工作時不允許改變 profile 或同時工作數，避免新舊配額重疊。
`39.0.102` 讓 MEGA、
Direct HTTP 與 Gopeed 工作表以資料簽章跳過相同快照，變動時在批次期間
暫停中間 repaint；逐 cell 重用候選因基準較慢而撤回。`39.0.101` 將 YouTube、
Bilibili、網站搜尋與播放清單的縮圖改由主視窗層級的單一有界服務共用，
只請求目前可見列與前後緩衝；離開頁面取消該頁請求，返回後再補載。
`39.0.100` 將非目前核心工作區與已啟用的選用工作區改為第一次開啟才匯入
模組、建立介面，建立後保留使用者狀態。`39.0.99` 合併高頻的下載 RUNNING 進度通知，同一工作
每 100 ms 最多將最新快照送往 UI 一次，
但狀態轉換及終態仍立即送達；Qt Multimedia 播放元件也改為第一次
有效預覽才建立，停止或關閉後釋放。`39.0.98` 將 version、verify、Provider 與
Plugin 非圖形角色分流到重型 Bootstrap／可信 UI 匯入前，並新增隔離
AppData、禁止網路與可見 UI 的啟動資源基準。`39.0.97` 新增低資源
背景待機、右下角關閉行為選擇、系統匣還原／完整結束，以及預設關閉的 Windows
登入後背景啟動。待機只暫停不可見 UI 的重複輪詢；下載、轉換、轉錄、排程與
剪貼簿規則維持原服務生命週期。`39.0.96` 移除第三方 MOD 驗證警告中失效的
硬編碼 `core 3.0`，並讓 GitHub Quality workflow 統一使用具 60 秒測試逾時、
受限收集範圍與外部隔離暫存目錄的 Repository runner。`39.0.95`
移除啟動時自動開啟的首次 MOD 設定與依賴環境模態視窗，改由主畫面的 MOD 管理
與環境狀態按鈕明確開啟；啟動不會改變 MOD 狀態或安裝工具。`39.0.94` 保留 39.0.93
H.265 Main10 NVENC preset 經本機品質比較較佳的 p7／HQ 參數，並在原子提交前
驗證 Matroska、HEVC Main 10、10-bit、Opus、來源解析度與固定影格率；不符合
契約的 `.part` 會被刪除，來源與輸出 Opus 封包 SHA-256 也必須相同。執行前
仍必須偵測 `hevc_nvenc`，且第一條來源音訊
必須是 Opus；沒有 CPU 或音訊轉碼 fallback。Testing `1.2.3` 已保留給此來源的
本機未簽署 `SAFE_MODE` 候選；不 push、不簽署、不發布，Testing `1.2.2` 及更早
產物維持不可變。`39.0.13` 修正搜尋聚合
與歷史污染；`39.0.14` 補齊 Search v2 provider 已宣告但通用 UI 無法選擇的
`playlist`／`live` 內容類型；`39.0.15` 改善 YouTube 相似音樂種子查詢精度；
`39.0.16` 防止搜尋詞組別名誤改較長單字；`39.0.17` 保證修正後查詢不突破
Search v2 的 200 字元上限；`39.0.18` 在通用 UI 提供所有已啟用來源的有界聚合搜尋；
`39.0.19` 讓已顯示結果能即時套用片長與語言篩選，不重新送出 provider 請求；
`39.0.20` 讓通用 Search v2 下一頁安全追加，且失敗不再清空已載入結果；
`39.0.21` 統一 YouTube 官方網域別名的搜尋結果身分，避免跨頁或多來源重複列出；
`39.0.22` 修正搜尋 MOD 停用後仍保留舊游標及假啟用控制項的狀態落差；
`39.0.23` 修正相似音樂與替代搜尋未同步檢查其綁定搜尋來源的依賴狀態；
`39.0.24` 讓多來源聚合搜尋可安全追加仍有下一頁的來源；`39.0.25` 在工作區
達到 200 筆有界容量時終止分頁並停用下一頁操作；`39.0.26` 修正所選搜尋
來源消失後可能退回停用來源的狀態錯誤；`39.0.27` 防止搜尋進行中切換來源
狀態後，舊 worker 的晚到結果覆蓋新狀態；`39.0.28` 讓 MOD 管理介面送出的
外部狀態事件也清除舊搜尋結果與分頁游標；`39.0.29` 修正聚合搜尋在各來源
頁面總量大於顯示上限時，游標跳過尚未合併結果的分頁資料遺失；`39.0.30`
防止帶 userinfo 或顯式連接埠的非 canonical URL 佔用官方 YouTube 去重身分；
`39.0.31` 在 Discovery 結果契約統一驗證有界純 HTTPS URL，讓畸形外部結果
被隔離為無效回應，不再中斷其他正常搜尋來源；`39.0.32` 讓共用 Search registry
在派送前拒絕重複或無效的 provider ID，避免配額失真與重複外部請求；`39.0.33`
以有界方式正規化 provider iterable，拒絕字串／不可迭代輸入，且最多讀取
17 項便判定超過 16 個來源上限，避免無限 generator 或過長清單造成無界耗用；
`39.0.34` 讓公開 Discovery service 在來源查找前共用同一正規化入口，不再先
完整展開輸入或把拆解後的字元誤報為不存在的來源；`39.0.35` 統一搜尋結果
上限的型別驗證，拒絕布林、字串與小數被靜默轉成整數後派送。
`39.0.36` 讓 federated provider cursor mapping 在任何搜尋 MOD 派送前有界正規化，
不再完整物化過長 Mapping，亦不接受契約外容器或無效游標值；`39.0.37` 在服務與
registry 入口先驗證 Search v2 查詢欄位，讓無來源與有來源路徑維持同一錯誤契約；
`39.0.38` 拒絕非字串的外層分頁游標，避免假值觸發重複首分頁請求；`39.0.39`
讓搜尋 capability 身分驗證在任何 registry mutation 前完成，失敗註冊不再污染狀態；
`39.0.40` 統一正規化查詢與 provider 回傳的標題／作者，使 Unicode 相容字元與
組合形式能使用相同的本機排序規則；`39.0.41` 限制偏好建議的歷史事件消耗，
並防止 selection 事件出現在「最近搜尋」；`39.0.42` 統一歷史與偏好建議的
Unicode NFKC 去重身分；`39.0.43` 讓精確的作者與標題跨欄位查詢獲得明確排序
優先級；`39.0.44` 防止 selection.query 被偏好建議誤當成主動搜尋詞；`39.0.45`
讓常見作者／標題分隔符使用同一個精確跨欄位規則；`39.0.46` 讓標點包圍的
已知錯字仍能依完整詞邊界修正，並保留使用者原本的標點與空白；`39.0.47`
確保精確跨欄位結果不會被標題片語加作者關鍵字的較弱候選超越；`39.0.48`
統一語言篩選與搜尋排序的 Unicode 正規化規則；`39.0.49` 防止拉丁字搜尋片語
誤命中較長單字內部，同時保留無空格文字系統的子字串搜尋；`39.0.50` 讓整個
標題完全相等的結果優先於只包含查詢片語的延伸標題；`39.0.51` 讓作者完全相等
的作品優先於只在標題提及作者名稱的內容；`39.0.52` 分別套用中英混合片語的
首尾文字邊界，避免其中的拉丁詞退回任意子字串匹配；`39.0.53` 合併偏好作者的
Unicode／大小寫等價計數，讓搜尋建議與相似音樂偏好加權使用同一作者身分；
`39.0.54` 統一相似音樂 token 與種子查詢的 Unicode 作者身分，避免等價作者被
當成不同作者並占用有限查詢槽位；`39.0.55` 新增拉丁重音折疊的次級排序，
無重音輸入可找到重音標題／作者，但不會超越原始重音完全相等結果；`39.0.56`
統一相似音樂候選的語言與分類 Unicode／大小寫身分，避免等價 metadata 失分；
`39.0.57` 在作者 metadata 缺失時先保留精確曲名查詢，再加入 related fallback；
`39.0.58` 讓無空格作者／曲名分隔符也使用精確跨欄位排序；`39.0.59` 合併偏好
作者中的前後與重複空白，避免同一作者被拆分計數；`39.0.60` 以 Unicode／
大小寫等價身分去除相似音樂計畫中的重複查詢，保留有限槽位給備援訊號；
`39.0.61` 讓拉丁音樂訊號遵守完整詞界，避免 `mix` 誤命中一般單字。
`39.0.62` 補齊常見音樂複數與 remix 詞形，在嚴格詞界下保留合法召回。
`39.0.63` 在 History 偏好契約拒絕 bool-as-int，隔離畸形外部偏好資料。
`39.0.64` 統一拉丁重音搜尋身分，避免等價作者拆分偏好計數、重複列入建議
或占用相似音樂計畫的有界查詢槽。
`39.0.65` 讓相似候選的標題與作者 token 使用同一拉丁重音身分，補回等價候選
原本遺失的 title／artist 相關性分數。
`39.0.66` 修正 39.0.65 將所有 token 限為 200 字元的回歸，長標題尾端關鍵字
重新納入相似度計算。
`39.0.67` 補齊 soundtrack／OST／karaoke 音樂詞形，並保留拉丁完整詞界以防
一般單字誤分類。
`39.0.68` 讓 music scope 的提示附加遵守 Search v2 既有 200 字元上限；只有
194 字元以下且補上 ` music` 後仍合法的查詢才會附加，較長查詢保持原樣。
`39.0.69` 將 U+2018／U+2019 智慧撇號納入本機搜尋身分，讓標題排序、歷史建議
與相似音樂偏好使用同一作者身分，同時保留畫面及 provider 查詢的原始文字。
`39.0.70` 將 U+2010～U+2015 排版連字號／破折號折疊為本機 ASCII 連字號身分，
改善同名排序並避免歷史建議及相似查詢槽重複，仍保留所有顯示與查詢原文。
`39.0.71` 使用 yt-dlp 既有的 channel／uploader metadata，將嚴格以破折號加
`Topic` 結尾的 YouTube 自動音樂頻道辨識為 music；一般 Topic 文字不受影響。
`39.0.72` 將連字號／破折號兩側空白納入同一個本機搜尋身分，避免來源格式差異
影響精確排序、歷史建議去重與相似音樂的有限查詢槽；顯示與查詢原文不改寫。
`39.0.73` 將 U+201C／U+201D 智慧雙引號納入本機搜尋身分，改善同名排序、歷史
建議去重與相似音樂的有限查詢槽；顯示、歷史代表值與 provider 查詢原文不改寫。
`39.0.74` 讓相似音樂的標題與作者 token 將底線視為詞界，與共用搜尋排序一致，
補回使用底線分隔單字的 provider 標題原本遺失的本機相關性分數。
`39.0.75` 從本機比較身分忽略 U+FE0E／U+FE0F 顯示選擇符，讓文字與 Emoji
呈現變體維持同一搜尋身分；原始顯示、歷史代表值與 provider 查詢不改寫。
`39.0.76` 將已知 phrase alias 內的 ASCII 連字號擴充為 U+2010～U+2015
排版變體，讓複製的 `lo‑fi`／`lo–fi` 也使用既有 `lofi` 修正，且保持完整詞界。
`39.0.77` 將 U+2212 Unicode 負號納入同一個本機連字號身分、`lo-fi` 別名與
嚴格 YouTube `Artist - Topic` 後綴，補齊複製文字在排序、建議及相似搜尋的落差。
`39.0.78` 將共用查詢準備流程接入 Bilibili 專用搜尋工作區，讓已知別名與
拼字修正和通用／YouTube 入口一致；官方 Bilibili 網址仍在修正前直接辨識。
`39.0.79` 讓 Bilibili 專用結果使用共用本機相關性排序，完全同名作品能優先
於延伸標題，同分結果仍維持 provider 原順序且不增加外部請求。
`39.0.80` 讓 YouTube／Bilibili 專用工作區在達到共用 200 筆結果上限時終止
分頁並顯示上限狀態，不再保留只能產生空合併的下一頁游標。
`39.0.81` 讓有明確雙引號界線的 `"標題" by 作者` 查詢取得作者／標題跨欄位
精確排序；一般未加引號的 `by` 保持標題文字語意，不新增模糊拆分。
`39.0.82` 讓整個查詢以成對雙引號包住時，未帶引號的同名正式標題仍取得完整
相等順位；未閉合引號不會被剝除，provider 查詢原文也不改寫。
`39.0.83` 讓完整引號曲名搭配作者的正向／反向語法使用既有有限分隔符白名單
取得跨欄位精確排序；部分引號曲名不會被誤升為完整匹配。
`39.0.84` 將平衡引號候選整理為標題／作者共用欄位規則，讓完整引號作者取得
作者完全相等順位；未閉合引號與 provider 原查詢保持不變。
`39.0.85` 將完整引號作者加入既有跨欄位有限候選，讓引號作者搭配完整曲名
取得精確順位；部分引號作者不會被誤升為完整匹配。
`39.0.86` 將東亞成對書名／引號標記納入共用本機搜尋身分，並同步隔離的相似
音樂 MOD；錯配標記維持原文，不會被誤剝除。
`39.0.87` 補齊斜線、日文中點與單側空白的作者／標題完整分隔符，並移除已被
正規化層吸收的重複破折號候選。
`39.0.88` 將同一批有限分隔符的兩側空白納入共用本機搜尋身分，讓歷史建議與
相似音樂查詢去重和精確排序一致；分隔符仍保留，沒有分隔符的文字維持不同。
`39.0.89` 讓既有 `lo-fi → lofi` 查詢別名接受連字號／排版破折號兩側的有限
空白形式；較長單字的完整詞界與 200 字元查詢上限維持不變。
已封存的 Testing `1.2.0` 仍以 Development `39.0.11` 為來源；公開的
[Testing `1.2.1`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.1)
仍由 Development `39.0.12` 建置且保持不可變。Testing `1.2.2` 已獲授權由
Development `39.0.39` 的乾淨 source freeze 建置、建立新目錄與 prerelease；
它維持未簽署 Testing 身分，不是 Stable。下一次 Development 更新已有
[資源與 MOD 效能計畫](performance-mod-optimization-plan.md)，但版本、實作、build、
Testing／Stable、push 與發布均尚未指派或授權。Development 40.0 仍為
`NO RELEASE`，Repository 也沒有可發布 Stable 候選。

## 已完成範圍

- 核心、可信 UI、下載佇列、媒體庫、版本與 MOD 生命週期已有非 UI 回歸。
- YouTube、Bilibili、MEGA、Direct HTTP 與 generic Beta 的網站權限分離。
- 官方媒體主機採 exact-host、窄路徑與 provider/site-matrix 一致性檢查。
- 外部 MOD 提供 schema v2、Ed25519 發布者信任、依賴圖、交易復原、受控程序
  與宣告式 UI。
- 格式工廠、localhost-only Gopeed Bridge、選用 Speech to Text 與 Automation
  已納入內建 MOD 管理。
- 可信桌面使用 channel-neutral `MediaManager v1.0` 產品名稱；實際核心與發布
  metadata 仍維持三軌分離。
- Development 39.0.12 的 YouTube 工作區可由單一選取結果啟動相似音樂搜尋；
  候選只使用公開搜尋與既有本機排序，不使用 Cookie、私人推薦或觀看紀錄。
- Development 39.0.13 保留媒體 ID 原始大小寫，避免聚合與跨頁合併漏掉不同
  結果；通用搜尋只在目前世代、初始頁且所有來源成功後寫入本機搜尋歷史。
- Development 39.0.14 的通用搜尋內容類型隨目前 provider capability 動態更新；
  切換來源會移除不支援的類型並優先安全回退至 `all`，不新增網路 fallback。
- Development 39.0.15 的相似音樂查詢優先組合所選結果的歌手與曲名，再保留
  歌手類型、偏好歌手或曲名 related 的有界備援；仍只使用公開 YouTube 搜尋。
- Development 39.0.16 將 `lo-fi`、`sound track`、`bg music` 等本機別名限制
  為完整詞組匹配，不再破壞 `flo-fi`、`sound tracker`、`bg musicology` 等較長單字。
- Development 39.0.17 逐次檢查本機詞組與拼字 correction 的結果長度；若修正
  會突破 200 字元契約便保留原查詢，避免 UI、歷史與 provider 實際查詢分歧。
- Development 39.0.18 將既有 federated search 接入通用 UI；至少兩個來源啟用
  且具有共同內容類型時才顯示聚合選項，結果保留來源與失敗隔離。
- Development 39.0.19 快取最近一次聯合搜尋的原始結果；片長或語言條件改變時
  只在本機重新篩選、排序與顯示；遠端搜尋條件變更、新搜尋、錯誤、相似或替代
  流程會清除舊快取。
- Development 39.0.20 將單一來源的下一頁合併至既有有界結果，沿用 canonical
  identity 去重並保留實際來源；載入更多失敗時保留結果與游標，允許安全重試。
- Development 39.0.21 在 canonical identity 層以 authoritative exact-host 清冊
  統一 YouTube 官方網域別名；第三方網站的相同 ID 與大小寫不同 ID 仍維持獨立。
- Development 39.0.22 在搜尋來源可用性改變時清除舊游標與聯合結果快取；搜尋
  與下一頁按鈕只有在目前單一來源已啟用，或聚合來源仍符合共同能力時才可用。
- Development 39.0.23 讓相似音樂與替代搜尋只有在 `youtube-search` 仍啟用時
  才可操作；服務層會在啟動規劃 MOD 前驗證綁定來源，避免無效子程序與晚期錯誤。
- Development 39.0.24 以有界 HMAC 聚合游標綁定原查詢、內容類型與來源順序；
  下一頁只呼叫仍有游標的來源，canonical 去重追加結果，暫時失敗則保留該來源
  的原游標供重試，已耗盡來源不會重新查詢第一頁。
- Development 39.0.25 在跨頁合併達工作區 200 筆上限時捨棄後續游標；可信 UI
  會停用「下一頁」並顯示已達容量，不再發出無法增加可見結果的重複請求。
- Development 39.0.26 在搜尋來源清單重建時以 provider ID 尋找第一個實際
  啟用來源；不再無條件優先停用的 YouTube，也不依受聚合項位移的位置索引。
- Development 39.0.27 在搜尋條件或 MOD 狀態變更時，若仍有搜尋進行中便遞增
  generation、清除 busy 與游標狀態；晚到回應會因世代不符而被可信 UI 忽略。
- Development 39.0.28 統一 MOD 管理事件與本頁 QAction 的搜尋失效流程；外部
  停用或啟用搜尋 provider 後不再保留可被重新啟用的舊結果快取與下一頁游標。
- Development 39.0.29 將聚合頁面上限公平分配給本次實際查詢來源，讓每個
  provider 的下一頁游標緊接已合併結果；超額回傳會被分類為無效回應，不再
  靜默截斷並前移游標。
- Development 39.0.30 以共用 exact-host 路由判斷 canonical YouTube 身分；
  userinfo、顯式連接埠、非 HTTPS 或不合法路徑不再與合法官方結果互相去重，
  避免外部 MOD 的非 canonical 結果先到後排擠官方項目。
- Development 39.0.31 將既有 Discovery 欄位規則集中到 `DiscoveryItemV1`
  建構邊界，拒絕無主機、畸形 IPv6、超範圍 port、URL credentials、空白控制
  字元與超過 4096 字元的結果 URL；壞來源被分類為無效回應，其他來源仍可顯示。
- Development 39.0.32 在 `SearchAdapterRegistry.search()` 自身驗證 provider 選擇
  必須是唯一、非空的字串；不再只依賴上層 `DiscoveryService`，直接使用 registry
  的呼叫端也不會讓同一 MOD 重複請求或以重複項稀釋每來源頁面配額。
- Development 39.0.33 將 provider iterable 的展開限制為來源上限加一項；字串不再
  被拆成單字元來源，不可迭代輸入統一回報穩定的 validation error，超長或無限
  generator 也不會在拒絕前被完整消耗。
- Development 39.0.34 將來源選擇正規化提升為 `SearchAdapterRegistry` 的共用
  入口，`DiscoveryService.federated_search()` 在可用性／啟用狀態查找前即採用
  同一個 16 項上限與錯誤契約，避免公開服務路徑繞過 39.0.33 的底層防護。
- Development 39.0.35 將搜尋結果上限正規化集中於共用 registry 邊界；公開
  Discovery service 在建立 Search v2 查詢前使用同一入口，非整數型別不再被
  `int()` 靜默截斷或轉換，既有整數 0→1、超過 50→50 行為保持相容。
- Development 39.0.36 將 federated cursor mapping 的展開限制為來源上限加一組；
  只接受 Mapping，並在派送前驗證唯一非空 provider ID 與 1～500 字元游標，
  避免超長輸入的無界物化及無效呼叫被誤列為 provider failure。
- Development 39.0.37 將 Search v2 查詢本身的正規化與型別驗證提升到共用契約；
  即使沒有註冊或啟用任何 provider，空白／非字串查詢、無效內容類型、布林頁面
  大小與非字串游標也會在路由前拒絕，不再靜默回傳空結果或污染 provider 健康狀態。
- Development 39.0.38 在外層簽署游標解碼前先驗證實際字串型別；`None`、布林、
  整數與空容器不再因為是假值而跳過解碼、重查第一頁及改寫來源健康計數。
- Development 39.0.39 在 Search provider 寫入下載 registry 與服務索引前，先建立
  並核對宣告 capability 的 provider ID；身分不符的外部 MOD 失敗後，同 ID 修正版
  可在同一服務實例重新註冊，不再被殘留的「already registered」狀態阻擋。
- Development 39.0.40 讓搜尋查詢、provider 標題與作者共用 Unicode NFKC、
  `casefold` 與空白收斂；全形拉丁字元與組合／分解重音形式能穩定參與
  本機排序，不改寫 provider 資料或增加網路請求。
- 39.0.40 的 regression-first 案例由 `2 failed, 5 passed` 修正為 `7 passed`；
  相關搜尋、版本與入口點測試為 `28 passed`，完整 repository runner 為
  `1469 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字污染
  `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與 Repository 外
  compileall 均通過。
- Development 39.0.41 將偏好搜尋建議改為邊讀取、邊去重、達上限即停止，
  避免為顯示 2～12 筆建議先完整消耗過長或未知長度的歷史 iterable；
  「最近搜尋」只接受 `search` 事件，selection 紀錄仍保留給偏好統計，但不再
  被誤列為使用者曾主動搜尋的詞。
- 39.0.41 的 regression-first 案例由 `2 failed, 7 passed` 修正為 `9 passed`；
  相關搜尋、歷史、版本與入口點套件為 `30 passed`，完整 repository runner 為
  `1470 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字污染
  `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、
  版本文件 `4` 與 Testing `1.2.1`／`1.2.2` 版本稽核均通過。
- Development 39.0.42 讓「最近搜尋」與偏好建議共用 NFKC 去重身分鍵；
  選單仍顯示最新或優先級最高的原始文字，但全形／半形拉丁字元、組合／預組
  重音形式不再重複佔用建議配額。
- 39.0.42 的 regression-first 案例由 `2 failed, 9 passed` 修正為建議與歷史
  `11 passed`；相關建議、歷史、版本與入口點套件為 `32 passed`，完整 repository
  runner 為 `1472 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與隔離
  `compileall` 均通過。
- Development 39.0.43 將精確的 `artist + title` 與 `title + artist` 組合列為
  75 分完整符合；只有兩個欄位皆非空且正規化後整串相等才套用，不擴大為模糊
  跨欄位匹配。Regression-first 案例由 `1 failed, 7 passed` 修正為 `8 passed`；
  搜尋排序、版本文件、版本通道與入口點針對性套件為 `29 passed`，完整 repository
  runner 為 `1473 passed, 7 skipped`。Quality audit、MOD 群組、網站矩陣、依賴鎖、
  版本文件、Testing `1.2.1`／`1.2.2` 版本稽核與隔離 `compileall` 均通過。
- Development 39.0.44 讓偏好建議從原始事件補位時只接受 `search`；selection
  仍由 History MOD 聚合成作者、語言、類型與分類偏好，不再直接把 selection.query
  顯示成搜尋建議。Regression-first 案例由 `1 failed, 4 passed` 修正為 `5 passed`；
  建議、歷史、版本文件、版本通道與入口點針對性套件為 `33 passed`，完整
  repository runner 為 `1474 passed, 7 skipped`。Quality audit、MOD 群組、網站
  矩陣、依賴鎖、版本文件、Testing `1.2.1`／`1.2.2` 版本稽核與隔離
  `compileall` 均通過。
- Development 39.0.45 以有限白名單辨識作者與標題之間的空白、`-`、`–`、`—`、
  `|`、`:` 與 `·`；兩欄仍須非空，且查詢必須精確等於其中一種正向或反向組合。
  Regression-first 案例由 `1 failed, 8 passed` 修正為 `9 passed`；搜尋排序、版本
  文件、版本通道與入口點針對性套件為 `30 passed`，完整 repository runner 為
  `1475 passed, 7 skipped`。Quality audit、MOD 群組、網站矩陣、依賴鎖、版本文件、
  Testing `1.2.1`／`1.2.2` 版本稽核與隔離 `compileall` 均通過。
- Development 39.0.46 將已知 token typo 改為不跨單字的大小寫不敏感詞邊界
  搜尋；`(OFFICAL), lyrcis!` 會修正為 `(official), lyrics!`，括號、逗號、驚嘆號、
  空白與其他原始文字不被重組。每次取代仍先檢查 Search v2 的 200 字元上限。
  Regression-first 案例修正前為 `1 failed, 9 passed`，修正後搜尋排序套件為
  `10 passed`；搜尋排序、版本文件、版本通道與入口點針對性套件為 `31 passed`，
  完整 repository runner 為 `1476 passed, 7 skipped`。Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本
  稽核與隔離 `compileall` 均通過。
- Development 39.0.47 將兩欄非空且查詢精確等於「作者＋標題」或反向組合的
  結果由 75 分提升為 100 分；匹配條件與有限分隔符白名單不變，只修正它可能被
  60 分標題片語再加 20 分作者關鍵字反向超車的分數階級錯誤。Regression-first
  案例修正前為 `1 failed, 10 passed`，修正後搜尋排序套件為 `11 passed`；搜尋
  排序、版本文件、版本通道與入口點針對性套件為 `32 passed`，完整 repository
  runner 為 `1477 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與隔離
  `compileall` 均通過。
- Development 39.0.48 讓語言篩選值與 provider 結果的 `language` 欄位共用
  NFKC、`casefold` 與空白收斂；全形 `ＪＡ` 可匹配 `ja`，分解 `Café` 可匹配
  預組 `café`。篩選仍採整欄相等，不擴大為子字串或模糊匹配。Regression-first
  案例修正前為 `2 failed, 11 passed`，修正後搜尋排序與篩選套件為 `13 passed`；
  搜尋排序、版本文件、版本通道與入口點針對性套件為 `34 passed`，完整 repository
  runner 為 `1479 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與隔離
  `compileall` 均通過。
- Development 39.0.49 讓拉丁字與其他具單字邊界的搜尋片語只在完整詞界命中；
  `art` 不再被 `cartoon` 誤列為標題完整符合。中日韓、泰文、寮文、高棉文與
  緬甸文仍保留無空格子字串匹配。Regression-first 案例修正前為 `1 failed`，
  修正後搜尋排序套件為 `15 passed`；搜尋排序、版本文件、版本通道與入口點
  針對性套件為 `36 passed`，完整 repository runner 為 `1481 passed, 7 skipped`。
  Quality audit 通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  `1.2.1`／`1.2.2` 版本稽核與隔離 `compileall` 均通過。
- Development 39.0.50 將正規化後完全等於查詢的標題列為 85 分及「標題完全
  相等」；一般標題片語維持 60 分，嚴格作者＋標題跨欄位結果維持 100 分。
  `Midnight Echo live cover` 不再僅因 provider 順序排在 `Midnight Echo` 前。
  Regression-first 案例修正前為 `1 failed`，修正後搜尋排序套件為 `16 passed`；
  搜尋排序、版本文件、版本通道與入口點針對性套件為 `37 passed`，完整 repository
  runner 為 `1482 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python
  檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與隔離
  `compileall` 均通過。
- Development 39.0.51 將正規化後完全等於查詢的作者列為 70 分及「作者完全
  相等」；標題只提及作者名稱維持 60 分，完整標題與嚴格跨欄位精確結果仍分別
  為 85 與 100 分。Regression-first 案例修正前為 `1 failed`，修正後搜尋排序
  套件為 `17 passed`；搜尋排序、版本文件、版本通道與入口點針對性套件為
  `38 passed`，完整 repository runner 為 `1483 passed, 7 skipped`。Quality audit
  通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、
  網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／
  `1.2.2` 版本稽核與隔離 `compileall` 均通過。
- Development 39.0.52 將搜尋片語首尾獨立判斷是否需要單字邊界；`art 音樂`
  的拉丁開頭仍要求左側詞界，中文結尾則不要求空白。純中文、日文及其他慣用
  無空格文字維持既有子字串召回。Regression-first 案例修正前為 `1 failed`，
  修正後搜尋排序套件為 `18 passed`；搜尋排序、版本文件、版本通道與入口點
  針對性套件為 `39 passed`，完整 repository runner 為
  `1484 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2` 版本稽核與隔離 `compileall`
  均通過。
- Development 39.0.53 將偏好作者的 NFKC／大小寫等價鍵有界合併，搜尋建議會
  依合併後總次數選擇代表作者，相似音樂也能對等價作者套用偏好加權。兩個
  Regression-first 案例修正前為 `2 failed`，修正後搜尋建議與相似音樂套件為
  `17 passed`；搜尋、相似音樂、版本文件、版本通道與入口點針對性套件為
  `38 passed`，完整 repository runner 為 `1486 passed, 7 skipped`。Quality audit
  通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、
  網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing `1.2.1`／`1.2.2`
  版本稽核均通過。
- Development 39.0.54 將相似音樂的標題／作者 token 與偏好作者比較共用
  NFKC＋casefold 身分；Unicode 等價作者可取得 artist overlap，且不再產生重複的
  偏好作者查詢。Regression-first 案例修正前為 `1 failed`，修正後相似音樂套件
  為 `12 passed`；相似音樂、版本同步與內建雜湊針對性組合為
  `51 passed, 1 skipped`，完整 repository runner 為 `1487 passed, 7 skipped`。
  Quality audit 通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案。
- Development 39.0.55 以原始 Unicode 比對與只折疊拉丁重音的次級比對建立
  兩層排序；`cafe` 可將精確的 `Café` 排在 `Cafe live cover` 前，但 `café` 查詢
  仍優先原始重音完全相等結果。Regression-first 案例修正前為 `1 failed`，修正後
  搜尋排序套件為 `20 passed`；搜尋排序與版本同步針對性套件為 `41 passed`，
  完整 repository runner 為 `1489 passed, 7 skipped`。Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染 `474` 個受控檔案。
- Development 39.0.56 將相似音樂候選的語言與分類比較改用有界的
  NFKC＋casefold 身分；不同 provider 的全形／半形或大小寫等價 metadata 可取得
  相同的 10／15 分。Regression-first 案例修正前為 `1 failed`；相似音樂、內建
  完整性與 YouTube MOD 矩陣針對性套件為 `25 passed, 1 skipped`；完整 repository
  runner 為 `1490 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔
  與文字污染 `474` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、Testing 版本稽核與隔離 `compileall` 均通過。
- Development 39.0.57 修正缺少作者 metadata 的相似音樂種子只產生
  `title related`、未先搜尋精確曲名的缺口；現在以精確曲名為第一個查詢，並保留
  related fallback 與最多 3 個查詢的既有界線。Regression-first 案例修正前為
  `1 failed`；相似音樂、內建完整性與 YouTube MOD 矩陣針對性套件為
  `26 passed, 1 skipped`；完整 repository runner 為 `1491 passed, 7 skipped`。
  Quality audit 通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD
  群組、網站矩陣、依賴鎖、版本文件、Testing 版本稽核與隔離 `compileall` 均通過。
- Development 39.0.58 擴充作者／曲名精確跨欄位身分，接受連字號、短／長破折號、
  直線、冒號與間隔點前後沒有空白的常見輸入；分離欄位的正式結果固定取得 100 分。
  Regression-first 案例修正前為 `1 failed`；搜尋排序套件為 `21 passed`，完整
  repository runner 為 `1492 passed, 7 skipped`。Quality audit 通過 Ruff `366`
  個 Python 檔與文字污染 `474` 個受控檔案；MOD、網站、依賴、版本、Testing
  版本稽核與隔離 `compileall` 均通過。
- Development 39.0.59 讓搜尋建議的偏好身分在 NFKC＋casefold 前先折疊空白；
  `Aimer` 與前後／重複空白等價鍵會合併計數，不再錯選計數較低的其他作者。
  Regression-first 案例修正前為 `1 failed`；搜尋建議與歷史套件為 `14 passed`，
  完整 repository runner 為 `1493 passed, 7 skipped`。Quality audit 通過 Ruff
  `366` 個 Python 檔與文字污染 `474` 個受控檔案；MOD、網站、依賴、版本、
  Testing 版本稽核與隔離 `compileall` 均通過。
- Development 39.0.60 讓 YouTube 相似音樂查詢計畫使用 NFKC＋casefold 身分
  去重；全形分類產生的等價查詢不再重複占用三個查詢槽位，語言＋分類備援
  查詢可正常保留。Regression-first 案例修正前為 `1 failed`；相似搜尋、內建
  完整性與 YouTube MOD 矩陣為 `27 passed, 1 skipped`，完整 repository runner
  為 `1494 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染 `474` 個受控檔案；MOD、網站、依賴、版本、Testing 版本與隔離
  `compileall` 均通過。
- Development 39.0.61 讓 YouTube 搜尋 MOD 的拉丁音樂訊號使用完整詞界，
  `mixed media tutorial` 與 `concrete mixing tutorial` 不再因內含 `mix` 而漏加
  音樂限定詞或被分類為音樂；無空格 CJK 訊號維持既有子字串行為。
  Regression-first 案例修正前為 `1 failed`；YouTube scope、內建完整性與 MOD
  矩陣為 `16 passed, 1 skipped`，完整 repository runner 為
  `1495 passed, 7 skipped`。Quality audit 通過 Ruff `366` 個 Python 檔與文字
  污染 `474` 個受控檔案；MOD、網站、依賴、版本、Testing 版本與隔離
  `compileall` 均通過。
- Development 39.0.62 顯式補齊 `remix`／`remixes`、`songs`、`albums`、
  `playlists` 與 `mixes`；合法音樂詞形不再因 39.0.61 的嚴格詞界而漏加分類，
  `mixed`／`mixing` 誤判防護仍保留。Regression-first 五種詞形修正前為
  `5 failed`；YouTube scope、內建完整性與 MOD 矩陣為
  `21 passed, 1 skipped`，完整 repository runner 為 `1500 passed, 7 skipped`。
  Quality audit 通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案；
  MOD、網站、依賴、版本、Testing 版本與隔離 `compileall` 均通過。
- Development 39.0.63 在 `HistoryPreferencesV1.from_dict()` 同時拒絕布林總數
  與布林 counter；外部 History MOD 的畸形資料不再進入搜尋建議或相似音樂
  偏好加權。Regression-first 修正前為 `2 failed`；History、搜尋建議與相似音樂
  套件為 `31 passed`，完整 repository runner 為 `1502 passed, 7 skipped`。
  Quality audit 通過 Ruff `366` 個 Python 檔與文字污染 `474` 個受控檔案；
  MOD、網站、依賴、版本、Testing 版本與隔離 `compileall` 均通過。
- Development 39.0.64 將搜尋排序既有的拉丁重音折疊抽成共用文字身分，並套用
  至最近搜尋、偏好建議與 `youtube-similar` 計畫；`Beyoncé`／`Beyonce`
  等價作者會合併計數、去重歷史建議，也不再排擠精確曲名的 related fallback。
  Regression-first 三個案例修正前為 `3 failed`；定向搜尋、History、相似 MOD、
  內建雜湊與版本套件為 `85 passed`，完整 repository runner 為
  `1505 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD、網站、依賴、版本、Testing 版本與隔離
  `compileall` 均通過。
- Development 39.0.65 讓 `youtube-similar` 的標題／作者 token 沿用 39.0.64
  的拉丁重音折疊；`Café`／`Cafe` 與 `Beyoncé`／`Beyonce` 候選不再只靠
  語言、分類取得最低相關性。Regression-first 兩個案例修正前為 `2 failed`；
  定向相似、搜尋身分、內建雜湊與版本套件為 `78 passed`，完整 repository
  runner 為 `1507 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python
  檔與文字污染 `475` 個受控檔案；MOD、網站、依賴、版本、Testing 版本與隔離
  `compileall` 均通過。
- Development 39.0.66 讓相似 token 使用 DiscoveryItem 既有欄位界線：標題
  300 字元、作者 200 字元；39.0.65 不再把合法長標題的尾端關鍵字截掉。
  Regression-first 257 字元標題案例修正前只得 `25` 分並形成 `1 failed`；
  定向相似、搜尋身分、內建雜湊與版本套件為 `79 passed`，完整 repository
  runner 為 `1508 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python
  檔與文字污染 `475` 個受控檔案；MOD、網站、依賴、版本、Testing 版本與隔離
  `compileall` 均通過。
- Development 39.0.67 讓 YouTube 搜尋 scope 辨識 `soundtrack`／`soundtracks`、
  `OST` 與 `karaoke`；明確音樂查詢不再重複附加 `music`，all scope 的相同
  metadata 也會歸為 music。`post`／`cost` 負例仍受完整詞界保護。
  Regression-first 四個新詞形修正前為 `4 failed`；定向 YouTube scope、內建
  雜湊、搜尋排序與版本套件為 `64 passed`，完整 repository runner 為
  `1512 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD、網站、依賴、版本、Testing 版本與隔離
  `compileall` 均通過。
- Development 39.0.68 修正顯式 music scope 對沒有音樂詞形的查詢一律附加
  ` music`，使 195–200 字元合法輸入超出 Search v2 上限的契約落差。194 字元
  查詢仍可補至剛好 200 字元；195 與 200 字元查詢保持使用者原文，不截斷。
  Regression-first 邊界案例修正前為 `1 failed`；YouTube scope 套件修正後為
  `14 passed`。定向 scope、內建雜湊、YouTube MOD 矩陣、搜尋排序與版本套件為
  `65 passed`，完整 repository runner 為 `1513 passed, 7 skipped`。Quality audit
  通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD、網站、依賴、
  版本、Testing 版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有
  `0` 個 `.pyc`。
- Development 39.0.69 統一直撇號與 U+2018／U+2019 智慧撇號的本機比較身分。
  真正同名但使用智慧撇號的標題不再被較長的 ASCII `live cover` 結果超越；
  歷史建議不再重複列出標點變體，相似音樂計畫也不再讓同一作者占用第三個
  有限查詢槽。Regression-first 三條案例修正前為 `3 failed`，修正後為
  `3 passed`；搜尋排序、建議、歷史與相似音樂相關套件為 `61 passed`，定向
  搜尋、歷史、相似、內建雜湊、YouTube MOD 矩陣與版本套件為 `91 passed`。
  完整 repository runner 為 `1516 passed, 7 skipped`。Quality audit 通過 Ruff
  `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD、網站、依賴、版本、
  Testing 版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有
  `0` 個 `.pyc`。
- Development 39.0.70 統一 ASCII `-` 與 U+2010～U+2015 排版連字號／破折號
  的本機比較身分。真正同名但使用 en dash 的標題不再被較長的 ASCII
  `live cover` 結果超越；歷史建議與相似音樂作者偏好也不再把破折號變體視為
  不同文字。Regression-first 三條案例修正前為 `3 failed`，修正後為
  `3 passed`。定向搜尋、歷史、相似、內建雜湊、YouTube MOD 矩陣與版本套件為
  `94 passed`，完整 repository runner 為 `1519 passed, 7 skipped`。Quality audit
  通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD、網站、依賴、
  版本、Testing 版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有
  `0` 個 `.pyc`。
- Development 39.0.71 補用 yt-dlp 平面搜尋結果已帶回的 channel／uploader
  metadata，嚴格辨識 `Artist - Topic` 與排版破折號變體。標題本身沒有 music、
  OST 等關鍵字的歌曲不再誤標為 video；`Topic World`、`off-topic` 與空白頻道
  仍維持 video。Regression-first 正例修正前為 `2 failed`，同檔正負案例修正後
  為 `19 passed`。定向套件為 `113 passed`，完整 repository runner 為
  `1524 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD、網站、依賴、版本、Testing 版本與 Repository 外
  隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。此變更不增加請求、
  Cookie、登入或下載權限。
- Development 39.0.72 將 `Artist-Title`、`Artist - Title` 與使用排版破折號的
  空格變體統一為相同的本機比較身分。修正前，同名結果會落後於較長的
  `live cover`、歷史建議產生兩筆且相似音樂浪費第三個查詢槽；regression-first
  三條案例修正前為 `3 failed`，修正後為 `3 passed`。顯示、歷史代表值與送往
  provider 的原始文字維持不變。定向套件為 `116 passed`，完整 repository runner
  為 `1527 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD、網站、依賴、版本、Testing 版本與 Repository 外
  隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.90 補齊格式工廠需求中的本機影片影像浮水印。新 preset
  只接受單一一般影片來源與單一 PNG／JPEG／WebP／BMP／TIFF 本機影像，固定
  右下位置、固定有界 filter graph，並以 H.264／AAC 寫入新檔；不允許網址、
  自訂 filter、連結檔或覆寫來源。文件、DVD 與 CD 不屬於此 FFmpeg 媒體工作區，
  不列為已支援。Regression-first 案例修正前為 `1 failed`；命令契約、offscreen
  UI 與本機 FFmpeg smoke 修正後為 `3 passed`；五個定向套件為
  `69 passed, 1 skipped`，完整 repository runner 為 `1567 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、兩個
  Testing 版本、Repository 外隔離 `compileall` 與 `git diff --check` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.91 將 yt-dlp flat-search 回傳的片長視為不可信 metadata；
  有限數值且介於 0～86400 秒才轉成整數，其餘 `NaN`、無限值、布林、負值與
  超界值都降為未知片長。Regression-first 案例修正前因 `int(NaN)` 為
  `1 failed`，修正後可讓整頁結果通過 `DiscoveryItemV1` 契約。七個定向套件為
  `127 passed`，完整 repository runner 為 `1568 passed, 7 skipped`。Quality
  audit 通過 Ruff `367` 個 Python 檔與文字污染 `476` 個受控檔案；MOD 群組
  `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、兩個 Testing
  版本、Repository 外隔離 `compileall` 與 `git diff --check` 均通過，`Version/`
  中有 `0` 個 `.pyc`。預設搜尋仍不需 API key；可選 YouTube Data API 外部 MOD
  的分離方案記錄於搜尋強化計畫。
- Development 39.0.92 將顯式 `music` scope 從一般 `ytsearch + music` 提示改為
  yt-dlp 已提供的 `music.youtube.com/search#songs` extractor；查詢使用標準 URL
  編碼、仍受既有 200 筆工作區與 `playlistend` 上限約束。相似音樂流程原本已
  以 `content_type="music"` 呼叫搜尋，因此會直接取得歌曲區段候選；`all` 與
  `video` scope 不變，也不新增 API key、Cookie、登入或未授權 fallback。
  Regression-first 路由案例修正前為 `1 failed`；YouTube scope／MOD matrix 修正後
  為 `29 passed`，七個呼叫鏈定向套件為 `119 passed`，完整 repository runner
  為 `1569 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與
  文字污染 `476` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、兩個 Testing 版本、Repository 外隔離
  `compileall` 與 `git diff --check` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.93 新增下載後本機 H.265 Main10 NVENC／Opus Passthru MKV
  preset。命令固定使用 `hevc_nvenc`、Main10／`p010le`、p7、HQ、VBR 300 kbps、
  full-resolution multipass、lookahead 與時空 AQ；不設定輸出 FPS 或尺寸，也不
  使用 `-vf`、`-af` 或 filter graph。來源第一條音訊不是 Opus 或缺少
  `hevc_nvenc` 時會在排入前拒絕，避免無聲轉碼或 CPU fallback。Regression-first
  四條案例修正前為 `4 failed`；相關套件修正後為 `76 passed, 2 skipped`，完整
  Repository runner 為 `1571 passed, 7 skipped`。Quality audit 通過 Ruff `367`
  個 Python 檔與文字污染 `476` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、兩個 Testing 版本、Repository 外
  隔離 `compileall` 與 `git diff --check` 均通過。本機短片實測確認 HEVC Main 10、
  Opus packet 雜湊不變，以及 1920x1080／24 FPS 來源保持同尺寸與影格率。
- Development 39.0.94 以相同 4 秒 1920x1080／24 FPS 樣本比較多組 NVENC
  選項；既有 p7／HQ 組合的 VMAF `62.479828`、SSIM `0.954483`，高於加入
  B-reference、UHQ、lookahead level 3 或改變 AQ strength 的候選，因此不更動
  編碼參數；另測的 300 kbps maxrate／600 kbps buffer 反而使同一樣本由
  `227806` 增為 `229185` bytes，VMAF 只增加 `0.044476`，因此也不採用。
  新增資料驅動的輸出契約，要求 Matroska、HEVC Main 10、10-bit、Opus、來源
  尺寸與 CFR 不變，且來源／輸出 Opus 壓縮封包 SHA-256 相同；欄位缺漏、規格
  或雜湊偏離都在原子提交前失敗並移除 `.part`。ffprobe 與封包雜湊子程序也
  接受相同取消事件；驗證中取消會終止子程序並清除 `.part`，不必等待最長
  300 秒雜湊 timeout。Regression-first 案例實作前為 `1 failed`；輸出契約
  定向案例為 `11 passed`，完整轉換服務為 `59 passed, 1 skipped`，完整
  Repository runner 為 `1592 passed, 7 skipped`。Quality audit 通過 Ruff
  `367` 個 Python 檔與
  文字污染 `476` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、兩個 Testing 版本、Repository 外隔離
  `compileall` 與 `git diff --check` 均通過，`Version/` 中有 `0` 個 `.pyc`。
  實機服務再次輸出 `227806` bytes 的 HEVC Main 10／`yuv420p10le`／Opus
  Matroska，並通過內建 Opus 封包 SHA-256 比對與 1920x1080／24 FPS 契約。
- Development 39.0.96 將 schema v1 executable MOD 的警告由固定 `core 3.0`
  改為呼叫端實際選用的核心版本，避免目前版本與測試指定版本被舊字串誤導。
  GitHub 的 Windows 完整套件及 Ubuntu symlink 安全套件都改由
  `tools.run_tests` 執行，沿用 runner 的 Repository `tests/` 邊界、每次獨立
  user-local 暫存目錄與完成後清理；runner 固定加入 `--timeout=60`。兩個新增
  regression-first 案例修正前為 `2 failed`；MOD、runner、workflow、入口與版本
  文件定向驗證修正後為 `37 passed, 1 skipped`，Windows 略過項目是目前權限
  無法建立目錄 symlink。完整 Repository runner 為 `1595 passed, 7 skipped`；
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `476` 個受控檔案，MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、兩個
  Testing 版本與隔離 `compileall` 也都通過。
- Development 39.0.102 將 MEGA 與 Direct HTTP 既有資料簽章／動態輪詢保留，
  套用變動快照期間暫停中間 repaint，選取列仍依 task ID 保留。Gopeed 的
  手動更新加入可見值 signature，相同 API 快照不動 UI；隱藏且無進行中工作的
  MEGA／Direct HTTP 以 10 秒低頻檢查，頁面關閉停止 timer。同一來源、無網路、
  不顯示 UI 的 200 列×50 次刷新以 2 warmup／7 samples 比較：整批重建與逐 cell
  重用的 workload p50 為 `443.808 / 497.525 ms`，p95 為
  `594.221 / 647.663 ms`；Private Bytes p50 為 `23,961,600 / 25,026,560`。
  重用雖將 item／progress 建立數從 `40,000 / 10,000` 降至 `800 / 200`，但沒有
  轉化成速度或記憶體優勢，因此依停止條件撤回，`QAbstractTableModel` 也未導入。
  證據位於 Repository 外的 `table-39.0.102-20260909.json`。定向回歸為
  `71 passed`，完整 Repository runner 為 `1627 passed, 7 skipped`；七項 skip
  均是目前 Windows 帳號缺少建立測試用 link 權限。此合成表格 workload
  不代表實際下載吞吐。
- Development 39.0.101 將先前各工作區各自持有的縮圖 network manager 與
  LRU cache 收斂為主視窗層級的單一可信服務；相同 URL 的同時請求會合併，
  回應仍受 HTTPS／CDN 白名單、1 MiB、1600 萬像素、8 秒 timeout、32 個
  pending 與 40 項快取上限保護。YouTube、Bilibili、網站搜尋及播放清單
  先建立文字列，只對 viewport 可見列加前後 2 列發出縮圖請求，捲動時才
  補載；離開分頁只取消該 client callback，其他頁與共用快取不受影響，返回
  後會恢復可見列載入。背景待機會取消全部 pending 並清空可重建快取。
  定向回歸為 `54 passed`，完整 Repository runner 為 `1624 passed, 7 skipped`；
  七項 skip 均是目前 Windows 帳號缺少建立測試用 link 權限。尚未完成固定大量結果工作負載的 OS 層 Before／After
  量測，因此只記錄預期降低重複連線、解碼與隱藏列記憶體壓力，不宣稱實測降幅。
- Development 39.0.100 將主視窗啟動改為只建立目前 YouTube 工作區。
  Bilibili、網站搜尋、本機媒體庫與已啟用的選用工作區只先建立輕量
  分頁 shell，首次開啟才匯入各自模組並物化 panel；再次切換保留同一物件與
  輸入。MOD 啟用／停用、直接下載 prefill 與關閉清理共用同一 manager，關閉
  期間不會因分頁變動反向建立工作區。乾淨啟動隔離回歸證明九個延遲
  工作區模組及 Qt Multimedia 均未匯入；選取 Bilibili 後只建立該頁並可重用。
  基準以同一來源、2 warmup、7 samples 比較 lazy 與物化全部 11 個可見工作區：
  elapsed p50 `1281.963 / 1605.220 ms`、private bytes `57,851,904 / 70,725,632`、
  Qt 子物件 `555 / 1,946`、active repeat timer `1 / 6`。這是同來源工作負載
  差異，不是舊版 Before／After；開啟所有頁面後固定成本仍會產生。證據儲存在
  Repository 外的 `workspace-39.0.100-20260908.json`。基準、manager 與主視窗
  定向回歸為 `14 passed`；完整 Repository runner 為 `1620 passed, 7 skipped`，
  七項 skip 均是目前 Windows 帳號缺少建立測試用 link 權限，來源樹的
  `.pyc`／`__pycache__` 仍為 `0`。
- Development 39.0.99 新增 thread-safe latest-wins 下載通知合併器：第一個
  RUNNING 狀態及後續狀態轉換立即送達，重複 RUNNING 進度只保留同一
  工作的最新快照，並由 GUI thread 的 100 ms single-shot coarse timer 合併送出。
  COMPLETED、FAILED 與 CANCELLED 不節流，送出前會捨棄過時進度；既有動態
  快照輪詢仍作為低頻一致性校正。音訊、影片、格式工廠切點與分割預覽不再
  於工作區建立時匯入或建立 Qt Multimedia player；只在通過世代、背景待機與
  檔案驗證後才建立，並在停止或關閉時清除 source、解除輸出、排程回收。
  隔離子程序回歸證明完整主視窗啟動後 `PySide6.QtMultimedia` 仍未匯入。
  修改前合併器 regression-first 在收集時出現 `1 error`；完成後相關 UI、預覽、
  下載、待機、分割與轉換套件為 `115 passed, 1 skipped`，skip 是 Windows 帳號
  無法建立測試用 symlink；完整 Repository runner 為 `1618 passed, 7 skipped`，
  七個 skip 均是目前 Windows 帳號缺少建立測試用 link 的權限。Quality audit 通過
  Ruff `374` 個 Python 檔與文字
  污染 `484` 個受控檔案。這些是結構與行為證據；未進行固定工作負載的
  OS 層 CPU／記憶體 Before／After 量測，不宣稱已取得百分比改善。
  完整測試首次復查發現 `plugin_host/__pycache__` 四個未追蹤 `.pyc`；根因是
  來源 Host 的 Python `-I` 會忽略 runner 設定的 `PYTHONDONTWRITEBYTECODE`。
  Provider 與 Plugin Host 命令現在本身加入 `-B`；兩個命令契約回歸加入後，
  重跑完整套件仍為上述結果，來源樹 `.pyc` 與 `__pycache__` 均為 `0`。
- Development 39.0.98 新增可重現的 Windows 啟動／Host 基準，使用獨立 AppData
  與暫存根目錄，禁止 socket 連線及可信圖形 shell 匯入，記錄 elapsed、CPU、
  private bytes、working set、peak working set 與 OS thread count；JSON 證據只
  能寫入 Repository 外。入口本身不再於模組匯入時載入 Bootstrap 或
  `trusted_ui.main_window`，version、verify、Provider 與 Plugin 先完成角色分流，
  一般 GUI 才延遲載入可信 UI。相同 Windows 測量方式以 2 次 warmup、7 次樣本
  比較：version elapsed p50 `243.229 → 87.643 ms`、private bytes
  `29,646,848 → 13,975,552`；provider host elapsed p50
  `246.544 → 142.293 ms`、private bytes `31,264,768 → 17,993,728`。
  verify-only 因保留完整 Bootstrap，elapsed p50 `257.699 → 268.335 ms`，未取得
  速度改善；private bytes `29,507,584 → 25,739,264`。定向入口與基準測試為
  `15 passed`；完整 Repository runner 為 `1612 passed, 7 skipped`，skip 均為
  既有 Windows link 權限限制。基準 probe 明確以 Repository `main.py` 作為應用
  根目錄，避免 verify-only 在 `tools/` 下建立 MOD 鏡像；測試 runner 也禁止 pytest
  子程序寫入 Python 位元碼快取。回復只需還原入口的 lazy import 與此基準工具，
  不遷移設定或改變 Provider／Plugin protocol。
- Development 39.0.97 新增背景閒置資源控制器：最小化或關閉至系統匣時暫停
  主視窗下仍在執行的非單次 UI 計時器、暫停播放預覽並釋放可重建的圖片快取，
  還原視窗時恢復原計時與播放狀態。Automation 剪貼簿改由 Qt 內容變更事件
  觸發；沒有啟用規則時 monitor 不再每 5 秒喚醒。非目前且閒置的狀態表由
  2.5 秒更新一次改為 10 秒，顯示資料未變時不重建 Automation 表格。下載、
  轉換、轉錄與排程的背景服務不由待機控制器關閉。
  右下角可選「縮到系統匣」或「完全結束」，系統匣選單提供還原與完整結束；
  系統匣不可用時不隱藏視窗。Windows 登入啟動預設關閉，只有使用者切換設定
  才保存設定並以可回復流程更新 HKCU Run 值；設定保存失敗時會回復原啟動項。
  Portable 模式會保留相同的資料模式。新增
  `--start-minimized` 只對圖形入口生效。回復方式是停用自動啟動並還原本次
  source changes；不需遷移既有設定，缺少新欄位時沿用安全預設。Regression-first
  基線為 `2 errors`，完成後基礎定向套件為 `59 passed`、資源調度六個套件為
  `30 passed`；生命週期修正相關套件為 `94 passed, 1 skipped`，完整 Repository
  runner 為 `1608 passed, 7 skipped`；skip 均為
  既有 Windows link 權限限制。Quality audit
  通過 Ruff `372` 個 Python 檔與文字污染 `482` 個受控檔案，兩個 Testing 版本、
  隔離 `compileall` 與 `git diff --check` 也都通過。
  後續生命週期查核另修正延遲最小化 callback 在視窗已還原後誤進待機的競態；
  背景期間才完成的預覽準備會清理暫存並取消播放，格式工廠的切點預覽倒數則會
  保留剩餘時間，不會在還原後失去停止期限。
- Development 39.0.95 將啟動流程改為非模態：不再自動執行首次 MOD 設定
  `QDialog`，核心工具未達 4/4 時也不再排程環境視窗。主畫面原有的 MOD 管理與
  環境狀態按鈕保留完整手動入口，既有設定不被靜默修改。Regression-first 案例
  修正前捕捉到首次 MOD 視窗並為 `1 failed`，移除自動路徑後為 `1 passed`；
  六個相關套件為 `44 passed`，完整 Repository runner 為
  `1593 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `476` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、兩個 Testing 版本、Repository 外隔離 `compileall` 與
  `git diff --check` 均通過。
- Development 39.0.73 將 U+201C／U+201D 左右智慧雙引號與直雙引號統一為
  相同的本機比較身分。修正前，同名結果會落後於較長的 `live cover`、歷史
  建議重複且相似音樂浪費第三個查詢槽；regression-first 三條案例修正前為
  `3 failed`，修正後為 `3 passed`。顯示、歷史代表值與送往 provider 的原始
  文字維持不變。定向套件為 `119 passed`，完整 repository runner 為
  `1530 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD、網站、依賴、版本、Testing 版本與 Repository 外
  隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.74 統一共用搜尋與 `youtube-similar` 的 token 詞界規則，
  標題／作者中的底線現在與其他非單字符號一樣作為分隔符。修正前，
  `Hello World` 與 `Hello_World` 的標題 token 完全沒有交集，只得到語言與分類
  25 分；regression-first 案例修正前為 `1 failed`，修正後為 `1 passed`。
  定向套件為 `120 passed`，完整 repository runner 為 `1531 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD、
  網站、依賴、版本、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.75 將 U+FE0E／U+FE0F Unicode 顯示選擇符從本機比較
  身分移除。修正前，`❤` 與 `❤️` 的同名作品排序失真、歷史建議重複且相似
  音樂浪費第三個查詢槽；regression-first 三條案例修正前為 `3 failed`，修正後
  為 `3 passed`。顯示、歷史代表值與 provider 查詢原文保持不變。定向套件為
  `123 passed`，完整 repository runner 為 `1534 passed, 7 skipped`。Quality
  audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD、網站、
  依賴、版本、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.76 讓已知 phrase alias 模式中的 `-` 接受 U+2010～U+2015
  排版變體。修正前，`LO‑FI`、`lo–fi` 與 `lo―fi` 不會套用既有 `lofi` 別名；
  regression-first 正例修正前失敗，`flo–fi` 負例原本即通過，修正後兩條測試
  均通過。其他查詢中的破折號不會被改寫。定向套件為 `125 passed`，完整
  repository runner 為 `1536 passed, 7 skipped`。Quality audit 通過 Ruff `367`
  個 Python 檔與文字污染 `475` 個受控檔案；MOD、網站、依賴、版本、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.77 將 U+2212 Unicode 負號視為既有 ASCII 連字號的本機
  搜尋身分，並同步 `lo-fi` phrase alias、隔離的 `youtube-similar` MOD 與嚴格
  YouTube Topic 頻道後綴。修正前，排序、建議、相似查詢與別名四條案例為
  `4 failed`，Topic 參數化案例為 `1 failed, 2 passed`；修正後相同案例為
  `7 passed`。顯示、歷史代表值與送往 provider 的原始查詢仍保持不變。定向
  套件為 `130 passed`，完整 repository runner 為 `1540 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.78 讓 Bilibili 專用工作區在派送文字搜尋前套用共用查詢
  準備流程，並將修正後文字回填欄位；官方 Bilibili URL 仍由既有網站路由優先
  處理。Regression-first 案例修正前為 `1 failed`、修正後為 `1 passed`；五個
  相關套件為 `55 passed`，完整 repository runner 為 `1541 passed, 7 skipped`。
  Quality audit 通過 Ruff `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD
  群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing
  版本與 Repository 外隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.79 讓 Bilibili 專用工作區在官方來源過濾與跨頁合併後套用
  共用穩定相關性排序，完全同名作品不再落在延伸標題之後；同分結果仍維持
  provider 原順序。Regression-first 案例修正前為 `1 failed`、修正後為
  `1 passed`；五個相關套件為 `56 passed`，完整 repository runner 為
  `1542 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.80 在 YouTube／Bilibili 專用工作區合併到共用 200 筆容量
  時清除下一頁游標、停用載入更多並顯示上限狀態，避免發出無法新增結果的
  後續請求。Regression-first 兩條案例修正前為 `2 failed`、修正後為
  `2 passed`；六個相關套件為 `54 passed`，完整 repository runner 為
  `1544 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.81 將有明確引號界線的 `"標題" by 作者` 納入既有嚴格
  跨欄位精確排序，同時以未加引號的 `Stand by Me` 負例防止一般作品名稱被
  誤拆。Regression-first 正例修正前為 `1 failed`，負例為 `1 passed`；最小
  修正後兩條案例均通過。七個相關套件為 `102 passed`，完整 repository runner
  為 `1546 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與
  文字污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、
  依賴鎖 `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall`
  均通過，`Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.82 讓整個查詢以成對雙引號包住時建立未帶引號的本機
  標題比較候選，使正式同名標題優先於保留引號整句的延伸內容；未閉合引號
  負例保持一般文字語意。Regression-first 正例修正前為 `1 failed`、負例為
  `1 passed`，最小修正後加上既有智慧引號與重音 fallback 共 `4 passed`。
  七個相關套件為 `104 passed`，完整 repository runner 為
  `1548 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.83 將完整 metadata 標題的成對引號形式加入既有嚴格
  作者／標題候選，使 `"標題" 作者`、`作者 "標題"` 及破折號形式在正向／
  反向排列均可精確排序；部分曲名負例不會取得 100 分。Regression-first 正例
  修正前為 `1 failed`、負例為 `1 passed`，修正後加上 39.0.81～82 引號案例
  共 `5 passed`。七個相關套件為 `106 passed`，完整 repository runner 為
  `1550 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.84 將 39.0.82 只供標題使用的平衡引號候選整理為共用欄位
  候選，讓 `“Nora Vale”` 也能匹配未帶引號的作者 metadata 並優先於標題提及
  內容；未閉合引號負例不取得作者完全相等分數。Regression-first 正例修正前
  為 `1 failed`、負例為 `1 passed`，修正後連同標題與重音回歸共 `5 passed`；
  七個相關套件為 `108 passed`，完整 repository runner 為
  `1552 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.85 將完整 metadata 作者的成對引號形式加入既有跨欄位候選，
  讓 `“Nora Vale” Midnight Echo`、`Midnight Echo - “Nora Vale”` 與雙欄皆加
  引號的明確語法取得完整作者／標題順位；部分作者負例不會取得 100 分。
  Regression-first 正例修正前為 `1 failed`、負例為 `1 passed`，修正後連同既有
  引號欄位回歸共 `6 passed`。七個相關套件為 `110 passed`，完整 repository
  runner 為 `1554 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python
  檔與文字污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing 版本與 Repository 外
  隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.86 將 `「」`、`『』`、`《》`、`〈〉` 的完整配對正規化為
  本機雙引號身分，讓 `《Midnight Echo》` 能匹配未加標記的正式標題，並讓
  搜尋建議與相似音樂偏好將同內容的東亞／ASCII 引號視為同一身分；錯配
  `「Midnight Echo』` 保持原文。Regression-first 修正前為
  `3 failed, 1 passed`，修正後為 `4 passed`。九個相關套件為
  `126 passed, 1 skipped`，完整 repository runner 為
  `1558 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.87 將作者／標題精確候選整理成正規化後的空白、連字號，
  以及 `|`、`:`、`·`、`・`、`/` 四種有限空白排列；全形 `／` 由既有 NFKC
  規則映射為 `/`。`Nora/Midnight Echo` 的部分作者負例不會取得 100 分。
  Regression-first 正例修正前為 `1 failed`、負例為 `1 passed`，修正後連同
  舊分隔符與引號欄位回歸共 `6 passed`。七個相關套件為 `116 passed`，完整
  repository runner 為 `1560 passed, 7 skipped`。Quality audit 通過 Ruff
  `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing 版本與 Repository 外
  隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.88 將 `/`、`|`、`:`、`·`、`・` 兩側空白折疊集中到共用
  本機搜尋身分，並同步隔離的 `youtube-similar` MOD；排序候選因此只需保留
  正規化後的七種有限分隔符。分隔符本身不會被移除，無分隔符文字保持不同。
  Regression-first 三條跨模組案例修正前為 `3 failed`，修正後為 `3 passed`；
  搜尋排序、建議、歷史與相似音樂四個相關套件為 `98 passed`，加上隔離 MOD
  雜湊及版本套件的八個定向套件為 `126 passed`；完整 repository runner 為
  `1563 passed, 7 skipped`。Quality audit 通過 Ruff `367` 個 Python 檔與文字
  污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`、版本文件 `4`、Testing 版本與 Repository 外隔離 `compileall` 均通過，
  `Version/` 中有 `0` 個 `.pyc`。
- Development 39.0.89 補齊既有 `lo-fi` 詞組別名的空白破折號形式；
  `LO - FI`、`lo – fi`、`lo— fi` 與 `lo −fi` 會正規化為 `lofi`，但
  `flo - fi` 與 `lo - fighter` 仍保留原文。Regression-first 正例修正前為
  `1 failed`，兩個較長單字負例為 `1 passed`；修正後兩項為 `2 passed`。
  搜尋排序、YouTube／Bilibili 工作區與版本定向回歸為 `92 passed`；完整
  repository runner 為 `1565 passed, 7 skipped`。Quality audit 通過 Ruff
  `367` 個 Python 檔與文字污染 `475` 個受控檔案；MOD 群組 `7 / 4`、網站矩陣
  `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`、Testing 版本與 Repository 外
  隔離 `compileall` 均通過，`Version/` 中有 `0` 個 `.pyc`。

## 已退役或取消

- 動畫瘋整合已自目前來源與 runtime 註冊移除；舊 UserData 與保留版本不改寫。
- 已取消的 Stable 1.0 候選、舊 Testing 候選與未授權 build 工作目錄都不是
  可發布資產。
- Development 40.0 仍為 `NO RELEASE / VERSION UNASSIGNED`，不以規劃文件建立
  空版本。下一次
  Development 更新只保留一份有效的資源與 MOD 效能計畫，尚未形成發行候選。

## 目前 Testing 工作

- Testing `1.2.0` 本機封存已存在於 `Version/Testing/1.2`，版本稽核確認核心
  為 Development `39.0.11`。封存來源固定為 revision
  `fab5cb9333274e54f65a35b2f44a86699f0f349f`；目前 39.0.93 工作樹不會回寫
  該不可變候選；GitHub 上沒有對應 Testing 1.2.0 Release 或 tag。
- Testing `1.2.1` 已建立於 `Version/Testing/1.2.1`；tag
  `test-v1.2.1` 精確指向 source revision
  `05442d7875da5367cd23babc2ce4e2e3e0cb87a2`。
- 主要下載附件是 `MediaManager-Testing-1.2.1.zip` 與同名 `.zip.sha256`；
  [GitHub prerelease](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.1)
  共有 9 個附件，ZIP digest 已與 sidecar 閉合。
- [Testing `1.2.2`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.2.2)
  已由 Development `39.0.39` 的乾淨 source freeze
  `f7c65ee1a8e92828ede299bcbdff5e66d16f6810` 建立於
  `Version/Testing/1.2.2`，並以 `test-v1.2.2` 發布為具有 9 個附件的
  prerelease；`MediaManager-Testing-1.2.2.zip` SHA-256 為
  `2dd688ceb6a3af9c3e100dca1c61a326ac8be2a19237b217bd2f8a21b6a7e2c4`，
  已與 ZIP sidecar 及 GitHub asset digest 閉合，且未覆寫 1.2.1。
- Testing 1.0 是不可覆寫的歷史版本，不以目前 39.x 來源重建或冒用。
- Testing 1.1 使用唯一修訂 tag `test-v1.1.0-r2`，精確指向 source revision
  `09b3a86e00938241d27050088583ebf81d9fb182`；9 個附件已發布且 digest 閉合。
- Testing 1.2.1 與 1.2.2 產物維持未簽署 `SAFE_MODE`、非 Stable；實際身分與雜湊以發行頁的
  `release-info.json`、`SHA256SUMS.txt` 與 ZIP sidecar 為準。

## 尚未成立的發行條件

- 沒有同一候選集上的 production Authenticode、Ed25519、checksum、SBOM、
  copied-folder smoke 與 release preflight 證據。
- 截圖只能證明可見版面；Tab／Shift+Tab、UIA／NVDA、讀屏、Windows 高對比及
  真實互動流程仍需人工驗證。
- 外部網站會變動；離線 regression 與 extractor 存在不等於即時網站 smoke。

這些未成立項目不阻擋 Testing 使用，但阻擋任何 Stable 或已簽署正式發布宣稱。

## 歷史與回復

目前樹只保留仍有效的下一次更新計畫，不保留已結案逐版 roadmap 與重複 release
journal。過去決策仍可從 Git 歷史、
不可變 `Version/` 產物及 GitHub Releases 的 checksum／metadata 追查。不得為了
縮小 Repository 而刪除公開附件、改寫 tag、重寫 Git 歷史或清除 UserData。
