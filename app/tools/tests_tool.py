"""Tests analysis tool - Coverage and test organization."""

import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


class TestsTool(BaseTool):
    """Analyze test coverage and organization."""

    @property
    def description(self) -> str:
        return "Analyzes test coverage, test organization, and test types (unit/integration/e2e)"

    @property
    def cache_patterns(self) -> list[str]:
        """Tests depend on test files and pytest configuration."""
        return ["tests/**/*.py", "test/**/*.py", "**/*_test.py", "pytest.ini", "pyproject.toml", "setup.cfg"]

    def analyze(self, project_path: Path) -> dict[str, Any]:
        """Analyze project tests.

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary with test analysis results

        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}

        try:
            # Find test directories and files
            test_files = self._find_test_files(project_path)

            # Check for different test types
            has_unit = self._has_test_type(test_files, "unit")
            has_integration = self._has_test_type(test_files, "integration")
            has_e2e = self._has_test_type(test_files, "e2e")

            # Detect virtual environment
            venv_python = self._detect_venv_python(project_path)

            # Run tests and coverage
            test_results = self._run_tests_and_coverage(project_path, venv_python)

            # Collect test names
            test_list = self._collect_test_names(project_path, venv_python)

            result = {
                "test_files": [str(f.relative_to(project_path)) for f in test_files],
                "total_test_files": len(test_files),
                "has_unit_tests": has_unit,
                "has_integration_tests": has_integration,
                "has_e2e_tests": has_e2e,
                "coverage_percent": test_results["coverage_percent"],
                "coverage_report": test_results["coverage_report"],
                "tests_passed": test_results["tests_passed"],
                "tests_failed": test_results["tests_failed"],
                "tests_skipped": test_results["tests_skipped"],
                "test_list": test_list,  # List of test names
            }

            # Add warning if present
            if test_results.get("warning"):
                result["warning"] = test_results["warning"]

            return result
        except Exception as e:
            logger.exception(f"Tests analysis failed: {e}")
            return {"error": str(e)}

    def _find_test_files(self, path: Path) -> list[Path]:
        """Find all test files (excluding __init__.py and conftest.py)."""
        test_files = []

        # Look for test_*.py and *_test.py files
        for pattern in ["test_*.py", "*_test.py"]:
            for file in path.rglob(pattern):
                # Exclude non-test files
                if file.name not in ["__init__.py", "conftest.py"]:
                    test_files.append(file)

        # Remove duplicates
        return list(set(test_files))

    def _has_test_type(self, test_files: list[Path], test_type: str) -> bool:
        """Check if project has specific test type.

        With fallback: If no subdirectories for unit/integration/e2e exist,
        classify all root tests/ files as unit tests.
        """
        # First check if any files match the type in their path
        matching_files = [f for f in test_files if test_type in str(f).lower()]

        if matching_files:
            return True

        # Fallback for flat structure: if checking for 'unit' and NO type-specific
        # subdirectories exist, treat root tests/ as unit tests
        if test_type == "unit":
            has_type_dirs = any(subtype in str(f).lower() for f in test_files for subtype in ["unit", "integration", "e2e"])

            if not has_type_dirs and test_files:
                # Flat structure detected - classify as unit tests
                return True

        return False

    def _detect_venv_python(self, project_path: Path) -> Path:
        """Detect virtual environment Python interpreter.

        Checks for venv in project directory and parent directory.
        Falls back to current interpreter if no venv found.
        """
        # Check both project directory and parent directory
        search_paths = [project_path, project_path.parent]

        venv_dirs = [".venv", "venv", "env"]

        for base_path in search_paths:
            for venv_name in venv_dirs:
                venv_path = base_path / venv_name
                if not venv_path.exists():
                    continue

                # Check OS-specific Python executable location
                if sys.platform == "win32":
                    python_exe = venv_path / "Scripts" / "python.exe"
                else:
                    python_exe = venv_path / "bin" / "python"

                if python_exe.exists():
                    logger.info(f"Found venv Python: {python_exe}")
                    return python_exe

        # Fallback to current interpreter
        logger.debug("No virtual environment found, using current interpreter")
        return Path(sys.executable)

    def _collect_test_names(self, project_path: Path, venv_python: Path) -> list[str]:
        """Collect all test names using pytest --collect-only.

        Returns:
            List of test IDs (e.g., 'tests/test_api.py::test_root')

        """
        try:
            python_cmd = str(venv_python)
            cmd = [
                python_cmd,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "--color=no",
                "--ignore=node_modules",
                "--ignore=venv",
                "--ignore=.venv",
                "--ignore=dist",
                "--ignore=build",
                "--ignore=.git",
                "--ignore=frontend",
                "--ignore=playwright-report",
                "--ignore=test-results",
            ]

            logger.info(f"Collecting tests with command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # Increased from 30s to handle larger test suites (140+ tests)
                cwd=project_path,
                errors="replace",
            )

            logger.debug(f"pytest collect output:\n{result.stdout}")

            # Parse test IDs from tree structure
            # Format: <Package tests> / <Package e2e> / <Module test_file.py> / <Function test_name>
            test_list = []
            current_path = []  # Track Package hierarchy
            current_module = None

            for line in result.stdout.splitlines():
                line = line.strip()

                # Track Package hierarchy for path building
                if "<Package " in line and ">" in line:
                    pkg_name = line.split("<Package ")[1].split(">")[0]
                    # Determine nesting level by indentation
                    indent = len(line) - len(line.lstrip())
                    # Adjust path based on indentation (2 spaces per level)
                    level = indent // 2
                    current_path = current_path[:level]
                    current_path.append(pkg_name)

                # Extract module name with full path
                elif "<Module " in line and ".py>" in line:
                    module_name = line.split("<Module ")[1].split(">")[0]
                    # Build full module path from packages + module
                    current_module = "/".join([*current_path, module_name])

                # Extract test functions/coroutines
                elif current_module and ("<Function " in line or "<Coroutine " in line):
                    test_name = line.split("<Function ")[1].split(">")[0] if "<Function " in line else line.split("<Coroutine ")[1].split(">")[0]

                    # Build full test ID: tests/e2e/test_audit_workflows.py::test_complete
                    test_id = f"{current_module}::{test_name}"
                    test_list.append(test_id)

            logger.info(f"Collected {len(test_list)} tests")
            return test_list

        except Exception as e:
            logger.warning(f"Failed to collect test names: {e}")
            return []

    def _build_pytest_command(self, project_path: Path, venv_python: Path) -> tuple[list[str], Path]:
        """Build the pytest command with coverage arguments.

        Returns:
            Tuple of (command list, test directory path)

        """
        python_cmd = str(venv_python)

        # Detect source directories for coverage
        source_dirs = ["."] if (project_path / "pyproject.toml").exists() else []
        if not source_dirs:
            if (project_path / "app").is_dir():
                source_dirs.append("app")
            if (project_path / "src").is_dir():
                source_dirs.append("src")
            if not source_dirs:
                source_dirs = ["."]

        # Build coverage args
        cov_args = []
        for src in source_dirs:
            cov_args.extend(["--cov", src])

        # Determine test directory
        test_dir = project_path / "tests"
        if not test_dir.is_dir():
            test_dir = project_path / "test"
        if not test_dir.is_dir():
            test_dir = project_path

        cmd = [
            python_cmd,
            "-m",
            "pytest",
            str(test_dir),
            *cov_args,
            "--cov-report=term-missing",
            "--cov-config=pyproject.toml",
            "-q",
            "--color=no",
            "--ignore=node_modules",
            "--ignore=venv",
            "--ignore=.venv",
            "--ignore=dist",
            "--ignore=build",
            "--ignore=.git",
            "--ignore=frontend",
            "--ignore=playwright-report",
            "--ignore=test-results",
            "--ignore=*.txt",
        ]

        return cmd, test_dir

    def _execute_pytest(self, cmd: list[str], project_path: Path) -> tuple[str, str, int]:
        """Execute pytest command and return output.

        Returns:
            Tuple of (stdout, stderr, return_code)

        """
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_path)

        logger.info(f"Running: {' '.join(cmd[:8])}...")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=project_path, env=env)

        return result.stdout, result.stderr, result.returncode

    def _parse_test_results(self, output: str) -> dict[str, int]:
        """Parse pytest summary line for passed/failed/skipped counts.

        Args:
            output: Combined stdout+stderr from pytest

        Returns:
            Dict with tests_passed, tests_failed, tests_skipped

        """
        results = {"tests_passed": 0, "tests_failed": 0, "tests_skipped": 0}

        for line in output.splitlines():
            line = line.strip()
            # Look for pytest summary line
            if "=" in line and ("passed" in line or "failed" in line or "error" in line):
                if match := re.search(r"(\d+)\s*passed", line):
                    results["tests_passed"] = int(match.group(1))
                if match := re.search(r"(\d+)\s*failed", line):
                    results["tests_failed"] = int(match.group(1))
                if match := re.search(r"(\d+)\s*skipped", line):
                    results["tests_skipped"] = int(match.group(1))
                if match := re.search(r"(\d+)\s*error", line):
                    results["tests_failed"] += int(match.group(1))

                if results["tests_passed"] or results["tests_failed"]:
                    logger.debug(f"Found test summary: {line}")
                    break

        return results

    def _parse_coverage(self, output: str, stderr: str) -> dict[str, Any]:
        """Parse coverage percentage and report from pytest output.

        Args:
            output: Combined stdout+stderr from pytest
            stderr: stderr only (for error detection)

        Returns:
            Dict with coverage_percent, coverage_report, warning

        """
        result = {"coverage_percent": 0, "coverage_report": "", "warning": None}

        # Check for missing pytest-cov
        if "No module named" in stderr and ("pytest_cov" in stderr or "coverage" in stderr):
            result["warning"] = "⚠️ MISSING: 'pytest-cov' not installed. Coverage unavailable."
            logger.warning(result["warning"])
            return result

        # Try multiple regex patterns for coverage percentage
        coverage_patterns = [
            r"TOTAL\s+\d+\s+\d+\s+(\d+)%",  # Standard
            r"TOTAL\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)%",  # With branches
            r"TOTAL.*?(\d+)%",  # Flexible
            r"coverage:\s*(\d+)%",  # Alternative
        ]

        for pattern in coverage_patterns:
            if match := re.search(pattern, output, re.IGNORECASE):
                result["coverage_percent"] = int(match.group(1))
                logger.info(f"Found coverage {result['coverage_percent']}%")
                break

        # Fallback: find percentage near TOTAL/coverage keywords
        if result["coverage_percent"] == 0:
            for line in output.splitlines():
                if ("total" in line.lower() or "coverage" in line.lower()) and (match := re.search(r"(\d+)%", line)):
                    result["coverage_percent"] = int(match.group(1))
                    break

        # Extract coverage report table
        if table_match := re.search(r"(Name\s+Stmts\s+Miss.*?TOTAL.*?\d+%)", output, re.DOTALL):
            result["coverage_report"] = table_match.group(1).strip()

        return result

    def _run_tests_and_coverage(self, project_path: Path, venv_python: Path) -> dict[str, Any]:
        """Run tests and coverage analysis.

        Orchestrates command building, execution, and parsing.
        Complexity reduced by extracting helper methods.
        """
        result_dict = {
            "coverage_percent": 0,
            "coverage_report": "",
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "warning": None,
        }

        # Skip during pytest to avoid recursion
        if os.environ.get("PYTEST_CURRENT_TEST"):
            logger.debug("Skipping test execution during pytest run")
            return result_dict

        # Quick check for test files
        if not self._find_test_files(project_path):
            logger.debug("No test files found, skipping execution")
            return result_dict

        try:
            # Build and execute command
            cmd, _ = self._build_pytest_command(project_path, venv_python)
            stdout, stderr, _ = self._execute_pytest(cmd, project_path)
            output = f"{stdout}\n{stderr}"

            # Parse results
            test_results = self._parse_test_results(output)
            coverage_results = self._parse_coverage(output, stderr)

            # Merge into result dict
            result_dict.update(test_results)
            result_dict.update(coverage_results)

            return result_dict

        except subprocess.TimeoutExpired:
            logger.warning("Test analysis timed out (300s limit)")
            result_dict["warning"] = "Warning: Test analysis timed out"
            return result_dict

        except Exception as e:
            logger.error(f"Test analysis failed: {e}", exc_info=True)
            result_dict["warning"] = f"Warning: Test analysis failed - {e!s}"
            return result_dict
