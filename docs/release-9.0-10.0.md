# MediaManager 開發版更新紀錄 9.0～10.0

## 9.1

- YouTube 與 Bilibili 改為可驗證的父 MOD／子 MOD：主 MOD 未啟用時不顯示子 MOD，
  停用主 MOD 會同步停用子 MOD並阻止背景殘留狀態。
- YouTube 下載工作區與 Bilibili 下載工作區完全分頁、分 URL 路由、分搜尋交接；錯誤
  網域無法加入佇列，Bilibili 搜尋不再出現在未啟用的 Bilibili 主 MOD 下。
- 內建網站 MOD 加入受 SHA-256 保護的 `group.json` 與四語言 `locales/`；核心語言
  `en`、`ja`、`zh-CN`、`zh-TW` 會同步到工作區、MOD 管理與搜尋子 MOD。
- 新增 `tools.audit_mod_groups`，檢查父子覆蓋、四語言完整性、provider 身分、網路權限
  與搜尋網站家族，禁止跨網域 provider 偽裝成已分離。
- `generic-ytdlp` 僅保留為預設停用的舊 Beta 相容項；新網站必須各自建立主 MOD，
  不得再加入多網域聚合 provider。
- 9.1 使用新的 `Version/Development/9.1` 資料夾，不覆寫 Development 9.0。

### 9.1 驗證結果

- Ruff 全專案檢查通過。
- Pytest：627 項通過、2 項因目前 Windows 帳戶無法建立 symlink 而跳過。
- `tools.audit_mod_groups`：通過，驗證 2 個網站群組與每組 4 個語言檔。
- copied-folder smoke：`--version`、`--verify-only`、`--headless`、凍結後 MOD 載入及
  YouTube Music 播放清單網址解析皆通過。
- `Version/Development/9.1`：58 項 SHA-256 稽核通過；`MediaManager.exe` SHA-256 為
  `3FF76A1E278E0C0C791941CECE16F1A8003CF51D1F5B1BB535513F1778B74393`。
- 發布 preflight 仍因缺少 production Ed25519 發布身分與 Authenticode 簽章而阻擋；
  9.1 僅為 Development／`SAFE_MODE` 成品，不是 Stable 1.0。
- 完整測試跳過、環境限制與正式發布阻擋記錄於
  [`release-9.1-known-issues.md`](release-9.1-known-issues.md)。
