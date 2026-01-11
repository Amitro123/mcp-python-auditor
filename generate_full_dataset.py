import json
import random
from pathlib import Path

# --- Configuration ---
TARGET_COUNT = 500
OUTPUT_FILE = Path("data/audit_dataset_500.jsonl")

# --- Generators for each tool ---

def gen_security_bandit():
    """Generates 100 Security (Bandit) examples."""
    examples = []
    
    # Templates for specific B-codes
    templates = [
        {
            "code": "B101", "name": "assert_used", "risk": "Low",
            "sinks": ["val.py", "auth.py", "logic.py"],
            "snippets": ["assert user.is_admin", "assert price > 0", "assert token"],
            "fix": "if not condition: raise Error()"
        },
        {
            "code": "B105", "name": "hardcoded_password_string", "risk": "High",
            "sinks": ["config.py", "settings.py", "consts.py"],
            "snippets": ["PASS = 'secret123'", "KEY = 'xcv987'", "TOKEN = '123456'"],
            "fix": "Use os.getenv()"
        },
        {
            "code": "B201", "name": "flask_debug_true", "risk": "High",
            "sinks": ["app.py", "main.py", "run.py"],
            "snippets": ["app.run(debug=True)", "app.run(port=80, debug=True)"],
            "fix": "debug=False in prod"
        },
        {
            "code": "B301", "name": "pickle", "risk": "High",
            "sinks": ["cache.py", "data.py"],
            "snippets": ["pickle.loads(data)", "pickle.load(f)"],
            "fix": "Use json or safe serialization"
        },
        {
            "code": "B608", "name": "hardcoded_sql_expressions", "risk": "Critical",
            "sinks": ["db.py", "query.py", "repo.py"],
            "snippets": ["f'SELECT * FROM t WHERE id={id}'", "'SELECT * FROM t WHERE n=' + name"],
            "fix": "Use parameterized queries"
        },
         {
            "code": "B303", "name": "md5", "risk": "Medium",
            "sinks": ["hashing.py", "util.py"],
            "snippets": ["hashlib.md5(data)", "hashlib.md5()"],
            "fix": "Use SHA256 or bcrypt"
        },
         {
            "code": "B104", "name": "hardcoded_bind_all_interfaces", "risk": "Medium",
            "sinks": ["server.py", "socket_listener.py"],
            "snippets": ["bind('0.0.0.0')", "run(host='0.0.0.0')"],
            "fix": "Bind to specific interface or use config"
        },
         {
            "code": "B603", "name": "subprocess_without_shell_equals_true", "risk": "Low",
            "sinks": ["process.py", "cmd.py"],
            "snippets": ["subprocess.call(cmd)", "subprocess.Popen(args)"],
            "fix": "Ensure inputs are trusted"
        },
         {
            "code": "B108", "name": "hardcoded_tmp_directory", "risk": "Medium",
            "sinks": ["file_handler.py", "upload.py"],
            "snippets": ["open('/tmp/f')", "path = '/tmp/' + name"],
            "fix": "Use tempfile module"
        },
         {
            "code": "B506", "name": "yaml_load", "risk": "High",
            "sinks": ["config_loader.py", "parser.py"],
            "snippets": ["yaml.load(f)", "yaml.load(stream)"],
            "fix": "Use yaml.safe_load()"
        }
    ]

    for _ in range(100):
        t = random.choice(templates)
        is_real = random.random() > 0.3 # 70% Real, 30% False Positive
        
        fname = random.choice(t["sinks"])
        line = random.randint(10, 200)
        snippet = random.choice(t["snippets"])
        
        if is_real:
            verdict = "REAL ISSUE"
            expl = f"Found {t['name']} pattern which is a security risk."
        else:
            verdict = "FALSE POSITIVE"
            expl = "Context indicates this usage is safe or intended for testing."
            
        instruction = f"Analyze this Bandit finding: {t['code']} {t['name']} in {fname} line {line}\nCode:\n{snippet}"
        output = f"{verdict}: {t['code']} detected.\n\nRisk Level: {t['risk']}\n\nExplanation: {expl}\n\nRecommendation: {t['fix']}."
        examples.append({"instruction": instruction, "output": output})
        
    return examples

def gen_architecture():
    """Generates 50 Architecture examples."""
    examples = []
    
    scenarios = [
        ("Monolithic main.py", "app/main.py is 1000 lines.", "Split into routers/services"),
        ("Circular Imports", "models.py imports views.py", "Break dependency cycle"),
        ("No Routers", "All endpoints in one file", "Create app/routers"),
        ("Missing Tests", "No tests/ directory", "Add tests folder"),
        ("God Object", "Manager class does generic logic and DB access", "Separate concerns"),
        ("Hardcoded Config", "Config in code files", "Use pydantic-settings"),
        ("Logic in View", "Heavy logic in endpoint handler", "Move to service layer"),
        ("Direct DB Access", "View calls DB directly", "Use Repository pattern")
    ]
    
    for _ in range(50):
        s = random.choice(scenarios)
        instruction = f"Analyze architecture finding:\nIssue: {s[0]}\nContext: {s[1]}\n\nIs this problematic?"
        output = f"REAL ISSUE: {s[0]} breaks clean architecture.\n\nExplanation: {s[1]}.\n\nRecommendation: {s[2]}."
        examples.append({"instruction": instruction, "output": output})
    return examples

def gen_dead_code():
    """Generates 50 Dead Code examples."""
    examples = []
    
    for _ in range(50):
        is_real = random.random() > 0.5
        func = f"func_{random.randint(1,100)}"
        file = f"service_{random.randint(1,10)}.py"
        
        if is_real:
            inst = f"Analyze dead code: Function {func} in {file} has 0 references."
            out = f"REAL DEAD CODE: Function {func} is unused.\n\nRecommendation: Remove or deprecate."
        else:
            deco = random.choice(["@app.route", "@celery.task", "@on_event"])
            inst = f"Analyze dead code: Function {func} in {file}\nDecorator: {deco}"
            out = f"FALSE POSITIVE: Function usage is dynamic via {deco}."
            
        examples.append({"instruction": inst, "output": out})
    return examples

def gen_duplication():
    """Generates 40 Duplication examples."""
    examples = []
    for _ in range(40):
        files = f"file_{random.randint(1,5)}.py, file_{random.randint(6,10)}.py"
        sim = random.randint(80, 100)
        
        is_test = random.random() > 0.6
        if is_test:
            inst = f"Duplication: {files} have {sim}% similarity.\nContext: Test fixtures setup."
            out = "ACCEPTABLE: Duplication in tests is often acceptable for isolation."
        else:
            inst = f"Duplication: {files} have {sim}% similarity.\nContext: Business logic validation."
            out = "REFACTOR NEEDED: High duplication in logic.\n\nRecommendation: Extract common logic to utility."
            
        examples.append({"instruction": inst, "output": out})
    return examples

def gen_efficiency():
    """Generates 40 Efficiency examples."""
    examples = []
    problems = [
        ("N+1 Query", "Loop executing DB query", "Use .joinedload()"),
        ("String Concat", "s += str in loop", "Use list join"),
        ("Global Regex", "re.compile inside loop", "Compile once globally"),
        ("Heavy Import", "Import inside function loop", "Move import to top"),
        ("Sync call", "Blocking I/O in async def", "Use async alternative")
    ]
    
    for _ in range(40):
        p = random.choice(problems)
        inst = f"Analyze efficiency finding: {p[0]}.\nCode Context: {p[1]}"
        out = f"REAL ISSUE: Performance bottleneck detected.\n\nExplanation: {p[1]}.\n\nRecommendation: {p[2]}."
        examples.append({"instruction": inst, "output": out})
    return examples

def gen_tests():
    """Generates 40 Test Coverage examples."""
    examples = []
    for i in range(40):
        cov = random.randint(0, 95)
        inst = f"Test Coverage Report:\nFiles: 20\nTests: {i*2}\nCoverage: {cov}%"
        
        if cov < 60:
            out = f"REAL ISSUE: Coverage {cov}% is below threshold (60%).\n\nRecommendation: Add unit tests."
        elif cov < 80:
             out = f"WARNING: Coverage {cov}% is adequate but can improve."
        else:
             out = f"ACCEPTABLE: Coverage {cov}% is excellent."
             
        examples.append({"instruction": inst, "output": out})
    return examples

def gen_generic_tool(name, count, issues):
    """Generic generator for smaller tool categories."""
    examples = []
    for _ in range(count):
        iss = random.choice(issues)
        inst = f"Analyze {name} finding:\nIssue: {iss[0]}"
        out = f"REAL ISSUE: {iss[1]}\n\nRecommendation: {iss[2]}"
        examples.append({"instruction": inst, "output": out})
    return examples

def gen_pr_review():
    """Generates 30 PR Review examples."""
    examples = []
    reviews = [
        ("Added new endpoint without auth", "Security risk", "Add @login_required"),
        ("Modified db model no migration", "Ops risk", "Generate migration script"),
        ("Added large file to git", "Repo size risk", "Remove and use .gitignore"),
        ("Refactored UserClass", "Good change", "Approve"),
        ("Added 500 lines test", "Good coverage", "Approve")
    ]
    for _ in range(30):
        r = random.choice(reviews)
        inst = f"PR Review analysis:\nChange: {r[0]}"
        if "Approve" in r[2]:
            out = f"Outcome: APPROVE\n\nReason: {r[1]}."
        else:
            out = f"Outcome: REQUEST CHANGES\n\nIssue: {r[1]}.\nAction: {r[2]}."
        examples.append({"instruction": inst, "output": out})
    return examples

# --- Main Generation Logic ---

def generate_full_dataset():
    all_examples = []
    
    all_examples += gen_security_bandit() # 100
    all_examples += gen_architecture()    # 50
    all_examples += gen_dead_code()       # 50
    all_examples += gen_duplication()     # 40
    all_examples += gen_efficiency()      # 40
    all_examples += gen_tests()           # 40
    
    # Structure (30)
    all_examples += gen_generic_tool("Structure", 30, [
        ("Nest folders too deep", "Hard to navigate", "Flatten structure"),
        ("Mixed file types", "Cluttered", "Group by type"),
        ("Non-standard naming", "Confusing", "Use snake_case")
    ])
    
    # Cleanup (30)
    all_examples += gen_generic_tool("Cleanup", 30, [
        ("Found .pyc files", "Generated files committed", "Remove and .gitignore"),
        ("Large logs folder", "Wasting space", "Rotate and exclude"),
        ("tmp files", "Temporary junk", "Delete")
    ])
    
    # Secrets (30)
    all_examples += gen_generic_tool("Secrets", 30, [
        (".env file committed", "Exposed secrets", "Remove from git history"),
        ("AWS Key in comments", "Potential leak", "Remove immediately"),
        ("Private Key file", "Security risk", "Add to .gitignore")
    ])

    # Git (30)
    all_examples += gen_generic_tool("Git", 30, [
        ("Large binary file", "Repo bloat", "Use LFS"),
        ("WIP commit on main", "Unstable branch", "Squash or branch"),
        ("No commit message", "Bad history", "Amend message")
    ])

    # Gitignore (30)
    all_examples += gen_generic_tool("Gitignore", 30, [
        ("Missing __pycache__", "Python artifacts", "Add __pycache__/"),
        ("Missing .env", "Secruity", "Add .env"),
        ("Missing venv", "Environment", "Add venv/")
    ])
    
    # Dependencies (30)
    all_examples += gen_generic_tool("Dependencies", 30, [
        ("Pinned old version", "Security vulns", "Upgrade package"),
        ("Circular dependency", "Import errors", "Refactor modules"),
        ("Unused dependency", "Bloat", "Remove from requirements.txt")
    ])
    
    # PR Review (30)
    all_examples += gen_pr_review()

    # Shuffle to ensure randomness in training
    random.shuffle(all_examples)
    
    # Trim to exactly 500 if we went slightly over
    final_examples = all_examples[:TARGET_COUNT]
    
    # Save
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for ex in final_examples:
            f.write(json.dumps(ex) + "\n")
            
    print(f"Successfully generated {len(final_examples)} examples in {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_full_dataset()
