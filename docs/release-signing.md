# 簽章與發行 Gate

目前沒有 Stable build、簽署或發布計畫。本文件只定義未來若重新授權發行時
不得降低的順序與秘密邊界。

## 兩種不同信任

- **Authenticode**：簽署 Windows EXE；必須由有效程式碼簽署憑證產生，並由
  `Get-AuthenticodeSignature` 回報 `Valid`。
- **Ed25519 release manifest**：簽署 final staged set 的檔案 hash 與 release
  metadata。production 私鑰必須保存在 Repository、`.work`、`Version` 與對話外。

兩者不能互相取代。Authenticode 會改變 PE 位元組，所以必須先簽 EXE，再產生
final checksum 與 Ed25519 manifest。

## 秘密處理

只可提交或在工作紀錄中提供非秘密的 key ID 與 raw 32-byte Ed25519 公鑰。
下列內容不得貼入 Codex、Issue、PR、命令列紀錄、Log 或版本檔：

- Ed25519 私鑰或 seed。
- Authenticode 憑證私鑰、PFX、密碼或 PIN。
- 簽署服務 Token、Cookie、session 或 recovery material。

發現疑似外洩時先停止工作，撤銷／輪替，再建立新的可追蹤信任身分。

## 必要順序

1. 使用已授權的乾淨 source-freeze commit。
2. 執行 Stable build-only，取得唯一工作目錄與 `build-receipt.json`。
3. 在外部安全環境簽署該目錄中的 exact EXE。
4. 獨立驗證 Authenticode `Valid`，只回傳非秘密狀態證據。
5. 執行 stage-built；工具必須重驗 channel、release version、source revision、
   receipt、wheel digest 與 EXE。
6. 在 staged set 產生 release metadata、SBOM 與 checksum。
7. 使用外部 production Ed25519 私鑰簽署 final manifest。
8. 執行 `release_preflight`、`audit_versions`、copied-folder smoke 與候選驗證。
9. 另行取得 push／發布／上傳授權。

任何一步失敗都停止；不可使用 self-signed Authenticode、臨時 Ed25519、複製簽章、
手改 `ready` 或放寬 preflight。

## 驗證範例

以下命令只適用於已存在且另行獲准的候選；目前不應執行：

```powershell
Get-AuthenticodeSignature -LiteralPath <work-dir>\MediaManager.exe |
  Select-Object Status, StatusMessage

.\.venv\Scripts\python.exe -m tools.audit_versions --root Version
.\.venv\Scripts\python.exe -m tools.release_preflight `
  --root Version\Stable\<version>
```

簽署命令的私鑰路徑應由 operator 直接在本機安全環境提供，不得寫入此文件、
Repository 設定或自動化輸出。
