# GitHub 自動檢查與合併

`Quality` 工作會在所有目標為 `main` 的 Pull Request 執行 Ruff 與完整 Pytest。

`Enable auto-merge` 只會處理本儲存庫擁有者在同一儲存庫建立、且已離開 Draft
狀態的 Pull Request。它不簽出或執行 PR 內容，並只負責啟用 squash auto-merge。
外部 fork、其他作者與 Draft PR 不會自動合併。

`main` 必須將 `Ruff and Pytest` 設為必要狀態檢查。設定完成後的流程為：

1. 建立或將 Pull Request 改為 Ready。
2. GitHub 自動啟用 squash auto-merge。
3. Windows runner 安裝專案、執行 Ruff 與 Pytest。
4. 必要檢查成功後才合併，失敗則保持開啟。

Pull Request 作者不能批准自己的變更；此流程不產生虛假的 Approve review。
