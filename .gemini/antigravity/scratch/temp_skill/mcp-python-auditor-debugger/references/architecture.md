# Architecture Overview

## Data Flow
```
User → Orchestrator → File Discovery → [Tools in Parallel] → Cache → Report
```

## Components

**AuditOrchestrator** (`app/core/audit_orchestrator.py`)
- Coordinates tool execution
- Manages parallelization
- Delegates to cache and file discovery

**FileDiscovery** (`app/core/file_discovery.py`)
- Lists Python files (Git or filesystem)
- Filters out .venv, __pycache__, etc.

**CacheManager** (`app/core/cache_manager.py`)
- Content-based hashing
- Stores in `.cache/auditor/`

**Tools** (`app/tools/*.py`)
- BaseTool: Abstract base with timeout, chunking
- Specific tools: BanditTool, VultureTool, etc.

## Performance Characteristics
- Git discovery: O(n), ~100ms for 1000 files
- Vulture: O(n²) worst case - main bottleneck
- Ruff: O(n), ~2s for 10k LOC
