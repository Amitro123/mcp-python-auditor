"""MCP Server adapter for stdio transport (AI clients like Claude Desktop, Cursor)."""
import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import Any, Dict

from app.agents.analyzer_agent import AnalyzerAgent
from app.core.tool_registry import registry

# Setup logging to file (not stdout, which is used for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='mcp_server.log'
)
logger = logging.getLogger(__name__)

# Initialize paths
BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports"
TOOLS_DIR = BASE_DIR / "app" / "tools"


class MCPServer:
    """MCP Server for stdio transport."""
    
    def __init__(self):
        self.analyzer = None
        self.tools = []
    
    async def initialize(self):
        """Initialize the MCP server."""
        logger.info("Initializing MCP Server")
        
        # Discover and load tools
        registry.discover_tools(TOOLS_DIR)
        self.tools = registry.list_tool_names()
        logger.info(f"Loaded {len(self.tools)} tools: {', '.join(self.tools)}")
        
        # Initialize analyzer
        self.analyzer = AnalyzerAgent(REPORTS_DIR)
        logger.info("Analyzer agent initialized")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "tools/list":
                return await self.list_tools()
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                return await self.call_tool(tool_name, arguments)
            
            elif method == "initialize":
                return {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "project-audit",
                        "version": "2.0.0"
                    }
                }
            
            else:
                return {"error": f"Unknown method: {method}"}
        
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return {"error": str(e)}
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools in MCP format."""
        tools_list = []
        
        # Full audit tool
        tools_list.append({
            "name": "audit_project",
            "description": "Perform comprehensive project audit with all analysis tools",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the project directory to audit"
                    },
                    "tools": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: Specific tools to run (leave empty for all)"
                    }
                },
                "required": ["path"]
            }
        })
        
        # Individual tool runners
        for tool_name in self.tools:
            tool = registry.get_tool(tool_name)
            if tool:
                tools_list.append({
                    "name": f"run_{tool_name}",
                    "description": tool.description,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Absolute path to the project directory"
                            }
                        },
                        "required": ["path"]
                    }
                })
        
        return {"tools": tools_list}
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return results."""
        project_path = arguments.get("path")
        
        if not project_path:
            return {"error": "Missing required argument: path"}
        
        try:
            if tool_name == "audit_project":
                # Full audit
                specific_tools = arguments.get("tools")
                result = await self.analyzer.analyze_project(
                    project_path=project_path,
                    dry_run=False,
                    specific_tools=specific_tools
                )
                
                # Read the generated report
                report_content = ""
                if result.report_path and Path(result.report_path).exists():
                    with open(result.report_path, 'r', encoding='utf-8') as f:
                        report_content = f.read()
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"# Audit Results\n\n**Score:** {result.score}/100\n\n{result.summary}\n\n---\n\n{report_content}"
                        }
                    ]
                }
            
            elif tool_name.startswith("run_"):
                # Individual tool
                actual_tool_name = tool_name.replace("run_", "")
                tool = registry.get_tool(actual_tool_name)
                
                if not tool:
                    return {"error": f"Tool not found: {actual_tool_name}"}
                
                path = Path(project_path)
                tool_result = tool.analyze(path)
                
                # Format result as text
                result_text = f"# {actual_tool_name.title()} Analysis\n\n"
                result_text += json.dumps(tool_result, indent=2)
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": result_text
                        }
                    ]
                }
            
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"error": f"Tool execution failed: {str(e)}"}


async def main():
    """Main MCP server loop."""
    server = MCPServer()
    await server.initialize()
    
    logger.info("MCP Server started, listening on stdin/stdout")
    
    # Read from stdin, write to stdout (MCP protocol)
    while True:
        try:
            # Read JSON-RPC request from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            
            if not line:
                break
            
            request = json.loads(line)
            logger.info(f"Received request: {request.get('method')}")
            
            # Handle request
            response = await server.handle_request(request)
            
            # Add request ID to response
            if "id" in request:
                response["id"] = request["id"]
            
            # Write JSON-RPC response to stdout
            print(json.dumps(response), flush=True)
            logger.info(f"Sent response for: {request.get('method')}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            break


if __name__ == "__main__":
    asyncio.run(main())
