"""
Verify all audit tools are properly installed.
Run this before auditing to ensure accurate results.
"""
import subprocess
import sys

tools = {
    "bandit": ("Security scanning", [sys.executable, "-m", "bandit", "--version"]),
    "detect-secrets": ("Secret detection", ["detect-secrets", "--version"]),
    "vulture": ("Dead code detection", [sys.executable, "-m", "vulture", "--version"]),
    "radon": ("Complexity analysis", [sys.executable, "-m", "radon", "--version"]),
    "ruff": ("Fast Python linter", [sys.executable, "-m", "ruff", "--version"]),
    "pip-audit": ("Dependency vulnerability check", ["pip-audit", "--version"]),
    "pytest": ("Test runner", [sys.executable, "-m", "pytest", "--version"]),
}

print("🔍 Verifying Audit Tools Installation\n")
print("=" * 50)

missing = []
installed = []

for tool, (description, cmd) in tools.items():
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=5,
            stdin=subprocess.DEVNULL
        )
        if result.returncode == 0:
            version = result.stdout.decode().strip().split('\n')[0]
            print(f"✅ {tool:20} - {description}")
            print(f"   Version: {version}")
            installed.append(tool)
        else:
            print(f"❌ {tool:20} - {description}")
            print(f"   ERROR: {result.stderr.decode().strip()[:80]}")
            missing.append(tool)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print(f"❌ {tool:20} - NOT INSTALLED")
        missing.append(tool)
    print()

print("=" * 50)
print(f"\n📊 Summary:")
print(f"   ✅ Installed: {len(installed)}/{len(tools)}")
print(f"   ❌ Missing:   {len(missing)}/{len(tools)}")

if missing:
    print(f"\n⚠️  Install missing tools with:")
    print(f"   pip install {' '.join(missing)}")
    sys.exit(1)
else:
    print(f"\n🎉 All tools are properly installed!")
    sys.exit(0)
