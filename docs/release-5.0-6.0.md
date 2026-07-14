# MediaManager 開發版 5.0 至 6.0 更新紀錄

本文件集中記錄 5.0 基線、5.1～5.9 漸進更新及 6.0 整合結果。5.x 次版本只提供
更新紀錄，不重複保存大型附件。

## 5.0 基線

- 聯合搜尋、格式分析、下載限制、Adapter SDK、SBOM 與 Preview 發布通道完成。
- 正式簽章身分未配置，維持 `SAFE_MODE`。

## 5.1

- 補強搜尋逾時、取消、無效回應與來源不可用分類，避免 UI 狀態殘留。

## 5.2

- YouTube 搜尋加入真實 offset 分頁、最多 50 筆顯示及 200 筆有界結果視窗。
- 增加來源、類型、時長與四語訊號的本機篩選。

## 5.3

- `youtube-history`、`youtube-recovery`、`youtube-similar` 維持獨立可停用 MOD。
- 失效影片可依標題、歌手、語言訊號搜尋替代；候選上限提高到 50。

## 5.4

- 外部 MOD 宣告式 UI schema v2 僅支援 `en`、`ja`、`zh-CN`、`zh-TW`。
- 缺少目前語言時回退 manifest 預設；未知語言與主動內容 fail-closed。

## 5.5

- 下載加入估算容量加 256 MiB 保留空間、批次優先級、恢復及完成通知。

## 5.6

- YouTube、Bilibili、generic provider 加入有界格式及網站品質回歸。
- Bilibili XML／ASS／MKV 彈幕能力維持獨立網站 MOD 邊界。

## 5.7

- 長篇 BGM 使用章節與音訊斷點產生切割草案；確認前不輸出最終分段。

## 5.8

- 多工作區、背景圖片、鍵盤操作、UI 縮放及大型清單低負載刷新完成整合。

## 5.9

- 加入正式版候選評估器；只輸出門檻與阻擋，不自動建立 Stable 產物。

## 6.0

- 搜尋最多顯示 50 筆並支援有界下一頁；來源隔離、去重與錯誤分類完成回歸。
- Search／Download Adapter SDK、四語宣告式 UI 與安全回退完成整合。
- 下載容量、恢復、原子輸出、Bilibili 彈幕及長音訊切割維持模組化邊界。
- 建立 `Version/Development/6.0`，Stable staging 未明確確認時立即拒絕。
- Ruff、531 項測試、copied-folder GUI／headless／verify、8 項依賴鎖及
  6 個網站／11 項能力矩陣通過。
- production Ed25519 與 Authenticode 仍是正式版阻擋。

6.0 後的演進接續記錄於 [`release-6.0-7.0.md`](release-6.0-7.0.md)。
