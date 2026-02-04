#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))


def check_env():
    print("=== Environment ===")
    print(f"Python: {sys.version}")
    print(f"In venv: {sys.prefix != sys.base_prefix}")


def check_structure():
    print("\n=== Structure ===")
    required = ["app/core/audit_orchestrator.py", "app/tools/", "audit.py"]
    for p in required:
        print(f"{'[OK]' if Path(p).exists() else '[X] '} {p}")


def check_discovery():
    print("\n=== File Discovery ===")
    try:
        from app.core.file_discovery import get_project_files

        files = get_project_files(Path())
        print(f"Found {len(files)} files")
        venv_files = [f for f in files if ".venv" in str(f)]
        print(f"{'[X] ' if venv_files else '[OK]'} No .venv files")
    except Exception as e:
        print(f"[X] Error: {e}")


if __name__ == "__main__":
    check_env()
    check_structure()
    check_discovery()
