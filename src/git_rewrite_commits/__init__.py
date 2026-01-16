"""AI-powered git commit message rewriter using OpenAI or DeepSeek."""

__version__ = "1.0.0"

from .git import CommitInfo
from .rewriter import GitCommitRewriter, RewriteOptions

__all__ = ["GitCommitRewriter", "RewriteOptions", "CommitInfo", "__version__"]
