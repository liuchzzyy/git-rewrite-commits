# AI Agent Guidelines for git-rewrite-commits

This document provides guidelines for AI agents working with this codebase.

## Project Overview

**git-rewrite-commits** is an AI-powered git commit message rewriter that uses OpenAI or DeepSeek to generate conventional commit messages from code diffs.

## Architecture

```
src/git_rewrite_commits/
├── __init__.py          # Package exports (GitCommitRewriter, RewriteOptions, CommitInfo)
├── __main__.py          # Entry point
├── cli.py               # CLI interface using Click
├── git.py               # Git operations wrapper (subprocess-based)
├── prompts.py           # AI prompt templates and language support
├── quality.py           # Commit message quality scoring
├── redaction.py         # Sensitive data redaction (API keys, tokens, etc.)
├── rewriter.py          # Core GitCommitRewriter class
├── hooks/
│   ├── __init__.py      # install_hooks() function
│   └── templates.py     # Git hook shell script templates
└── providers/
    ├── __init__.py      # Provider factory (create_provider)
    ├── base.py          # AIProvider ABC + OpenAICompatibleProvider base
    ├── deepseek.py      # DeepSeek provider (extends OpenAICompatibleProvider)
    └── openai.py        # OpenAI provider (extends OpenAICompatibleProvider)
```

## Key Design Patterns

### 1. Provider Pattern
All AI providers extend `OpenAICompatibleProvider` which handles:
- HTTP client setup (httpx)
- API key validation
- Chat completions API calls
- Response parsing

To add a new OpenAI-compatible provider, create a new file with:
```python
from .base import OpenAICompatibleProvider

class NewProvider(OpenAICompatibleProvider):
    BASE_URL = "https://api.example.com/v1/"
    ENV_VAR_NAME = "EXAMPLE_API_KEY"
    DEFAULT_MODEL = "example-model"
    PROVIDER_NAME = "Example"
```

### 2. Separation of Concerns
- `cli.py` - Only CLI argument parsing and output
- `rewriter.py` - Core business logic
- `git.py` - All git subprocess operations
- `hooks/` - Hook installation and templates

## Coding Standards

### Python Version
- Target Python 3.10+
- Use type hints consistently
- Use `from __future__ import annotations` for forward references

### Formatting
- Line length: 100 characters (ruff config)
- Linter: ruff with `E, F, I, N, W, UP` rules
- Type checker: mypy with strict mode

### Imports
- Use absolute imports within package
- Order: stdlib → third-party → local
- Pre-compile regex patterns at module level

### Error Handling
- Use custom exceptions (e.g., `GitError`)
- Always provide meaningful error messages
- Never suppress exceptions silently

## Security Considerations

### Sensitive Data Redaction
The `redaction.py` module automatically redacts:
- API keys (OpenAI, DeepSeek, AWS, Stripe, GitHub, Google Cloud)
- Passwords and secrets in common formats
- Private keys and certificates
- JWT tokens
- Database connection strings
- Bearer tokens
- `.env` file contents (completely hidden)

### User Consent
- Remote API calls require user consent unless `--skip-remote-consent` is set
- In quiet mode without explicit skip, API calls are blocked

## Testing

Run tests with:
```bash
uv run pytest tests/ -v
```

Current test coverage:
- `tests/test_quality.py` - Commit message quality scoring

## CLI Commands

```bash
# Install for development
uv pip install -e .

# Run CLI
uv run git-rewrite-commits --help

# Run linter
uv run ruff check src/

# Run type checker
uv run mypy src/
```

## GitHub Actions

Two workflows are available:
1. `rewrite-local.yml` - Rewrite commits in the current repository
2. `rewrite-remote.yml` - Rewrite commits in an external repository

Both use `uv` for Python package management.

## Common Tasks for AI Agents

### Adding a New Provider
1. Create `providers/newprovider.py` extending `OpenAICompatibleProvider`
2. Add to `providers/__init__.py` exports
3. Add to `create_provider()` factory function
4. Update CLI `--provider` choices in `cli.py`
5. Update README.md with provider documentation

### Adding a New CLI Option
1. Add `@click.option()` decorator in `cli.py`
2. Add parameter to `main()` function
3. Add field to `RewriteOptions` dataclass in `rewriter.py`
4. Update README.md usage section

### Modifying Redaction Patterns
1. Add pattern to `_REDACTION_PATTERNS` list in `redaction.py`
2. Use pre-compiled `re.compile()` for performance
3. Test with sample data containing the pattern

## Dependencies

Runtime:
- `click>=8.1` - CLI framework
- `httpx>=0.25` - HTTP client
- `rich>=13.0` - Terminal formatting

Development:
- `pytest>=7.0` - Testing
- `ruff` - Linting and formatting
- `mypy` - Type checking
