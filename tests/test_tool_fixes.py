from app.tools.tests_tool import TestsTool
from app.tools.secrets_tool import SecretsTool
import pytest
from unittest.mock import patch
from pathlib import Path
import json
import sys
import os
import textwrap

@pytest.fixture
def mock_subprocess():
    with patch("subprocess.run") as mock:
        yield mock

def test_tests_tool_coverage_parsing(mock_subprocess):
    tool = TestsTool()
    path = Path("/tmp/project")
    output = textwrap.dedent("""
    test_file.py . [100%]
    TOTAL   30   5   83%
    == 1 passed in 0.1s ==
    """).strip()

    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = output
    mock_subprocess.return_value.stderr = ""
    # Clear PYTEST_CURRENT_TEST to ensure execution proceeds
    with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': ''}, clear=False):
        with patch.object(TestsTool, '_find_test_files', return_value=[Path("test.py")]):
            results = tool._run_tests_and_coverage(path, Path(sys.executable))
            assert results["coverage_percent"] == 83
            assert results["tests_passed"] == 1
