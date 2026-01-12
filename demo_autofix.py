"""Demo script to test AutoFixOrchestrator on unused imports."""
from pathlib import Path
from app.core.fix_orchestrator import AutoFixOrchestrator

def main():
    print("=" * 60)
    print("🔧 AUTO-FIX DEMO: Unused Imports Cleanup")
    print("=" * 60)
    print()
    
    # Initialize the orchestrator
    orchestrator = AutoFixOrchestrator(project_path=".")
    
    # Run the cleanup mission
    result = orchestrator.run_cleanup_mission()
    
    print()
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    if result:
        print(f"Status: {result['status']}")
        print(f"Fixes Applied: {result['fixes_applied']}")
        print(f"Files Modified: {len(result['files_modified'])}")
        for file in result['files_modified']:
            print(f"  • {file}")
    print()
    print("💡 TIP: Check .bak files to restore if needed")
    print("=" * 60)

if __name__ == "__main__":
    main()
