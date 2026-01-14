# Type Hint Coverage and Architecture Analysis Functions
# These will be added to mcp_fastmcp_server.py after run_architecture_visualizer

def analyze_type_hints(path: Path) -> dict:
    """
    Analyze type hint coverage across all Python functions.
    Returns percentage coverage and examples of untyped functions.
    """
    import ast
    
    try:
        target = Path(path).resolve()
        py_files = [f for f in target.glob("**/*.py") 
                   if ".venv" not in str(f) and "venv" not in str(f)]
        
        fully_typed = []
        partially_typed = []
        untyped = []
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=str(py_file))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Get relative path
                        rel_path = py_file.relative_to(target)
                        func_sig = f"{rel_path}:{node.name}()"
                        
                        # Check return type
                        has_return_type = node.returns is not None
                        
                        # Check argument types
                        args_typed = all(
                            arg.annotation is not None 
                            for arg in node.args.args 
                            if arg.arg != 'self' and arg.arg != 'cls'
                        )
                        
                        total_args = len([arg for arg in node.args.args 
                                        if arg.arg != 'self' and arg.arg != 'cls'])
                        
                        if has_return_type and args_typed and total_args > 0:
                            fully_typed.append(func_sig)
                        elif (has_return_type or args_typed) and total_args > 0:
                            partially_typed.append(func_sig)
                        elif total_args > 0:  # Only count functions with args
                            untyped.append(func_sig)
                            
            except (SyntaxError, UnicodeDecodeError):
                continue
        
        total_funcs = len(fully_typed) + len(partially_typed) + len(untyped)
        coverage_pct = (len(fully_typed) / total_funcs * 100) if total_funcs > 0 else 0
        
        # Grade based on coverage
        if coverage_pct >= 90:
            grade = "A+"
        elif coverage_pct >= 80:
            grade = "A"
        elif coverage_pct >= 70:
            grade = "B"
        elif coverage_pct >= 60:
            grade = "C"
        elif coverage_pct >= 50:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "tool": "type_hints",
            "status": "analyzed",
            "coverage_percent": round(coverage_pct, 1),
            "grade": grade,
            "fully_typed": len(fully_typed),
            "partially_typed": len(partially_typed),
            "untyped": len(untyped),
            "total_functions": total_funcs,
            "untyped_examples": untyped[:10]  # First 10 examples
        }
        
    except Exception as e:
        return {"tool": "type_hints", "status": "error", "error": str(e)}


def analyze_architecture_issues(path: Path) -> dict:
    """
    Check for FastAPI/Flask best practice architecture patterns.
    Returns warnings for missing standard directories.
    """
    try:
        target = Path(path).resolve()
        issues = []
        
        # Check for FastAPI patterns
        app_dir = target / "app"
        if app_dir.exists():
            # Check for routers/
            if not (app_dir / "routers").exists() and not (app_dir / "routes").exists():
                issues.append({
                    "severity": "🟡",
                    "category": "FastAPI Structure",
                    "message": "No routers/ directory in FastAPI app",
                    "recommendation": "Consider organizing endpoints in routers/"
                })
            
            # Check for models/ or schemas/
            if not (app_dir / "models").exists() and not (app_dir / "schemas").exists():
                issues.append({
                    "severity": "🟡",
                    "category": "Data Models",
                    "message": "No models/ or schemas/ directory",
                    "recommendation": "Consider separating Pydantic models"
                })
            
            # Check for services/ or core/
            if not (app_dir / "services").exists() and not (app_dir / "core").exists():
                issues.append({
                    "severity": "🔵",
                    "category": "Business Logic",
                    "message": "No services/ or core/ directory",
                    "recommendation": "Consider separating business logic"
                })
        
        # Check for tests/
        if not (target / "tests").exists() and not (target / "test").exists():
            issues.append({
                "severity": "🔴",
                "category": "Testing",
                "message": "No tests/ directory found",
                "recommendation": "Add tests directory with unit/integration tests"
            })
        
        return {
            "tool": "architecture_issues",
            "status": "analyzed",
            "total_issues": len(issues),
            "issues": issues
        }
        
    except Exception as e:
        return {"tool": "architecture_issues", "status": "error", "error": str(e)}
