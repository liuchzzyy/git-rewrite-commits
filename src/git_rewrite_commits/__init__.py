"""AI-powered git commit message rewriter using OpenAI, DeepSeek, or Ollama."""

__version__ = "1.0.0"

from .rewriter import GitCommitRewriter, RewriteOptions, CommitInfo

__all__ = ["GitCommitRewriter", "RewriteOptions", "CommitInfo", "__version__"]
