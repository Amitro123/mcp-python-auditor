"""CI/CD Pipeline Generator - Generate audit pipelines for various platforms.

Generates:
- GitHub Actions workflows
- GitLab CI pipelines
- Bitbucket Pipelines
- Pre-commit hooks
- PR templates
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class CIGenerator:
    """Generate CI/CD pipeline configurations for Python Auditor integration."""

    def __init__(self, project_path: Path, score_threshold: int = 70):
        """
        Initialize CI generator.

        Args:
            project_path: Root path of the target project
            score_threshold: Minimum score to pass CI (default: 70)
        """
        self.project_path = Path(project_path).resolve()
        self.score_threshold = score_threshold

    def generate_github_actions(self, auto_fix: bool = True) -> str:
        """
        Generate GitHub Actions workflow for PR audits.

        Args:
            auto_fix: If True, include auto-fix step for formatting

        Returns:
            Path to the generated workflow file
        """
        workflow_dir = self.project_path / ".github" / "workflows"
        workflow_dir.mkdir(parents=True, exist_ok=True)

        workflow_content = f'''# Python Auditor CI Pipeline
# Runs security, quality, and coverage checks on every PR

name: Python Audit

on:
  pull_request:
    branches: [main, master, develop]
  push:
    branches: [main, master]

permissions:
  contents: read
  pull-requests: write

jobs:
  audit:
    name: Code Audit
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for accurate diff

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install bandit ruff vulture radon detect-secrets pip-audit pytest pytest-cov
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi

      - name: Run Bandit (Security)
        id: bandit
        continue-on-error: true
        run: |
          bandit -r . -f json -o bandit-results.json --exit-zero || true
          ISSUES=$(python -c "import json; d=json.load(open('bandit-results.json')); print(len(d.get('results',[])))")
          echo "issues=$ISSUES" >> $GITHUB_OUTPUT
          echo "### Security Scan" >> $GITHUB_STEP_SUMMARY
          echo "Found **$ISSUES** security issues" >> $GITHUB_STEP_SUMMARY

      - name: Run Ruff (Linting)
        id: ruff
        continue-on-error: true
        run: |
          ruff check . --output-format=json > ruff-results.json || true
          ISSUES=$(python -c "import json; print(len(json.load(open('ruff-results.json'))))")
          echo "issues=$ISSUES" >> $GITHUB_OUTPUT
          echo "### Code Quality" >> $GITHUB_STEP_SUMMARY
          echo "Found **$ISSUES** linting issues" >> $GITHUB_STEP_SUMMARY
'''

        if auto_fix:
            workflow_content += '''
      - name: Auto-fix formatting
        if: github.event_name == 'pull_request'
        run: |
          ruff check . --fix --exit-zero
          ruff format .
          git diff --exit-code || echo "::notice::Code was auto-formatted"
'''

        workflow_content += f'''
      - name: Run Tests with Coverage
        id: tests
        continue-on-error: true
        run: |
          pytest --cov=. --cov-report=json --cov-report=term -q || true
          if [ -f coverage.json ]; then
            COV=$(python -c "import json; print(int(json.load(open('coverage.json'))['totals']['percent_covered']))")
          else
            COV=0
          fi
          echo "coverage=$COV" >> $GITHUB_OUTPUT
          echo "### Test Coverage" >> $GITHUB_STEP_SUMMARY
          echo "Coverage: **$COV%**" >> $GITHUB_STEP_SUMMARY

      - name: Calculate Score
        id: score
        run: |
          BANDIT=${{{{ steps.bandit.outputs.issues }}}}
          RUFF=${{{{ steps.ruff.outputs.issues }}}}
          COV=${{{{ steps.tests.outputs.coverage }}}}

          # Score calculation (simplified)
          SCORE=100
          # Security penalties (max -30)
          if [ "$BANDIT" -gt 0 ]; then
            PENALTY=$((BANDIT * 5))
            [ $PENALTY -gt 30 ] && PENALTY=30
            SCORE=$((SCORE - PENALTY))
          fi
          # Quality penalties (max -20)
          if [ "$RUFF" -gt 0 ]; then
            PENALTY=$((RUFF / 5))
            [ $PENALTY -gt 20 ] && PENALTY=20
            SCORE=$((SCORE - PENALTY))
          fi
          # Coverage penalties (max -30)
          if [ "$COV" -lt 70 ]; then
            PENALTY=$((70 - COV))
            [ $PENALTY -gt 30 ] && PENALTY=30
            SCORE=$((SCORE - PENALTY))
          fi

          echo "score=$SCORE" >> $GITHUB_OUTPUT
          echo "## Audit Score: $SCORE/100" >> $GITHUB_STEP_SUMMARY

      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const score = ${{{{ steps.score.outputs.score }}}};
            const bandit = ${{{{ steps.bandit.outputs.issues }}}};
            const ruff = ${{{{ steps.ruff.outputs.issues }}}};
            const coverage = ${{{{ steps.tests.outputs.coverage }}}};

            let emoji = score >= 90 ? '🟢' : score >= 70 ? '🟡' : '🔴';
            let status = score >= {self.score_threshold} ? 'PASSED' : 'FAILED';

            const body = `## ${{emoji}} Python Audit: ${{status}}

            | Metric | Value |
            |--------|-------|
            | **Score** | ${{score}}/100 |
            | **Security Issues** | ${{bandit}} |
            | **Linting Issues** | ${{ruff}} |
            | **Test Coverage** | ${{coverage}}% |

            ${{score < {self.score_threshold} ? '> **Action Required:** Score is below the threshold of {self.score_threshold}. Please fix the issues above.' : '> All checks passed! Ready for review.'}}

            ---
            *Generated by Python Auditor*`;

            github.rest.issues.createComment({{
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: body
            }});

      - name: Check Score Threshold
        run: |
          SCORE=${{{{ steps.score.outputs.score }}}}
          if [ "$SCORE" -lt {self.score_threshold} ]; then
            echo "::error::Audit score ($SCORE) is below threshold ({self.score_threshold})"
            exit 1
          fi
          echo "Audit passed with score: $SCORE"
'''

        workflow_path = workflow_dir / "audit.yml"
        with open(workflow_path, 'w', encoding='utf-8') as f:
            f.write(workflow_content)

        logger.info(f"Generated GitHub Actions workflow: {workflow_path}")
        return str(workflow_path)

    def generate_gitlab_ci(self, auto_fix: bool = True) -> str:
        """
        Generate GitLab CI pipeline for audits.

        Returns:
            Path to the generated .gitlab-ci.yml file
        """
        ci_content = f'''# Python Auditor CI Pipeline for GitLab

stages:
  - audit
  - report

variables:
  SCORE_THRESHOLD: "{self.score_threshold}"
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.pip-cache"

cache:
  paths:
    - .pip-cache/
    - .venv/

.python-setup: &python-setup
  image: python:3.11-slim
  before_script:
    - python -m pip install --upgrade pip
    - pip install bandit ruff vulture radon detect-secrets pip-audit pytest pytest-cov
    - if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

security-scan:
  <<: *python-setup
  stage: audit
  script:
    - bandit -r . -f json -o bandit-results.json --exit-zero || true
    - echo "BANDIT_ISSUES=$(python -c \\"import json; d=json.load(open('bandit-results.json')); print(len(d.get('results',[])))\\")\" >> audit.env
  artifacts:
    reports:
      dotenv: audit.env
    paths:
      - bandit-results.json
    expire_in: 1 week
  allow_failure: true

lint-check:
  <<: *python-setup
  stage: audit
  script:
    - ruff check . --output-format=json > ruff-results.json || true
    - echo "RUFF_ISSUES=$(python -c \\"import json; print(len(json.load(open('ruff-results.json'))))\\")\" >> audit.env
'''

        if auto_fix:
            ci_content += '''    - ruff check . --fix --exit-zero
    - ruff format .
'''

        ci_content += f'''  artifacts:
    reports:
      dotenv: audit.env
    paths:
      - ruff-results.json
    expire_in: 1 week
  allow_failure: true

test-coverage:
  <<: *python-setup
  stage: audit
  script:
    - pytest --cov=. --cov-report=xml --cov-report=term -q || true
    - >
      if [ -f coverage.xml ]; then
        COV=$(python -c "import xml.etree.ElementTree as ET; print(int(float(ET.parse('coverage.xml').getroot().get('line-rate', 0)) * 100))")
      else
        COV=0
      fi
    - echo "COVERAGE=$COV" >> audit.env
  coverage: '/TOTAL.*\\s+(\\d+%)/'
  artifacts:
    reports:
      dotenv: audit.env
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
    expire_in: 1 week
  allow_failure: true

audit-report:
  <<: *python-setup
  stage: report
  needs:
    - job: security-scan
      artifacts: true
    - job: lint-check
      artifacts: true
    - job: test-coverage
      artifacts: true
  script:
    - |
      # Calculate score
      SCORE=100
      BANDIT=${{BANDIT_ISSUES:-0}}
      RUFF=${{RUFF_ISSUES:-0}}
      COV=${{COVERAGE:-0}}

      # Security penalties
      if [ "$BANDIT" -gt 0 ]; then
        PENALTY=$((BANDIT * 5))
        [ $PENALTY -gt 30 ] && PENALTY=30
        SCORE=$((SCORE - PENALTY))
      fi

      # Quality penalties
      if [ "$RUFF" -gt 0 ]; then
        PENALTY=$((RUFF / 5))
        [ $PENALTY -gt 20 ] && PENALTY=20
        SCORE=$((SCORE - PENALTY))
      fi

      # Coverage penalties
      if [ "$COV" -lt 70 ]; then
        PENALTY=$((70 - COV))
        [ $PENALTY -gt 30 ] && PENALTY=30
        SCORE=$((SCORE - PENALTY))
      fi

      echo "=== AUDIT REPORT ==="
      echo "Score: $SCORE/100"
      echo "Security Issues: $BANDIT"
      echo "Linting Issues: $RUFF"
      echo "Test Coverage: $COV%"
      echo "===================="

      if [ "$SCORE" -lt {self.score_threshold} ]; then
        echo "FAILED: Score ($SCORE) is below threshold ({self.score_threshold})"
        exit 1
      fi
      echo "PASSED: Audit score meets threshold"
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
'''

        ci_path = self.project_path / ".gitlab-ci.yml"
        with open(ci_path, 'w', encoding='utf-8') as f:
            f.write(ci_content)

        logger.info(f"Generated GitLab CI config: {ci_path}")
        return str(ci_path)

    def generate_bitbucket_pipelines(self, auto_fix: bool = True) -> str:
        """
        Generate Bitbucket Pipelines configuration.

        Returns:
            Path to the generated bitbucket-pipelines.yml file
        """
        pipelines_content = f'''# Python Auditor CI Pipeline for Bitbucket

image: python:3.11-slim

definitions:
  caches:
    pip: ~/.cache/pip

  steps:
    - step: &audit-step
        name: Python Audit
        caches:
          - pip
        script:
          - pip install bandit ruff vulture radon detect-secrets pip-audit pytest pytest-cov
          - if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

          # Security scan
          - bandit -r . -f json -o bandit-results.json --exit-zero || true
          - export BANDIT=$(python -c "import json; d=json.load(open('bandit-results.json')); print(len(d.get('results',[])))")

          # Linting
          - ruff check . --output-format=json > ruff-results.json || true
          - export RUFF=$(python -c "import json; print(len(json.load(open('ruff-results.json'))))")
'''

        if auto_fix:
            pipelines_content += '''
          # Auto-fix
          - ruff check . --fix --exit-zero
          - ruff format .
'''

        pipelines_content += f'''
          # Tests
          - pytest --cov=. --cov-report=term -q || true
          - export COV=$(python -c "import coverage; c=coverage.Coverage(); c.load(); print(int(c.report()))" 2>/dev/null || echo 0)

          # Calculate score
          - |
            SCORE=100
            if [ "$BANDIT" -gt 0 ]; then
              PENALTY=$((BANDIT * 5))
              [ $PENALTY -gt 30 ] && PENALTY=30
              SCORE=$((SCORE - PENALTY))
            fi
            if [ "$RUFF" -gt 0 ]; then
              PENALTY=$((RUFF / 5))
              [ $PENALTY -gt 20 ] && PENALTY=20
              SCORE=$((SCORE - PENALTY))
            fi
            if [ "$COV" -lt 70 ]; then
              PENALTY=$((70 - COV))
              [ $PENALTY -gt 30 ] && PENALTY=30
              SCORE=$((SCORE - PENALTY))
            fi

            echo "=== AUDIT REPORT ==="
            echo "Score: $SCORE/100"
            echo "Security Issues: $BANDIT"
            echo "Linting Issues: $RUFF"
            echo "Test Coverage: $COV%"

            if [ "$SCORE" -lt {self.score_threshold} ]; then
              echo "FAILED: Score below threshold ({self.score_threshold})"
              exit 1
            fi

pipelines:
  pull-requests:
    '**':
      - step: *audit-step

  branches:
    main:
      - step: *audit-step
    master:
      - step: *audit-step
'''

        pipelines_path = self.project_path / "bitbucket-pipelines.yml"
        with open(pipelines_path, 'w', encoding='utf-8') as f:
            f.write(pipelines_content)

        logger.info(f"Generated Bitbucket Pipelines config: {pipelines_path}")
        return str(pipelines_path)

    def generate_precommit_hooks(self) -> str:
        """
        Generate pre-commit hooks configuration.

        Returns:
            Path to the generated .pre-commit-config.yaml file
        """
        precommit_content = '''# Pre-commit hooks for Python Auditor
# Install: pip install pre-commit && pre-commit install

repos:
  # Ruff - Fast Python linter and formatter
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  # Bandit - Security linter
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.8
    hooks:
      - id: bandit
        args: [-c, pyproject.toml, -r, .]
        additional_dependencies: ["bandit[toml]"]

  # Detect secrets
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: [--baseline, .secrets.baseline]
        exclude: package.lock.json

  # Standard hooks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: check-merge-conflict
      - id: debug-statements

  # Type checking (optional - uncomment to enable)
  # - repo: https://github.com/pre-commit/mirrors-mypy
  #   rev: v1.10.0
  #   hooks:
  #     - id: mypy
  #       additional_dependencies: [types-all]

# CI configuration
ci:
  autofix_commit_msg: |
    [pre-commit.ci] auto-fix

  autofix_prs: true
  autoupdate_branch: ''
  autoupdate_commit_msg: '[pre-commit.ci] auto-update hooks'
  autoupdate_schedule: weekly
  skip: []
  submodules: false
'''

        precommit_path = self.project_path / ".pre-commit-config.yaml"
        with open(precommit_path, 'w', encoding='utf-8') as f:
            f.write(precommit_content)

        logger.info(f"Generated pre-commit config: {precommit_path}")
        return str(precommit_path)

    def generate_pr_template(self) -> str:
        """
        Generate PR template with audit checklist.

        Returns:
            Path to the generated PR template file
        """
        template_dir = self.project_path / ".github"
        template_dir.mkdir(parents=True, exist_ok=True)

        template_content = f'''## Description
<!-- Briefly describe what this PR does -->


## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Refactoring (no functional changes)
- [ ] Documentation update

## Audit Checklist
<!-- The Python Auditor CI will verify these automatically -->

### Security
- [ ] No hardcoded secrets or credentials
- [ ] No SQL injection vulnerabilities
- [ ] No command injection risks
- [ ] Dependencies are up to date

### Code Quality
- [ ] Code passes Ruff linting
- [ ] No unused imports or variables
- [ ] Functions have reasonable complexity (< 15)

### Testing
- [ ] Tests pass locally
- [ ] Coverage meets threshold ({self.score_threshold}%+)
- [ ] New code has appropriate test coverage

## Audit Score Target
This PR should achieve a minimum audit score of **{self.score_threshold}/100** to be merged.

---

### For Reviewers
The automated audit will comment with:
- Security scan results (Bandit)
- Linting issues (Ruff)
- Test coverage percentage
- Overall audit score

Please review the automated audit results before approving.
'''

        template_path = template_dir / "pull_request_template.md"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)

        logger.info(f"Generated PR template: {template_path}")
        return str(template_path)

    def generate_all(self, platform: str = "github") -> Dict[str, str]:
        """
        Generate all CI/CD configurations for a platform.

        Args:
            platform: One of 'github', 'gitlab', 'bitbucket'

        Returns:
            Dictionary mapping file types to their paths
        """
        results = {}

        # Generate platform-specific pipeline
        if platform.lower() == "github":
            results["workflow"] = self.generate_github_actions()
        elif platform.lower() == "gitlab":
            results["pipeline"] = self.generate_gitlab_ci()
        elif platform.lower() == "bitbucket":
            results["pipeline"] = self.generate_bitbucket_pipelines()
        else:
            raise ValueError(f"Unsupported platform: {platform}. Use: github, gitlab, bitbucket")

        # Generate common files
        results["precommit"] = self.generate_precommit_hooks()

        # PR template only for GitHub (GitLab/Bitbucket have different mechanisms)
        if platform.lower() == "github":
            results["pr_template"] = self.generate_pr_template()

        return results
