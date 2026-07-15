# MediaManager 文件入口

這個頁面是儲存庫文件的單一入口。請先依「目前有效文件」判斷現況；舊版發行紀錄
只保存當時事實，不代表目前功能、安裝方式或正式版狀態。

## 目前狀態

- 來源顯示為開發版 11.1，核心相容版本為 11.1.0；本次封裝明確標為 11.0 系列
  「測試檔案」，不是 Stable。
- 開發與測試成品仍維持 `SAFE_MODE`；目前沒有可宣告的 Stable 正式版。
- 目前來源含 19 個內建 MOD、5 個網站父群組與 4 種介面語言。
- 動畫瘋功能限於官方公開目錄、搜尋、封面、分頁集數導覽及官方播放頁；不下載
  串流、不處理廣告，也不規避登入、地區或播放器限制。
- GitHub 的 [`test-v1.0.0`](https://github.com/z1379228/MediaManager-/releases/tag/test-v1.0.0)
  是不可覆寫的既有測試附件。開發版 11.1 使用新的版本資料夾及 Pre-release，
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
- [Facebook／Instagram 能力邊界](meta-social-feasibility.md)
- [Threads 能力邊界](threads-feasibility.md)
- [同類軟體參考與取捨](comparable-software-options.md)
- [GitHub 自動檢查與合併](github-auto-merge.md)
- [正式簽章流程](release-signing.md)
- [版本資料夾與三軌發布政策](version-layout.md)
- [開發版 11.x 實際更新紀錄](release-11.0-12.0.md)
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

## 文件更新規則

1. 功能、數量、版本與測試結果只寫入目前文件及所屬大版本區間。
2. 尚未重新封裝的來源變更必須標示「尚未封裝」，不可回填到既有發布附件紀錄。
3. 開發次版本附加在同一大版本區間文件，不新增零散 release 文件。
4. Stable 文件只記錄候選評估；未取得簽署身分、完整驗證與使用者確認前，不宣告正式版。
5. 文件一律使用 UTF-8，提交前檢查合併標記、工具殘留、無效連結與版本事實衝突。
