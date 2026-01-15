"""Prompt templates and language support for commit message generation."""

# System prompt for the AI
SYSTEM_PROMPT = (
    "You are a helpful assistant that generates clear, conventional git commit messages."
)


# Language mapping for multi-language support
LANGUAGE_MAP = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "zh-cn": "Simplified Chinese",
    "zh-tw": "Traditional Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
}


def get_language_instruction(language: str) -> str:
    """Get the language instruction for the AI prompt.

    Args:
        language: Language code (e.g., 'en', 'zh', 'es')

    Returns:
        Language instruction string
    """
    lang_name = LANGUAGE_MAP.get(language.lower(), language)
    return f"Write the commit message in {lang_name}."


def parse_template(template: str) -> dict[str, str]:
    """Parse a custom commit message template.

    Args:
        template: Custom template like "(feat): message" or "[JIRA-123] feat: message"

    Returns:
        Dict with 'prefix', 'separator', 'example' keys
    """
    import re

    match = re.match(r"^(.*?)(\s*[:\-]\s*)(.*)$", template)
    if match:
        return {
            "prefix": match.group(1),
            "separator": match.group(2),
            "example": match.group(3),
        }
    return {
        "prefix": "",
        "separator": ": ",
        "example": template,
    }


def build_prompt(
    diff: str,
    files: list[str],
    old_message: str,
    template: str | None = None,
    language: str = "en",
    custom_prompt: str | None = None,
    custom_context: str | None = None,
) -> str:
    """Build the prompt for commit message generation.

    Args:
        diff: The git diff content
        files: List of changed files
        old_message: The original commit message
        template: Optional custom template
        language: Target language code
        custom_prompt: Optional custom prompt override
        custom_context: Optional project-specific context

    Returns:
        The complete prompt string
    """
    # Build format instructions based on template
    if template:
        parsed = parse_template(template)
        if parsed["prefix"]:
            format_instructions = f"""Follow this EXACT format: {template}
Where the message part should describe what was changed.
Example: If template is "(feat): message", generate something like "(feat): add user authentication"
Example: If template is "[JIRA-XXX] type: message", generate something like "[JIRA-123] fix: resolve null pointer exception\""""
        else:
            format_instructions = f"Use this format as a guide: {template}"
    else:
        format_instructions = """1. Follows the format: <type>(<scope>): <subject>
2. Types can be: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert
3. Scope is optional but recommended (e.g., auth, api, ui)
4. All should be in lowercase"""

    language_instruction = get_language_instruction(language)

    # Truncate diff if too long (max 8KB)
    truncated_diff = diff[:8000] if len(diff) > 8000 else diff

    files_list = "\n".join(files) if files else "(no files)"

    # Build the context section
    context_section = ""
    if custom_context:
        context_section = f"Project-specific guidelines:\n{custom_context}\n\n"

    if custom_prompt:
        # User provided custom prompt - use it with basic context
        return f"""You are a git commit message generator. Analyze the following git diff and file changes, then {custom_prompt}

{context_section}Old commit message: "{old_message}"

Files changed:
{files_list}

Git diff (truncated if too long, sensitive data redacted):
{truncated_diff}

{f"Format: {template}" if template else ""}
{language_instruction}

Return ONLY the commit message, nothing else."""

    # Default prompt with all standard instructions
    return f"""You are a git commit message generator. Analyze the following git diff and file changes, then generate a clear, concise commit message.

{context_section}Old commit message: "{old_message}"

Files changed:
{files_list}

Git diff (truncated if too long, sensitive data redacted):
{truncated_diff}

Generate a commit message that:
{format_instructions}
4. Subject should be clear and descriptive
5. Be concise but informative
6. Focus on WHAT was changed and WHY, not HOW
7. Use present tense ("add" not "added")
8. Don't end with a period
9. Maximum 72 characters for the first line
10. Lowercase the first letter
11. {language_instruction}

Return ONLY the commit message, nothing else. No explanations, just the message."""


def find_commit_message_context(repo_path: str | None = None) -> str | None:
    """Find custom commit message context file.

    Searches for COMMIT_MESSAGE.md in:
    1. Project root
    2. .git directory
    3. .github directory

    Args:
        repo_path: Path to the repository (defaults to cwd)

    Returns:
        Content of the context file if found, None otherwise
    """
    from pathlib import Path

    base = Path(repo_path) if repo_path else Path.cwd()

    search_paths = [
        base / "COMMIT_MESSAGE.md",
        base / ".git" / "COMMIT_MESSAGE.md",
        base / ".github" / "COMMIT_MESSAGE.md",
    ]

    for path in search_paths:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
        except (OSError, IOError):
            continue

    return None
