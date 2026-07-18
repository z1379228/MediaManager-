# 35→34 設定回復 Runbook

本程序只用於 `SettingsService` 在第一次 schema 1 write 前保存的未版本化 legacy snapshot。
檔名為歷史相容而保留 `settings.pre-35.<sha256>.json`，但 Development 34 已會建立它，
因此它代表 legacy／pre-schema1 bytes，不保證是緊鄰 Development 35 的時間點。工具不保證
34 能讀寫 35 的 future schema，也不會將 35 設定原檔直接交給舊版覆寫。

## 前置條件

1. 完全關閉 MediaManager，避免執行中程序保留與磁碟不一致的 runtime 狀態。套用工具
   仍會取得與正常設定 writer 相同的跨程序排他鎖；關閉程式不是取代該鎖的安全假設。
2. 確認設定檔與 `backups` 位於同一個 Settings 目錄；不要搬移、重新命名或編輯備份。
3. 一般安裝的設定路徑是
   `%APPDATA%\MediaManager\Settings\settings.json`；portable 模式則明確指定該副本的
   `UserData\Settings\settings.json`。工具不會隱式選擇使用者路徑。

## 1. 必做 dry-run

```powershell
$settings = Join-Path $env:APPDATA "MediaManager\Settings\settings.json"
.\.venv\Scripts\python.exe -m tools.settings_rollback --settings $settings
```

成功輸出為 `status=DRY_RUN`，並只列檔名、大小及 SHA-256，不列設定內容或完整個人路徑。
工具會驗證檔名雜湊、64 KiB 上限、regular-file／symlink／junction 邊界、legacy JSON object
與已知欄位型別。找到多份備份時會拒絕猜測；人工確認後以
`--backup <Settings\backups\完整檔名>` 明確選擇。

## 2. 明確套用

將上一個 dry-run 的 `current_sha256` 原樣帶入：

```powershell
$currentSha256 = "<dry-run 的 current_sha256>"
.\.venv\Scripts\python.exe -m tools.settings_rollback `
  --settings $settings `
  --apply `
  --expected-current-sha256 $currentSha256
```

套用時，工具會先取得與 `SettingsService.patch()` 共用的有界跨程序鎖，並在鎖內重新
規劃及核對 dry-run SHA。接著以不可覆寫的唯一檔名保存目前原始 bytes：
`settings.before-pre35-restore.<sha256>.<attempt>.json`，再以同目錄暫存檔原子替換
`settings.json`。目前設定或來源備份在任何檢查點改變時都會 `BLOCKED`，不執行替換。

## 失敗與回復

- `BLOCKED` 不代表已回復；先依錯誤修正路徑、雜湊或多備份歧義，再重新 dry-run。
- 若已輸出 `APPLIED`，保留輸出的 `current_backup_name`。它是套用前設定的 exact owned
  copy，不會被本工具刪除或覆寫。
- 回復結果不符合預期時，保持程式關閉並保留 `settings.json`、legacy 備份及 owned copy；
  不以 34 writer 改寫 35 格式，也不手動複製覆蓋。先由支援 35 schema 的版本或經審核的
  原子程序使用 owned copy 復原。

本工具不刪除設定、備份或 UserData，也不建立版本產物。正式操作前後仍需保存 G35
設定 migration／rollback 回歸與 copied-folder 證據。
