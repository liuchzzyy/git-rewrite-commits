"""Sensitive data redaction for diffs before sending to AI."""

import re
from re import Pattern

# Pre-compiled patterns for sensitive file detection
SENSITIVE_FILE_PATTERNS: list[Pattern[str]] = [
    re.compile(r"\.env(\.[a-z]+)?$", re.IGNORECASE),  # .env files
    re.compile(r"\.pem$", re.IGNORECASE),  # Certificate files
    re.compile(r"\.key$", re.IGNORECASE),  # Private key files
    re.compile(r"\.p12$", re.IGNORECASE),  # PKCS12 files
    re.compile(r"\.pfx$", re.IGNORECASE),  # Personal Information Exchange
    re.compile(r"id_rsa", re.IGNORECASE),  # SSH private keys
    re.compile(r"credentials", re.IGNORECASE),  # Credential files
    re.compile(r"secrets?\.(json|ya?ml|toml|ini)$", re.IGNORECASE),  # Secret configs
]

# Pre-compiled redaction patterns (pattern, replacement, flags)
# Patterns are ordered from most specific to most general
_REDACTION_PATTERNS: list[tuple[Pattern[str], str]] = [
    # .env file content (completely hide)
    (
        re.compile(
            r"^(diff --git a/.*\.env.*?$[\s\S]*?)(?=^diff --git |$)",
            re.MULTILINE,
        ),
        "[.ENV FILE CONTENT COMPLETELY HIDDEN FOR SECURITY]\n",
    ),
    # OpenAI API keys
    (
        re.compile(r"(['\"]?)(sk-[a-zA-Z0-9]{32,}|sk_[a-zA-Z0-9_-]{32,})(['\"]?)"),
        r"\1[REDACTED_OPENAI_KEY]\3",
    ),
    # GitHub tokens
    (
        re.compile(
            r"(['\"]?)(ghp_[a-zA-Z0-9]{36,}|ghs_[a-zA-Z0-9]{36,}|gho_[a-zA-Z0-9]{36,})(['\"]?)"
        ),
        r"\1[REDACTED_GITHUB_TOKEN]\3",
    ),
    # Slack tokens
    (
        re.compile(r"(['\"]?)(xox[pboa]-[a-zA-Z0-9-]{10,})(['\"]?)"),
        r"\1[REDACTED_SLACK_TOKEN]\3",
    ),
    # AWS access keys
    (
        re.compile(r"(AKIA[0-9A-Z]{16})"),
        "[REDACTED_AWS_ACCESS_KEY]",
    ),
    # Stripe keys
    (
        re.compile(
            r"(['\"]?)(sk_live_[a-zA-Z0-9]{24,}|pk_live_[a-zA-Z0-9]{24,}|"
            r"sk_test_[a-zA-Z0-9]{24,}|pk_test_[a-zA-Z0-9]{24,})(['\"]?)"
        ),
        r"\1[REDACTED_STRIPE_KEY]\3",
    ),
    # Private keys
    (
        re.compile(
            r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"
            r"[\s\S]*?"
            r"-----END (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
    # JWT tokens
    (
        re.compile(r"(['\"]?)(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)(['\"]?)"),
        r"\1[REDACTED_JWT_TOKEN]\3",
    ),
    # Passwords in common formats
    (
        re.compile(
            r"(password|passwd|pwd|secret|api_key|apikey|auth_token|access_token|private_key)"
            r"[\s]*[=:][\s]*['\"]([^'\"]{8,})['\"]",
            re.IGNORECASE,
        ),
        r"\1=[REDACTED]",
    ),
    # Database connection strings
    (
        re.compile(
            r"(mongodb(\+srv)?|postgres(ql)?|mysql|redis)://[^@\s]+@[^\s]+",
            re.IGNORECASE,
        ),
        r"\1://[REDACTED_CONNECTION_STRING]",
    ),
    # Bearer tokens
    (
        re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
        "Bearer [REDACTED_TOKEN]",
    ),
    # DeepSeek API keys (similar format to OpenAI)
    (
        re.compile(r"(['\"]?)(sk-[a-f0-9]{48,})(['\"]?)"),
        r"\1[REDACTED_DEEPSEEK_KEY]\3",
    ),
    # Google Cloud / Firebase API keys (same format - covering both)
    (
        re.compile(r"AIza[0-9A-Za-z\\-_]{35}"),
        "[REDACTED_GOOGLE_API_KEY]",
    ),
]


def redact_sensitive_data(text: str) -> str:
    """Redact sensitive patterns from diff text before sending to AI.

    Args:
        text: The diff text to redact

    Returns:
        Text with sensitive data redacted
    """
    redacted = text

    # Apply sensitive file pattern redaction
    for pattern in SENSITIVE_FILE_PATTERNS:
        file_pattern = re.compile(
            rf"^(diff --git a/.*{pattern.pattern}.*?$[\s\S]*?)(?=^diff --git |$)",
            re.MULTILINE | re.IGNORECASE,
        )
        redacted = file_pattern.sub(
            "[SENSITIVE FILE CONTENT HIDDEN FOR SECURITY]\n",
            redacted,
        )

    # Apply pre-compiled redaction patterns
    for pattern, replacement in _REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)

    return redacted
