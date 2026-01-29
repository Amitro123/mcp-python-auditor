from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Union

class Severity(BaseModel):
    label: str
    description: str
    recommendation: Optional[str] = None
    count: Optional[int] = None
    level: Optional[str] = None

class ToolSummary(BaseModel):
    name: str
    status: str
    details: str
    duration_s: str

class TemplateContext(BaseModel):
    """
    Pydantic model defining the expected structure for the audit report Jinja2 template.
    All fields sent to the template must be validated against this schema.
    """
    
    # === Metadata ===
    project_name: str
    repo_name: str
    score: int = Field(ge=0, le=100)
    grade: str = Field(pattern=r"^[A-F]$")
    report_id: str
    timestamp: str
    date: str
    time: str
    duration: str

    # === Penalties ===
    security_penalty: int = Field(ge=0)
    testing_penalty: int = Field(ge=0)
    quality_penalty: int = Field(ge=0)

    # === Severity Labels ===
    security_severity: Union[Severity, Dict[str, Any]]
    coverage_severity: Union[Severity, Dict[str, Any]]

    # === Sections (Dicts for flexibility, but verified presence) ===
    git: Dict[str, Any]
    structure: Dict[str, Any]
    architecture: Dict[str, Any]
    security: Dict[str, Any]
    secrets: Dict[str, Any]
    tests: Dict[str, Any]
    complexity: Dict[str, Any]
    efficiency: Dict[str, Any]
    duplication: Dict[str, Any]
    quality: Dict[str, Any]
    deadcode: Dict[str, Any]
    cleanup: Dict[str, Any]
    typing: Dict[str, Any]
    gitignore: Dict[str, Any]

    # === Lists ===
    tools_summary: List[ToolSummary]
    top_priorities: List[Dict[str, Any]]

    # === Integrity ===
    all_sections_present: bool = True
    missing_sections: List[str] = []
    
    # === Raw Data (Optional but usually present) ===
    raw_results: Optional[Dict[str, Any]] = None

    class Config:
        strict = False
