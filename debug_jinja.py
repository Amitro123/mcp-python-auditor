
import sys
import logging
from pathlib import Path
from datetime import datetime
import json

# Setup path
sys.path.append(str(Path.cwd()))

# Configure logging
logging.basicConfig(level=logging.DEBUG)

from app.core.report_generator_v2 import ReportGeneratorV2

# Mock data based on user's reports
tool_results = {
    "bandit": {
        "tool": "bandit",
        "status": "issues_found",
        "total_issues": 32,
        "issues": [{"severity": "MEDIUM", "message": "Test issue", "filename": "test.py", "line": 10}],
        "metrics": {"_totals": {"loc": 1000}}
    },
    "secrets": {
        "tool": "secrets",
        "status": "clean",
        "total_secrets": 0,
        "secrets": []
    },
    "ruff": {
        "tool": "ruff",
        "status": "clean",
        "total_issues": 0,
        "issues": []
    },
    "cleanup": {
        "tool": "cleanup",
        "status": "cleanup_available",
        "total_size_mb": 10.9,
        "cleanup_targets": {
            "__pycache__": 122,
            ".pytest_cache": 1,
            ".ruff_cache": 1
        },
        "items": ["file1", "file2"]
    },
    "structure": {
        "total_py_files": 67,
        "total_lines": 13900,
        "top_directories": ["app", "docs"],
        "directory_tree": "..."
    },
    "tests": {
        "coverage_percent": 10,
        "has_unit_tests": True,
        "has_integration_tests": True,
        "total_test_files": 53,
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0
    },
    "git_info": {
        "branch": "main",
        "uncommitted_changes": 19,
        "last_commit": "89ba8456 : Merge pull request #2"
    },
    "duration": "65.45s"
}

try:
    print("Initializing generator...")
    generator = ReportGeneratorV2(Path("reports_debug"))
    
    print("Generating report...")
    generator.generate_report(
        report_id="debug_test",
        project_path=str(Path.cwd()),
        score=25,
        tool_results=tool_results,
        timestamp=datetime.now()
    )
    print("SUCCESS!")
    
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    with open("TRACEBACK.txt", "w") as f:
        traceback.print_exc(file=f)
    print(f"FAILED: {e}")
