# MediaManager 4.3 MOD 適配工具

狀態：來源里程碑完成。次版本只提供中文更新說明，不重建或覆寫 `v4.0.0`
大型附件。

## 已完成

- 新增 Search v2／Download v2 Adapter SDK，可建立最小離線範例。
- `adapter.json` 明確宣告核心版本範圍、能力、最小權限、外部工具與程式依賴。
- 離線驗證器檢查 schema、ID、入口路徑、檔案大小、symlink、權限與 capability
  provider ID，不執行 adapter 程式碼。
- CLI 可輸出人類可讀結果或 JSON 相容報告，供 CI 與發布前檢查。
- 搜尋與下載權限分離；Cookie、帳密、任意檔案、shell 與瀏覽器控制不在允許
  集合內。
- 正式安裝仍須封裝為 schema v2 MOD，通過檔案清單、Ed25519 簽章、發布者
  Trust Store 與使用者啟用流程；SDK PASS 不代表受信任。
- 既有 subprocess runtime 的總逾時、閒置逾時、取消、程序樹終止、stdout／
  stderr 大小限制與單一 MOD 故障隔離保持有效。

## 使用入口

詳見 `docs/adapter-sdk.md`：

```powershell
.\.venv\Scripts\python.exe -m tools.adapter_sdk create search example.search .\example-search
.\.venv\Scripts\python.exe -m tools.adapter_sdk validate .\example-search --json
```

## 驗證基線

- Ruff 通過。
- 完整 Pytest：513 passed、2 個 Windows symlink 能力測試明確 skipped。
