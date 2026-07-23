# 最新來源更新

目前核心版本：Development `39.0.10`

## 內容

- 補入具官方 URL 與安裝版 extractor 雙重證據的
  `player.bilibili.com`、`w.soundcloud.com` exact host。
- 對新增主機加入窄路徑／查詢契約、bootstrap owner、integrity pin、
  provider manifest、site matrix 與 regression，未知或相似子網域仍 fail closed。
- 將程式中的主機分成可貼入媒體頁、受限 API／CDN、官方說明頁與 localhost
  服務，避免把「程式曾連線」誤寫成可下載媒體支援。
- 可信 UI 顯示 `MediaManager v1.0`，但 CLI、核心相容、MOD 及發布判斷繼續使用
  Development metadata。
- 完成第三方外部 MOD 作者／使用者／核心責任分流與精確快取清理規則。
- 將 GitHub 文件收斂為目前狀態、最新更新與仍有效契約；移除過期 roadmap、
  候選、逐版重複日誌及退役功能文件。這是純文件整理，不增加修正號。

## 最後驗證

39.0.10 程式與文件收斂後取得下列本機證據：

- 完整非 UI 測試：`1317 passed, 7 skipped`。
- Ruff：`364` 個 Python 檔案；文字污染：`471` 個受控文字檔。
- MOD 群組：`7` 組、`4` 語言；網站：`12` sites、`34` features、
  `49` workflows；依賴鎖：`10` 項。
- 版本文件：`4` 個 canonical 來源一致；保留版本：`3` 個通過。
- `21` 份目前 Markdown 的本機連結為 `0` 失效。
- Repository 外 compileall、source-only `--verify-only` 與
  `git diff --check` 通過；`Version/` 為 `0` 個 `.pyc`。
- 清除 `32` 個未追蹤且可再生的 pytest、Ruff 與 Python cache 目錄；未刪除
  `.venv`、Version、UserData 或使用者檔案。

## 發行狀態

39.0.10 已取得 stage、commit 與 source freeze 授權；Testing 1.1 已取得本機
build、未簽署 EXE 與打包授權。Testing 必須維持 `SAFE_MODE`，且本輪不包含
Authenticode、production Ed25519、push 或發布。實際產物狀態與雜湊以
`Version/Testing/1.1` 內的 metadata 為準。
