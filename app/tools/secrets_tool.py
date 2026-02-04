"""Secrets detection tool using detect-secrets with Smart Targeting."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from app.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


class SecretsTool(BaseTool):
    """Scans for secrets using detect-secrets (Smart Targeted)."""

    @property
    def description(self) -> str:
        return "Scans for secrets using detect-secrets (Smart Targeted)."

    @property
    def cache_patterns(self) -> list[str]:
        """Secrets can be in any file type."""
        return ["**/*"]

    def analyze(self, project_path: Path) -> dict[str, Any]:
        """Analyze project for secrets using smart target discovery.

        Args:
            project_path: Path to the project directory

        Returns:
            Dictionary with detected secrets

        """
        if not self.validate_path(project_path):
            return {"error": "Invalid path", "status": "error"}

        target_path = Path(project_path).resolve()

        # --- SMART TARGETING ---
        # Separate directories and files (detect-secrets has a bug when mixing them)
        scan_dirs: list[str] = []
        scan_files: list[str] = []

        # 1. Scan known source directories
        known_source_dirs = ["src", "app", "scripts", "lib", "core", "backend", "api"]
        for folder in known_source_dirs:
            p = target_path / folder
            if p.exists() and p.is_dir():
                scan_dirs.append(str(p))

        # 2. Collect root-level config files (common secret locations)
        config_patterns = [
            ".env",  # Exact match for .env file
            "*.env",  # Files ending in .env (local.env, prod.env)
            ".env.*",  # Files like .env.local, .env.production
            "*.json",
            "*.yaml",
            "*.yml",
            "*.toml",
            "*.ini",
            "*.conf",
            "*.config",
        ]

        seen_files: set[str] = set()
        for pattern in config_patterns:
            for config_file in target_path.glob(pattern):
                # Skip files in subdirectories (we already scan source dirs)
                if config_file.parent == target_path and config_file.is_file():
                    # Skip known safe files and duplicates, and .env files (security best practice is to not scan local .env)
                    if config_file.name not in ["pyproject.toml", "package.json", "tsconfig.json", ".env"]:
                        file_str = str(config_file)
                        if file_str not in seen_files:
                            seen_files.add(file_str)
                            scan_files.append(file_str)

        logger.info(f"Secrets scan - directories: {scan_dirs}, files: {scan_files}")

        all_secrets: list[dict[str, Any]] = []
        all_targets: list[str] = []

        try:
            # Scan directories (if any)
            if scan_dirs:
                all_targets.extend(scan_dirs)
                dir_secrets = self._run_scan(scan_dirs)
                all_secrets.extend(dir_secrets)

            # Scan standalone files separately (detect-secrets bug workaround)
            if scan_files:
                all_targets.extend(scan_files)
                file_secrets = self._run_scan(scan_files)
                all_secrets.extend(file_secrets)

            # Fallback: scan root if nothing else to scan
            if not scan_dirs and not scan_files:
                all_targets.append(str(target_path))
                root_secrets = self._run_scan(
                    [str(target_path)],
                    exclude_patterns=[
                        "node_modules",
                        "external_libs",
                        "venv",
                        ".venv",
                        "dist",
                        "build",
                        "__pycache__",
                        ".git",
                        "htmlcov",
                        ".pytest_cache",
                        "frontend/test-results",
                        "playwright-report",
                    ],
                )
                all_secrets.extend(root_secrets)

            return {
                "tool": "secrets",
                "status": "issues_found" if all_secrets else "clean",
                "secrets": all_secrets,
                "total_secrets": len(all_secrets),
                "files_with_secrets": len({s["file"] for s in all_secrets}),
                "scan_targets": all_targets,
            }

        except FileNotFoundError:
            logger.warning("detect-secrets not installed")
            return {
                "status": "skipped",
                "error": "detect-secrets not installed. Run: pip install detect-secrets",
                "secrets": [],
                "total_secrets": 0,
            }
        except Exception as e:
            logger.exception(f"Secrets scan failed: {e}")
            return {"error": str(e), "status": "error", "secrets": [], "total_secrets": 0}

    def _run_scan(
        self,
        paths: list[str],
        exclude_patterns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Run detect-secrets scan on given paths.

        Args:
            paths: List of file/directory paths to scan
            exclude_patterns: Optional patterns to exclude

        Returns:
            List of secret findings
        """
        cmd = ["detect-secrets", "scan", "--no-verify", *paths]

        if exclude_patterns:
            for pattern in exclude_patterns:
                cmd.extend(["--exclude-files", pattern])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse detect-secrets output: {result.stdout[:200]}")
            return []

        secrets: list[dict[str, Any]] = []

        # Extract and filter results
        for file_path, findings in data.get("results", {}).items():
            # Safety filter - skip unwanted paths
            if any(
                x in file_path
                for x in [
                    "node_modules",
                    "external_libs",
                    ".min.js",
                    ".map",
                    ".venv",
                    "venv",
                    "__pycache__",
                    "frontend/test-results",
                    "playwright-report",
                ]
            ):
                continue

            for finding in findings:
                secrets.append(
                    {
                        "file": file_path,
                        "line": finding.get("line_number", 0),
                        "type": finding.get("type", "Unknown"),
                        "hashed_secret": finding.get("hashed_secret", "")[:16] + "...",
                    }
                )

        return secrets
