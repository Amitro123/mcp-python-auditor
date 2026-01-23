import sys
import argparse
import subprocess
import json
from pathlib import Path

# Add the current directory to sys.path so we can import the app
sys.path.append(str(Path(__file__).parent))

try:
    # Import the internal logic function (not the tool wrapper)
    from mcp_fastmcp_server import _audit_pr_changes_logic
except ImportError as e:
    print(f"❌ Critical Error: Could not import audit logic: {e}")
    # Print traceback to see the root cause (e.g. missing dependency)
    import traceback
    traceback.print_exc()
    print("Make sure you are running this from the root of the repo.")
    sys.exit(1)

def check_environment_sanity():
    """
    Smoke test to ensure tools are actually executable.
    Detects broken venvs where files exist but paths are wrong.
    """
    required_tools = ["bandit", "ruff", "radon"]
    print("🔍 Performing Environment Smoke Test...")
    
    for tool in required_tools:
        try:
            # We try to run '--version' which is fast and harmless
            # capturing output prevents spamming the logs
            subprocess.run(
                [tool, "--version"],  # nosec B603 - tool names are hardcoded, not user input
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ Sanity Check Failed: '{tool}' is not working correctly.")
            print("   -> Your virtual environment might be corrupted or moved.")
            print("   -> Tip: Delete .venv and run 'uv sync' or 'pip install -r requirements.txt'")
            return False
            
    print("✅ Environment is healthy.")
    return True

def main():
    parser = argparse.ArgumentParser(description="Run PR Audit for CI/CD")
    parser.add_argument("--branch", default="main", help="Target branch for diff (default: main)")
    args = parser.parse_args()

    # 1. Sanity Check (The fix for the issue you mentioned)
    if not check_environment_sanity():
        sys.exit(1)

    print(f"🚀 Starting PR Audit against branch: {args.branch}")

    try:
        # 2. Run the Audit Logic
        # We pass run_tests=True to ensure safety
        report_json = _audit_pr_changes_logic(
            path=".", 
            base_branch=args.branch, 
            run_tests=True
        )
        
        # 3. Parse Result
        # The logic function returns a JSON string, we need to parse it
        data = json.loads(report_json)
        score = data.get("score", 0)
        report_md = data.get("report", "")

        # 4. Print Report for GitHub Actions Logs
        print("\n" + "="*50)
        print(report_md)
        print("="*50 + "\n")

        # 5. Decision Logic
        if score < 80:
            print(f"❌ Audit Failed! Score: {score}/100 (Threshold: 80)")
            sys.exit(1) # Fail the Pipeline
        else:
            print(f"✅ Audit Passed! Score: {score}/100")
            sys.exit(0) # Pass the Pipeline

    except Exception as e:
        print(f"💥 Fatal Error during audit: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
