"""FastAPI MCP server for ProjectAuditAgent."""
import logging
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    AuditRequest,
    AuditResult,
    ToolInfo,
    ToolRunRequest,
    ReportResponse
)
from app.core.tool_registry import registry
from app.agents.analyzer_agent import AnalyzerAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize paths
BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "reports"
TOOLS_DIR = BASE_DIR / "app" / "tools"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup: Discover and load tools
    logger.info("Starting ProjectAuditAgent MCP Server")
    logger.info(f"Discovering tools from: {TOOLS_DIR}")
    
    registry.discover_tools(TOOLS_DIR)
    tools = registry.list_tool_names()
    logger.info(f"Loaded {len(tools)} tools: {', '.join(tools)}")
    
    # Initialize analyzer agent
    app.state.analyzer = AnalyzerAgent(REPORTS_DIR)
    logger.info("Analyzer agent initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ProjectAuditAgent MCP Server")


# Create FastAPI app
app = FastAPI(
    title="ProjectAuditAgent MCP",
    description="Production-ready MCP server for comprehensive Python/FastAPI project analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ProjectAuditAgent MCP",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "audit": "POST /audit",
            "report": "GET /report/{report_id}",
            "tools": "GET /tools",
            "run_tool": "POST /tools/{tool_name}/run"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    tools_count = len(registry.list_tool_names())
    return {
        "status": "healthy",
        "tools_loaded": tools_count
    }


@app.post("/audit", response_model=AuditResult)
async def audit_project(request: AuditRequest):
    """
    Perform comprehensive project audit.
    
    Args:
        request: AuditRequest with project path and options
        
    Returns:
        AuditResult with analysis results and report path
    """
    try:
        logger.info(f"Audit request for: {request.path}")
        
        result = await app.state.analyzer.analyze_project(
            project_path=request.path,
            dry_run=request.dry_run,
            specific_tools=request.tools
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit failed: {str(e)}"
        )


@app.get("/report/{report_id}", response_class=PlainTextResponse)
async def get_report(report_id: str):
    """
    Get generated report by ID.
    
    Args:
        report_id: Report identifier
        
    Returns:
        Markdown report content
    """
    report_path = REPORTS_DIR / f"{report_id}.md"
    
    if not report_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
    
    except Exception as e:
        logger.error(f"Failed to read report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read report: {str(e)}"
        )


@app.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """
    List all available analysis tools.
    
    Returns:
        List of ToolInfo objects
    """
    tools = registry.get_all_tools()
    
    return [
        ToolInfo(
            name=tool.name,
            description=tool.description,
            version=tool.version,
            enabled=tool.enabled
        )
        for tool in tools.values()
    ]


@app.post("/tools/{tool_name}/run")
async def run_specific_tool(tool_name: str, request: ToolRunRequest):
    """
    Run a specific analysis tool.
    
    Args:
        tool_name: Name of the tool to run
        request: ToolRunRequest with project path
        
    Returns:
        Tool analysis results
    """
    tool = registry.get_tool(tool_name)
    
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}"
        )
    
    if not tool.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tool is disabled: {tool_name}"
        )
    
    try:
        path = Path(request.path)
        result = tool.analyze(path)
        
        return {
            "tool_name": tool_name,
            "success": 'error' not in result,
            "data": result
        }
    
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )


@app.post("/tools/{tool_name}/enable")
async def enable_tool(tool_name: str):
    """Enable a specific tool."""
    if registry.enable_tool(tool_name):
        return {"message": f"Tool enabled: {tool_name}"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Tool not found: {tool_name}"
    )


@app.post("/tools/{tool_name}/disable")
async def disable_tool(tool_name: str):
    """Disable a specific tool."""
    if registry.disable_tool(tool_name):
        return {"message": f"Tool disabled: {tool_name}"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Tool not found: {tool_name}"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
