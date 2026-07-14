# MediaManager 3.5.0

3.5 新增離線站點品質稽核，檢查六個通用網站家族的唯一 ID、主機清單與支援
狀態，以及 Bilibili 公開影片、分 P、番劇契約、字幕、XML／ASS／MKV 彈幕能力。
稽核同時要求明列 Cookie、地區、DRM 與付費限制，不以擷取器可用性取代授權。

```powershell
.\.venv\Scripts\python.exe -m tools.site_quality_audit --root .
```

## 驗證結果

- Ruff 與完整測試通過：`468 passed, 2 skipped`。
- 離線品質稽核通過 6 個網站家族與 5 項 Bilibili 能力。
- 1.0～3.5 共 24 個版本、所有 wheel 與 SHA-256 稽核通過。
- 3.5 copied-folder 的版本、Portable verify、headless 與 GUI 啟動通過。
- 一次性 Ed25519 演練驗證 36 個檔案、偵測竄改且不保留金鑰。

本版本仍是 `SAFE_MODE` 開發版；正式發布仍需要外部生產 Ed25519 身分與
Windows Authenticode 憑證，不降低既有 preflight 條件。
