"""Windows-Safe Command Chunking Utility.

Prevents WinError 206 (command line too long) by splitting file lists into batches.
"""

import logging
import subprocess

logger = logging.getLogger(__name__)

# Windows has a ~8191 character limit for command lines
# We use a conservative chunk size to stay well under this limit
DEFAULT_CHUNK_SIZE = 50


def run_tool_in_chunks(
    base_cmd: list[str],
    files: list[str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    merge_json: bool = True,
    timeout: int = 300,
) -> subprocess.CompletedProcess:
    """Run a command-line tool on a large file list by splitting into chunks.

    Args:
        base_cmd: Base command (e.g., ['python', '-m', 'bandit', '-f', 'json'])
        files: List of file paths to process
        chunk_size: Maximum files per batch
        merge_json: If True, merge JSON results from all chunks
        timeout: Timeout per chunk in seconds

    Returns:
        CompletedProcess with merged results

    """
    if not files:
        logger.warning("run_tool_in_chunks called with empty file list")
        return subprocess.CompletedProcess(args=base_cmd, returncode=0, stdout='{"results": [], "metrics": {}}', stderr="")

    # If file list is small enough, run directly
    if len(files) <= chunk_size:
        cmd = base_cmd + files
        logger.info(f"Running single batch: {len(files)} files")
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    # Split into chunks
    chunks = [files[i : i + chunk_size] for i in range(0, len(files), chunk_size)]
    logger.info(f"Splitting {len(files)} files into {len(chunks)} chunks of ~{chunk_size} files")

    all_results = []
    all_metrics = {}
    combined_stdout = ""
    combined_stderr = ""

    for i, chunk in enumerate(chunks, 1):
        cmd = base_cmd + chunk
        logger.info(f"Processing chunk {i}/{len(chunks)}: {len(chunk)} files")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            combined_stderr += result.stderr

            if merge_json and result.stdout:
                try:
                    import json

                    data = json.loads(result.stdout)

                    # Merge results
                    if "results" in data:
                        all_results.extend(data["results"])

                    # Merge metrics
                    if "metrics" in data:
                        all_metrics.update(data["metrics"])

                except json.JSONDecodeError:
                    logger.warning(f"Chunk {i} produced invalid JSON, skipping merge")
                    combined_stdout += result.stdout
            else:
                combined_stdout += result.stdout

        except subprocess.TimeoutExpired:
            logger.exception(f"Chunk {i}/{len(chunks)} timed out")
            combined_stderr += f"\n[CHUNK {i} TIMEOUT]"
        except Exception as e:
            logger.exception(f"Chunk {i}/{len(chunks)} failed: {e}")
            combined_stderr += f"\n[CHUNK {i} ERROR: {e}]"

    # Build merged result
    if merge_json and all_results:
        import json

        merged_data = {"results": all_results, "metrics": all_metrics}
        combined_stdout = json.dumps(merged_data, indent=2)

    return subprocess.CompletedProcess(
        args=[*base_cmd, f"<{len(files)} files in {len(chunks)} chunks>"],
        returncode=0,
        stdout=combined_stdout,
        stderr=combined_stderr,
    )


def filter_python_files(files: list[str]) -> list[str]:
    """Safety filter: Ensure only .py files are in the list.

    Args:
        files: List of file paths

    Returns:
        Filtered list containing only .py files

    """
    python_files = [f for f in files if f.endswith(".py")]

    if len(python_files) < len(files):
        excluded = len(files) - len(python_files)
        logger.warning(f"Filtered out {excluded} non-Python files")

    return python_files


def validate_file_list(files: list[str], tool_name: str) -> bool:
    """Safety check: Validate file list before running a tool.

    Args:
        files: List of file paths
        tool_name: Name of the tool (for logging)

    Returns:
        True if valid, False otherwise

    """
    if not files:
        logger.warning(f"{tool_name}: Empty file list provided")
        return False

    # Check for suspicious patterns
    suspicious = [f for f in files if any(x in f.lower() for x in [".venv", "site-packages", "node_modules"])]
    if suspicious:
        logger.error(f"{tool_name}: File list contains excluded paths: {suspicious[:5]}")
        return False

    return True
