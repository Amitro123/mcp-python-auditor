from app.tools.tests_tool import TestsTool
from app.tools.secrets_tool import SecretsTool
import pytest
from unittest.mock import patch
from pathlib import Path
import json
import sys
import os

@pytest.fixture
def mock_subprocess():
    with patch("subprocess.run") as mock:
        yield mock

def test_tests_tool_coverage_parsing(mock_subprocess):
    tool = TestsTool()
    path = Path("/tmp/project")
    output = "TOTAL   30   5   83%"
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = output
    mock_subprocess.return_value.stderr = ""
    with patch.dict(os.environ, {'PYTEST_CURRENT_TEST': ''}, clear=False):
        with patch.object(TestsTool, '_find_test_files', return_value=[Path("test.py")]):
            percent, warning, table = tool._get_coverage(path, Path(sys.executable))
            assert percent == 83
