# 下一次 Development 資源與 MOD 效能計畫

狀態：`IN PROGRESS — Development 39.0.106`
查核日期：2026-09-09
版本：39.0.106 已完成階段 A、階段 B、階段 C，以及階段 D 的安全實驗工具；
階段 D 原型 build 與比較尚未執行。
本計畫不授權 build、Testing／Stable、簽署、push 或發布。

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
link 權限限制。
此項尚未以固定大量搜尋結果工作負載量測 OS 層 CPU、Private Working Set 與
網路請求數；預期效益是移除各頁重複 manager／cache，並避免隱藏列提前下載與
解碼。正式 Before／After 數據取得前，不宣稱已量得降幅。

### 階段 C：核心 YouTube 效能 profile 與下載

**完成（39.0.103）**：新增 schema 1、由核心驗證的 profile；provider 只接收
核心覆寫後的完整配置，無效或不完整的配置會失敗關閉：

| Profile | 同時下載工作 | 單項 fragment 併發 | 全域上限 | 用途 |
|---|---:|---:|---:|---|
| 省資源 | 建議 1、最多 2 | 1～2 | 2 | 低 CPU、低記憶體或背景工作 |
| 平衡 | 建議 2、最多 4 | 1～2 | 4 | 預設 |
| 高速 | 建議 2、最多 4 | 2～4 | 8 | 使用者明確選取且網路／磁碟足夠 |
| 自動 | 建議 2、最多 4 | 依工作數分配 | 4 | 不突破固定片段配額 |

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

1. **安全工具完成（39.0.105～39.0.106），實驗未執行**：PyInstaller spec 支援明確
   onefile／onedir 實驗切換，正式 `build_version` 則強制 onefile，不接受繼承
   環境改變發行配置。`tools.package_layout_experiment` 預設只輸出無副作用計畫，
   必須帶 `--execute` 才會在 Repository 外建立兩種原型；量測冷啟動、第二次
   啟動、verify-only、Provider Host、CPU time、Private／Working Set、thread、
   檔案數、磁碟大小、完整樹 SHA-256 及 copied-folder smoke。原型來源必須是
   乾淨 commit，證據路徑也不得位於 Repository。
   39.0.106 再將證據路徑預檢移到 build 前，寫入前仍二次驗證；Windows child
   以 suspended 狀態建立，加入 kill-on-close Job Object 後才恢復，逾時與設定
   失敗都會終止並 reap 完整程序樹。
2. 若完成早期分流與 onedir 後，YouTube 搜尋／分析仍有明顯可重現的固定 Host
   成本，再實驗短期暖 discovery Host。下載與 FFmpeg 繼續使用獨立程序。

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

39.0.106 的輸出預檢、Job Object 收容、版本與入口定向回歸為 `32 passed`；完整
Repository runner 為 `1659 passed, 7 skipped`。七項 skip 都是目前 Windows
帳號缺少建立測試用 link 權限，沒有功能測試失敗。安全補強沒有執行
PyInstaller 或保留任何原型。

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
