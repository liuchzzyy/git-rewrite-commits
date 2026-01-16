"""Main GitCommitRewriter class for rewriting commit messages with AI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .git import GitRepo, CommitInfo, GitError
from .prompts import SYSTEM_PROMPT, build_prompt, find_commit_message_context
from .providers import create_provider, AIProvider
from .quality import score_commit_message
from .redaction import redact_sensitive_data


if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class RewriteOptions:
    """Options for the commit rewriter."""

    provider: str = "openai"
    api_key: str | None = None
    model: str | None = None
    ollama_url: str = "http://localhost:11434"
    branch: str | None = None
    dry_run: bool = False
    verbose: bool = False
    quiet: bool = False
    max_commits: int | None = None
    skip_backup: bool = False
    skip_well_formed: bool = True
    min_quality_score: int = 7
    template: str | None = None
    language: str = "en"
    prompt: str | None = None
    skip_remote_consent: bool = False


class GitCommitRewriter:
    """AI-powered git commit message rewriter."""

    def __init__(
        self,
        options: RewriteOptions | None = None,
        repo_path: str | Path | None = None,
    ) -> None:
        """Initialize the rewriter.

        Args:
            options: Rewrite options
            repo_path: Path to the git repository (defaults to cwd)
        """
        self.options = options or RewriteOptions()
        self.repo = GitRepo(repo_path)
        self.console = Console(quiet=self.options.quiet)

        # Create the AI provider
        base_url = None
        if self.options.provider == "ollama":
            base_url = self.options.ollama_url

        self._provider: AIProvider | None = None

    def _get_provider(self) -> AIProvider:
        """Lazily create and return the AI provider."""
        if self._provider is None:
            base_url = None
            if self.options.provider == "ollama":
                base_url = self.options.ollama_url

            self._provider = create_provider(
                provider=self.options.provider,
                api_key=self.options.api_key,
                model=self.options.model,
                base_url=base_url,
            )
        return self._provider

    def _check_remote_api_consent(self) -> bool:
        """Check if user consents to sending data to remote API.

        Returns:
            True if user consents (or using local provider)
        """
        # Local Ollama doesn't need consent
        if self.options.provider == "ollama":
            return True

        # Skip if explicitly disabled
        if self.options.skip_remote_consent:
            return True

        # Quiet mode without explicit skip - fail safe
        if self.options.quiet:
            return False

        self.console.print("\n[bold yellow]⚠️  Data Privacy Notice[/]")
        self.console.print(
            "[yellow]This tool will send the following data to a remote AI provider:[/]"
        )
        self.console.print("[yellow]  • List of changed files[/]")
        self.console.print("[yellow]  • Git diff content (up to 8KB per commit)[/]")
        self.console.print(f"[yellow]  • Provider: {self.options.provider}[/]")
        self.console.print(f"[yellow]  • Model: {self.options.model or 'default'}[/]")

        self.console.print("\n[bold green]✅ Security Measures:[/]")
        self.console.print("[green]  • .env files are COMPLETELY HIDDEN from diffs[/]")
        self.console.print("[green]  • API keys, tokens, and secrets are automatically REDACTED[/]")
        self.console.print("[green]  • Private keys and certificates are REMOVED[/]")

        self.console.print("\n[yellow]⚠️  Still may include:[/]")
        self.console.print("[yellow]  • Source code (non-sensitive files)[/]")
        self.console.print("[yellow]  • Configuration files (with secrets redacted)[/]")

        try:
            from rich.prompt import Confirm

            return Confirm.ask("\nDo you consent to sending this data to the remote AI provider?")
        except (KeyboardInterrupt, EOFError):
            return False

    def _generate_commit_message(
        self,
        diff: str,
        files: list[str],
        old_message: str,
    ) -> str:
        """Generate a new commit message using AI.

        Args:
            diff: The git diff content
            files: List of changed files
            old_message: The original commit message

        Returns:
            The generated commit message
        """
        # Redact sensitive data
        redacted_diff = redact_sensitive_data(diff)

        # Find custom context
        custom_context = find_commit_message_context(str(self.repo.path))

        # Build the prompt
        prompt = build_prompt(
            diff=redacted_diff,
            files=files,
            old_message=old_message,
            template=self.options.template,
            language=self.options.language,
            custom_prompt=self.options.prompt,
            custom_context=custom_context,
        )

        # Generate with AI
        provider = self._get_provider()
        return provider.generate_commit_message(prompt, SYSTEM_PROMPT)

    def generate_for_staged(self) -> str:
        """Generate a commit message for staged changes.

        Returns:
            The generated commit message

        Raises:
            GitError: If not a git repository or no staged changes
        """
        self.repo.check_repository()

        # Check consent
        if not self._check_remote_api_consent():
            raise RuntimeError("User declined to send data to remote AI provider")

        # Get staged changes
        staged_files = self.repo.get_staged_files()
        if not staged_files:
            raise GitError("No staged changes found. Stage your changes with: git add <files>")

        staged_diff = self.repo.get_staged_diff()
        if not staged_diff.strip():
            raise GitError("No staged changes found")

        return self._generate_commit_message(staged_diff, staged_files, "")

    def rewrite(self) -> None:
        """Rewrite commit history with AI-generated messages."""
        if not self.options.quiet:
            self.console.print("\n[bold cyan]🚀 git-rewrite-commits[/]\n")

        # Check git repository
        self.repo.check_repository()

        # Get current branch
        current_branch = self.repo.get_current_branch()
        if not self.options.quiet:
            self.console.print(f"[blue]Current branch: {current_branch}[/]")

        # Check for uncommitted changes
        if self.repo.has_uncommitted_changes():
            self.console.print("\n[yellow]⚠️  Warning: You have uncommitted changes![/]")
            self.console.print("[yellow]Please commit or stash them before proceeding.[/]")

            if not self.options.quiet:
                try:
                    from rich.prompt import Confirm

                    if not Confirm.ask("Do you want to continue anyway?"):
                        return
                except (KeyboardInterrupt, EOFError):
                    return

        # Get commits
        commits = self.repo.get_commits(self.options.max_commits)
        if not self.options.quiet:
            self.console.print(f"\n[green]Found {len(commits)} commits to process[/]")

        if not commits:
            if not self.options.quiet:
                self.console.print("[yellow]No commits found to process.[/]")
            return

        # Check consent for remote API
        if not self._check_remote_api_consent():
            return

        # Warning about rewriting history
        if not self.options.dry_run and not self.options.quiet:
            self.console.print("\n[bold red]⚠️  WARNING: This will REWRITE your git history![/]")
            self.console.print(
                "[red]This is dangerous if you have already pushed to a remote repository.[/]"
            )
            self.console.print("[yellow]Make sure to:[/]")
            self.console.print("[yellow]  1. Work on a separate branch[/]")
            self.console.print("[yellow]  2. Have a backup of your repository[/]")
            self.console.print(
                "[yellow]  3. Coordinate with your team if this is a shared repository[/]"
            )

            try:
                from rich.prompt import Confirm

                if not Confirm.ask("\nDo you want to proceed?"):
                    self.console.print("[yellow]Operation cancelled.[/]")
                    return
            except (KeyboardInterrupt, EOFError):
                return

        # Create backup branch
        backup_branch: str | None = None
        if not self.options.skip_backup and not self.options.dry_run:
            backup_branch = self.repo.create_backup_branch(current_branch)
            if not self.options.quiet:
                self.console.print(f"\n[green]✅ Created backup branch: {backup_branch}[/]")

        # Process commits
        if not self.options.quiet:
            self.console.print("\n[cyan]📝 Generating new commit messages with AI...[/]\n")

        message_map: dict[str, str] = {}
        skipped_count = 0
        improved_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            disable=self.options.quiet,
        ) as progress:
            task = progress.add_task("Processing commits...", total=len(commits))

            for i, commit_hash in enumerate(commits):
                pct = (i + 1) / len(commits) * 100
                short_hash = commit_hash[:8]

                try:
                    commit_info = self.repo.get_commit_info(commit_hash)

                    # Check if well-formed and should be skipped
                    if self.options.skip_well_formed:
                        score, is_good, reason = score_commit_message(commit_info.message)

                        if is_good:
                            skipped_count += 1
                            progress.update(
                                task,
                                description=f"[{pct:.1f}%] {short_hash}: ✓ Already well-formed (score: {score}/10)",
                            )
                            progress.advance(task)
                            continue
                        else:
                            progress.update(
                                task,
                                description=f"[{pct:.1f}%] {short_hash}: needs improvement ({reason})",
                            )
                    else:
                        progress.update(
                            task,
                            description=f"[{pct:.1f}%] Processing {short_hash}...",
                        )

                    # Verbose output
                    if self.options.verbose:
                        progress.stop()
                        self.console.print(f"\n{'═' * 80}")
                        self.console.print(f"[yellow]📋 Commit: {short_hash}[/]")
                        self.console.print(f"[dim]Original message: {commit_info.message}[/]")
                        self.console.print(f"[dim]Files changed ({len(commit_info.files)}):[/]")
                        for f in commit_info.files[:10]:
                            self.console.print(f"[dim]  • {f}[/]")
                        if len(commit_info.files) > 10:
                            self.console.print(
                                f"[dim]  ... and {len(commit_info.files) - 10} more[/]"
                            )
                        progress.start()

                    # Generate new message
                    new_message = self._generate_commit_message(
                        commit_info.diff,
                        commit_info.files,
                        commit_info.message,
                    )

                    if new_message != commit_info.message:
                        message_map[commit_hash] = new_message
                        improved_count += 1

                        if not self.options.quiet:
                            progress.stop()
                            self.console.print(
                                f"[green][{pct:.1f}%] {short_hash}: ✨ "
                                f'"{commit_info.message}" → "{new_message}"[/]'
                            )
                            progress.start()
                    else:
                        if not self.options.quiet:
                            progress.update(
                                task,
                                description=f"[{pct:.1f}%] {short_hash}: Keeping original message",
                            )

                    progress.advance(task)

                except Exception as e:
                    progress.stop()
                    self.console.print(f"[red][{pct:.1f}%] Error processing {short_hash}: {e}[/]")
                    progress.start()
                    progress.advance(task)

        # Build ordered message list
        ordered_messages: list[str] = []
        for commit in commits:
            if commit in message_map:
                ordered_messages.append(message_map[commit])
            else:
                ordered_messages.append(self.repo.get_commit_full_message(commit))

        # Summary
        changed_count = len(message_map)
        if not self.options.quiet:
            self.console.print("\n[cyan]📊 Summary:[/]")
            self.console.print(f"[blue]  • Total commits analyzed: {len(commits)}[/]")
            if self.options.skip_well_formed:
                self.console.print(f"[cyan]  • Well-formed commits (skipped): {skipped_count}[/]")
            self.console.print(f"[green]  • Commits improved: {improved_count}[/]")
            self.console.print(f"[yellow]  • Commits to be rewritten: {changed_count}[/]")

        if changed_count == 0:
            if not self.options.quiet:
                if skipped_count > 0:
                    self.console.print(
                        "\n[green]✨ All commits are already well-formed! No changes needed.[/]"
                    )
                else:
                    self.console.print("\n[yellow]⚠️  No commits were changed.[/]")
                self.console.print(
                    "[dim]Tip: Use --no-skip-well-formed to force rewriting all commits[/]"
                )

            # Remove unnecessary backup
            if backup_branch:
                self.repo.delete_branch(backup_branch)
                if not self.options.quiet:
                    self.console.print(
                        f"[dim]Removed unnecessary backup branch: {backup_branch}[/]"
                    )
            return

        # Dry run stops here
        if self.options.dry_run:
            if not self.options.quiet:
                self.console.print(
                    "\n[yellow]🔍 Dry run completed. No changes were made to your repository.[/]"
                )
                self.console.print(
                    "[blue]Review the proposed changes above and run without --dry-run to apply them.[/]"
                )
            return

        # Confirm rewrite
        if not self.options.quiet:
            try:
                from rich.prompt import Confirm

                if not Confirm.ask("\nDo you want to apply the new commit messages?"):
                    self.console.print(
                        "[yellow]Rewrite cancelled. Your history remains unchanged.[/]"
                    )
                    if backup_branch:
                        self.console.print(
                            f"[blue]You can restore from backup branch: {backup_branch}[/]"
                        )
                    return
            except (KeyboardInterrupt, EOFError):
                return

        # Apply changes
        if not self.options.quiet:
            self.console.print("\n[cyan]🔄 Rewriting git history...[/]")

        try:
            self.repo.rewrite_history(ordered_messages)

            if not self.options.quiet:
                self.console.print("\n[bold green]✅ Successfully rewrote git history![/]")
                self.console.print("\n[bold yellow]📌 Important next steps:[/]")
                self.console.print("[yellow]  1. Review the changes: git log --oneline[/]")
                self.console.print(
                    "[yellow]  2. If satisfied, force push: git push --force-with-lease[/]"
                )
                if backup_branch:
                    self.console.print(
                        f"[yellow]  3. If something went wrong, restore: git reset --hard {backup_branch}[/]"
                    )
                    self.console.print(
                        f"[yellow]  4. Clean up backup when done: git branch -D {backup_branch}[/]"
                    )
        except Exception as e:
            if not self.options.quiet:
                self.console.print(f"\n[red]❌ Error rewriting history: {e}[/]")
                if backup_branch:
                    self.console.print(
                        f"[yellow]You can restore from backup: git reset --hard {backup_branch}[/]"
                    )
            raise


# Re-export CommitInfo for convenience
__all__ = ["GitCommitRewriter", "RewriteOptions", "CommitInfo"]
