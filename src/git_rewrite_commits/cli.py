"""CLI interface for git-rewrite-commits."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .rewriter import GitCommitRewriter, RewriteOptions
from .git import GitRepo, GitError


console = Console()


def install_hooks() -> None:
    """Install AI commit message hooks."""
    console.print("\n[bold cyan]🎯 Installing AI Commit Message Hooks[/]\n")

    # Check if in a git repository
    try:
        repo = GitRepo()
        repo.check_repository()
    except GitError:
        console.print("[red]❌ Error: Not a git repository![/]")
        console.print("[yellow]Please run this command from within a git repository.[/]")
        sys.exit(1)

    is_windows = sys.platform == "win32"

    hooks = [
        ("pre-commit", "Preview AI message before committing"),
        ("prepare-commit-msg", "Generate AI message automatically"),
    ]

    console.print(f"[blue]Installing hooks for {'Windows' if is_windows else 'Unix/macOS'}:[/]\n")
    for name, desc in hooks:
        console.print(f"  • [bold]{name}[/] - {desc}")
    console.print("")

    installed = 0
    updated = 0

    hooks_dir = Path.cwd() / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    for hook_name, _ in hooks:
        target_path = hooks_dir / hook_name

        # Check if hook already exists
        existed_before = target_path.exists()
        if existed_before:
            # Check if it's our hook
            existing_content = target_path.read_text(encoding="utf-8", errors="ignore")
            if "git-rewrite-commits" not in existing_content:
                # Backup existing hook
                backup_path = target_path.with_suffix(f".backup-{int(__import__('time').time())}")
                import shutil

                shutil.copy2(target_path, backup_path)
                console.print(
                    f"  [yellow]⚠ {hook_name} - backed up existing to {backup_path.name}[/]"
                )

        # Get hook content
        if hook_name == "pre-commit":
            content = get_pre_commit_hook(is_windows)
        else:
            content = get_prepare_commit_msg_hook(is_windows)

        try:
            target_path.write_text(content, encoding="utf-8")

            # Make executable on Unix
            if not is_windows:
                import stat

                target_path.chmod(target_path.stat().st_mode | stat.S_IEXEC)

            if existed_before:
                console.print(f"  [green]✓ {hook_name} - updated[/]")
                updated += 1
            else:
                console.print(f"  [green]✓ {hook_name} - installed[/]")
                installed += 1
        except Exception as e:
            console.print(f"  [red]✗ {hook_name} - installation failed: {e}[/]")

    # Summary
    console.print("\n[cyan]📊 Summary:[/]")
    if installed > 0:
        console.print(f"[green]  ✓ Installed: {installed} new hook(s)[/]")
    if updated > 0:
        console.print(f"[blue]  ↻ Updated: {updated} existing hook(s)[/]")

    if installed > 0 or updated > 0:
        console.print("\n[blue]💡 Setup Instructions:[/]")
        console.print("[bold yellow]\n⚠️  IMPORTANT: Hooks are opt-in for security and privacy[/]")

        console.print("\n1. Enable the hooks you want (REQUIRED):")
        console.print(
            "[dim]   git config hooks.preCommitPreview true    # Enable preview before commit[/]"
        )
        console.print(
            "[dim]   git config hooks.prepareCommitMsg true    # Enable auto-generation[/]"
        )

        console.print("\n2. Set up your AI provider:")
        console.print("[dim]   # Option A: OpenAI (sends data to remote API)[/]")
        if is_windows:
            console.print('[dim]   set OPENAI_API_KEY="your-api-key"[/]')
        else:
            console.print('[dim]   export OPENAI_API_KEY="your-api-key"[/]')

        console.print("\n[dim]   # Option B: DeepSeek (NEW - sends data to remote API)[/]")
        if is_windows:
            console.print('[dim]   set DEEPSEEK_API_KEY="your-api-key"[/]')
        else:
            console.print('[dim]   export DEEPSEEK_API_KEY="your-api-key"[/]')
        console.print("[dim]   git config hooks.commitProvider deepseek[/]")

        console.print(
            "\n[dim]   # Option C: Ollama (local processing - recommended for privacy)[/]"
        )
        console.print("[dim]   ollama pull llama3.2[/]")
        console.print("[dim]   ollama serve[/]")
        console.print("[dim]   git config hooks.commitProvider ollama[/]")

        console.print("\n3. Optional customizations:")
        console.print('[dim]   git config hooks.commitTemplate "type(scope): message"[/]')
        console.print('[dim]   git config hooks.commitLanguage "en"[/]')

        console.print("\n[green]✨ You're all set! The hooks will work with your git commits.[/]")


def get_pre_commit_hook(is_windows: bool) -> str:
    """Get pre-commit hook content."""
    if is_windows:
        return """@echo off
REM git-rewrite-commits pre-commit hook
REM Preview AI-generated commit message before committing

REM Check if hook is enabled
for /f "tokens=*" %%i in ('git config --get hooks.preCommitPreview') do set ENABLED=%%i
if not "%ENABLED%"=="true" exit /b 0

REM Get provider from config or default to openai
for /f "tokens=*" %%i in ('git config --get hooks.commitProvider') do set PROVIDER=%%i
if "%PROVIDER%"=="" set PROVIDER=openai

REM Preview the message
echo.
echo AI Commit Message Preview:
echo ==========================
python -m git_rewrite_commits --staged --quiet --provider %PROVIDER% --skip-remote-consent
echo ==========================
echo.
"""
    else:
        return """#!/bin/sh
# git-rewrite-commits pre-commit hook
# Preview AI-generated commit message before committing

# Check if hook is enabled
ENABLED=$(git config --get hooks.preCommitPreview)
if [ "$ENABLED" != "true" ]; then
    exit 0
fi

# Get provider from config or default to openai
PROVIDER=$(git config --get hooks.commitProvider)
PROVIDER=${PROVIDER:-openai}

# Preview the message
echo ""
echo "AI Commit Message Preview:"
echo "=========================="
python -m git_rewrite_commits --staged --quiet --provider "$PROVIDER" --skip-remote-consent
echo "=========================="
echo ""
"""


def get_prepare_commit_msg_hook(is_windows: bool) -> str:
    """Get prepare-commit-msg hook content."""
    if is_windows:
        return """@echo off
REM git-rewrite-commits prepare-commit-msg hook
REM Automatically generate AI commit message

REM Check if hook is enabled
for /f "tokens=*" %%i in ('git config --get hooks.prepareCommitMsg') do set ENABLED=%%i
if not "%ENABLED%"=="true" exit /b 0

REM Don't override if message already provided (e.g., -m flag, merge, etc.)
if "%2"=="message" exit /b 0
if "%2"=="merge" exit /b 0
if "%2"=="squash" exit /b 0

REM Get provider from config or default to openai
for /f "tokens=*" %%i in ('git config --get hooks.commitProvider') do set PROVIDER=%%i
if "%PROVIDER%"=="" set PROVIDER=openai

REM Get template from config
for /f "tokens=*" %%i in ('git config --get hooks.commitTemplate') do set TEMPLATE=%%i

REM Get language from config
for /f "tokens=*" %%i in ('git config --get hooks.commitLanguage') do set LANGUAGE=%%i
if "%LANGUAGE%"=="" set LANGUAGE=en

REM Generate message
set TEMPLATE_OPT=
if not "%TEMPLATE%"=="" set TEMPLATE_OPT=--template "%TEMPLATE%"

python -m git_rewrite_commits --staged --quiet --provider %PROVIDER% --language %LANGUAGE% %TEMPLATE_OPT% --skip-remote-consent > %1
"""
    else:
        return """#!/bin/sh
# git-rewrite-commits prepare-commit-msg hook
# Automatically generate AI commit message

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Check if hook is enabled
ENABLED=$(git config --get hooks.prepareCommitMsg)
if [ "$ENABLED" != "true" ]; then
    exit 0
fi

# Don't override if message already provided (e.g., -m flag, merge, etc.)
case "$COMMIT_SOURCE" in
    message|merge|squash)
        exit 0
        ;;
esac

# Get provider from config or default to openai
PROVIDER=$(git config --get hooks.commitProvider)
PROVIDER=${PROVIDER:-openai}

# Get template from config
TEMPLATE=$(git config --get hooks.commitTemplate)
TEMPLATE_OPT=""
if [ -n "$TEMPLATE" ]; then
    TEMPLATE_OPT="--template \"$TEMPLATE\""
fi

# Get language from config
LANGUAGE=$(git config --get hooks.commitLanguage)
LANGUAGE=${LANGUAGE:-en}

# Generate message
python -m git_rewrite_commits --staged --quiet --provider "$PROVIDER" --language "$LANGUAGE" $TEMPLATE_OPT --skip-remote-consent > "$COMMIT_MSG_FILE"
"""


@click.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "ollama", "deepseek"]),
    default="openai",
    help='AI provider to use: "openai", "ollama", or "deepseek"',
)
@click.option(
    "-k",
    "--api-key",
    help="API key (defaults to OPENAI_API_KEY or DEEPSEEK_API_KEY env var)",
)
@click.option(
    "-m",
    "--model",
    help="AI model to use (default varies by provider)",
)
@click.option(
    "--ollama-url",
    default="http://localhost:11434",
    help="Ollama server URL",
)
@click.option(
    "-b",
    "--branch",
    help="Branch to rewrite (defaults to current branch)",
)
@click.option(
    "-d",
    "--dry-run",
    is_flag=True,
    help="Show what would be changed without modifying repository",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed output including diffs and file changes",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress all informational output (useful for git hooks)",
)
@click.option(
    "--max-commits",
    type=int,
    help="Process only the last N commits",
)
@click.option(
    "--skip-backup",
    is_flag=True,
    help="Skip creating a backup branch (not recommended)",
)
@click.option(
    "--skip-well-formed/--no-skip-well-formed",
    default=True,
    help="Skip commits that already have well-formed messages",
)
@click.option(
    "--min-quality-score",
    type=int,
    default=7,
    help="Minimum quality score (0-10) to consider well-formed",
)
@click.option(
    "-t",
    "--template",
    help='Custom commit message template (e.g., "(feat): message")',
)
@click.option(
    "-l",
    "--language",
    default="en",
    help='Language for commit messages (default: "en")',
)
@click.option(
    "-p",
    "--prompt",
    help="Custom prompt for AI message generation",
)
@click.option(
    "--staged",
    is_flag=True,
    help="Generate a message for staged changes (for git hooks)",
)
@click.option(
    "--skip-remote-consent",
    is_flag=True,
    help="Skip consent prompt for remote API calls (for automation)",
)
@click.option(
    "--install-hooks",
    is_flag=True,
    help="Install AI commit message hooks (pre-commit and prepare-commit-msg)",
)
@click.option(
    "--repo",
    help="Target repository (local path or GitHub URL)",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push changes back to remote after rewrite",
)
@click.version_option(__version__)
def main(
    provider: str,
    api_key: str | None,
    model: str | None,
    ollama_url: str,
    branch: str | None,
    dry_run: bool,
    verbose: bool,
    quiet: bool,
    max_commits: int | None,
    skip_backup: bool,
    skip_well_formed: bool,
    min_quality_score: int,
    template: str | None,
    language: str,
    prompt: str | None,
    staged: bool,
    skip_remote_consent: bool,
    install_hooks: bool,
    repo: str | None,
    push: bool,
) -> None:
    """AI-powered git commit message rewriter using OpenAI, DeepSeek, or Ollama.

    \b
    Examples:
      # Basic usage (uses OPENAI_API_KEY env var)
      git-rewrite-commits

      # Dry run to preview changes
      git-rewrite-commits --dry-run

      # Use DeepSeek instead of OpenAI
      git-rewrite-commits --provider deepseek

      # Use local Ollama
      git-rewrite-commits --provider ollama --model llama3.2

      # Process only the last 10 commits
      git-rewrite-commits --max-commits 10

      # Generate message for staged changes (for hooks)
      git-rewrite-commits --staged

      # Install git hooks
      git-rewrite-commits --install-hooks
    """
    try:
        # Handle --install-hooks option
        if install_hooks:
            install_hooks_func()
            return

        # Show provider info
        if provider == "ollama" and not quiet:
            console.print(f"[blue]ℹ️  Using Ollama provider at {ollama_url}[/]")
            console.print("[dim]   Make sure Ollama is running: ollama serve[/]")
        elif provider == "deepseek" and not quiet:
            console.print("[blue]ℹ️  Using DeepSeek provider[/]")
            console.print("[dim]   Make sure DEEPSEEK_API_KEY is set[/]")

        options = RewriteOptions(
            provider=provider,
            api_key=api_key,
            model=model,
            ollama_url=ollama_url,
            branch=branch,
            dry_run=dry_run,
            verbose=verbose,
            quiet=quiet,
            max_commits=max_commits,
            skip_backup=skip_backup,
            skip_well_formed=skip_well_formed,
            min_quality_score=min_quality_score,
            template=template,
            language=language,
            prompt=prompt,
            skip_remote_consent=skip_remote_consent,
            repo=repo,
            push=push,
        )

        rewriter = GitCommitRewriter(options)

        if staged:
            # Generate message for staged changes
            message = rewriter.generate_for_staged()
            click.echo(message)
        else:
            rewriter.rewrite()

    except Exception as e:
        if verbose:
            console.print_exception()
        else:
            console.print(f"\n[red]❌ Error: {e}[/]")
        sys.exit(1)


# Alias for install_hooks to avoid name collision with the flag
install_hooks_func = install_hooks


if __name__ == "__main__":
    main()
