"""Sensitive data redaction for diffs before sending to AI."""

import re


# Patterns for sensitive file detection
SENSITIVE_FILE_PATTERNS = [
    re.compile(r"\.env(\.[a-z]+)?$", re.IGNORECASE),  # .env files
    re.compile(r"\.pem$", re.IGNORECASE),  # Certificate files
    re.compile(r"\.key$", re.IGNORECASE),  # Private key files
    re.compile(r"\.p12$", re.IGNORECASE),  # PKCS12 files
    re.compile(r"\.pfx$", re.IGNORECASE),  # Personal Information Exchange
    re.compile(r"id_rsa", re.IGNORECASE),  # SSH private keys
    re.compile(r"credentials", re.IGNORECASE),  # Credential files
    re.compile(r"secrets?\.(json|ya?ml|toml|ini)$", re.IGNORECASE),  # Secret configs
]


def redact_sensitive_data(text: str) -> str:
    """Redact sensitive patterns from diff text before sending to AI.

    Args:
        text: The diff text to redact

    Returns:
        Text with sensitive data redacted
    """
    redacted = text

    # Hide .env file content completely
    redacted = re.sub(
        r"^(diff --git a/.*\.env.*?$[\s\S]*?)(?=^diff --git |$)",
        r"[.ENV FILE CONTENT COMPLETELY HIDDEN FOR SECURITY]\n",
        redacted,
        flags=re.MULTILINE,
    )

    # Hide other sensitive files
    for pattern in SENSITIVE_FILE_PATTERNS:
        file_pattern = re.compile(
            rf"^(diff --git a/.*{pattern.pattern}.*?$[\s\S]*?)(?=^diff --git |$)",
            re.MULTILINE | re.IGNORECASE,
        )
        redacted = file_pattern.sub(
            "[SENSITIVE FILE CONTENT HIDDEN FOR SECURITY]\n",
            redacted,
        )

    # Redact OpenAI API keys
    redacted = re.sub(
        r"(['\"]?)(sk-[a-zA-Z0-9]{32,}|sk_[a-zA-Z0-9_-]{32,})(['\"]?)",
        r"\1[REDACTED_OPENAI_KEY]\3",
        redacted,
    )

    # Redact GitHub tokens
    redacted = re.sub(
        r"(['\"]?)(ghp_[a-zA-Z0-9]{36,}|ghs_[a-zA-Z0-9]{36,}|gho_[a-zA-Z0-9]{36,})(['\"]?)",
        r"\1[REDACTED_GITHUB_TOKEN]\3",
        redacted,
    )

    # Redact Slack tokens
    redacted = re.sub(
        r"(['\"]?)(xox[pboa]-[a-zA-Z0-9-]{10,})(['\"]?)",
        r"\1[REDACTED_SLACK_TOKEN]\3",
        redacted,
    )

    # Redact AWS access keys
    redacted = re.sub(
        r"(AKIA[0-9A-Z]{16})",
        "[REDACTED_AWS_ACCESS_KEY]",
        redacted,
    )

    # Redact Stripe keys
    redacted = re.sub(
        r"(['\"]?)(sk_live_[a-zA-Z0-9]{24,}|pk_live_[a-zA-Z0-9]{24,}|"
        r"sk_test_[a-zA-Z0-9]{24,}|pk_test_[a-zA-Z0-9]{24,})(['\"]?)",
        r"\1[REDACTED_STRIPE_KEY]\3",
        redacted,
    )

    # Redact private keys
    redacted = re.sub(
        r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"
        r"[\s\S]*?"
        r"-----END (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
        "[REDACTED_PRIVATE_KEY]",
        redacted,
    )

    # Redact JWT tokens
    redacted = re.sub(
        r"(['\"]?)(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)(['\"]?)",
        r"\1[REDACTED_JWT_TOKEN]\3",
        redacted,
    )

    # Redact passwords in common formats
    redacted = re.sub(
        r"(password|passwd|pwd|secret|api_key|apikey|auth_token|access_token|private_key)"
        r"[\s]*[=:][\s]*['\"]([^'\"]{8,})['\"]",
        r"\1=[REDACTED]",
        redacted,
        flags=re.IGNORECASE,
    )

    # Redact database connection strings
    redacted = re.sub(
        r"(mongodb(\+srv)?|postgres(ql)?|mysql|redis)://[^@\s]+@[^\s]+",
        r"\1://[REDACTED_CONNECTION_STRING]",
        redacted,
        flags=re.IGNORECASE,
    )

    # Redact Bearer tokens
    redacted = re.sub(
        r"Bearer\s+[a-zA-Z0-9_\-\.]+",
        "Bearer [REDACTED_TOKEN]",
        redacted,
        flags=re.IGNORECASE,
    )

    # Redact DeepSeek API keys (similar format to OpenAI)
    redacted = re.sub(
        r"(['\"]?)(sk-[a-f0-9]{48,})(['\"]?)",
        r"\1[REDACTED_DEEPSEEK_KEY]\3",
        redacted,
    )

    return redacted
