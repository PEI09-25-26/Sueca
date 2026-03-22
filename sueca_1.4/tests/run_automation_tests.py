"""Run the Sueca 1.4 automated test suite with one command."""

import unittest
from pathlib import Path
import sys
import os


def _maybe_reexec_with_target_python() -> None:
    """Re-run this script with a chosen interpreter when SUECA_TEST_PYTHON is set."""
    target = os.getenv("SUECA_TEST_PYTHON", "").strip()
    if not target:
        return

    target_path = Path(target).expanduser().resolve()
    current_path = Path(sys.executable).expanduser().resolve()
    if not target_path.exists():
        print(f"[automation] SUECA_TEST_PYTHON does not exist: {target_path}")
        return
    if target_path == current_path:
        return

    os.execv(str(target_path), [str(target_path), __file__, *sys.argv[1:]])


def main() -> int:
    _maybe_reexec_with_target_python()
    print(f"[automation] Using Python: {sys.executable}")
    root = Path(__file__).resolve().parent
    suite = unittest.defaultTestLoader.discover(start_dir=str(root / "tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
