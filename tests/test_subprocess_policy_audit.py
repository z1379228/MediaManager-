from __future__ import annotations

from pathlib import Path

from tools.subprocess_policy_audit import audit_subprocess_window_policy


def test_audit_rejects_runtime_subprocess_without_hidden_windows_policy(
    tmp_path: Path,
) -> None:
    source = tmp_path / "core" / "worker.py"
    source.parent.mkdir()
    source.write_text(
        "import subprocess\nsubprocess.run(['helper'])\n",
        encoding="utf-8",
    )

    issues = audit_subprocess_window_policy(tmp_path)

    assert tuple(issue.render() for issue in issues) == (
        "VISIBLE_SUBPROCESS_RISK core/worker.py:2 subprocess.run",
    )


def test_audit_accepts_direct_and_module_level_hidden_windows_policies(
    tmp_path: Path,
) -> None:
    core = tmp_path / "core"
    core.mkdir()
    (core / "direct.py").write_text(
        """import os
import subprocess
subprocess.run(
    ['helper'],
    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
)
""",
        encoding="utf-8",
    )
    (core / "constant.py").write_text(
        """import os
import subprocess
SUBPROCESS_CREATION_FLAGS = (
    subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
)
subprocess.Popen(['helper'], creationflags=SUBPROCESS_CREATION_FLAGS)
""",
        encoding="utf-8",
    )

    assert audit_subprocess_window_policy(tmp_path) == ()


def test_repository_runtime_subprocesses_enforce_hidden_windows_policy() -> None:
    root = Path(__file__).resolve().parents[1]

    assert audit_subprocess_window_policy(root) == ()
