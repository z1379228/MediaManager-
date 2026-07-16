# 開發版 16.0～17.0 實際更新紀錄

狀態：16.1 Development 附件已建立；本文件只記錄已完成成果；
其餘預定範圍與驗收條件見
[`roadmap-development-17.0.md`](roadmap-development-17.0.md)。

## 16.1（可重現來源與建置基線）

- 來源版本升為開發版 `16.1`、核心相容版本 `16.1.0`；建立新的
  `Version/Development/16.1`，既有 16.0 保持唯讀。
- 開發工作從受保護的 `main` 分離至 `codex/development-17`，保留先前所有未提交來源，
  不使用 reset 或覆寫歷史版本。
- `tools.build_version` 在打包前檢查 Git 工作區；有已修改或未追蹤來源時直接拒絕，
  防止 `source_revision` 指向舊提交而成品實際包含其他程式碼。
- PyInstaller、wheel 或 stage 任一階段失敗時，自動重試清除該次
  `.work/<track>/<version>-attempt-*`；不會刪除其他 attempt、Version 成品或使用者資料。
  若 Windows 程序鎖定仍無法刪除，保留原始建置例外並附加重啟後清理提示；
  `--keep-work` 仍可明確保留失敗現場。
- Ruff 全專案、Git 空白、依賴、8 組父 MOD／4 語言、13 網站／39 功能／56 工作流、
  501 檔文字污染及 current + previous 版本稽核通過。
- 完整 offscreen 回歸為 `848 passed, 2 skipped`；略過項目仍是目前 Windows 帳號
  無法建立檔案與目錄 symlink，將由 16.2 的 symlink-capable CI 補足。
- 網域／子網域靜態交叉掃描補上 Direct HTTP 對 `threads.com` 與 `mega.io` 的網站所有權
  排除；Threads 的 `threads.com`／舊 `threads.net`、MEGA 的 `mega.io`／`mega.nz`
  仍各自回到官方父 MOD，106 項路由、官方工具與完整性回歸通過。

- 16.1 `release-info.json` 綁定 revision `33880ca82c0875f09715edf9e86c8b7a1278cafd`，
  source fingerprint 為 `a809c39116b03f1758642aa7c0d531b271fd6673a1dc55871bf0a11f1419d234`。
  EXE SHA-256 為 `1a4a232d096166dfb1f4a70a2fe51e6b07e42efe2b54f6ab45e570d9db0215d3`，
  wheel SHA-256 為 `52e8429ace9d3dd73d5254ae0f86cbf7f7caccced6ee82ebcf33b167830521ee`。
- 隱藏 copied-folder smoke 的 `--version`、`--portable --verify-only`、
  `--portable --headless` 均在 30 秒內以 exit code 0 結束；正式 preflight 僅因
  production Ed25519／Authenticode 未提供而維持 `ready: false`。

後續每完成一個次版本，才在本文件新增對應分節、實際變更、測試數量、已知限制與
是否建立附件。17.0 完成時再新增 `## 17.0`，並記錄完整 Development 成品、provider
smoke、copied-folder 啟動、簽署演練、release-info 與 SHA-256 結果。

本文件不得回填未完成能力，不得把 Development 宣稱為 Testing 或 Stable，也不得修改
[`release-15.0-16.0.md`](release-15.0-16.0.md) 已封存的 16.0 歷史內容。
