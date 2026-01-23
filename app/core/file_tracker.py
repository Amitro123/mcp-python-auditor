"""
File Tracker - MD5-based file change detection for incremental audits.

Tracks file hashes to detect:
- New files (not in index)
- Modified files (hash changed)
- Deleted files (in index but not on disk)
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional

logger = logging.getLogger(__name__)

# Directories to always exclude from tracking
EXCLUDE_DIRS = {
    '.venv', 'venv', 'env', 'node_modules', '.git', '__pycache__',
    '.pytest_cache', '.mypy_cache', '.ruff_cache', 'dist', 'build',
    'htmlcov', '.audit_index', '.audit_cache', 'site-packages',
    'frontend', 'static', '.tox', '.eggs', 'eggs'
}

# File patterns to exclude
EXCLUDE_PATTERNS = {'.pyc', '.pyo', '.so', '.dylib', '.dll'}


@dataclass
class FileChange:
    """Represents a detected file change."""
    path: str
    change_type: str  # 'new', 'modified', 'deleted'
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None


@dataclass
class ChangeSet:
    """Collection of detected changes."""
    new_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
    unchanged_files: List[str] = field(default_factory=list)

    @property
    def changed_files(self) -> List[str]:
        """All files that need re-analysis."""
        return self.new_files + self.modified_files

    @property
    def has_changes(self) -> bool:
        return bool(self.new_files or self.modified_files or self.deleted_files)

    @property
    def total_changed(self) -> int:
        return len(self.new_files) + len(self.modified_files) + len(self.deleted_files)

    @property
    def total_cached(self) -> int:
        return len(self.unchanged_files)

    def summary(self) -> str:
        """Human-readable summary of changes."""
        parts = []
        if self.new_files:
            parts.append(f"{len(self.new_files)} new")
        if self.modified_files:
            parts.append(f"{len(self.modified_files)} modified")
        if self.deleted_files:
            parts.append(f"{len(self.deleted_files)} deleted")
        if not parts:
            return "No changes detected"
        return f"{', '.join(parts)} ({len(self.unchanged_files)} unchanged)"


class FileTracker:
    """
    Tracks file changes using MD5 hashes.

    Stores index in .audit_index/file_index.json
    """

    INDEX_DIR = ".audit_index"
    INDEX_FILE = "file_index.json"

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path).resolve()
        self.index_dir = self.project_path / self.INDEX_DIR
        self.index_file = self.index_dir / self.INDEX_FILE
        self._index: Dict[str, dict] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load existing index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._index = data.get('files', {})
                    logger.info(f"Loaded file index with {len(self._index)} entries")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load index: {e}, starting fresh")
                self._index = {}
        else:
            logger.info("No existing index found, will create on first scan")
            self._index = {}

    def _save_index(self) -> None:
        """Save index to disk."""
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Ensure .audit_index is gitignored
        gitignore_path = self.project_path / '.gitignore'
        self._ensure_gitignored(gitignore_path, self.INDEX_DIR)

        data = {
            'version': '1.0',
            'project_path': str(self.project_path),
            'last_updated': datetime.now().isoformat(),
            'total_files': len(self._index),
            'files': self._index
        }

        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved file index with {len(self._index)} entries")

    def _ensure_gitignored(self, gitignore_path: Path, pattern: str) -> None:
        """Ensure pattern is in .gitignore."""
        if not gitignore_path.exists():
            return

        try:
            content = gitignore_path.read_text(encoding='utf-8')
            if pattern not in content and f"/{pattern}" not in content:
                with open(gitignore_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n# Audit index cache\n{pattern}/\n")
                logger.info(f"Added {pattern} to .gitignore")
        except IOError:
            pass

    def _should_track(self, path: Path) -> bool:
        """Check if file should be tracked."""
        # Only track Python files
        if path.suffix != '.py':
            return False

        # Check exclude patterns
        if path.suffix in EXCLUDE_PATTERNS:
            return False

        # Check exclude directories
        path_parts = set(path.relative_to(self.project_path).parts)
        if path_parts & EXCLUDE_DIRS:
            return False

        # Additional checks for common excludes
        path_str = str(path)
        if any(excl in path_str for excl in ['.venv', 'venv', 'site-packages', 'node_modules']):
            return False

        return True

    def _compute_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of file contents."""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except IOError as e:
            logger.warning(f"Failed to hash {file_path}: {e}")
            return ""

    def scan_files(self) -> Dict[str, str]:
        """
        Scan project for all Python files and compute hashes.

        Returns:
            Dict mapping relative path -> MD5 hash
        """
        current_files = {}

        for py_file in self.project_path.rglob('*.py'):
            if not self._should_track(py_file):
                continue

            rel_path = str(py_file.relative_to(self.project_path))
            file_hash = self._compute_hash(py_file)
            if file_hash:
                current_files[rel_path] = file_hash

        logger.info(f"Scanned {len(current_files)} Python files")
        return current_files

    def detect_changes(self) -> ChangeSet:
        """
        Compare current files against stored index.

        Returns:
            ChangeSet with categorized file changes
        """
        current_files = self.scan_files()
        indexed_files = set(self._index.keys())
        current_file_set = set(current_files.keys())

        changes = ChangeSet()

        # New files (in current but not in index)
        changes.new_files = list(current_file_set - indexed_files)

        # Deleted files (in index but not in current)
        changes.deleted_files = list(indexed_files - current_file_set)

        # Check for modifications in common files
        common_files = indexed_files & current_file_set
        for file_path in common_files:
            current_hash = current_files[file_path]
            stored_hash = self._index[file_path].get('hash', '')

            if current_hash != stored_hash:
                changes.modified_files.append(file_path)
            else:
                changes.unchanged_files.append(file_path)

        logger.info(f"Change detection: {changes.summary()}")
        return changes

    def update_index(self, files: Optional[List[str]] = None) -> None:
        """
        Update index with current file hashes.

        Args:
            files: Specific files to update (None = all files)
        """
        current_files = self.scan_files()

        if files is None:
            # Full update
            self._index = {}
            for rel_path, file_hash in current_files.items():
                self._index[rel_path] = {
                    'hash': file_hash,
                    'last_analyzed': datetime.now().isoformat()
                }
        else:
            # Partial update
            for rel_path in files:
                if rel_path in current_files:
                    self._index[rel_path] = {
                        'hash': current_files[rel_path],
                        'last_analyzed': datetime.now().isoformat()
                    }
                elif rel_path in self._index:
                    # File was deleted
                    del self._index[rel_path]

        self._save_index()

    def remove_deleted(self, deleted_files: List[str]) -> None:
        """Remove deleted files from index."""
        for file_path in deleted_files:
            if file_path in self._index:
                del self._index[file_path]
        self._save_index()

    def clear_index(self) -> None:
        """Clear the entire index (force full re-scan)."""
        self._index = {}
        if self.index_file.exists():
            self.index_file.unlink()
        logger.info("Cleared file index")

    def get_stats(self) -> dict:
        """Get index statistics."""
        return {
            'total_files': len(self._index),
            'index_exists': self.index_file.exists(),
            'index_path': str(self.index_file),
            'last_updated': self._index.get('_meta', {}).get('last_updated') if self._index else None
        }
