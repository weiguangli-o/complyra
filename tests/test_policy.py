from __future__ import annotations

from app.core.config import settings
from app.services.policy import evaluate_output_policy


def test_output_policy_blocks_secret_like_content() -> None:
    original_enabled = settings.output_policy_enabled
    original_message = settings.output_policy_block_message
    original_patterns = list(settings.output_policy_block_patterns)

    settings.output_policy_enabled = True
    settings.output_policy_block_message = "blocked"
    settings.output_policy_block_patterns = [r"AKIA[0-9A-Z]{16}"]

    try:
        evaluation = evaluate_output_policy("Token leaked: AKIA1234567890ABCDEF")
        assert evaluation.blocked is True
        assert evaluation.answer == "blocked"
        assert evaluation.matched_rules == [r"AKIA[0-9A-Z]{16}"]
    finally:
        settings.output_policy_enabled = original_enabled
        settings.output_policy_block_message = original_message
        settings.output_policy_block_patterns = original_patterns


def test_output_policy_can_be_disabled() -> None:
    original_enabled = settings.output_policy_enabled
    original_patterns = list(settings.output_policy_block_patterns)

    settings.output_policy_enabled = False
    settings.output_policy_block_patterns = [r"AKIA[0-9A-Z]{16}"]

    try:
        evaluation = evaluate_output_policy("Token leaked: AKIA1234567890ABCDEF")
        assert evaluation.blocked is False
        assert evaluation.answer == "Token leaked: AKIA1234567890ABCDEF"
        assert evaluation.matched_rules == []
    finally:
        settings.output_policy_enabled = original_enabled
        settings.output_policy_block_patterns = original_patterns


def test_output_policy_empty_patterns_passes() -> None:
    original = list(settings.output_policy_block_patterns)
    original_enabled = settings.output_policy_enabled
    settings.output_policy_enabled = True
    settings.output_policy_block_patterns = []

    try:
        evaluation = evaluate_output_policy("AKIA1234567890ABCDEF")
        assert evaluation.blocked is False
    finally:
        settings.output_policy_block_patterns = original
        settings.output_policy_enabled = original_enabled


def test_output_policy_no_match_passes() -> None:
    original = list(settings.output_policy_block_patterns)
    original_enabled = settings.output_policy_enabled
    settings.output_policy_enabled = True
    settings.output_policy_block_patterns = [r"NEVER_MATCH_THIS_PATTERN_XYZ"]

    try:
        evaluation = evaluate_output_policy("This is a safe answer")
        assert evaluation.blocked is False
        assert evaluation.matched_rules == []
    finally:
        settings.output_policy_block_patterns = original
        settings.output_policy_enabled = original_enabled
