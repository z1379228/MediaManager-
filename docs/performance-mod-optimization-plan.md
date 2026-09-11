# 下一次 Development 資源與 MOD 效能計畫

狀態：`COMPLETED — Development 39.0.112`
查核日期：2026-09-11
版本：39.0.106 已完成階段 A、階段 B、階段 C，以及階段 D 的安全實驗工具與
onefile／onedir 隔離原型比較；39.0.107 已完成階段 E 的下載工作流與 UI 改善，
39.0.108 完成實作後完整性稽核與回歸修正；39.0.109 完成第一批手動工作流增強；
39.0.110 完成硬體轉檔 preset 與非阻塞能力偵測；39.0.111 完成兩階段目標
容量及音量標準化；39.0.112 完成手動 MusicBrainz 中繼資料 MOD。
暖 discovery Host 已完成無網路固定成本重測；真實搜尋 workload 門檻尚未成立，
因此本輪不導入常駐程序。
39.0.106 只有隔離的開發實驗 build；39.0.107～39.0.112 未 build，且不建立 Testing／Stable、
不簽署、不 stage、不 commit、不 push、不發布。受控 HTTPS 多樣本吞吐量比較保留為
後續量測條件，不阻擋已完成的功能與安全驗證。

## 目標與優先順序

1. 提高啟動、切換頁面、搜尋、分析及進度更新的流暢度。
2. 降低前景閒置與背景待機的 CPU、記憶體、執行緒及喚醒次數。
3. 在不繞過網站限制、不降低完整性驗證的前提下改善下載吞吐量。

所有效能結論都必須以相同硬體、資料、網路條件與量測方式比較 Before／After；
未量測前只能標示 Expected Benefit。

## 已確認現況

- `main.py` 在解析 `--provider-host` 前匯入 Bootstrap 與可信 UI；每次內建下載或
  搜尋 MOD 操作則由 `SubprocessDownloadProvider` 建立一個新程序。
- 目前 PyInstaller spec 將 binaries 與 datas 直接放入 `EXE`，沒有 onedir 的
  `COLLECT` 階段。Portable ZIP 雖然解壓後使用，內部仍是 onefile 執行方式。
- 主視窗啟動時建立 YouTube、Bilibili、網站搜尋與媒體庫；所有已啟用的選用
  工作區也立即建立。搜尋與 YouTube 預覽控制會立即建立 Qt Multimedia player。
- 下載佇列的每一筆 provider progress 都會通知主視窗；下載表格同時保留動態
  500 ms～10 s 快照輪詢。下載主表已跳過不變內容，但部分其他工作表仍會整表重建。
- 背景待機已停止非必要 Qt 重複計時器、暫停播放器並清除可重建圖片快取；沒有
  啟用規則的 Automation monitor 已採事件等待。快速最小化／還原有狀態重查，
  背景期間完成的預覽準備不會開始播放，具期限的切點預覽會保留剩餘倒數。
  這些現有措施應保留。
- 格式、畫質、字幕與容器已由 `contracts/media_options_v1.py` 管理；核心可以在
  不接收網站解析責任的情況下再管理 YouTube 效能 profile。

## 重新評估結果

| 選項 | 優點 | 主要缺點／風險 | 決定 |
|---|---|---|---|
| Provider／Plugin 參數解析早於重型匯入 | 減少每次 Host 啟動的不相關 Python、Bootstrap、UI 匯入 | 入口重排可能影響 frozen CLI 分流 | P0 採用；補齊 GUI、headless、provider、plugin 入口回歸 |
| Portable ZIP 改為 onedir | 免除 onefile 每次啟動解壓；符合「解壓後點 EXE」流程 | 檔案數增加，缺檔或竄改面積較大 | P0 候選；先建立並比較原型，沿用 manifest、SHA-256 與 copied-folder smoke，量測通過才取代 |
| 建立獨立 Provider Host EXE，共用 onedir libraries | Host 不需包含 GUI 啟動圖；仍保留程序隔離 | spec、啟動與發行驗證較複雜 | P1 候選；在 onedir 原型後評估 |
| 延遲建立非目前工作區 | 降低冷啟動物件、計時器、網路 manager 與基礎記憶體 | 第一次開啟頁面會有短暫成本，需保存頁面狀態 | P0 採用；先建 tab shell，首次切換才建立且建立後保留 |
| 按下預覽後才建立 QMediaPlayer／QAudioOutput | 不使用預覽時不載入重型 multimedia runtime | 第一次預覽稍慢，錯誤處理路徑改變 | P0 採用；增加第一次建立、停止、關閉及重開測試 |
| 合併高頻 progress，只把最新狀態送往 UI | 減少跨執行緒 signal、複製與 UI event backlog | 不當節流可能漏掉終態或造成顯示延遲 | P0 採用；每工作最多 10 Hz，完成／失敗／暫停／取消永不節流，保留低頻 reconciliation |
| 共用縮圖 Network Manager 與 LRU | 合併重複 URL、連線與快取，取消不可見請求 | callback 生命週期與跨頁狀態較複雜 | P1 採用；限 GUI thread、使用 generation token，維持 URL／大小／數量上限 |
| 工作表逐步改為 QAbstractTableModel | 大量資料可增量更新及只建立可見列 | 重構範圍大，對目前有界小清單可能沒有足夠收益 | P2 條件採用；先修正仍整表重建的表格，只有量測顯示瓶頸才遷移 |
| YouTube 效能選項由核心管理 | UI、驗證、全域額度與預設值穩定；MOD 只做 yt-dlp 映射 | 核心與 provider 契約需版本化，過多選項會提高維護成本 | P0 採用；只公開穩定 profile，不直接暴露所有 yt-dlp flags |
| YouTube 搜尋／分析短期暖 Host | 可攤提 Python 與 yt-dlp 匯入成本 | 增加常駐記憶體、狀態污染、逾時、取消與 crash blast radius | P2 條件採用；先完成早期分流與 onedir 量測，仍有明顯固定成本才導入最多一個、30～60 秒 idle timeout 的 discovery Host |
| 所有 MOD 永久常駐 | 後續呼叫延遲低 | 待機記憶體、程序數、狀態與攻擊面增加 | 不採用 |
| 移除每次完整性驗證或只信任 mtime | 減少雜湊 I/O | 可被同大小／時間戳替換，破壞安全邊界 | 不採用；以程序生命週期攤提完整驗證，不降低驗證內容 |
| 無限制提高下載工作與 fragment threads | 特定高速網路可能增加吞吐 | CPU、記憶體、連線、限流與失敗率同步增加 | 不採用；改用有界全域額度 |
| 預設磁碟縮圖快取 | 重啟後可能減少網路請求 | 增加磁碟 I/O、清理與來源存取紀錄 | 不採用；先共用有界記憶體 LRU |
| 預設 HEVC Slowest 轉碼 | 可優先縮小部分輸出 | 與處理速度及低 CPU 優先順序衝突 | 不採用為下載預設；只保留格式工廠的容量優先工作 |

## 下一次更新範圍

### 階段 A：基線與低風險固定成本

1. **完成（39.0.98）**：新增不開啟可見 UI、不連線網站的啟動／Host 基準，
   記錄 elapsed time、private bytes、working set、CPU time、thread count 與 peak
   working set；工具強制隔離使用者資料，證據只允許輸出至 Repository 外。
2. **完成（39.0.98）**：將 Provider、Plugin、version／verify 等角色分流移到
   重型 Bootstrap／UI 匯入前；GUI 仍只在一般圖形入口初始化後載入。
3. **完成（39.0.99）**：下載進度加入 thread-safe latest-wins 合併器；
   重複 RUNNING 通知由 100 ms GUI timer 批次送出，狀態轉換與終態即時送達，
   表格保留低頻一致性校正。
4. **完成（39.0.99）**：Qt Multimedia player 改為通過前景、世代與檔案
   驗證後才建立；停止或關閉時釋放 source、output 與 Qt 物件。完整主視窗
   的隔離子程序回歸證明乾淨啟動不匯入 `PySide6.QtMultimedia`。

39.0.99 的合併器 regression-first 修正前因類別尚未存在而在收集階段出現
`1 error`。完成後相關下載、預覽、待機、主視窗、分割與轉換回歸為
`115 passed, 1 skipped`，完整 Repository runner 為 `1618 passed, 7 skipped`；skip
均是 Windows 帳號無法建立測試用 link。此階段尚未使用
固定預覽／下載 workload 量測 OS 層 CPU 與記憶體，因此只能確認匯入、
物件生命週期與通知數量上限，不宣稱已實測資源降幅。
完整測試的污染復查曾發現來源 Plugin Host 在 `-I` 模式下忽略
`PYTHONDONTWRITEBYTECODE`；Provider／Plugin Host 命令改為同時使用 `-B -I`後，
重跑完整套件的來源樹位元碼污染為 `0`。

39.0.98 的同方法 Windows 基準使用 2 次 warmup、7 次樣本及隔離的 AppData：
`--version` elapsed p50 由 243.229 ms 降至 87.643 ms，provider host 由
246.544 ms 降至 142.293 ms；private bytes p50 分別由 29,646,848 降至
13,975,552，以及由 31,264,768 降至 17,993,728。`--verify-only` 必須執行完整
Bootstrap，elapsed p50 由 257.699 ms 變為 268.335 ms，沒有速度改善；private
bytes p50 由 29,507,584 降至 25,739,264。這是同機短樣本基線，不外推至其他
硬體。後續可用下列方式重測，`--output` 必須指向 Repository 外且不存在的檔案：

```powershell
.\.venv\Scripts\python.exe -m tools.startup_baseline `
  --output <Repository 外的 startup-baseline.json>
```

### 階段 B：UI 記憶體與頁面流暢度

1. **完成（39.0.100）**：選用工作區及非目前核心頁面改為首次開啟才
   匯入模組並建立，建立後保留使用者輸入；啟用／停用與下載 prefill 均會
   經由同一 manager 物化或清理。
2. **完成（39.0.101）**：建立主視窗層級的單一可信縮圖服務；YouTube、
   Bilibili、網站搜尋與播放清單只載入目前可見列加前後 2 列，離開頁面只
   取消該 client 的 pending request，返回後補載，共用 LRU 快取維持 40 項上限。
3. **完成並以量測選案（39.0.102）**：MEGA、Direct HTTP、Gopeed 工作表使用
   signature 跳過相同快照，批次套用期間暫停 repaint，timer 在關閉時停止。
   同機 200 列×50 次刷新基準顯示逐 cell 重用的 workload p50／p95 均較整批
   重建慢，因此撤回該候選；`QAbstractTableModel` 也未提前遷移。

39.0.102 使用 2 次 warmup、7 次樣本：整批重建／逐 cell 重用 workload p50
為 `443.808 / 497.525 ms`，p95 為 `594.221 / 647.663 ms`，Private Bytes p50
為 `23,961,600 / 25,026,560`。外部證據是
`<Repository 外的 benchmark 目錄>\table-39.0.102-20260909.json`。
定向回歸為 `71 passed`，完整 Repository runner 為 `1627 passed, 7 skipped`；
skip 均是 Windows 測試用 link 權限限制。

39.0.100 將 `gui-lazy` 與 `gui-materialized` 加入同一隔離基準。使用
2 次 warmup、7 次樣本與相同來源，lazy 啟動與後續物化全部 11 個可見
工作區的 p50 比較為：elapsed `1281.963 / 1605.220 ms`、CPU time
`1015.625 / 1375.000 ms`、private bytes `57,851,904 / 70,725,632`、working set
`87,191,552 / 99,905,536`、Qt 子物件 `555 / 1,946`、active repeat timer `1 / 6`、
OS thread `8 / 9`。lazy 狀態物化工作區與延遲模組均為 `0`；分頁 shell 仍完整
呈現 12 個可見工作區項目。這是同一新來源的 lazy／all-materialized 工作負載
差異，不是 39.0.99 與 39.0.100 的歷史 Before／After，也不代表使用者開啟所有
工作區後仍會保留此差異。證據保存於 Repository 外：
`<Repository 外的 benchmark 目錄>\workspace-39.0.100-20260908.json`。
相關定向回歸為 `14 passed`，完整 Repository runner 為
`1620 passed, 7 skipped`；skip 均是 Windows 測試用 link 權限限制。

39.0.101 的共用縮圖服務與四個可見列 client 已完成 `54 passed` 的定向回歸；
完整 Repository runner 為 `1624 passed, 7 skipped`，skip 均是 Windows 測試用
link 權限限制。39.0.107 再加入固定 200 筆、頂端／底端捲動、完全封鎖網路的
`search-results` workload。初始結果填入的 elapsed p50／p95 為
`407.624 / 413.729 ms`，CPU time 為 `406.25 / 421.875 ms`；頂端只提出 8 個縮圖
請求，捲到底部合計 16 個，沒有提前請求其餘 184 筆。

結果填入先停用中間 repaint 後，elapsed p50 為 `390.214 ms`；再於同一批次暫停
四個 `ResizeToContents` 欄位的重複寬度掃描，完成後恢復原模式，最終 elapsed
p50／p95 為 `23.414 / 26.490 ms`，CPU time p50／p95 均為 `31.25 ms`。縮圖請求、
200 列及 164 個 panel Qt 子物件不變；live Private Bytes p50 由 `35,762,176`
變為 `35,377,152`，差異不足以宣稱記憶體改善。將每列高度改為一次性預設值的
候選反而使 elapsed p50／p95 成為 `484.693 / 575.025 ms`，已撤回。Before、
repaint-only、撤回候選與最終證據分別保存於 Repository 外的
`mediamanager-search-results-39.0.107-20260910-a.json` 至 `-d.json`。

39.0.107 的待機角色先將基準 schema 提升為 2；加入通用搜尋結果 workload 後
升為 3，再加入 YouTube／Bilibili 專用搜尋結果角色後目前 schema 為 4。
5 秒固定觀察使用
`gui-foreground-idle`／`gui-background-idle` 及對應全部工作區已物化角色。
同機使用 2 次 warmup、7 次樣本：乾淨 lazy 前景／背景的 active repeat timer
p50 為 `1 / 0`；全部 11 個延遲工作區物化後為 `6 / 0`，OS thread p50 為
`9 / 8`。5 秒觀察期 CPU time 的 lazy p50／p95 兩邊同為 `0 / 15.625 ms`，
物化後兩邊同為 `0 / 0 ms`，故只能確認週期喚醒來源已停止，不能宣稱已量得 CPU
百分比下降。物化後 Private Bytes p50 前景／背景為
`71,696,384 / 71,815,168`，Working Set 為 `101,376,000 / 101,425,152`；差異很小
且背景沒有較低，不宣稱記憶體改善。背景待機保留已建立工作區與輸入狀態；目前
不為追求未證實的記憶體降幅強制卸載頁面，基礎記憶體仍以 lazy 物化控制。
證據位於 Repository 外的 `mediamanager-idle-39.0.107-20260910-b.json`。

同一工具現在也分別物化真實 YouTube／Bilibili 專用工作區，以相同 200 筆、
頂端／底端、無網路與 offscreen 條件建立可重跑基準。未套用額外批次 layout
候選時，YouTube elapsed p50／p95 為 `23.956 / 27.657 ms`，Bilibili 為
`31.106 / 34.020 ms`，兩者頂端／底端縮圖請求均為 `9 / 18`。將通用搜尋採用的
repaint 暫停與 `ResizeToContents` 延後原樣套入後，YouTube p50／p95 退為
`26.945 / 34.463 ms`，Bilibili 為 `31.072 / 37.354 ms`；主要互動 p95 退步，
因此候選與其專用測試已撤回。撤回後重測分別為 `23.855 / 24.438 ms` 與
`30.305 / 33.399 ms`，縮圖視窗不變。A／候選 B／撤回確認 C 證據位於
Repository 外的 `mediamanager-site-results-39.0.107-20260910-a.json` 至
`-c.json`。CPU time 的 15.625 ms 取樣刻度與數十 KiB 記憶體波動不足以推翻
互動 p95 結論，也不宣稱資源降幅。

### 階段 C：核心 YouTube 效能 profile 與下載

**完成（39.0.103）**：新增 schema 1、由核心驗證的 profile；provider 只接收
核心覆寫後的完整配置，無效或不完整的配置會失敗關閉：

| Profile | 同時下載工作 | 單項 fragment 併發 | 全域上限 | 用途 |
|---|---:|---:|---:|---|
| 省資源 | 建議 1、最多 2 | 1～2 | 2 | 低 CPU、低記憶體或背景工作 |
| 平衡 | 建議 2、最多 4 | 1～2 | 4 | 預設 |
| 高速 | 建議 4、最多 4 | 2 | 8 | 使用者明確選取且網路／磁碟足夠 |
| 自動 | 依容量選 1／2／4 | 依實際模式 | 2／4／8 | 啟動時保守分級，工作中不跳檔 |

- 保留 yt-dlp 自動調整 buffer，不加入官方仍標示 experimental 且涉及服務端
  限速規避語意的 HTTP chunk 選項。
- 官方文件確認 fragment 並行只作用於 DASH／HLS native；一般單檔來源不會因
  此設定保證加速。本輪未以真實網站進行 Before／After 吞吐量量測，因此只確認
  參數契約、全域上限及 UI 狀態，不宣稱已測得下載速度提升。
- **完成（39.0.104）**：大型播放清單加入預設關閉的快速模式；只有 YouTube
  工作區由使用者明確勾選後，才傳送可選 `lazy=true`，provider 映射為
  `lazy_playlist=True`。仍以核心能力限制最多 500 項，UI 明示結果不是完整總數，
  且不支援隨機或反向排序。未勾選、非 YouTube 與既有第三方 provider payload
  維持不變；目前仍是整批 tuple 回傳，不宣稱具備逐列即時串流 UI。
- 速度／低資源 profile 保留來源編碼與 stream copy／remux；耗時轉碼留在格式工廠。
- 定向回歸為 `68 passed`；舊 context 相容性失敗修正後的 3 項重查通過，完整
  Repository runner 為 `1643 passed, 7 skipped`。七項 skip 都是目前 Windows
  帳號缺少建立測試用 link 權限，沒有功能測試失敗。
- 39.0.104 的播放清單契約、subprocess、provider、UI 與內建雜湊定向回歸為
  `99 passed`；完整 Repository runner 為 `1649 passed, 7 skipped`。七項 skip
  都是目前 Windows 帳號缺少建立測試用 link 權限，沒有功能測試失敗。

### 階段 D：條件實驗，不預設交付

1. **完成（39.0.105～39.0.106）**：PyInstaller spec 支援明確
   onefile／onedir 實驗切換，正式 `build_version` 則強制 onefile，不接受繼承
   環境改變發行配置。`tools.package_layout_experiment` 預設只輸出無副作用計畫，
   必須帶 `--execute` 才會在 Repository 外建立兩種原型；量測冷啟動、第二次
   啟動、verify-only、Provider Host、CPU time、Private／Working Set、thread、
   檔案數、磁碟大小、完整樹 SHA-256 及 copied-folder smoke。原型來源必須是
   乾淨 commit，證據路徑也不得位於 Repository。
   39.0.106 再將證據路徑預檢移到 build 前，寫入前仍二次驗證；Windows child
   以 suspended 狀態建立，加入 kill-on-close Job Object 後才恢復，逾時與設定
   失敗都會終止並 reap 完整程序樹。第一次真實 build 發現 `verify-only` 會把
   89 個已釘選內建 MOD 物化到執行檔旁，舊檢查誤判為 artifact 竄改；回歸修正
   改在兩個獨立副本中量測，只允許這 89 個檔案新增，原始 artifact 全程唯讀。
2. **條件未成立，不導入（39.0.107）**：YouTube 搜尋／分析短期暖 discovery
   Host。完成早期分流後以目前來源執行 2 次 warmup、7 次無網路 Provider Host
   樣本；elapsed p50／p95 為 `351.495 / 377.174 ms`，CPU time p50／p95 為
   `218.75 / 234.375 ms`，Private Bytes p50／p95 為
   `18,509,824 / 18,952,192`。這只量到無有效請求的固定啟動成本，不能證明真實
   搜尋的 p95 或總等待時間會改善；常駐則確定增加程序生命週期、記憶體、逾時、
   取消及狀態污染風險。因此維持每次請求的程序隔離，只有固定合法真實 workload
   證明 Host 啟動占主要延遲且收益超過常駐成本時才重新開案。下載與 FFmpeg
   繼續使用獨立程序。

### 階段 E：下載工作流與可信 UI

1. **完成（39.0.107）**：手動貼入與 TXT／CSV 使用同一個下載收件匣。它以
   狀態文字及列選取呈現可加入、無效、重複、工作區不符與 MOD 未啟用項目，
   不因單一錯誤丟失整批內容。
2. **完成（39.0.107）**：新增有界 `mediamanager://add` 及
   `--browser-handoff` 契約。只接受主機、路徑與 provider 已知的公開 HTTPS
   下載頁；喚醒後顯示對應工作區，不自動排隊，也不註冊系統 Registry。
3. **完成（39.0.107）**：將既有核心效能 profile 提升為所有下載頁可見的全域
   資源模式。省資源／平衡／高速預設 1／2／4 個工作，YouTube 才另外接收
   片段額度；進行中工作仍拒絕切換。自動模式只在程序內偵測一次邏輯處理器與
   總記憶體，資訊不足回復平衡，不以持續輪詢或動態跳檔增加背景負擔。
4. **既有能力，保留回歸**：Automation 已能建立預設關閉的頻道／播放清單
   排程，定期展開時依下載封存去重；不再建立第二個訂閱服務。
5. **完成（39.0.107）**：格式工廠加入可先檢視串流、明確選擇音訊／字幕軌且以
   Matroska stream copy 輸出的無損軌道工作流。ffprobe 維持 256 KiB／128 streams
   上限並在背景 thread 探測；選取軌道於排隊前再次確認，輸出仍採原子提交，且
   codec 與所選來源／輸出封包 SHA-256 必須一致。
6. **完成（39.0.107）**：Speech to Text 支援明確分類、SHA-256 驗證的 VAD
   模型；可信 UI 在使用者要求後才於背景檢查 whisper-cli 是否同時提供 `--vad`
   與 `--vad-model`。選項預設關閉，缺少 CLI 能力或 VAD 模型時保持停用，不會
   靜默改變字幕分段語意。模型不自動下載，子程序在 Windows 使用 no-window flag。
7. **完成（39.0.107）**：媒體庫重複檔案使用大小 → 首尾指紋 → 完整 SHA-256
   分層確認。只有前兩層相符的候選才計算完整雜湊；完整雜湊快取隨檔案大小或
   修改時間變更失效。檢查在 GUI thread 外執行、可取消且顯示進度，完整雜湊
   相同後才稱為重複檔案；介面只列出結果，不會自動刪除媒體。
8. **完成安全合成基準，保留現值（39.0.107）**：Direct HTTP 的串流讀取大小
   改由單一私有常數控制，並新增不開 socket 的 `tools.direct_http_io_baseline`。
   工具載入真實 provider，保留 HTTPS／副檔名／輸出路徑、`.part`、SHA-256 與
   原子 rename 路徑，只在隔離模組替換 DNS 與 opener 邊界。32 MiB、2 次 warmup
   與 7 次記錄顯示 256 KiB／1 MiB／4 MiB 的 elapsed p50 分別為
   `35.116 / 44.308 / 43.977 ms`，tracemalloc peak p50 為
   `660,427 / 2,232,539 / 8,523,819 bytes`；但 256 KiB 每樣本產生 128 次進度
   事件，為 1 MiB 的 4 倍。此 workload 沒有真實網路、pipe flush 或 UI 消費者，
   不足以證明縮小分塊可改善端到端下載，因此保留 1 MiB 折衷，不採用 4 MiB。
9. **完成單次真實 HTTPS smoke，不作效能外推（39.0.107）**：新增預設 dry-run
   的 `tools.direct_http_https_baseline`，只允許
   [W3C HTML5 media-events](https://www.w3.org/2010/05/video/mediaevents) 測試頁所用
   的固定 Sintel HTTPS URL，並把 provider 的檔案上限收緊至 8 MiB。真實 provider
   成功取得 `4,372,373` bytes、送出 5 次 1 MiB 進度事件、記錄 SHA-256，且 owned
   暫存下載已移除。單次 elapsed／throughput 觀察為 `2562.414 ms / 1.627 MiB/s`；
   公共測試主機不作重複負載，因此此數字只證明 TLS、驗證、串流寫檔、進度、
   雜湊與清理路徑可用，不是下載速度改善證據。若要比較 p50／p95，必須改用
   自有且受控的 HTTPS 伺服器、相同網路條件與多次樣本。
10. **完成稽核修正（39.0.108）**：真實 FFmpeg 發現 `.mks` 不能穩定由副檔名
    推斷 Matroska muxer，軌道複製命令改為明確指定 `-f matroska`；媒體庫在每次
    重複確認前重查目前大小與修改時間，避免採信掃描後過期的指紋或完整雜湊；
    whisper 模型雜湊與複製移至 GUI thread 外，支援關閉取消與暫存清理。
11. **完成第一批手動工作流增強（39.0.109）**：下載網址、Direct HTTP 與格式
    工廠來源使用同一個有界拖放分類器，再分流至既有收件與白名單，不自動啟動
    工作。格式工廠新增最多 20 秒實際輸出試轉及 15 秒開頭解碼健康檢查；兩者
    在背景執行、可取消，並與正式轉換序列化，避免多個 FFmpeg 同時爭用資源。
    試轉檔限制於服務私有暫存目錄並具明確清理；自我檢查只報告暖狀態。
12. **完成硬體轉檔擴充（39.0.110）**：加入 Intel QSV、AMD AMF 的 H.264／
    H.265，以及 NVIDIA／Intel／AMD AV1 明確 preset。每個 preset 以本機 FFmpeg
    回報的 encoder 作能力閘，沒有跨硬體或 CPU 自動回退；實際 device／driver
    失敗會保留為可診斷的工作失敗。六項 FFmpeg build 探測移至 GUI thread 外，
    支援頁面關閉取消與世代隔離，避免能力重查凍結介面或晚到結果污染狀態。
13. **完成容量與音量工作流（39.0.111）**：H.264 目標容量採兩階段平均位元率，
    來源時長在背景取得，保留 3% 容器餘裕並在 commit 前拒絕超限輸出；不使用
    會截斷內容的 `-fs`。pass log 是服務擁有的暫存資料，所有終態都清除。
    Loudnorm 另提供 FLAC 與 Opus 新檔，明確要求 FFmpeg 的 `loudnorm` filter
    及對應 encoder，且不宣稱 Passthru 或原始音訊位元相同。
14. **完成 MusicBrainz 輔助中繼資料（39.0.112）**：可停用 MOD 在受控程序內
    只連線官方固定錄音搜尋 API；`manual` 可見性使它只由本機媒體庫操作觸發，
    不加入一般網站來源或聚合搜尋。每次最多 10 筆、回應最多 512 KiB、同一
    instance 每秒最多一個請求。結果先預覽再選取，套用只更新本機 SQLite 的
    標題、歌手與 MBID 標籤，不改寫媒體檔、檔名或內容雜湊；沒有背景輪詢。

UI 依 [Windows design principles](https://learn.microsoft.com/windows/apps/design/design-principles)
採用清楚階層、克制強調色與一致字型層級；依
[Qt accessibility](https://doc.qt.io/qt-6/accessible.html) 保留可縮放 layout、
鍵盤焦點、文字狀態與足夠對比。一般驗證錯誤優先顯示於工作內容，只有重要確認
使用模態對話框，避免多餘中斷。

39.0.107 的第一輪視覺整理只採用靜態 QSS 與 widget 屬性，不加入陰影動畫、
模糊背景或常駐繪製：卡片／說明／輸入／primary action 降低同權重競爭，導覽
捲動按鈕、選取分頁、scrollbar hover、選單分隔線與 2 px 鍵盤焦點改為一致狀態。
依 [NavigationView](https://learn.microsoft.com/windows/apps/design/controls/navigationview)
準則，超過 5 個頂層工作區時另提供按需建立的「工作區」選單，分為下載、
搜尋與媒體、工具、自動化、官方工具及其他；第三方未知 ID 也保留於其他，
不會失去入口。選單直接切換既有 tab 並沿用 lazy 物化，不建立背景 timer；原有
分頁、左右捲動及快捷鍵保留，形成可回復的漸進式導覽調整。內容區採
[Windows spacing guidance](https://learn.microsoft.com/windows/apps/design/basics/content-basics)
的 8／12／16／24 間距節奏；動效若加入，只能是使用者操作後的短暫直接回饋，
背景待機時必須停止。只有後續可用性或 940 px 版面量測證明仍有問題，才考慮
將整個頂層導覽替換為左側 rail，避免目前就進行高風險結構重寫。

## 驗收與停止條件

- 每個候選至少執行冷啟動、第二次啟動、可見閒置、背景待機、首次／再次開啟
  頁面、搜尋 Host 以及固定合法測試媒體下載場景。
- Before／After 使用相同機器、顯示縮放、程式設定、資料集與網路；至少保存
  p50、p95、CPU time、Private Working Set、thread count、下載吞吐與失敗結果。
- 先取得基線再設定改善門檻；任何候選若造成主要互動 p95、下載失敗率或安全
  驗證退步，即使平均值較好也不保留。
- UI thread 不做同步程序等待；所有 model 更新回到 GUI thread。
- 不移除 Job Object、timeout、取消、輸入大小、完整性、簽章或能力限制。
- onedir、暖 Host 與提高 fragment 併發都必須有獨立 feature flag 或清楚回復路徑。

## Rollback

- 入口分流可回復至目前單入口 `_run`，但保留新增的角色回歸測試。
- lazy panel／player 可切回 eager factory，不遷移或刪除使用者設定。
- progress 合併器可停用並回到目前通知路徑；終態契約保持不變。
- YouTube profile 保存穩定 enum；未知值回復「平衡」，不把原始 yt-dlp 參數寫入設定。
- onedir 原型不覆寫既有 Testing／Stable 目錄、tag 或附件；未通過 copied-folder
  smoke 時繼續使用目前封裝方式。

39.0.105 的配置切換、既有 build 工具、Windows 真實 child process 量測、版本
同步及實驗工具定向回歸為 `57 passed`；完整 Repository runner 為
`1657 passed, 7 skipped`。七項 skip 都是目前 Windows 帳號缺少建立測試用 link
權限，沒有功能測試失敗。本輪未執行 PyInstaller，仍沒有 onefile／onedir
Before／After 數據。

39.0.106 的完整隔離實驗使用 2 次 warmup、7 次樣本。onefile／onedir 的 cold
version 為 `2415.406 / 521.547 ms`；version p50／p95 為
`2238.396 / 2436.356 ms` 與 `341.116 / 348.725 ms`，verify-only 為
`2355.176 / 2396.625 ms` 與 `523.244 / 665.158 ms`，Provider Host 為
`2257.093 / 2294.564 ms` 與 `421.681 / 434.545 ms`。onedir 在本機啟動路徑明顯
較快，但 artifact 由 1 個 `97,493,836` bytes 檔案增加為 445 個、總計
`221,740,815` bytes；兩者完整樹 SHA-256、複製資料夾 smoke 與 89 個釘選 MOD
物化都通過。現有 onefile 資源取樣只可靠涵蓋 PyInstaller launcher 父程序，
因此 CPU、Private Bytes 與 Working Set 不作跨 layout 結論；正式改用 onedir 前
仍需補齊 GUI 與完整程序樹資源量測。證據位於
`<Repository 外的 benchmark 目錄>\package-layout-39.0.106-20260909.json`。
物化誤判修正定向回歸為 `10 passed`；完整 Repository runner 為
`1660 passed, 7 skipped`。七項 skip 都是目前 Windows 帳號缺少建立測試用 link
權限，沒有功能測試失敗；實驗原型已自動清除。

39.0.107 的下載收件匣、瀏覽器交付、全域與自動資源模式、靜態視覺整理、
無損軌道、VAD 能力閘及完整重複確認已完成。完整 Repository runner 為
`1731 passed, 7 skipped`；七項 skip 都是目前 Windows 帳號缺少建立測試用 link
權限。Quality audit 通過 Ruff `386` 個 Python 檔與文字污染掃描 `496` 個受控
檔案，版本文件稽核與 `git diff --check` 亦通過。本輪未執行 PyInstaller build、
stage、commit、push 或發布；固定真實 HTTPS 端到端 smoke 已完成，但沒有在公共
主機上進行重複吞吐量比較，也不據此宣稱下載加速。
Provider Host 固定成本證據保存於 Repository 外的
`mediamanager-provider-host-39.0.107-20260910-a.json`；它禁止網路與可見 UI，
不能替代真實搜尋或下載 workload。Direct HTTP 合成 I/O 證據保存於 Repository
外的 `mediamanager-direct-http-io-39.0.107-20260910-a.json`；單次真實 HTTPS 證據
為 `mediamanager-direct-http-https-39.0.107-20260910-b.json`。兩者所有短暫下載
均已清除；只有前者可比較固定本機 I/O，後者只作真實網路整合 smoke。

39.0.108 的完整性稽核以回歸測試先重現 `.mks` muxer、掃描後同大小改寫與大型
模型同步匯入三個缺口。修正後完整 Repository runner 為
`1734 passed, 7 skipped`；七項 skip 均為 Windows 測試帳號缺少建立 link 權限。
Quality audit 通過 Ruff `386` 個 Python 檔與文字污染掃描 `496` 個受控檔案；
版本文件稽核與 `git diff --check` 通過。真實 FFmpeg SubRip `.mks` 複製的來源／
輸出封包 SHA-256 相同；暫存輸出已清除。本次未 build、stage、commit、push 或發布。

39.0.109 的有界拖放、輸出試轉、快速健康檢查及手動自檢暖狀態已完成。
完整 Repository runner 為 `1753 passed, 9 skipped`；九項 skip 均為 Windows
測試帳號缺少建立 link 權限，其中兩項是新增的拖放及試轉暫存 link 拒絕案例。
本機 FFmpeg smoke 實際完成 WAV 開頭解碼、1 秒 PCM 試轉、ffprobe 驗證及暫存
清理。Quality audit 通過 Ruff `390` 個 Python 檔與文字污染掃描 `500` 個受控
檔案；版本文件稽核通過。本次未 build、stage、commit、push 或發布。

39.0.110 的硬體 preset 與背景能力偵測已完成。新增 preset 只依 FFmpeg build
回報啟用，不能把「編譯存在 encoder」誤稱為顯示卡或驅動已可工作；正式工作
仍執行 runtime validation，且不靜默回退 CPU。完整 Repository runner 為
`1762 passed, 9 skipped`；九項 skip 均為 Windows 測試帳號缺少建立 link 權限。
Quality audit 通過 Ruff `390` 個 Python 檔與文字污染掃描 `500` 個受控檔案。
本次未 build、stage、commit、push 或發布。

39.0.111 的目標容量與音量標準化已完成。格式工廠完整定向套件為
`100 passed, 2 skipped`；兩項 skip 均為 Windows 測試帳號缺少建立 link 權限。
本機 FFmpeg 真實完成 H.264 兩階段目標容量與 Loudnorm／FLAC 輸出，容量上限、
輸出契約及 pass log 清理均通過。此變更已與後續 39.0.112 一起納入下方完整
Repository runner。本次未 build、stage、commit、push 或發布。

39.0.112 的 MusicBrainz provider、手動搜尋隔離、媒體庫資料更新及非阻塞 UI
定向回歸為 `108 passed`，跨模組定向回歸為 `273 passed, 5 skipped`；完整
Repository runner 為 `1790 passed, 9 skipped`。九項 skip 均是目前 Windows
帳號缺少建立測試用 link 權限。Quality audit 通過 Ruff `392` 個 Python 檔與
文字污染掃描 `503` 個受控檔案；版本文件、版本產物及 diff 格式稽核通過。
本次未 build、stage、commit、push 或發布。

## 官方研究依據

- [PyInstaller onefile／onedir 執行模式](https://www.pyinstaller.org/en/stable/operating-mode.html)
- [PyInstaller child-process 與 frozen 環境注意事項](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html)
- [PyInstaller multipackage／shared COLLECT](https://pyinstaller.org/en/latest/spec-files.html)
- [Qt QProcess 非同步程序通道](https://doc.qt.io/qt-6/qprocess.html)
- [Qt Model/View 與大量資料建議](https://doc.qt.io/qt-6.5/model-view-programming.html)
- [Qt QNetworkAccessManager](https://doc.qt.io/qt-6/qnetworkaccessmanager.html)
- [Qt TimerType](https://doc.qt.io/qt-6.5/qt.html)
- [Python threading 與 GIL](https://docs.python.org/3/library/threading.html)
- [yt-dlp 官方下載選項](https://github.com/yt-dlp/yt-dlp/blob/master/README.md)
- [Windows Performance Recorder](https://learn.microsoft.com/windows-hardware/test/wpt/introduction-to-wpr)
