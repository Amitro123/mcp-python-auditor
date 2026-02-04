"""Code duplication detection tool with Safety-First Execution."""

import ast
import hashlib
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from app.core.base_tool import BaseTool
from app.core.command_chunker import filter_python_files, validate_file_list

logger = logging.getLogger(__name__)


class DuplicationTool(BaseTool):
    """Detect duplicate code patterns in Python files."""

    @property
    def description(self) -> str:
        return "Detects duplicate functions and code patterns using AST and fuzzy matching"

    def analyze(self, project_path: Path, file_list: list[str] | None = None) -> dict[str, Any]:
        """Analyze code for duplicates using explicit file list.

        SAFETY-FIRST EXECUTION:
        1. Guard Clause: Empty file list check
        2. Guard Clause: Extension filter (only .py files)

        Args:
            project_path: Path to the project directory
            file_list: Optional list of absolute file paths to scan

        Returns:
            Dictionary with duplicate code information

        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path"}

        # STEP 1: GUARD CLAUSE - Empty Check
        if file_list is not None and not file_list:
            logger.warning("Duplication: Empty file list provided, skipping scan")
            return {
                "status": "skipped",
                "duplicates": [],
                "total_duplicates": 0,
                "total_functions_analyzed": 0,
            }

        # STEP 2: GUARD CLAUSE - Extension Filter
        if file_list:
            file_list = filter_python_files(file_list)
            if not validate_file_list(file_list, "Duplication"):
                return {"error": "Invalid file list (contains excluded paths or empty)"}
            logger.info(f"[OK] Duplication: Analyzing {len(file_list)} Python files (explicit list)")

        try:
            # Extract all functions from the project
            functions = self._extract_functions(project_path, file_list)

            # Find duplicates
            duplicates = self._find_duplicates(functions)

            return {
                "status": "analyzed" if duplicates else "clean",
                "duplicates": duplicates,
                "total_duplicates": len(duplicates),
                "total_functions_analyzed": len(functions),
            }
        except Exception as e:
            logger.exception(f"Duplication analysis failed: {e}")
            return {"error": str(e)}

    def _extract_functions(self, path: Path, file_list: list[str] | None = None) -> list[dict[str, Any]]:
        """Extract all functions from Python files."""
        functions = []

        # Use explicit file list if provided
        if file_list:
            py_files = [Path(f) for f in file_list if f.endswith(".py")]
        else:
            # Fallback: Use centralized file walker from BaseTool
            py_files = list(self.walk_project_files(path))

        for py_file in py_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()
                    tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_info = self._extract_function_info(node, py_file, path, content)
                        if func_info:
                            functions.append(func_info)

            except Exception as e:
                logger.debug(f"Failed to parse {py_file}: {e}")

        return functions

    def _extract_function_info(self, node: ast.FunctionDef, file_path: Path, project_path: Path, file_content: str) -> dict[str, Any]:
        """Extract information about a function."""
        try:
            # Get function source code
            func_lines = file_content.split("\n")[node.lineno - 1 : node.end_lineno]
            func_source = "\n".join(func_lines)

            # Normalize the source (remove comments, docstrings, whitespace)
            normalized = self._normalize_code(func_source)

            # Create hash of normalized code
            code_hash = hashlib.md5(normalized.encode()).hexdigest()  # nosec

            return {
                "name": node.name,
                "file": str(file_path.relative_to(project_path)),
                "line": node.lineno,
                "source": func_source,
                "normalized": normalized,
                "hash": code_hash,
                "length": len(func_lines),
            }
        except Exception as e:
            logger.debug(f"Failed to extract function info: {e}")
            return None

    def _normalize_code(self, code: str) -> str:
        """Normalize code by removing comments, docstrings, and extra whitespace."""
        try:
            tree = ast.parse(code)

            # Remove docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)) and ast.get_docstring(node):
                    node.body = node.body[1:] if len(node.body) > 1 else node.body

            # Convert back to code (this removes comments automatically)
            import astor

            normalized = astor.to_source(tree)

            # Remove extra whitespace
            return " ".join(normalized.split())

        except Exception:
            # Fallback: simple normalization
            lines = [line.strip() for line in code.split("\n")]
            lines = [line for line in lines if line and not line.startswith("#")]
            return " ".join(lines)

    def _find_duplicates(self, functions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find duplicate functions."""
        duplicates = []

        # Group by hash for exact duplicates
        hash_groups = defaultdict(list)
        for func in functions:
            if func["length"] >= 3:  # Only consider functions with 3+ lines
                hash_groups[func["hash"]].append(func)

        # Find exact duplicates
        for funcs in hash_groups.values():
            if len(funcs) > 1:
                duplicates.append(
                    {
                        "function_name": funcs[0]["name"],
                        "similarity": 100,
                        "type": "exact",
                        "locations": [f"{f['file']}:{f['line']}" for f in funcs],
                        "count": len(funcs),
                    }
                )

        # Find similar functions (fuzzy matching)
        # Only check functions not already marked as exact duplicates
        processed_hashes = {h for h, funcs in hash_groups.items() if len(funcs) > 1}
        remaining_functions = [f for f in functions if f["hash"] not in processed_hashes and f["length"] >= 5]

        # OPTIMIZATION: Limit comparisons to avoid O(n²) slowdown
        MAX_COMPARISONS = 5000  # Limit total comparisons
        MAX_SIMILAR_DUPLICATES = 200  # Stop after finding enough duplicates
        comparisons = 0

        # Sort by length for faster length-based filtering
        remaining_functions.sort(key=lambda f: f["length"])

        # Compare pairs of functions
        for i, func1 in enumerate(remaining_functions):
            if len(duplicates) >= MAX_SIMILAR_DUPLICATES:
                logger.info(f"Duplication: Stopping early after finding {len(duplicates)} duplicates")
                break

            for func2 in remaining_functions[i + 1 :]:
                comparisons += 1
                if comparisons > MAX_COMPARISONS:
                    logger.info(f"Duplication: Stopping after {MAX_COMPARISONS} comparisons")
                    break

                # OPTIMIZATION: Skip if length difference > 30% (unlikely to be similar)
                len_ratio = min(func1["length"], func2["length"]) / max(func1["length"], func2["length"])
                if len_ratio < 0.7:
                    continue

                # Skip if same file and similar names (likely overloads)
                if func1["file"] == func2["file"] and func1["name"] == func2["name"]:
                    continue

                # Calculate similarity
                similarity = fuzz.ratio(func1["normalized"], func2["normalized"])

                if similarity >= 80:  # 80% similarity threshold
                    duplicates.append(
                        {
                            "function_name": f"{func1['name']} / {func2['name']}",
                            "similarity": similarity,
                            "type": "similar",
                            "locations": [
                                f"{func1['file']}:{func1['line']}",
                                f"{func2['file']}:{func2['line']}",
                            ],
                            "count": 2,
                        }
                    )

            if comparisons > MAX_COMPARISONS:
                break

        # Sort by similarity (highest first)
        duplicates.sort(key=lambda x: x["similarity"], reverse=True)

        return duplicates
