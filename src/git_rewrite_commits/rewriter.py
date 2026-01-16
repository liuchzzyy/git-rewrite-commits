"""Main GitCommitRewriter class for rewriting commit messages with AI."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .git import GitError, GitRepo
from .prompts import SYSTEM_PROMPT, build_prompt, find_commit_message_context
from .providers import AIProvider, create_provider
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
    repo: str | None = None
    push: bool = False


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
        self.console = Console(quiet=self.options.quiet)
        self._provider: AIProvider | None = None
        self._temp_dir: str | None = None

        # Handle remote repository or specific path
        target_path = repo_path
        if self.options.repo:
            if self.options.repo.startswith(("http://", "https://", "git@")):
                # Remote repository - clone it
                target_path = self._clone_repo(self.options.repo)
            else:
                # Local path
                target_path = Path(self.options.repo).resolve()

        self.repo = GitRepo(target_path)

        # Statistics
        self._skipped_count = 0
        self._improved_count = 0

    def _clone_repo(self, repo_url: str) -> Path:
        """Clone a remote repository to a temporary directory."""
        if not self.options.quiet:
            self.console.print(f"[blue]Cloning repository: {repo_url}[/]")

        self._temp_dir = tempfile.mkdtemp(prefix="git-rewrite-")
        try:
            subprocess.run(
                ["git", "clone", repo_url, self._temp_dir],
                check=True,
                capture_output=True,
                text=True,
            )
            return Path(self._temp_dir)
        except subprocess.CalledProcessError as e:
            shutil.rmtree(self._temp_dir)
            self._temp_dir = None
            raise GitError(f"Failed to clone repository {repo_url}: {e.stderr}")

    def __del__(self) -> None:
        """Clean up temporary directory."""
        if hasattr(self, "_temp_dir") and self._temp_dir:
            try:
                shutil.rmtree(self._temp_dir)
            except Exception:
                pass

    def _get_provider(self) -> AIProvider:
        """Lazily create and return the AI provider."""
        if self._provider is None:
            self._provider = create_provider(
                provider=self.options.provider,
                api_key=self.options.api_key,
                model=self.options.model,
            )
        return self._provider

    def _check_remote_api_consent(self) -> bool:
        """Check if user consents to sending data to remote API.

        Returns:
            True if user consents
        """
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
        """Generate a new commit message using AI."""
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

    def _process_commits(self, commits: list[str]) -> dict[str, str]:
        """Process a list of commits and generate new messages."""
        message_map: dict[str, str] = {}
        self._skipped_count = 0
        self._improved_count = 0

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
                            self._skipped_count += 1
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
                        progress.start()

                    # Generate new message
                    new_message = self._generate_commit_message(
                        commit_info.diff,
                        commit_info.files,
                        commit_info.message,
                    )

                    if new_message != commit_info.message:
                        message_map[commit_hash] = new_message
                        self._improved_count += 1

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

        return message_map

    def generate_for_staged(self) -> str:
        """Generate a commit message for staged changes."""
        self.repo.check_repository()

        if not self._check_remote_api_consent():
            raise RuntimeError("User declined to send data to remote AI provider")

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

        self.repo.check_repository()

        # Checkout target branch if specified
        if self.options.branch:
            try:
                self.repo.checkout(self.options.branch)
            except GitError:
                if not self.options.quiet:
                    self.console.print(
                        f"[yellow]Branch '{self.options.branch}' not found. Staying on current branch.[/]"
                    )

        current_branch = self.repo.get_current_branch()

        if not self.options.quiet:
            self.console.print(f"[blue]Current branch: {current_branch}[/]")

        if self.repo.has_uncommitted_changes():
            self.console.print("\n[yellow]⚠️  Warning: You have uncommitted changes![/]")
            if not self.options.quiet:
                from rich.prompt import Confirm

                if not Confirm.ask("Do you want to continue anyway?"):
                    return

        commits = self.repo.get_commits(self.options.max_commits)
        if not commits:
            if not self.options.quiet:
                self.console.print("[yellow]No commits found to process.[/]")
            return

        if not self._check_remote_api_consent():
            return

        # Warning about rewriting history
        if not self.options.dry_run and not self.options.quiet:
            self.console.print("\n[bold red]⚠️  WARNING: This will REWRITE your git history![/]")
            from rich.prompt import Confirm

            if not Confirm.ask("\nDo you want to proceed?"):
                return

        # Create backup
        backup_branch = None
        if not self.options.skip_backup and not self.options.dry_run:
            backup_branch = self.repo.create_backup_branch(current_branch)
            if not self.options.quiet:
                self.console.print(f"\n[green]✅ Created backup branch: {backup_branch}[/]")

        # Process
        message_map = self._process_commits(commits)

        # Build ordered list for rewrite
        ordered_messages = [
            message_map.get(c, self.repo.get_commit_full_message(c)) for c in commits
        ]

        # Summary
        if not self.options.quiet:
            self.console.print("\n[cyan]📊 Summary:[/]")
            self.console.print(f"[blue]  • Total commits analyzed: {len(commits)}[/]")
            self.console.print(f"[green]  • Commits improved: {self._improved_count}[/]")
            self.console.print(f"[yellow]  • Commits to be rewritten: {len(message_map)}[/]")

        if not message_map:
            if not self.options.quiet:
                self.console.print("\n[green]✨ No changes needed.[/]")
            if backup_branch:
                self.repo.delete_branch(backup_branch)
            return

        if self.options.dry_run:
            return

        if not self.options.quiet:
            from rich.prompt import Confirm

            if not Confirm.ask("\nDo you want to apply the new commit messages?"):
                return

        # Apply
        try:
            self.repo.rewrite_history(ordered_messages, self.options.max_commits)
            if not self.options.quiet:
                self.console.print("\n[bold green]✅ Successfully rewrote git history![/]")

            # Push back to remote if requested
            if self.options.push:
                if not self.options.quiet:
                    self.console.print("[blue]Pushing changes to remote...[/]")

                branch = self.options.branch or self.repo.get_current_branch()
                try:
                    self.repo._run("push", "origin", f"HEAD:{branch}", "--force")
                    if not self.options.quiet:
                        self.console.print(f"[green]✅ Successfully pushed to origin/{branch}[/]")
                except GitError as e:
                    self.console.print(f"[red]❌ Failed to push to remote: {e}[/]")
                    raise
        except Exception as e:
            self.console.print(f"\n[red]❌ Error: {e}[/]")
            if backup_branch:
                self.console.print(f"[yellow]Restore with: git reset --hard {backup_branch}[/]")
            raise


__all__ = ["GitCommitRewriter", "RewriteOptions"]
