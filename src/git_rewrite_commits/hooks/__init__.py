"""Git hooks for AI commit message generation."""

from __future__ import annotations

import shutil
import stat
import sys
import time
from pathlib import Path

from rich.console import Console

from ..git import GitError, GitRepo
from .templates import get_pre_commit_hook, get_prepare_commit_msg_hook


def install_hooks(console: Console | None = None) -> None:
    """Install AI commit message hooks.

    Args:
        console: Rich console for output (creates new one if None)
    """
    if console is None:
        console = Console()

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
                backup_path = target_path.with_suffix(f".backup-{int(time.time())}")
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

        console.print("\n3. Optional customizations:")

        console.print('[dim]   git config hooks.commitTemplate "type(scope): message"[/]')
        console.print('[dim]   git config hooks.commitLanguage "en"[/]')

        console.print("\n[green]✨ You're all set! The hooks will work with your git commits.[/]")


__all__ = [
    "install_hooks",
    "get_pre_commit_hook",
    "get_prepare_commit_msg_hook",
]
