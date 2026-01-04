"""Safe subprocess execution wrapper for external tools."""
import subprocess
import logging
from typing import Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class SubprocessWrapper:
    """Safe wrapper for executing external commands."""
    
    @staticmethod
    def run_command(
        command: List[str],
        cwd: Path,
        timeout: int = 300,
        check_venv: bool = True
    ) -> Tuple[bool, str, str]:
        """
        Safely execute a command with error handling.
        
        Args:
            command: Command and arguments as list
            cwd: Working directory
            timeout: Timeout in seconds
            check_venv: Whether to check for virtual environment
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        # Check if command exists
        cmd_name = command[0]
        if not SubprocessWrapper._command_exists(cmd_name):
            logger.warning(f"Command not found: {cmd_name}")
            return False, "", f"Command not found: {cmd_name}"
        
        # Check for venv if required
        if check_venv and not SubprocessWrapper._has_venv(cwd):
            logger.info(f"No virtual environment detected in {cwd}")
        
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                errors='replace'  # Handle encoding errors gracefully
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
        
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s: {' '.join(command)}")
            return False, "", f"Command timed out after {timeout}s"
        
        except FileNotFoundError:
            logger.error(f"Command not found: {cmd_name}")
            return False, "", f"Command not found: {cmd_name}"
        
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return False, "", str(e)
    
    @staticmethod
    def _command_exists(cmd: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                timeout=5
            )
            return True
        except:
            return False
    
    @staticmethod
    def _has_venv(path: Path) -> bool:
        """Check if directory has a virtual environment."""
        venv_indicators = [
            path / 'venv',
            path / '.venv',
            path / 'env',
            path / 'ENV'
        ]
        
        return any(p.exists() for p in venv_indicators)
    
    @staticmethod
    def run_python_module(
        module: str,
        args: List[str],
        cwd: Path,
        timeout: int = 300
    ) -> Tuple[bool, str, str]:
        """
        Run a Python module with error handling.
        
        Args:
            module: Module name (e.g., 'pytest', 'coverage')
            args: Module arguments
            cwd: Working directory
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        command = ['python', '-m', module] + args
        return SubprocessWrapper.run_command(command, cwd, timeout)
