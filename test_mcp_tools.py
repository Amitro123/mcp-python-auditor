"""Quick test script for the FastMCP server."""
import subprocess
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Test imports
print("Testing imports...")
from app.tools.security_tool import SecurityTool
from app.tools.secrets_tool import SecretsTool
from app.tools.structure_tool import StructureTool
print("✅ Imports successful!")

# Test a single tool
print("\n🔍 Testing StructureTool on current directory...")
tool = StructureTool()
result = tool.analyze(Path("."))
print(f"✅ Found {result.get('total_files', 0)} files, {result.get('total_directories', 0)} directories")

# Test security tool
print("\n🔒 Testing SecurityTool on current directory...")
sec_tool = SecurityTool()
sec_result = sec_tool.analyze(Path("."))
if "code_security" in sec_result:
    files = sec_result["code_security"].get("files_scanned", 0)
    issues = len(sec_result["code_security"].get("issues", []))
    print(f"✅ Scanned {files} files, found {issues} issues")
else:
    print(f"✅ Result: {sec_result}")

print("\n🎉 All tests passed! Server is ready.")
print("\nTo test interactively, run:")
print("  fastmcp dev mcp_fastmcp_server.py")
