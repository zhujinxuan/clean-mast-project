#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from test_fingerprint import match_by_coverage, normalize_whitespace


def hash_text(text: str) -> str:
    return hashlib.sha256(normalize_whitespace(text).encode()).hexdigest()


def hash_match(text_a: str, text_b: str) -> bool:
    return hash_text(text_a) == hash_text(text_b)


def load_test_cases() -> dict:
    path = Path(__file__).parent / "test_cases.json"
    return json.loads(path.read_text())


def main() -> int:
    test_cases = load_test_cases()

    rows = []
    all_correct = True
    for name, case in test_cases.items():
        hash_result = hash_match(case["typst_text"], case["docx_text"])
        fp_result, cov_a, cov_b = match_by_coverage(case["typst_text"], case["docx_text"])

        hash_ok = hash_result == case["expected_hash_match"]
        fp_ok = fp_result == case["expected_fingerprint_match"]
        if not hash_ok or not fp_ok:
            all_correct = False

        rows.append({
            "name": name,
            "hash": "✓" if hash_result else "✗",
            "fingerprint": "✓" if fp_result else "✗",
            "coverage": f"{cov_a:.0%}",
            "hash_expected": "✓" if case["expected_hash_match"] else "✗",
            "fp_expected": "✓" if case["expected_fingerprint_match"] else "✗",
            "hash_ok": "✓" if hash_ok else "✗",
            "fp_ok": "✓" if fp_ok else "✗",
        })

    print(f"{'Test Case':<30} {'Hash':<6} {'FP':<6} {'Cov':<6} {'HashExp':<8} {'FPExp':<6} {'H_OK':<5} {'FP_OK':<5}")
    print("-" * 80)
    for row in rows:
        print(f"{row['name']:<30} {row['hash']:<6} {row['fingerprint']:<6} {row['coverage']:<6} {row['hash_expected']:<8} {row['fp_expected']:<6} {row['hash_ok']:<5} {row['fp_ok']:<5}")

    print()
    if all_correct:
        print("All results match expectations.")
    else:
        print("Some results differ from expectations.")

    return 0 if all_correct else 1


if __name__ == "__main__":
    exit(main())
