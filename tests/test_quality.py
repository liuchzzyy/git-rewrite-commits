import pytest
from git_rewrite_commits.quality import score_commit_message, is_well_formed


def test_score_commit_message_conventional():
    score, is_good, reason = score_commit_message("feat: add new feature")
    assert score >= 7
    assert is_good
    assert "follows conventional format" in reason


def test_score_commit_message_generic():
    score, is_good, reason = score_commit_message("update")
    assert score < 7
    assert not is_good
    assert "too generic" in reason


def test_score_commit_message_too_short():
    score, is_good, reason = score_commit_message("fix: a")
    assert "too short" in reason


def test_is_well_formed():
    assert is_well_formed("feat: implementation of something")
    assert not is_well_formed("wip")
