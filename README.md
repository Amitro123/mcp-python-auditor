# MCP Python Auditor

A high-performance codebase auditor and refactoring tool designed for Python projects. It integrates multiple static analysis tools (Ruff, Bandit, Vulture, Radon) into a single, unified pipeline with caching, parallel execution, and AI-driven insights.

## Key Features

- **Unified CLI**: Run 10+ tools with a single command (`python audit.py .`).
- **Parallel Execution**: Uses `AuditOrchestrator` to run tools concurrently for maximum speed.
- **Smart Caching**: Caches results to avoid re-running slow tools on unchanged code.
- **Interactive Mode**: CLI with emoji support, score breakdown, and AI analysis integration.
- **Auto-Fixing**: Can automatically fix common linting issues and upgrade vulnerable packages.
- **MCP Integration**: Exposes audit capabilities as Model Context Protocol (MCP) tools.

## Tech Stack

- **Language**: Python 3.11+
- **Core**: FastAPI, Pydantic
- **Static Analysis**:
  - **Ruff**: Fast linting and formatting
  - **Bandit**: Security scanning
  - **Vulture**: Dead code detection
  - **Radon**: Complexity analysis
  - **detect-secrets**: Secret scanning
  - **pip-audit**: Dependency vulnerability checking
- **Testing**: Pytest, Coverage.py
- **Protocol**: Model Context Protocol (fastmcp)

## Prerequisites

- **Python**: 3.11 or higher
- **Git**: For file change detection

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Amitro123/mcp-python-auditor.git
cd mcp-python-auditor
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run an Audit

The easiest way to start is with the interactive CLI:

```bash
python audit.py
```

Or run a fast audit directly (skips slow tools like secrets/coverage):

```bash
python audit.py . --fast
```

## Usage Guide

### CLI Options

| Command | Description |
|---------|-------------|
| `python audit.py` | Interactive mode (default) |
| `python audit.py .` | Full audit of current directory |
| `python audit.py <path>` | Audit specific directory |
| `python audit.py . --fast` | Fast audit (skips coverage, secrets, pip-audit) |
| `python audit.py . --pr` | Audit only changed files (PR mode) |
| `python audit.py . --json-out` | Output results as JSON |
| `python audit.py . --skip-slow` | Skip very slow tools only (secrets, coverage) |

### Interactive Features

When running in interactive mode, you can:
1. Select audit depth (Full vs Fast)
2. View detailed progress with caching status
3. Get a score (0-100) and grade (A-F)
4. Request **AI Analysis** (via Groq or Ollama) to explain issues
5. **Auto-Apply Fixes** for common problems (Ruff linting, upgrades, cache cleanup)

## Architecture

The project follows a modular architecture designed for extensibility and performance.

### Directory Structure

```
├── app/
│   ├── core/
│   │   ├── audit_orchestrator.py  # Main engine: manages tool execution & caching
│   │   ├── cli_adapter.py         # Adapts legacy CLI to orchestrator
│   │   ├── cache_manager.py       # Caching logic
│   │   └── report_generator.py    # Report generation logic
│   ├── tools/                     # Individual tool implementations
│   │   ├── bandit_tool.py
│   │   ├── fast_audit_tool.py     # Wraps Ruff (linting + complexity)
│   │   ├── deadcode_tool.py       # Wraps Vulture
│   │   └── ...
│   └── main.py                    # FastAPI entry point for MCP
├── audit.py                       # CLI entry point
├── pyproject.toml                 # Tool configuration (Ruff, Pytest, Bandit)
└── requirements.txt               # Project dependencies
```

### Core Components

**1. Audit Orchestrator (`app/core/audit_orchestrator.py`)**
 The brain of the system. It handles:
 - **Parallelization**: Runs independent tools concurrently using `asyncio`.
 - **Caching**: Checks file hashes to skip redundant work.
 - **File Discovery**: Efficiently lists project files using Git/filesystem.

**2. CLI Adapter (`app/core/cli_adapter.py`)**
 Bridges the user-facing `audit.py` script with the orchestrator. It ensures backward compatibility by mapping legacy tool names to the new architecture and formatting results.

**3. Tools (`app/tools/`)**
 Each static analysis tool is encapsulated in a dedicated class inheriting from `BaseTool`. This makes it easy to add new tools without touching the core engine.

### Scoring System

The audit score (0-100) is calculated based on:
- **Security (-40pts)**: Vulnerabilities found by Bandit, Secrets, or Pip-Audit.
- **Quality (-35pts)**: Linting errors (Ruff), Dead code, Duplication.
- **Analysis (-25pts)**: Low test coverage, high complexity, typing issues.

## Testing

Run the test suite to ensure the auditor itself is working correctly:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_audit.py
```

## Troubleshooting

### "Vulture timed out"
If `deadcode` check is taking too long (>120s), it usually means it's scanning too many files recursively.
**Fix**: Ensure `file_discovery.py` is correctly identifying project files and passing them to the tool (fixed in v2.0+).

### "Command not found"
Ensure all dependencies are installed and you are in the virtual environment.
**Fix**: `pip install -r requirements.txt`

### "WinError 206: Filename and extension too long"
Caused by passing too many files in a single command line on Windows.
**Fix**: The `BaseTool` handles chunking automatically to split large file lists into smaller batches.

## License

MIT License. See [LICENSE](LICENSE) for details.
