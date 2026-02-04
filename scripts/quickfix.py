#!/usr/bin/env python3
import shutil
from pathlib import Path

print("=== Quick Fix ===")

# Clean cache
cache = Path(".cache/auditor")
if cache.exists():
    shutil.rmtree(cache)
    print("✓ Cache cleared")

# Check dependencies
print("\n✓ Run: pip install -r requirements.txt")
print("✓ Run: pytest tests/")
print("✓ Run: python audit.py . --fast")
