#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path


@dataclass
class SubstringMatch:
    text_a_start: int
    text_a_end: int
    text_b_start: int
    text_b_end: int
    substring: str


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def find_ordered_matches(text_a: str, text_b: str, min_length: int = 20) -> list[SubstringMatch]:
    text_a = normalize_whitespace(text_a)
    text_b = normalize_whitespace(text_b)
    matcher = SequenceMatcher(None, text_a, text_b, autojunk=False)
    matches = []
    for a_start, b_start, length in matcher.get_matching_blocks():
        if length >= min_length:
            matches.append(SubstringMatch(
                text_a_start=a_start,
                text_a_end=a_start + length,
                text_b_start=b_start,
                text_b_end=b_start + length,
                substring=text_a[a_start:a_start + length],
            ))
    return matches


def calculate_coverage(text: str, matches: list[SubstringMatch], use_a: bool) -> float:
    text = normalize_whitespace(text)
    if not text:
        return 0.0
    covered = set()
    for match in matches:
        start = match.text_a_start if use_a else match.text_b_start
        end = match.text_a_end if use_a else match.text_b_end
        for i in range(start, end):
            covered.add(i)
    return len(covered) / len(text)


def match_by_coverage(text_a: str, text_b: str, min_length: int = 20, threshold: float = 0.8) -> tuple[bool, float, float]:
    matches = find_ordered_matches(text_a, text_b, min_length)
    coverage_a = calculate_coverage(text_a, matches, use_a=True)
    coverage_b = calculate_coverage(text_b, matches, use_a=False)
    is_match = coverage_a >= threshold and coverage_b >= threshold
    return is_match, coverage_a, coverage_b


def test_pure_text():
    test_cases = load_test_cases()
    case = test_cases["pure_text"]
    is_match, cov_a, cov_b = match_by_coverage(case["typst_text"], case["docx_text"])
    assert is_match is True
    assert cov_a == 1.0
    assert cov_b == 1.0


def test_with_reference():
    test_cases = load_test_cases()
    case = test_cases["with_reference"]
    is_match, cov_a, cov_b = match_by_coverage(case["typst_text"], case["docx_text"])
    assert is_match is True
    assert cov_a >= 0.8
    assert cov_b >= 0.8


def test_with_inline_equation():
    test_cases = load_test_cases()
    case = test_cases["with_inline_equation"]
    is_match, cov_a, cov_b = match_by_coverage(case["typst_text"], case["docx_text"])
    assert is_match is True
    assert cov_a >= 0.8
    assert cov_b >= 0.8


def test_mixed_content():
    test_cases = load_test_cases()
    case = test_cases["mixed_content"]
    is_match, cov_a, cov_b = match_by_coverage(case["typst_text"], case["docx_text"])
    assert is_match is True
    assert cov_a >= 0.7
    assert cov_b >= 0.7


def test_long_text_with_reference():
    test_cases = load_test_cases()
    case = test_cases["long_text_with_reference"]
    is_match, cov_a, cov_b = match_by_coverage(case["typst_text"], case["docx_text"])
    assert is_match is True
    assert cov_a >= 0.9
    assert cov_b >= 0.9


def test_short_text_reference():
    test_cases = load_test_cases()
    case = test_cases["short_text_reference"]
    is_match, cov_a, cov_b = match_by_coverage(case["typst_text"], case["docx_text"])
    assert is_match is False
    assert cov_a == 0.0
    assert cov_b == 0.0


def test_formatting_difference():
    test_cases = load_test_cases()
    case = test_cases["formatting_difference"]
    is_match, cov_a, cov_b = match_by_coverage(case["typst_text"], case["docx_text"])
    assert is_match is True
    assert cov_a == 1.0
    assert cov_b == 1.0


def load_test_cases() -> dict:
    path = Path(__file__).parent / "test_cases.json"
    return json.loads(path.read_text())


if __name__ == "__main__":
    test_pure_text()
    test_with_reference()
    test_with_inline_equation()
    test_mixed_content()
    test_long_text_with_reference()
    test_short_text_reference()
    test_formatting_difference()
    print("All fingerprint tests passed")
