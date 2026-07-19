# MediaManager 文件入口

這個頁面是儲存庫文件的單一入口。請先依「目前有效文件」判斷現況；舊版發行紀錄
只保存當時事實，不代表目前功能、安裝方式或正式版狀態。

## 目前狀態

- 目前來源版本為開發版 38.0（核心相容版本 38.0.0），已進入本機 source-freeze／Development 候選流程；34.0 source freeze 保持不變，
  35.0～37.0 source-only Exit Gate 已完成，38.0／G38-01 為唯一
  `ACTIVE / P1 FIXES VALIDATED / MANUAL REVALIDATION BLOCKED / SAFE_MODE`。
  歷史 Development 產物只作回退與稽核用途，不覆寫既有內容。
- 開發與測試成品仍維持 `SAFE_MODE`；目前沒有可宣告的 Stable 正式版。
- G37 source-only Exit Gate 的最新完整 pytest 已透過固定 Repository 根目錄及隔離使用者暫存的
  安全入口完成：`1278 passed, 7 skipped`；未廣域收集 `AppData`，測試 basetemp 位於
  Repository 外。G38 無頭 UI／四語精準基線另計 `58 passed, 0 skipped`；焦點指示與
  安全 badge 讀屏名稱兩項 P1 修正後相關 UI 組 `12 passed`，post-fix 完整
  Repository `1279 passed, 7 skipped`。AniGamer targeted suite 為 `60 passed, 1 skipped`，加入
  canonical 單集 URL 回歸後的完整 Repository 為 `1281 passed, 7 skipped`；最新 G38 Shared DoD 的
  Ruff／文字污染 `366 / 571`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、
  保留版本 `5`、compileall、Version `.pyc` 零污染與 diff check 均通過；人工矩陣仍阻擋。
- G36-01 只對 `DiscoveryItemV1`、history、recovery 與 provider failure 的六個列名 result DTO
  接受最多 8 個有界 JSON extra；保留版本欄位、遺失必填、超深／超大內容仍拒絕，writer 不保留 extras。
  capability token claims、Download／Provider capability、plugin manifest 與 UI descriptor 的 unknown field
  仍由 strict regression 拒絕。
- G36-01 最終 Shared DoD：完整 Repository `1255 passed, 7 skipped`；Ruff／文字污染
  `363 / 566`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、
  scoped compileall、Version `.pyc` 零污染與 `git diff --check` 均通過。
- G37-01 已以 `EVIDENCE READY / NO CLAIM / SOURCE ONLY / SAFE_MODE` 完成；strict evidence v1、provider
  exit metadata、UTF-8 有界 redaction、queue restore、原子 self-check 匯出與 WER runbook 已完成。
  最終 G37 targeted `112 passed`，完整 Repository `1278 passed, 7 skipped`；Shared DoD 的
  Ruff／文字污染 `365 / 570`、MOD `8 / 4`、網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、
  保留版本 `5`、scoped compileall、Version `.pyc` 零污染與 diff check 均通過。沒有重現 native crash，
  provider 間歇 exit 1 的 root cause 仍未知；不宣稱已修復。
- G35-02A 新增唯讀、immutable 且有界的外部 MOD dependency graph snapshot、candidate
  overlay 與間接 cycle validator。
- G35-02B 新增共用且有界的跨程序 lifecycle lock、compare-and-set `ENABLE`／`DISABLE`
  journal、鎖內狀態重讀及 fail-closed TrustStore／publisher reconciliation。
- G35-02C 完成序列化 supervisor handle ownership、handshake cleanup failure 的 exact-handle
  接管、短期 capability 即時撤銷、transitive dependency readiness／dependent-safe disable，
  以及 graph 異常時 journal-first 的 runtime containment。
- G35-02D 完成 bounded candidate transaction、fail-closed lifecycle path、dependency-first
  startup／transaction recovery、dependent-first toggle recovery 與補償失敗後的下次啟動收斂；
  最終相關 15 檔 targeted suite `175 passed`，原發現者重審未發現未解 P0／P1。
- G35-02E 已同步 operator／release／roadmap 文件；Ruff／文字污染 `360 / 563`、MOD `8 / 4`、
  網站 `13 / 42 / 56`、依賴鎖 `10`、版本文件 `4`、保留版本 `5`、compileall 與 diff 均通過。
- 34.0 已完成本機 source freeze；35.0～37.0 Exit Gate 證據本身不構成操作授權。使用者已於
  2026-07-19 明確授權將目前 35.0～38.0 核准變更 stage、本機 commit、固定為 Development 38.0
  source freeze，並建立一次 SAFE_MODE 未簽署 Development 38.0 包；push、Testing／Stable、
  簽署與發布仍未授權。
- Development 38.0 已從 freeze revision
  `6534e3f5ebcc3e3c459a34a335e2b176b2cd1107` 建立於 `Version/Development/38.0`；
  runtime policy 6/6、116 筆 checksum 與 copied-folder `38.0 → 32.1 → 38.0` 均通過，
  `rollback=true / source_unchanged=true / process_tree_safe=true`。EXE 為 `NotSigned`；這項
  封裝證據不替代 G38 人工 UI 矩陣，也沒有保存 G40 所需的精確 SAFE_MODE stdout。
- `tools.audit_version_docs` 會離線比對 `core/version.py`、`pyproject.toml` 與目前文件；
  版本分歧時以非零狀態結束。
- 目前來源含 32 個內建 MOD、8 個網站父群組與 4 種介面語言。
- 16.0 的離線能力稽核覆蓋 8 個網站父 MOD、5 個通用白名單站點、39 項功能與
  56 個工作流階段；Self Check 可匯入最近一次手動 provider smoke schema 2 JSON。
- 動畫瘋功能包含官方公開目錄、搜尋、封面、明確啟用後的分頁集數導覽、官方播放頁，以及選取單集
  的公開索引／本機媒體保存。官方搜尋或作品頁要求 Cloudflare 瀏覽器驗證時，介面會改為
  引導貼入標準作品／單集網址，不下載網站串流、不處理網站廣告，也不規避驗證、DRM、登入、付費、
  地區或播放器限制。
- `media-ad-trim` 是 `media-convert` 下預設關閉的本機子 MOD，只依手動時間區間
  重新編碼並另存新檔；可預覽第一切點，不覆寫原檔，也不接受網站網址。
- GitHub 的 [`test-v1.1.0`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.1.0)
  是不可覆寫的既有測試附件。開發版 11.1 使用獨立版本資料夾及 Pre-release，
  不能讓文件假稱舊附件已包含後續功能。

## 目前有效文件

- [專案首頁與執行方式](../README.md)
- [Development 34.0～40.0 唯一版本更新計畫與優先度](roadmap-development-34.0-40.0.md)
- [Development 34.0 目前執行證據與阻擋](roadmap-development-34.0.md)
- [Development 35.0～36.0 更新紀錄](release-35.0-36.0.md)
- [Development 37.0～38.0 更新紀錄](release-37.0-38.0.md)
- [原生崩潰去識別證據 Runbook](native-crash-evidence-runbook.md)
- [Development 35→34 設定回復 Runbook](settings-pre35-rollback.md)
- [網站父 MOD、子 MOD 與四語言契約](site-mod-group-format.md)
- [動畫瘋整合範圍與限制](ani-gamer-feasibility.md)
- [第三方 MOD 開發流程](mod-developer-guide.md)
- [Search／Download Adapter SDK](adapter-sdk.md)
- [下載工作契約](downloads-v1.md)
- [MOD 套件格式](mod-package-v1.md)
- [執行環境與依賴檢查](dependency-health.md)
- [MEGA MOD 能力邊界](mega-feasibility.md)
- [Direct HTTP MOD 能力邊界](direct-http-boundary.md)
- [Facebook／Instagram 能力邊界](meta-social-feasibility.md)
- [X／Twitter 能力邊界](x-twitter-feasibility.md)
- [Threads 能力邊界](threads-feasibility.md)
- [同類軟體參考與取捨](comparable-software-options.md)
- [GitHub 自動檢查與合併](github-auto-merge.md)
- [正式簽章流程](release-signing.md)
- [版本資料夾與三軌發布政策](version-layout.md)
- [開發版 33.0～34.0 更新紀錄（34.0 尚未封裝）](release-33.0-34.0.md)
- [開發版 12.x 實際更新紀錄](release-12.0-13.0.md)
- [開發版 13.x 實際更新紀錄](release-13.0-14.0.md)
- [開發版 14.x 實際更新紀錄](release-14.0-15.0.md)
- [開發版 15.x 實際更新紀錄](release-15.0-16.0.md)
- [開發版 16.x 實際更新紀錄（規劃中）](release-16.0-17.0.md)
- [測試版 1.1 發布附件紀錄](release-testing-1.1.md)
- [正式版 1.0 候選狀態](release-stable-1.0-candidate.md)

## 歷史發行紀錄

下列文件是唯讀歷史，用來追查當時變更與雜湊。它們不是目前安裝指引，也不應改寫
成新版本內容：

- [開發版 3.0～4.0](release-3.0-4.0.md)
- [開發版 4.0～5.0](release-4.0-5.0.md)
- [開發版 5.0～6.0](release-5.0-6.0.md)
- [開發版 6.0～7.0](release-6.0-7.0.md)
- [開發版 7.0～8.0](release-7.0-8.0.md)
- [開發版 8.0～9.0](release-8.0-9.0.md)
- [開發版 9.0～10.0](release-9.0-10.0.md)
- [開發版 10.0～11.0](release-10.0-11.0.md)
- [開發版 11.0～12.0](release-11.0-12.0.md)

`release-1.x.md`、`release-2.x.md` 及舊 roadmap 同樣屬於歷史資料。GitHub Releases
上已公開的 EXE、`SHA256SUMS.txt`、`release-info.json` 與其對應版本文件不得刪除或
覆寫；日常介面與 README 只連到本入口，避免舊內容被誤認為最新版本。

## 後續候選方案

下列 roadmap 是尚未全部完成的候選設計，不是目前功能承諾：

- [多網站下載與彈幕](multisite-danmaku-roadmap.md)
- [YouTube 自動切割](youtube-auto-split-roadmap.md)
- [YouTube 搜尋、歷史、替代與相似內容](youtube-discovery-roadmap.md)
- [選用 YouTube 影片預覽](youtube-player-roadmap.md)
- [正式版 1.1 第三方 MOD 目標](roadmap-stable-1.1.md)
- [開發版 15.0 網站工作流可靠性計畫](roadmap-development-15.0.md)
- [開發版 16.0 網域搜尋、MOD 適配與下載可靠性計畫](roadmap-development-16.0.md)
- [開發版 17.0 可重現發行、分站可靠性與第三方 MOD 計畫](roadmap-development-17.0.md)
- [開發版 28.0～29.0 更新紀錄](release-28.0-29.0.md)
- [開發版 29.0 可重現性、Self Check 與 MOD 維護計畫](roadmap-development-29.0.md)

## 文件更新規則

1. 功能、數量、版本與測試結果只寫入目前文件及所屬大版本區間。
2. 尚未重新封裝的來源變更必須標示「尚未封裝」，不可回填到既有發布附件紀錄。
3. 開發次版本附加在同一大版本區間文件，不新增零散 release 文件。
4. Stable 文件只記錄候選評估；未取得簽署身分、完整驗證與使用者確認前，不宣告正式版。
5. 文件一律使用 UTF-8，提交前檢查合併標記、工具殘留、無效連結與版本事實衝突。
