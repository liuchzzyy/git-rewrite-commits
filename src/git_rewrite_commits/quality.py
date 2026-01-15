"""Commit message quality scoring."""

import re


def score_commit_message(message: str) -> tuple[int, bool, str]:
    """Assess the quality of a commit message.

    Scores from 0-10 based on conventional commit best practices.

    Args:
        message: The commit message to assess

    Returns:
        Tuple of (score, is_well_formed, reason)
    """
    score = 0
    reasons: list[str] = []

    # Check for conventional commit format
    conventional_pattern = re.compile(
        r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)"
        r"(\([^)]+\))?: .+"
    )

    if conventional_pattern.match(message):
        score += 4
        reasons.append("follows conventional format")

    # Check message length
    first_line = message.split("\n")[0]
    if 10 <= len(first_line) <= 72:
        score += 2
        reasons.append("appropriate length")
    elif len(first_line) < 10:
        reasons.append("too short")
    else:
        reasons.append("too long")

    # Check for descriptive content (not generic)
    generic_messages = [
        "update",
        "fix",
        "change",
        "modify",
        "commit",
        "initial",
        "test",
        "wip",
        "tmp",
        "temp",
    ]
    msg_lower = message.lower().strip(".")
    is_generic = any(
        msg_lower == generic or msg_lower == f"{generic} commit" for generic in generic_messages
    )

    if not is_generic:
        score += 2
        reasons.append("descriptive")
    else:
        reasons.append("too generic")

    # Check for present tense / imperative mood
    # Conventional commits should start lowercase after the type
    present_tense_pattern = re.compile(
        r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)?"
        r"(\([^)]+\))?: [a-z]"
    )
    if present_tense_pattern.match(message):
        score += 1
        reasons.append("uses present tense")

    # Check for no trailing period
    if not first_line.endswith("."):
        score += 1
        reasons.append("no trailing period")

    reason = ", ".join(reasons) if reasons else "no specific issues"

    return score, score >= 7, reason


def is_well_formed(message: str, min_score: int = 7) -> bool:
    """Check if a commit message is well-formed.

    Args:
        message: The commit message to check
        min_score: Minimum score to be considered well-formed (0-10)

    Returns:
        True if the message is well-formed
    """
    score, _, _ = score_commit_message(message)
    return score >= min_score


def needs_improvement(message: str, min_score: int = 7) -> tuple[bool, str]:
    """Check if a commit message needs improvement.

    Args:
        message: The commit message to check
        min_score: Minimum score threshold

    Returns:
        Tuple of (needs_improvement, reason)
    """
    score, is_good, reason = score_commit_message(message)
    return score < min_score, reason
