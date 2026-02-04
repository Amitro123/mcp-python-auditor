"""Grading utilities for audit scores.

Provides letter grade calculation with +/- modifiers.
"""


def get_letter_grade(score: int) -> str:
    """Convert numeric score to letter grade with +/- modifiers.

    Args:
        score: Numeric score (0-100)

    Returns:
        Letter grade (A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F)
    """
    if score >= 97:
        return "A+"
    if score >= 93:
        return "A"
    if score >= 90:
        return "A-"
    if score >= 87:
        return "B+"
    if score >= 83:
        return "B"
    if score >= 80:
        return "B-"
    if score >= 77:
        return "C+"
    if score >= 73:
        return "C"
    if score >= 70:
        return "C-"
    if score >= 67:
        return "D+"
    if score >= 63:
        return "D"
    if score >= 60:
        return "D-"
    return "F"


def get_simple_grade(score: int) -> str:
    """Convert numeric score to simple letter grade (no modifiers).

    Args:
        score: Numeric score (0-100)

    Returns:
        Simple letter grade (A+, A, B, C, D, F)
    """
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def get_grade_color(grade: str) -> str:
    """Get Rich color for a grade.

    Args:
        grade: Letter grade

    Returns:
        Rich color name
    """
    if grade.startswith("A"):
        return "green"
    if grade.startswith("B"):
        return "blue"
    if grade.startswith("C"):
        return "yellow"
    if grade.startswith("D"):
        return "orange1"
    return "red"


def get_score_color(score: int) -> str:
    """Get Rich color for a score.

    Args:
        score: Numeric score (0-100)

    Returns:
        Rich color name
    """
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    return "red"


def get_score_emoji(score: int) -> str:
    """Get emoji for a score.

    Args:
        score: Numeric score (0-100)

    Returns:
        Emoji string
    """
    if score >= 90:
        return "\U0001f389"  # party popper
    if score >= 70:
        return "\u2705"  # check mark
    return "\u26a0\ufe0f"  # warning
