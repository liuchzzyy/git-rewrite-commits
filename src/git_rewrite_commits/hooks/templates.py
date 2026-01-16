"""Git hook templates for AI commit message generation."""


def get_pre_commit_hook(is_windows: bool) -> str:
    """Get pre-commit hook content.

    Args:
        is_windows: Whether to generate Windows batch script

    Returns:
        Hook script content
    """
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
    """Get prepare-commit-msg hook content.

    Args:
        is_windows: Whether to generate Windows batch script

    Returns:
        Hook script content
    """
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


__all__ = ["get_pre_commit_hook", "get_prepare_commit_msg_hook"]
