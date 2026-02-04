#!/usr/bin/env python3
import sys
from pathlib import Path


def check_env():
    print("=== Environment ===")
    print(f"Python: {sys.version}")
    print(f"In venv: {sys.prefix != sys.base_prefix}")


def check_structure():
    print("\n=== Structure ===")
    required = ["app/core/audit_orchestrator.py", "app/tools/", "audit.py"]
    for p in required:
        print(f"{'✓' if Path(p).exists() else '✗'} {p}")


def check_discovery():
    print("\n=== File Discovery ===")
    try:
        from app.core.file_discovery import FileDiscovery

        files = FileDiscovery().discover_python_files(Path())
        print(f"Found {len(files)} files")
        venv_files = [f for f in files if ".venv" in str(f)]
        print(f"{'✗' if venv_files else '✓'} No .venv files")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    check_env()
    check_structure()
    check_discovery()
