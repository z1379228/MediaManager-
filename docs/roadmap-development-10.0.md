# MediaManager 開發版 10.0 規劃

## 進入 10.0 前：先封住 9.x 搜尋拆分

Development 9.1 已把 YouTube 與 Bilibili 下載工作區、搜尋來源、父子 MOD 及語言資源
拆分，並產生新的 9.1 成品。開始 10.0 前仍須完成：

- 聯合搜尋不得讓第一個來源吃滿全部結果；採每來源有界收集與穩定 round-robin，
  讓所有已啟用來源都有機會回傳結果。
- 明確指定但已停用或不存在的來源必須 fail closed，不得改查 YouTube 或其他網站。
- 將 Development 9.1 提交並讓 CI 通過；由該最終 revision 重建後，再執行
  copied-folder、SHA-256、MOD 接線與來源隔離稽核。
- 以上完成前，9.1 只能視為本機已驗證的 Development 成品，不能視為已公開或可升格
  Stable 的 9.x 成品。

## 10.0 主題：發布門檻強化與低耗用診斷

### P0：發布證據必須綁定實際成品

- `release-info.json` 記錄可重現的來源 revision／指紋、建置識別與工具 schema 版本。
- 候選 evidence 綁定核心版本、來源指紋、`SHA256SUMS.txt` digest、產生時間與工具版本；
  任何欄位不符目前成品即拒絕沿用，不能只接受一組過期布林值。
- 修正式簽署順序：先對建置區 EXE 套用並驗證 Authenticode，再 stage 並產生最終
  SHA-256，最後產生 Ed25519 release manifest；簽署後不得再修改成品。
- 補齊 wheel、`release-info.json` 與 `SHA256SUMS.txt` 的簽章錨點決策及回歸測試，
  避免公開附件只有自我宣告的雜湊。
- 提供單一 release-operator 流程；在該流程及測試完成前，不得依舊文件手動封裝 Stable。

### P1：內建 MOD 與依賴的單一診斷來源

- 建立 typed `BuiltinModDescriptor`／catalog，集中 14 個內建 MOD 的類型、名稱、預設
  狀態、控制路由、選用頁面與依賴；安全權限 allowlist 與 release hash 仍保持獨立，
  再由診斷服務交叉比對。
- 將 FFmpeg、Deno／EJS、whisper-cli、模型與 PATH 檢測收斂為共用唯讀 snapshot，
  並按 YouTube、Bilibili、通用下載、轉檔與轉錄分別回報 readiness。
- 先確保檢查正確，再以檔案大小／修改時間、必要 SHA-256 及 PATH 指紋做有界快取；
  手動重新整理或相關狀態變更才讓快取失效。
- 收斂主視窗三套重複的選用分頁同步流程，避免新增 MOD 時漏接顯示、關閉或生命週期。

### P2：Self Check 介面

- 新增可信核心內的手動、唯讀 Self Check 頁面；它不是可執行外部 provider，也不取得
  額外權限。
- 檢查 catalog、registry、唯一啟用路由、action／tab binding、依賴 snapshot、安全模式、
  發布成品與目前來源是否一致。
- 結果分為通過、警告、阻擋，提供穩定 `remediation_id`、安全導向入口及去識別 JSON
  匯出；不自動啟用 MOD、不安裝工具、不降低 SAFE_MODE。
- 自檢不得連線、啟動 provider／FFmpeg、處理媒體、執行 Pytest 或建立暫存資料。

完成條件：9.x 搜尋來源公平且 fail closed；過期候選證據會被拒絕；正式簽署流程可由
回歸測試證明順序正確；暖快取自檢可在秒級完成、零網路、零 provider 程序、零暫存，
且結果與實際 UI／registry／成品狀態一致。

## 本版不處理

- 批次命名、群組下載與下載後處理移到下一個「下載」大版本。
- 搜尋平行化、取消與更多來源可靠性移到下一個「搜尋」大版本；9.x 只修正公平性與
  來源隔離正確性。
- 第三方 MOD 的 inventory／sign／pack／完整生命週期工具移到 Stable 1.1 準備階段。
- production Ed25519 私鑰與 Authenticode 憑證屬外部發布身分，不能由程式碼偽造。

## 後續區塊式開發規則

- 每個開發大版本只設定一個核心主題，不在同一大版本同時大改下載、搜尋與 MOD 適配。
- 主題內依網站切成可獨立驗收的區塊；YouTube、Bilibili、通用網站與 MEGA 等特殊協定
  使用獨立 MOD、權限、錯誤提示與測試。
- 下載佇列、格式模型、搜尋結果合約與歷史資料等跨網站能力留在核心；登入、網址規則、
  彈幕及網站特有解析留在對應 MOD。
- 區塊未完成不得標記大版本完成，也不得把半成品帶入正式版候選。

建議順序：9.x 搜尋收尾 → 10.0 發布門檻與診斷 → 下載大版本 → 搜尋大版本 →
第三方 MOD 適配。Stable 1.0 仍須先取得 production 簽署身分並通過完整發布門檻。
