"""Git operations wrapper using subprocess."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommitInfo:
    """Information about a git commit."""

    hash: str
    message: str
    files: list[str]
    diff: str


class GitError(Exception):
    """Error during git operations."""

    pass


class GitRepo:
    """Wrapper for git operations using subprocess."""

    # Empty tree hash for comparing initial commits
    EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

    def __init__(self, path: str | Path | None = None) -> None:
        """Initialize git repository wrapper.

        Args:
            path: Path to the repository (defaults to current directory)
        """
        self.path = Path(path) if path else Path.cwd()

    def _run(
        self,
        *args: str,
        check: bool = True,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command.

        Args:
            *args: Git command arguments
            check: Raise exception on non-zero exit
            capture_output: Capture stdout/stderr

        Returns:
            CompletedProcess result

        Raises:
            GitError: If command fails and check is True
        """
        cmd = ["git", *args]
        try:
            result = subprocess.run(
                cmd,
                cwd=self.path,
                check=check,
                capture_output=capture_output,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return result
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Command failed: {' '.join(cmd)}\nExit code: {e.returncode}\nStderr: {e.stderr}"
            ) from e

    def is_repository(self) -> bool:
        """Check if this is a valid git repository."""
        try:
            self._run("rev-parse", "--git-dir")
            return True
        except GitError:
            return False

    def check_repository(self) -> None:
        """Check if this is a valid git repository.

        Raises:
            GitError: If not a git repository
        """
        if not self.is_repository():
            raise GitError("Not a git repository!")

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        result = self._run("status", "--porcelain")
        return bool(result.stdout.strip())

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = self._run("rev-parse", "--abbrev-ref", "HEAD")
        return result.stdout.strip()

    def get_commits(self, max_commits: int | None = None) -> list[str]:
        """Get commit hashes in reverse chronological order.

        Args:
            max_commits: Maximum number of commits to return

        Returns:
            List of commit hashes (oldest first for processing)
        """
        args = ["rev-list", "--reverse", "HEAD"]
        if max_commits and max_commits > 0:
            args = ["rev-list", "-n", str(max_commits), "--reverse", "HEAD"]

        result = self._run(*args)
        commits = [line for line in result.stdout.strip().split("\n") if line]
        return commits

    def get_commit_message(self, commit_hash: str) -> str:
        """Get the commit message for a specific commit."""
        result = self._run("log", "-1", "--format=%s", commit_hash)
        return result.stdout.strip()

    def get_commit_full_message(self, commit_hash: str) -> str:
        """Get the full commit message including body."""
        result = self._run("log", "-1", "--format=%B", commit_hash)
        return result.stdout.strip()

    def get_commit_files(self, commit_hash: str) -> list[str]:
        """Get list of files changed in a commit."""
        result = self._run("diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash)
        return [f for f in result.stdout.strip().split("\n") if f]

    def get_commit_diff(self, commit_hash: str) -> str:
        """Get the diff for a specific commit."""
        # Check if this commit has a parent
        try:
            self._run("rev-parse", f"{commit_hash}^")
            # Has parent - diff against parent
            result = self._run(
                "diff-tree", "--no-commit-id", "-p", f"{commit_hash}^..{commit_hash}"
            )
        except GitError:
            # No parent (initial commit) - diff against empty tree
            result = self._run("diff-tree", "--no-commit-id", "-p", self.EMPTY_TREE, commit_hash)
        return result.stdout

    def get_commit_info(self, commit_hash: str) -> CommitInfo:
        """Get full commit information."""
        return CommitInfo(
            hash=commit_hash,
            message=self.get_commit_message(commit_hash),
            files=self.get_commit_files(commit_hash),
            diff=self.get_commit_diff(commit_hash),
        )

    def get_staged_diff(self) -> str:
        """Get diff of staged changes."""
        result = self._run("diff", "--cached")
        return result.stdout

    def get_staged_files(self) -> list[str]:
        """Get list of staged files."""
        result = self._run("diff", "--cached", "--name-only")
        return [f for f in result.stdout.strip().split("\n") if f]

    def create_backup_branch(self, base_name: str | None = None) -> str:
        """Create a backup branch of the current state.

        Args:
            base_name: Base name for the backup branch

        Returns:
            Name of the created backup branch
        """
        import time

        if base_name is None:
            base_name = self.get_current_branch()

        backup_name = f"backup-{base_name}-{int(time.time())}"
        self._run("branch", backup_name)
        return backup_name

    def delete_branch(self, branch_name: str) -> None:
        """Delete a branch."""
        self._run("branch", "-D", branch_name)

    def rewrite_history(self, messages: list[str]) -> None:
        """Rewrite commit history with new messages.

        Args:
            messages: Ordered list of new messages (oldest commit first)
        """
        commits = self.get_commits()
        if len(messages) != len(commits):
            raise GitError(
                f"Message count ({len(messages)}) does not match commit count ({len(commits)})"
            )

        # Get the parent of the first commit to be rewritten
        # If it's the root commit, parent is None
        first_commit = commits[0]
        try:
            parent_result = self._run("rev-parse", f"{first_commit}^")
            new_parent = parent_result.stdout.strip()
        except GitError:
            new_parent = None

        # Rewrite each commit
        for commit_hash, new_message in zip(commits, messages):
            # Get the tree of the original commit
            tree_result = self._run("rev-parse", f"{commit_hash}^{{tree}}")
            tree_hash = tree_result.stdout.strip()

            # Build the commit-tree command
            cmd_args = ["commit-tree", tree_hash]
            if new_parent:
                cmd_args.extend(["-p", new_parent])

            # Run commit-tree and provide message via stdin
            process = subprocess.run(
                ["git", *cmd_args],
                cwd=self.path,
                input=new_message,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            new_parent = process.stdout.strip()

        # Update HEAD to the new tip
        if new_parent:
            self._run("reset", "--hard", new_parent)

    def install_hook(self, hook_name: str, content: str) -> Path:
        """Install a git hook.

        Args:
            hook_name: Name of the hook (e.g., 'prepare-commit-msg')
            content: Content of the hook script

        Returns:
            Path to the installed hook
        """
        import os
        import stat

        hooks_dir = self.path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        hook_path = hooks_dir / hook_name
        hook_path.write_text(content, encoding="utf-8")

        # Make executable on Unix
        if os.name != "nt":
            hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

        return hook_path
