"""Code editor tool for safe file modifications with backup."""

import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CodeEditorTool:
    """Tool for safely editing code files with automatic backup."""

    def delete_line(self, file_path: str, line_number: int) -> dict[str, Any]:
        """Delete a specific line from a file with backup.

        Args:
            file_path: Path to the file to edit
            line_number: Line number to delete (1-indexed)

        Returns:
            Dictionary with status and details

        """
        try:
            file_path = Path(file_path)

            # Security check
            if not file_path.exists():
                return {"status": "error", "error": f"File not found: {file_path}"}

            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            shutil.copy2(file_path, backup_path)

            # Read all lines
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Validate line number
            if line_number < 1 or line_number > len(lines):
                return {
                    "status": "error",
                    "error": f"Line {line_number} out of range (1-{len(lines)})",
                }

            # Delete the line (convert to 0-indexed)
            deleted_content = lines[line_number - 1].strip()
            del lines[line_number - 1]

            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            logger.info(f"Deleted line {line_number} from {file_path}: '{deleted_content}'")

            return {
                "status": "success",
                "file": str(file_path),
                "line": line_number,
                "deleted_content": deleted_content,
                "backup": str(backup_path),
            }

        except Exception as e:
            logger.error(f"Failed to delete line from {file_path}: {e}")
            return {"status": "error", "error": str(e)}

    def restore_backup(self, file_path: str) -> dict[str, Any]:
        """Restore file from .bak backup.

        Args:
            file_path: Path to the original file

        Returns:
            Dictionary with status

        """
        try:
            file_path = Path(file_path)
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")

            if not backup_path.exists():
                return {"status": "error", "error": f"Backup not found: {backup_path}"}

            shutil.copy2(backup_path, file_path)

            return {"status": "success", "file": str(file_path), "restored_from": str(backup_path)}

        except Exception as e:
            return {"status": "error", "error": str(e)}
