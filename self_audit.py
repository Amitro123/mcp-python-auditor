import asyncio
import sys
import logging
from pathlib import Path
from app.agents.analyzer_agent import AnalyzerAgent
from app.schemas import AuditResult

# Import ALL tools to trigger registration
from app.tools.structure_tool import StructureTool
from app.tools.architecture_tool import ArchitectureTool
from app.tools.duplication_tool import DuplicationTool
from app.tools.deadcode_tool import DeadcodeTool

try:
    from app.tools.git_tool import GitTool
except ImportError:
    pass # Git tool might be optional or have issues

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

from app.core.tool_registry import registry

async def run_analysis(agent, project_path):
    # Ensure tools are loaded!
    tools_path = project_path / "app" / "tools"
    logger.info(f"Discovering tools from {tools_path}...")
    registry.discover_tools(tools_path)
    logger.info(f"Registered tools: {registry.list_tool_names()}")
    
    return await agent.analyze_project(project_path)

def run_self_audit():
    project_path = Path(".")
    print(f"[*] Starting Self-Audit on {project_path.absolute()}...")
    
    reports_dir = project_path / "reports"
    agent = AnalyzerAgent(reports_dir)
    
    # Run analysis (Need asyncio wrapper)
    audit_result = asyncio.run(run_analysis(agent, project_path))
    
    # AuditResult is a Pydantic model
    results = audit_result.tool_results # This is a dict of ToolResult objects
    
    # --- VERIFICATION ---
    print("\n" + "="*50)
    print("MATCHING SUCCESS CRITERIA")
    print("="*50)
    
    # 1. File Count Check
    # Need to access data inside ToolResult object
    structure_result = results.get('structure')
    total_files = 0
    if structure_result and structure_result.success:
         total_files = structure_result.data.get('total_files', 0)
         
    print(f"[FILES] Total Files Scanned: {total_files}")
    if total_files > 150:
        print("[FAIL] File count too high! Exclusions might not be working.")
    else:
        print("[PASS] File count is within expected range (< 150).")

    # 2. Tool Execution Status
    print("\n[TOOLS] Tool Execution Summary:")
    failed_tools = []
    
    print(f"{'Tool':<15} | {'Status':<10} | {'Time (s)':<10}")
    print("-" * 40)
    
    for name, tool_res in results.items():
        status = 'success' if tool_res.success else 'failed'
        duration = round(tool_res.execution_time, 2)
        print(f"{name:<15} | {status:<10} | {duration:<10}")
        
        if not tool_res.success:
            # Check if skipped (not a failure really)
            if tool_res.data and tool_res.data.get('skipped'):
                print(f"  -> Skipped: {tool_res.data.get('reason')}")
            else:
                failed_tools.append(name)
                print(f"  -> Error: {tool_res.errors}")
            
    if failed_tools:
        print(f"\n[FAIL] The following tools failed: {failed_tools}")
    else:
        print("\n[PASS] All tools ran successfully (or were safely skipped).")

    # 3. False Positive Check (site-packages)
    print("\n[CHECK] Checking for False Positives (site-packages/venv)...")
    false_positives = []
    
    # Recursive search on the dictionaries
    def search_issues(data, path=""):
        if isinstance(data, dict):
            for k, v in data.items():
                if k in ['file', 'path'] and isinstance(v, str):
                    if 'site-packages' in v or 'venv' in v or 'node_modules' in v:
                        false_positives.append(f"{path}.{k}={v}")
                else:
                    search_issues(v, path + f".{k}")
        elif isinstance(data, list):
            for item in data:
                search_issues(item, path)

    # Convert ToolResult items to dict for searching
    tools_data_dict = {
        name: res.data 
        for name, res in results.items() 
        if res.success
    }
    search_issues(tools_data_dict)
    
    if false_positives:
        print(f"[FAIL] Found {len(false_positives)} issues in ignored directories:")
        for fp in false_positives[:5]:
            print(f"  - {fp}")
    else:
        print("[PASS] Zero issues found in ignored directories.")

    # Check Report Generation
    if audit_result.report_path:
        print(f"\n[REPORT] Report generated successfully: {audit_result.report_path}")
        # Copy content to SELF_AUDIT_REPORT.md for easy reading
        try:
            import shutil
            shutil.copy(audit_result.report_path, "SELF_AUDIT_REPORT.md")
            print("   (Copied to SELF_AUDIT_REPORT.md)")
        except (IOError, OSError) as e:
            print(f"   (Could not copy report: {e})")
    else:
        print("\n[FAIL] Report was not generated.")

if __name__ == "__main__":
    run_self_audit()
