"""Adapter shim for metaclean to integrate with stunning-octo-funicular.

Exports `adapter` object implementing run(args) -> int. Dry-run by default.
"""
from pathlib import Path
import subprocess
from typing import List

REPO_ROOT = Path(__file__).resolve().parent


class MetaCleanAdapter:
    name = "metaclean"
    description = "Adapter for metaclean repository"

    def run(self, args: List[str]) -> int:
        if "--exec" in args:
            if (REPO_ROOT / "tests").exists() or (REPO_ROOT / "pyproject.toml").exists():
                cmd = ["/usr/bin/env", "bash", "-lc", "echo Running metaclean tests; pytest -q || true"]
            else:
                cmd = ["/usr/bin/env", "bash", "-lc", "ls -la"]
            print(f"Running adapter command in {REPO_ROOT}: {' '.join(cmd)}")
            return subprocess.run(cmd, cwd=str(REPO_ROOT)).returncode
        else:
            print(f"[dry-run] would run metaclean adapter against {REPO_ROOT}")
            print("Use --exec to execute a safe example command")
            return 0


adapter = MetaCleanAdapter()
