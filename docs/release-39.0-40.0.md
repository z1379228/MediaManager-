# Development 39.0–40.0 更新紀錄

本文件是目前開發世代的 canonical release 摘要；逐工作包的歷史證據仍由 Git
歷史與不可變版本附件保存。產品顯示名稱 `MediaManager v1.0` 不取代核心、Testing
或 Stable 的三軌版本身分。

## 39.0.0–39.0.8

- 完成本機格式工廠、FFmpeg／ffprobe 能力與輸出驗證、原子提交及失敗回復。
- 完成 localhost-only Gopeed Bridge／P2P Transfer、Direct HTTP 安全邊界及選用
  Speech to Text 相依檢查。
- 固定 Stable `1.0.0`、Testing `1.1.0` 與 Development 的獨立公開身分。
- 加入 receipt-bound build handoff、不可覆寫版本資料夾、本機歷史清理計畫器及
  production Ed25519 公開信任身分；正式私鑰不進入 Repository。

## 39.0.9–39.0.10

- 新增 `player.bilibili.com` 與 `w.soundcloud.com` 的 exact-host、窄路徑／查詢
  驗證及 provider／site-matrix／integrity 一致性回歸。
- 可信桌面改用 channel-neutral `MediaManager v1.0` 顯示；內部相容、MOD 與
  release metadata 仍使用 Development `39.0.10`。
- GitHub 文件收斂為目前狀態、有效契約與本摘要；已結案 roadmap、過期候選與
  退役功能文件由 Git 歷史追查，不覆寫已公開附件。
- 暫存清理保留 `dist/UserData` 及整個 `.work`；`.work` 可能包含 rollback
  backups、build receipts、Git worktrees 與驗證證據，只能經精準人工稽核清除。

## 39.0.11

- YouTube 搜尋新增內容類型、頁面／數量、時長、排序、來源與顯示欄位，並保留
  多來源搜尋的逐 provider 上限及取消、歷史與選取流程。
- 新增只接受已稽核 staged release 的 deterministic 自包含 ZIP 工具；拒絕
  UserData、秘密、link-like、路徑衝突、來源 revision 不一致與覆寫既有附件。
- Testing 公開候選身分升為 `1.2.0`；`MediaManager v1.0` 產品名稱及 Stable
  `1.0.0` 身分不變。
- 候選來源已通過 `90` 項定向回歸、完整 `1364 passed, 7 skipped`、quality
  audit、Repository 外 compileall、版本／MOD／網站／依賴稽核及
  `git diff --check`。
- 本次獲授權 commit 作為 Development `39.0.11` source freeze；build、未簽署
  EXE、Testing staging 與 ZIP 亦已獲授權，但仍必須由工具輸出證明。push、
  簽署與發布未獲授權，不得將 1.1 產物改名為 1.2。

## 39.0.12（工作來源）

- YouTube 專用工作區新增「搜尋相似音樂」入口；只在恰好選取一筆結果且
  YouTube 主 MOD、搜尋 MOD 與相似內容 MOD 均啟用時可執行。
- 相似候選沿用既有 `youtube-similar` 排序及公開 `ytsearch` 管線，固定使用
  music query scope、單次最多顯示 20 筆，並排除原始項目與重複影片；搜尋
  提示不等於 YouTube 官方分類，候選內容仍需由使用者確認。
- 此流程不讀取 Cookie、觀看紀錄或私人推薦 API，不自動下載，也不改變現有
  Testing `1.2.0` 產物。Development `39.0.12` 已被選為 Testing `1.2.1`
  候選來源；source freeze、未簽署 EXE、自包含 ZIP 與 GitHub 上傳已獲授權，
  但仍須由實際工具輸出證明完成。
- 工作來源驗證：完整 repository runner `1388 passed, 7 skipped`；Ruff／文字污染
  quality audit 覆蓋 `366 / 474` 個檔案，Repository 外 compileall 通過。
- 稽核證據：版本文件 `4`、MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖
  `10`；本機保留的 Testing `1.1` 與 `1.2` 共 `2` 個版本均通過 checksum 稽核。

## 39.0.11 Validation Baseline

- 完整 repository runner：`1364 passed, 7 skipped`。
- Quality audit：Ruff `364` 個 Python 檔案、文字污染 `471` 個受控文字檔。
- MOD 群組 `7 / 4`、網站矩陣 `12 / 34 / 49`、依賴鎖 `10`、版本文件 `4`。
- 本機保留版本稽核：`3` 個版本通過。
- source freeze 文件稽核涵蓋 `21` 份 Markdown，本機連結 `0` 失效。
- 精準清除 `32` 個可再生的 pytest、Ruff 與 Python cache 目錄；未刪除
  `.venv`、`Version`、`UserData` 或使用者檔案。
- source freeze 已通過 Repository 外 compileall、source-only `--verify-only`
  與 `git diff --check`；`Version/` 中有 `0` 個 `.pyc`。

## Testing 1.1 Gate

使用者已授權 Development 39.0.10 的 stage、commit、source freeze，以及由同一
乾淨 revision 建立、上傳未簽署 `SAFE_MODE` Testing `1.1.0`。GitHub Release
使用唯一 tag `test-v1.1.0-r2`，精確指向 `09b3a86e00938241d27050088583ebf81d9fb182`；
9 個附件的 GitHub digest 與本機 SHA-256 一致。遠端 metadata 目前誤設為非
prerelease 並被視為 Latest，需另行授權修正；Testing 1.0 與既有 tags 不覆寫。
Authenticode 與 production signed release manifest 仍未成立，因此 Stable Gate
保持阻擋。

## Testing 1.2 Gate

Development `39.0.11` 已於 revision
`fab5cb9333274e54f65a35b2f44a86699f0f349f` source freeze，並由同一 revision
完成 build、建立未簽署 EXE、stage Testing `1.2.0` 與產生自包含 ZIP；
`Version/Testing/1.2/release-info.json` 已記錄相同來源。push、簽署與發布
當時未獲授權，且公開 GitHub API 查核顯示沒有 Testing `1.2.0` Release 或 tag。
此本機候選保留為不可覆寫歷史，Development `39.0.12` 不回寫該目錄。

Testing `1.2.1` 使用新的 patch 目錄 `Version/Testing/1.2.1`，候選來源為
Development `39.0.12`，預定唯一 tag 為 `test-v1.2.1`，預定主要附件為
`MediaManager-Testing-1.2.1.zip` 與
`MediaManager-Testing-1.2.1.zip.sha256`。source freeze、未簽署 EXE、stage、
ZIP、建立 Release 與上傳已獲授權，但狀態仍是
`AUTHORIZED / PENDING / NOT PUBLISHED`；source revision、SHA-256、Release URL
與遠端資產只能在實際完成並驗證後記錄。Testing 維持未簽署 `SAFE_MODE`，
不得宣稱 Stable，也不得覆寫 Testing `1.2.0` 歷史。

## 40.0

沒有獨立 material delta，狀態為 `ABSORBED / NO RELEASE / NO PLAN`。不得為維持
版本號建立空版本；若日後出現可重現缺口，需另建計畫並重新取得相應授權。
