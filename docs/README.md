# MediaManager 文件入口

這個頁面是儲存庫文件的單一入口。請先依「目前有效文件」判斷現況；舊版發行紀錄
只保存當時事實，不代表目前功能、安裝方式或正式版狀態。

## 目前狀態

- 來源顯示為開發版 16.1，核心相容版本為 16.1.0；最新完整 Development 成品仍是
  `Version/Development/16.0`，且未覆寫 15.0。16.0 的 7/7 封裝 provider smoke 與
  copied-folder 啟動已通過；16.1 可重現基線正在實作且尚未封裝，仍不是 Stable。
- 開發與測試成品仍維持 `SAFE_MODE`；目前沒有可宣告的 Stable 正式版。
- 目前來源最終回歸為 848 passed、2 skipped；兩個略過項目皆為 Windows symlink
  權限限制，不偽裝為通過。
- 目前來源含 31 個內建 MOD、8 個網站父群組與 4 種介面語言。
- 16.0 的離線能力稽核覆蓋 8 個網站父 MOD、5 個通用白名單站點、39 項功能與
  56 個工作流階段；Self Check 可匯入最近一次手動 provider smoke schema 2 JSON。
- 動畫瘋功能包含官方公開目錄、搜尋、封面、明確啟用後的分頁集數導覽、官方播放頁，以及選取單集
  的公開索引／本機媒體保存。官方搜尋或作品頁要求 Cloudflare 瀏覽器驗證時，介面會改為
  引導貼入標準作品／單集網址，不下載網站串流、不處理網站廣告，也不規避驗證、DRM、登入、付費、
  地區或播放器限制。
- `media-ad-trim` 是 `media-convert` 下預設關閉的本機子 MOD，只依手動時間區間
  重新編碼並另存新檔；可預覽第一切點，不覆寫原檔，也不接受網站網址。
- GitHub 的 [`test-v1.0.0`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.0.0)
  是不可覆寫的既有測試附件。開發版 11.1 使用獨立版本資料夾及 Pre-release，
  不能讓文件假稱舊附件已包含後續功能。

## 目前有效文件

- [專案首頁與執行方式](../README.md)
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
- [開發版 12.x 實際更新紀錄](release-12.0-13.0.md)
- [開發版 13.x 實際更新紀錄](release-13.0-14.0.md)
- [開發版 14.x 實際更新紀錄](release-14.0-15.0.md)
- [開發版 15.x 實際更新紀錄](release-15.0-16.0.md)
- [開發版 16.x 實際更新紀錄（規劃中）](release-16.0-17.0.md)
- [測試版 1.0 已發布附件紀錄](release-testing-1.0.md)
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

## 文件更新規則

1. 功能、數量、版本與測試結果只寫入目前文件及所屬大版本區間。
2. 尚未重新封裝的來源變更必須標示「尚未封裝」，不可回填到既有發布附件紀錄。
3. 開發次版本附加在同一大版本區間文件，不新增零散 release 文件。
4. Stable 文件只記錄候選評估；未取得簽署身分、完整驗證與使用者確認前，不宣告正式版。
5. 文件一律使用 UTF-8，提交前檢查合併標記、工具殘留、無效連結與版本事實衝突。
