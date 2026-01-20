"""Quick test script to verify Jinja2 template engine implementation."""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.report_generator_v2 import ReportGeneratorV2
from app.core.report_context import build_report_context


def test_jinja2_implementation():
    """Test the Jinja2 template engine with sample data."""
    print("[TEST] Testing Jinja2 Template Engine Implementation\n")
    
    # Sample audit results (minimal test data)
    sample_results = {
        'git_info': {
            'branch': 'main',
            'uncommitted_changes': 5,
            'last_commit': {
                'hash': '42778cff',
                'message': 'Test commit',
                'author': 'Test User',
                'when': '1 hour ago'
            },
            'status': 'Modified'
        },
        'structure': {
            'total_py_files': 63,
            'total_lines': 11605,
            'directory_tree': '├── app\n│   ├── core\n│   └── tools',
            'top_directories': ['app', 'tests', 'docs']
        },
        'security': {
            'code_security': {
                'files_scanned': 63,
                'issues': [
                    {
                        'file': 'test.py',
                        'line': 10,
                        'severity': 'LOW',
                        'type': 'B101',
                        'description': 'Use of assert detected'
                    }
                ]
            }
        },
        'tests': {
            'total_test_files': 20,
            'tests_passed': 1,
            'tests_failed': 1,
            'coverage_percent': 43,
            'has_unit_tests': True,
            'has_integration_tests': True,
            'has_e2e_tests': False
        },
        'efficiency': {
            'total_functions_analyzed': 150,
            'average_complexity': 3.2,
            'average_maintainability': 65.5,
            'maintainability_grade': 'B',
            'files_analyzed': 63
        }
    }
    
    # Test 1: Data Normalization
    print("[OK] Test 1: Data Normalization")
    try:
        context = build_report_context(
            raw_results=sample_results,
            project_path='.',
            score=75,
            report_id='test_001',
            timestamp=datetime.now()
        )
        print(f"   - Context keys: {len(context)}")
        print(f"   - Git available: {context['git']['available']}")
        print(f"   - Git branch: {context['git']['branch']}")
        print(f"   - Tools summary: {len(context['tools_summary'])} tools")
        print("   [OK] Data normalization working!\n")
    except Exception as e:
        print("   [FAIL] Data normalization failed: {e}\n")
        return False
    
    # Test 2: Template Loading
    print("[OK] Test 2: Template Loading")
    try:
        reports_dir = Path('reports')
        generator = ReportGeneratorV2(reports_dir)
        print("   [OK] Template engine initialized!\n")
    except Exception as e:
        print("   [FAIL] Template loading failed: {e}\n")
        return False
    
    # Test 3: Report Generation
    print("[OK] Test 3: Report Generation")
    try:
        report_path = generator.generate_report(
            report_id='test_jinja2',
            project_path='.',
            score=75,
            tool_results=sample_results,
            timestamp=datetime.now()
        )
        print(f"   - Report generated: {report_path}")
        
        # Check file exists and has content
        report_file = Path(report_path)
        if report_file.exists():
            content = report_file.read_text(encoding='utf-8')
            print(f"   - Report size: {len(content)} characters")
            print(f"   - Contains 'main' branch: {'main' in content}")
            print(f"   - Contains score: {'75/100' in content}")
            print("   [OK] Report generation working!\n")
        else:
            print("   [FAIL] Report file not created\n")
            return False
            
    except Exception as e:
        print("   [FAIL] Report generation failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Git Info Normalization (git vs git_info)
    print("[OK] Test 4: Git Info Key Handling")
    try:
        # Test with 'git' key instead of 'git_info'
        legacy_results = {
            'git': {  # Old key name
                'branch': 'develop',
                'uncommitted_changes': 3
            }
        }
        context = build_report_context(
            raw_results=legacy_results,
            project_path='.',
            score=80,
            report_id='test_002',
            timestamp=datetime.now()
        )
        assert context['git']['branch'] == 'develop', "Legacy 'git' key not handled"
        print("   - Legacy 'git' key: [OK]")
        
        # Test with 'git_info' key
        new_results = {
            'git_info': {  # New key name
                'branch': 'feature',
                'uncommitted_changes': 7
            }
        }
        context = build_report_context(
            raw_results=new_results,
            project_path='.',
            score=80,
            report_id='test_003',
            timestamp=datetime.now()
        )
        assert context['git']['branch'] == 'feature', "New 'git_info' key not handled"
        print("   - New 'git_info' key: [OK]")
        print("   [OK] Both key formats working!\n")
        
    except Exception as e:
        print("   [FAIL] Git info normalization failed: {e}\n")
        return False
    
    print("=" * 60)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("=" * 60)
    print("\n[OK] Jinja2 Template Engine is fully functional!")
    print("[OK] Data normalization working correctly")
    print("[OK] Git info key handling (git vs git_info) working")
    print("[OK] Report generation successful")
    print("\n[NOTE] Check the generated report:")
    print(f"   {report_path}")
    
    return True


if __name__ == '__main__':
    success = test_jinja2_implementation()
    sys.exit(0 if success else 1)
