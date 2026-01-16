"""CLI interface for git-rewrite-commits."""

from __future__ import annotations

import sys

import click
from rich.console import Console

from . import __version__
from .hooks import install_hooks as install_hooks_func
from .rewriter import GitCommitRewriter, RewriteOptions

console = Console()


@click.command()
@click.option(
    "--provider",
    type=click.Choice(["openai", "deepseek"]),
    default="openai",
    help='AI provider to use: "openai" or "deepseek"',
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
    """AI-powered git commit message rewriter using OpenAI or DeepSeek.

    \b
    Examples:
      # Basic usage (uses OPENAI_API_KEY env var)
      git-rewrite-commits

      # Dry run to preview changes
      git-rewrite-commits --dry-run

      # Use DeepSeek instead of OpenAI
      git-rewrite-commits --provider deepseek

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
            install_hooks_func(console)
            return

        # Show provider info
        if provider == "deepseek" and not quiet:
            console.print("[blue]ℹ️  Using DeepSeek provider[/]")
            console.print("[dim]   Make sure DEEPSEEK_API_KEY is set[/]")

        options = RewriteOptions(
            provider=provider,
            api_key=api_key,
            model=model,
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


if __name__ == "__main__":
    main()
