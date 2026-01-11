"""Templates for generating diverse audit dataset examples.

This module contains templates and generators for creating realistic,
varied examples across all 13 audit tools.
"""

# Security Tool Templates (Bandit B-codes)
SECURITY_TEMPLATES = {
    "B101": {
        "name": "assert_used",
        "risk": "Medium",
        "scenarios": [
            ("validators.py", "assert user.is_authenticated", "authentication check"),
            ("payment_processor.py", "assert amount > 0", "payment validation"),
            ("config_validator.py", "assert os.path.exists(config_file)", "file check"),
            ("api_middleware.py", "assert request.headers.get('API-Key')", "API key check"),
        ]
    },
    "B105": {
        "name": "hardcoded_password_string",
        "risk": "Critical",
        "scenarios": [
            ("config.py", "DATABASE_PASSWORD = 'MySecretPass123'", "database password"),
            ("api_client.py", "API_KEY = 'sk-1234567890abcdef'", "API key"),
            ("constants.py", "DEFAULT_PASSWORD = 'changeme'", "default password"),
            ("setup.py", "ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')", "fallback password"),
        ]
    },
    "B201": {
        "name": "flask_debug_true",
        "risk": "High",
        "scenarios": [
            ("app.py", "app.run(debug=True)", "debug mode"),
            ("server.py", "app.config['DEBUG'] = True", "debug config"),
            ("__init__.py", "app.debug = True", "debug attribute"),
        ]
    },
    "B301": {
        "name": "pickle",
        "risk": "Critical",
        "scenarios": [
            ("cache.py", "data = pickle.loads(cached_value)", "cache deserialization"),
            ("session_manager.py", "session_data = pickle.load(session_file)", "session loading"),
        ]
    },
    "B303": {
        "name": "md5",
        "risk": "High",
        "scenarios": [
            ("password_hasher.py", "hashlib.md5(password.encode()).hexdigest()", "password hashing"),
            ("api_signature.py", "hashlib.md5(f'{timestamp}{secret}'.encode()).hexdigest()", "API signature"),
        ]
    },
    "B608": {
        "name": "hardcoded_sql_expressions",
        "risk": "Critical",
        "scenarios": [
            ("query.py", "cursor.execute(f'SELECT * FROM users WHERE id={user_id}')", "SQL query"),
            ("search.py", "f\"SELECT * FROM products WHERE name LIKE '%{search_term}%'\"", "search query"),
        ]
    },
}

# Architecture Tool Templates
ARCHITECTURE_TEMPLATES = [
    {
        "issue": "Monolithic main.py",
        "structure": "app/\n├── main.py (850 lines)\n├── models.py\n└── utils.py",
        "severity": "High",
        "recommendation": "Split into routers, services, schemas"
    },
    {
        "issue": "Circular imports",
        "structure": "app.py imports models.py\nmodels.py imports app.py",
        "severity": "Critical",
        "recommendation": "Use dependency injection or factory pattern"
    },
    {
        "issue": "No tests directory",
        "structure": "src/\n├── app/\n└── utils/\nNo tests/ found",
        "severity": "High",
        "recommendation": "Create tests/ with pytest structure"
    },
]

# Dead Code Templates
DEADCODE_TEMPLATES = [
    {
        "function": "parse_xml",
        "decorator": "@register_handler",
        "verdict": "FALSE POSITIVE",
        "reason": "Dynamically registered via decorator"
    },
    {
        "function": "old_process_data",
        "decorator": None,
        "verdict": "REAL DEAD CODE",
        "reason": "No references found, no dynamic usage"
    },
    {
        "function": "__init__",
        "decorator": None,
        "verdict": "FALSE POSITIVE",
        "reason": "Magic method called by Python runtime"
    },
]

# Duplication Templates
DUPLICATION_TEMPLATES = [
    {
        "files": ["tests/test_user.py", "tests/test_admin.py"],
        "similarity": 95,
        "context": "setup() methods in test fixtures",
        "verdict": "ACCEPTABLE",
        "reason": "Test isolation requires duplicate setup"
    },
    {
        "files": ["api/users.py", "api/products.py"],
        "similarity": 88,
        "context": "CRUD endpoint implementations",
        "verdict": "REFACTOR NEEDED",
        "reason": "Extract to generic CRUDBase class"
    },
]

# Efficiency Templates
EFFICIENCY_TEMPLATES = [
    {
        "issue": "String concatenation in loop",
        "code": "for item in items:\n    result += str(item)",
        "severity": "Medium",
        "fix": "Use ''.join() or list append"
    },
    {
        "issue": "Nested loops depth 3",
        "code": "for x in range(n):\n    for y in range(m):\n        for z in range(k):",
        "severity": "High",
        "fix": "Use list comprehension or vectorization"
    },
]

# Test Coverage Templates
TEST_TEMPLATES = [
    {
        "files": 0,
        "tests": 0,
        "coverage": "N/A",
        "verdict": "REAL ISSUE",
        "severity": "Critical"
    },
    {
        "files": 45,
        "tests": 45,
        "coverage": "85%",
        "verdict": "ACCEPTABLE",
        "severity": "None"
    },
]

def generate_security_example(code, scenario, risk_level):
    """Generate a security finding example."""
    file, code_snippet, context = scenario
    return {
        "instruction": f"Analyze this Bandit finding: {code} in {file}\nCode: {code_snippet}",
        "output": f"REAL ISSUE: {context}\n\nRisk Level: {risk_level}\n\nExplanation: [Security explanation]\n\nRecommendation: [Fix with code example]"
    }

def generate_architecture_example(template):
    """Generate an architecture issue example."""
    return {
        "instruction": f"Analyze this project structure:\n{template['structure']}\nIssue: {template['issue']}",
        "output": f"Analysis: {template['issue']}\n\nIssues Found:\n1. [{template['severity']}] {template['issue']}\n\nRecommendation: {template['recommendation']}"
    }

def generate_deadcode_example(template):
    """Generate a dead code example."""
    decorator_text = f"\nDecorator: {template['decorator']}" if template['decorator'] else ""
    return {
        "instruction": f"Analyze dead code warning:\nFunction: {template['function']}{decorator_text}",
        "output": f"{template['verdict']}: {template['reason']}"
    }
