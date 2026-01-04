# Changes Tracker

## Modified Files
- `app/agents/analyzer_agent.py`: Implemented parallelism and smart skipping.

## Test Results
- `tests/test_analyzer_agent.py`: 5 passed.
- `tests/test_parallel_audit.py`: 3 passed (New test covers parallelism, skipping, and safety).

## Diffs

### app/agents/analyzer_agent.py
```diff
@@ -2,9 +2,10 @@
 import time
 import re
 from pathlib import Path
-from typing import Dict, Any, Optional, List
+from typing import Dict, Any, Optional, List, Set
 from datetime import datetime
 import logging
+import asyncio
 
 from app.core.tool_registry import registry
 from app.core.report_generator import ReportGenerator
@@ -49,26 +49,42 @@
         
         logger.info(f"Starting analysis of {project_path} (report_id: {report_id})")
         
+        # Pre-flight check: Count python files
+        py_files_count = self._count_python_files(path)
+        logger.info(f"Project contains {py_files_count} Python files")
+        
+        heavy_tools = {'complexity', 'deadcode', 'duplication'}
+        skipped_tools = []
+        
         # Get tools to run
         if specific_tools:
-            tools = {name: registry.get_tool(name) for name in specific_tools}
-            tools = {k: v for k, v in tools.items() if v is not None}
-        else:
-            tools = registry.get_enabled_tools()
-        
-        # Run each tool
+            tools_to_run = {name: registry.get_tool(name) for name in specific_tools}
+            tools_to_run = {k: v for k, v in tools_to_run.items() if v is not None}
+        else:
+            tools_to_run = registry.get_enabled_tools()
+            
+        # Smart Skipping logic
+        if py_files_count > 300:
+            for tool_name in list(tools_to_run.keys()):
+                if tool_name in heavy_tools:
+                    logger.warning(f"Skipping heavy tool '{tool_name}' due to project size ({py_files_count} files)")
+                    skipped_tools.append(tool_name)
+                    del tools_to_run[tool_name]
+        
+        # Run tools in parallel
         tool_results = {}
-        for tool_name, tool in tools.items():
-            logger.info(f"Running tool: {tool_name}")
+        
+        async def run_tool_safe(name, tool):
+            logger.info(f"Running tool: {name}")
             tool_start = time.time()
-            
-            try:
-                result_data = tool.analyze(path)
+            try:
+                # Use asyncio.to_thread for blocking I/O (subprocess calls in tools)
+                result_data = await asyncio.to_thread(tool.analyze, path)
                 success = 'error' not in result_data
                 errors = [result_data['error']] if 'error' in result_data else []
                 
-                tool_results[tool_name] = ToolResult(
-                    tool_name=tool_name,
+                return name, ToolResult(
+                    tool_name=name,
                     success=success,
                     data=result_data,
                     errors=errors,
@@ -75,8 +75,8 @@
                 )
             except Exception as e:
-                logger.error(f"Tool {tool_name} failed: {e}")
-                tool_results[tool_name] = ToolResult(
-                    tool_name=tool_name,
+                logger.error(f"Tool {name} failed: {e}")
+                return name, ToolResult(
+                    tool_name=name,
                     success=False,
                     errors=[str(e)],
                     execution_time=time.time() - tool_start
@@ -83,4 +83,10 @@
         
+        # Execute all tools concurrently
+        tasks = [run_tool_safe(name, tool) for name, tool in tools_to_run.items()]
+        if tasks:
+            results = await asyncio.gather(*tasks)
+            tool_results = {name: result for name, result in results}
+        
         # Calculate score
         score = self._calculate_score(tool_results)
...
```
