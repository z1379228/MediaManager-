# GitHub 自動檢查與合併

`Quality` 工作會在所有目標為 `main` 的 Pull Request 執行兩個 job：

- Windows `Ruff and Pytest`：執行 Ruff、完整 Pytest、文字、MOD、網站、依賴、
  版本文件與可用版本產物稽核。
- Ubuntu `Symlink security tests (Ubuntu)`：執行內建 provider 與媒體庫的
  symbolic-link 安全回歸。

`Enable auto-merge` 只會處理本儲存庫擁有者在同一儲存庫建立、且已離開 Draft
狀態的 Pull Request。它不簽出或執行 PR 內容，並只負責啟用 squash auto-merge。
外部 fork、其他作者與 Draft PR 不會自動合併。

目前 `main` 將 `Ruff and Pytest` 設為必要狀態檢查；
`Symlink security tests (Ubuntu)` 會執行並回報結果，但尚未列入 branch
protection 的必要檢查。流程為：

1. 建立或將 Pull Request 改為 Ready。
2. GitHub 自動啟用 squash auto-merge。
3. Windows 與 Ubuntu runner 分別執行上述檢查。
4. `Ruff and Pytest` 成功後才符合目前的 branch protection；失敗則保持開啟。
5. 若要讓 symbolic-link 安全 job 也阻止合併，必須另將
   `Symlink security tests (Ubuntu)` 加入必要狀態檢查。

雲端測試對每個測試設定 60 秒上限，避免 Windows subprocess 或外部工具異常時
讓必要檢查永久停在 pending；逾時會顯示實際測試名稱並阻止合併。

Pull Request 作者不能批准自己的變更；此流程不產生虛假的 Approve review。
