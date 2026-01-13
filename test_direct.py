"""Direct test of audit tools without MCP wrapper."""
import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from app.tools.security_tool import SecurityTool
from app.tools.secrets_tool import SecretsTool

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

if __name__ == "__main__":
    target = Path(".").resolve()
    log(f"=== Testing on: {target} ===")
    
    # Test Bandit
    log("--- Running SecurityTool (Bandit)... ---")
    start = time.time()
    try:
        result = SecurityTool().analyze(target)
        files = result.get('code_security', {}).get('files_scanned', 'N/A')
        issues = result.get('total_issues', 0)
        log(f"Bandit DONE in {time.time()-start:.1f}s - Files: {files}, Issues: {issues}")
    except Exception as e:
        log(f"Bandit FAILED: {e}")
    
    # Test Secrets
    log("--- Running SecretsTool... ---")
    start = time.time()
    try:
        result = SecretsTool().analyze(target)
        secrets = result.get('total_secrets', 0)
        status = result.get('status', 'unknown')
        log(f"Secrets DONE in {time.time()-start:.1f}s - Found: {secrets}, Status: {status}")
    except Exception as e:
        log(f"Secrets FAILED: {e}")
    
    log("=== TEST COMPLETE ===")
