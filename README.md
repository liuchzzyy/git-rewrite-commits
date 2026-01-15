# git-rewrite-commits

AI-powered git commit message rewriter using OpenAI, DeepSeek, or Ollama.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automatically rewrite your entire git commit history with better, conventional commit messages using AI. Perfect for cleaning up messy commit histories before open-sourcing projects or improving repository maintainability.

## 🚀 Why git-rewrite-commits?

Messy commit histories like "fix", "update", "wip" make it hard to understand project evolution. This tool uses state-of-the-art AI to analyze your actual code changes and generate meaningful, conventional commit messages that reflect what *really* changed.

## ✨ Features

- **AI-powered commit message generation** using OpenAI, DeepSeek, or local Ollama models
- **Blazing fast history rewrite** using native git tree operations (no more slow `filter-branch`)
- **Conventional commits** format (feat, fix, chore, etc.) strictly enforced
- **Multi-language support** - generate commits in any language
- **Smart filtering** - skip already well-formed commits to save API costs
- **Local AI option** with Ollama - 100% privacy, no data leaves your machine
- **Git hooks integration** - automatic AI messages on every commit
- **Intelligent analysis** of code changes to generate meaningful messages
- **Safe operation** with automatic backup branches
- **Quality scoring** to identify commits that need improvement
- **Sensitive data redaction** - automatically removes API keys, tokens, passwords from diffs

## 🛠️ Installation

### From PyPI (Recommended)

```bash
pip install git-rewrite-commits
```

### From Source

```bash
git clone https://github.com/f/git-rewrite-commits.git
cd git-rewrite-commits
pip install -e .
```

## Quick Start

### Set up your AI provider

**Option A: OpenAI (default)**
```bash
export OPENAI_API_KEY="your-api-key"
git-rewrite-commits
```

**Option B: DeepSeek (NEW)**
```bash
export DEEPSEEK_API_KEY="your-api-key"
git-rewrite-commits --provider deepseek
```

**Option C: Ollama (local, privacy-friendly)**
```bash
ollama pull llama3.2
ollama serve
git-rewrite-commits --provider ollama
```

### Generate commit message for staged changes

```bash
git add -A
git commit -m "$(git-rewrite-commits --staged --quiet --skip-remote-consent)"
```

### Rewrite last 10 commits

```bash
git-rewrite-commits --max-commits 10 --dry-run  # Preview
git-rewrite-commits --max-commits 10            # Apply
```

## Usage

```
Usage: git-rewrite-commits [OPTIONS]

Options:
  --provider [openai|ollama|deepseek]
                                  AI provider to use
  -k, --api-key TEXT              API key (defaults to env var)
  -m, --model TEXT                AI model to use
  --ollama-url TEXT               Ollama server URL
  -b, --branch TEXT               Branch to rewrite
  -d, --dry-run                   Preview changes without applying
  -v, --verbose                   Show detailed output
  -q, --quiet                     Suppress all output
  --max-commits INTEGER           Process only last N commits
  --skip-backup                   Skip creating backup branch
  --skip-well-formed / --no-skip-well-formed
                                  Skip well-formed commits
  --min-quality-score INTEGER     Quality threshold (0-10)
  -t, --template TEXT             Custom commit template
  -l, --language TEXT             Output language (e.g., en, zh, es)
  -p, --prompt TEXT               Custom AI prompt
  --staged                        Generate for staged changes
  --skip-remote-consent           Skip consent prompt
  --install-hooks                 Install git hooks
  --version                       Show version
  --help                          Show this message
```

## Git Hooks

Install AI commit message hooks:

```bash
git-rewrite-commits --install-hooks
```

Then enable them:

```bash
# Enable preview before commit
git config hooks.preCommitPreview true

# Enable automatic message generation
git config hooks.prepareCommitMsg true

# Set your provider
git config hooks.commitProvider deepseek  # or openai, ollama
```

## Providers

### OpenAI
- Default provider
- Models: `gpt-4o-mini` (default), `gpt-4o`, `gpt-3.5-turbo`
- Requires: `OPENAI_API_KEY` environment variable

### DeepSeek (NEW)
- OpenAI-compatible API
- Models: `deepseek-chat` (default), `deepseek-coder`, `deepseek-reasoner`
- Requires: `DEEPSEEK_API_KEY` environment variable
- Website: https://platform.deepseek.com/

### Ollama
- Local processing - no data sent externally
- Models: `llama3.2` (default), any model you have pulled
- Requires: Ollama running locally (`ollama serve`)

## Security & Privacy

When using remote AI providers (OpenAI, DeepSeek), this tool:

✅ **Automatically redacts** API keys, passwords, and tokens
✅ **Completely hides** .env file contents
✅ **Removes** private keys and certificates
✅ **Creates backups** before history rewrites
✅ **Requires consent** before sending data (unless `--skip-remote-consent`)

For maximum privacy, use Ollama:
```bash
git config hooks.commitProvider ollama
```

## Custom Templates

```bash
# Conventional commits with scope
git-rewrite-commits --template "feat(scope): message"

# With ticket number
git-rewrite-commits --template "[JIRA-XXX] type: message"

# With emoji
git-rewrite-commits --template "🔧 fix: message"
```

## Multi-language Support

```bash
git-rewrite-commits --language zh    # Chinese
git-rewrite-commits --language es    # Spanish
git-rewrite-commits --language ja    # Japanese
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Credits

Python port of [f/git-rewrite-commits](https://github.com/f/git-rewrite-commits) by Fatih Kadir Akın.
