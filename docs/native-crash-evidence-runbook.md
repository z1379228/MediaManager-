# 原生崩潰去識別證據 Runbook

狀態：`EVIDENCE READY / NO CLAIM`。本流程只準備 Development 37.0 的人工採證邊界；
目前沒有可重現的 `0x80000003`、同時段 WER faulting module／offset 或可證 root cause，
因此不得宣稱原生崩潰已修復。

## 目的與非目標

目的只有在使用者可控制、可停止的重現過程中，保存足以區分 provider 子程序退出、runtime
原生錯誤與 WER 事件的最小 metadata。流程不會自動啟用 WER、搜尋事件、掃描或解析 dump、
啟動 provider、連線網站、讀取 Cookie／token，亦不會複製、移動、保存或上傳 dump。

Self Check 的 `run_id` 只是同一份 evidence bundle 的 correlation ID，不是 crash process session ID、
trace ID 或同一執行期的證明。只有時間與觸發條件能與相符 WER 事件交叉核對。

## 開始前

1. 保持 `SAFE_MODE`，不要使用 production 身分、正式簽章或登入資料。
2. 在 MOD 管理頁由使用者手動執行 Self Check，匯出去識別 JSON，記下其中 32 位小寫十六進位
   `run_id` 與 UTC `generated_at`。匯出仍使用既有 self-check 原子出口，沒有第二套 exporter。
3. 先以文字記下預定重現動作；不得包含完整 URL、query、fragment、媒體標題、檔名或本機路徑。
4. 若錯誤沒有再現，停止並記錄 `NOT_REPRODUCED`；不要以 retry、關閉驗證或放寬 assertion
   製造通過結果。

## 錯誤再現時只記錄的欄位

使用者確認程序已結束後，可人工查看同一精確時間附近的 Windows Application WER Event
1000／1001。只抄錄下列 allowlisted metadata：

- `component`：`provider`、`runtime` 或 `wer`。
- `observed_at`：換算為 UTC 的 RFC 3339 時間。
- `exit_code`：32-bit 代碼，格式為 `0x` 加 8 位小寫十六進位；例如 breakpoint 是
  `0x80000003`，但代碼本身不證明 faulting module 或 root cause。
- `faulting_module`：只保留 ASCII 小寫 basename，例如 `qt6core.dll`；不得保留 application path。
- `faulting_offset`：`0x` 加 1～16 位小寫十六進位。
- `artifact_sha256`：預設留空。只有使用者明確選定「本次新產生」的既有 dump 時，才可在本機
  計算 SHA-256 並只抄錄 64 位小寫 hash；不讀取內容、不保留路徑、不搬移、不加入 Git、不上傳。

不得保存 Event XML／EVTX、完整事件訊息、application／module／dump path、command line、stack、
環境變數、URL、query、fragment、Cookie、token、媒體內容或 dump bytes。沒有 exact-time matching
event 或使用者明確確認的新 dump 時，對應欄位保持 `null`，不得推測。

## Evidence v1 格式

`contracts/diagnostic_evidence_v1.py` 是 strict privacy boundary；reader 拒絕 unknown field，writer
不接受自由文字。紀錄只可附加到相同 `run_id` 的 schema 1 self-check JSON
`diagnostic_evidence` 陣列，最多 16 筆。範例：

```json
{
  "schema_version": 1,
  "run_id": "0123456789abcdef0123456789abcdef",
  "component": "wer",
  "observed_at": "2026-07-18T19:12:17Z",
  "exit_code": "0x80000003",
  "faulting_module": "qt6core.dll",
  "faulting_offset": "0xab",
  "artifact_sha256": null
}
```

舊 consumer 可忽略新增的頂層 `diagnostic_evidence`；self-check schema 仍為 1。若欄位形狀不符、
`run_id` 不一致、module 不是 basename 或出現 unknown field，整筆 evidence 必須 fail closed。

## 判定與後續

- `NOT_REPRODUCED`：保持 `EVIDENCE READY / NO CLAIM`，不建立 crash fix。
- 只有同一觸發可重現，且有 exact-time exit／module／offset 證據時，才把對應 regression 升為 P0。
- provider `stdout_eof`／`handoff_deadline` 只表示觀察階段；不可自動 retry，也不可據此猜測 native
  module。先以結構化 exit code 區分 child 真實退出與既有 handoff 行為。
- 回復方式是移除新增 evidence 附加欄位與入口；不遷移、刪除或重寫 UserData，也不處理原始 dump。
