"""Pydantic schemas for ProjectAuditAgent."""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class AuditRequest(BaseModel):
    """Request model for project audit."""
    path: str = Field(..., description="Absolute path to the project directory")
    dry_run: bool = Field(default=False, description="If true, only analyze without generating report")
    tools: Optional[List[str]] = Field(default=None, description="Specific tools to run (None = all)")
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate that path exists and is a directory."""
        p = Path(v)
        if not p.exists():
            raise ValueError(f"Path does not exist: {v}")
        if not p.is_dir():
            raise ValueError(f"Path is not a directory: {v}")
        return str(p.absolute())


class ToolResult(BaseModel):
    """Result from a single analysis tool."""
    tool_name: str
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    execution_time: float = 0.0


class AuditResult(BaseModel):
    """Complete audit result."""
    report_id: str
    project_path: str
    timestamp: datetime = Field(default_factory=datetime.now)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    tool_results: Dict[str, ToolResult] = Field(default_factory=dict)
    report_path: Optional[str] = None
    summary: str = ""
    total_execution_time: float = 0.0


class ToolInfo(BaseModel):
    """Information about an available tool."""
    name: str
    description: str
    version: str = "1.0.0"
    enabled: bool = True


class ToolRunRequest(BaseModel):
    """Request to run a specific tool."""
    path: str
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate that path exists."""
        p = Path(v)
        if not p.exists():
            raise ValueError(f"Path does not exist: {v}")
        return str(p.absolute())


class ReportResponse(BaseModel):
    """Response containing report content."""
    report_id: str
    content: str
    format: str = "markdown"
    generated_at: datetime
