#!/usr/bin/env python3
"""
Test runner script for the MCP Python Auditor.
Runs different test suites based on command line arguments.
"""
import sys
import subprocess
from pathlib import Path


def run_tests(test_type="all"):
    """Run tests based on type."""
    
    test_commands = {
        "unit": ["pytest", "tests/unit", "-v"],
        "integration": ["pytest", "tests/integration", "-v"],
        "e2e": ["pytest", "tests/e2e", "-v"],
        "tools": ["pytest", "tests/tools", "-v"],
        "mcp": ["pytest", "tests/mcp", "-v"],
        "all": ["pytest", "tests/", "-v"],
        "coverage": ["pytest", "tests/", "--cov=.", "--cov-report=term-missing", "--cov-report=html"],
        "quick": ["pytest", "tests/unit", "tests/tools", "-v", "-x"],  # Stop on first failure
    }
    
    if test_type not in test_commands:
        print(f"❌ Unknown test type: {test_type}")
        print(f"Available types: {', '.join(test_commands.keys())}")
        return 1
    
    print(f"🧪 Running {test_type} tests...\n")
    
    cmd = test_commands[test_type]
    result = subprocess.run(cmd)
    
    return result.returncode


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        test_type = "all"
    
    print("=" * 60)
    print("  MCP Python Auditor - Test Suite")
    print("=" * 60)
    print()
    
    exit_code = run_tests(test_type)
    
    print()
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed.")
    
    print()
    print("Test categories:")
    print("  - unit         : Unit tests (scoring, dependencies)")
    print("  - integration  : Integration tests (tool interactions)")
    print("  - e2e          : End-to-end workflow tests")
    print("  - tools        : Individual tool tests")
    print("  - mcp          : MCP server tests")
    print("  - coverage     : All tests with coverage report")
    print("  - quick        : Fast unit + tools tests")
    print("  - all          : All tests (default)")
    print()
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
