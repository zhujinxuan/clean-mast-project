#!/usr/bin/env python3
"""Create test cases for fingerprint matching algorithm.

This experiment tests ordered substring coverage matching for paragraph detection.

Test scenarios:
1. Pure text paragraphs (should match with both hash and fingerprint)
2. Paragraphs with references (hash fails, fingerprint works)
3. Paragraphs with inline equations (hash fails, fingerprint partial)
4. Mixed content (realistic paragraphs)
"""

from __future__ import annotations

import json
from pathlib import Path

# Test cases designed to test fingerprint matching
TEST_CASES = {
    "pure_text": {
        "description": "Pure text - should match with both hash and fingerprint",
        "typst_text": "The wind speed at 80 meters height was measured using a calibrated anemometer with an accuracy of plus or minus 0.1 meters per second.",
        "docx_text": "The wind speed at 80 meters height was measured using a calibrated anemometer with an accuracy of plus or minus 0.1 meters per second.",
        "expected_hash_match": True,
        "expected_fingerprint_match": True,
        "expected_coverage": 1.0,
    },
    "with_reference": {
        "description": "Text with reference - hash fails, fingerprint works",
        "typst_text": "See Figure \\ref{fig1} for details. The wind speed data shows a clear diurnal pattern with maximum values occurring during afternoon hours.",
        "docx_text": "See Figure 1 for details. The wind speed data shows a clear diurnal pattern with maximum values occurring during afternoon hours.",
        "expected_hash_match": False,
        "expected_fingerprint_match": True,
        "expected_coverage": 0.85,  # Approximate
    },
    "with_inline_equation": {
        "description": "Text with inline equation - hash fails, fingerprint works",
        "typst_text": "The energy output is calculated using $E = mc^2$ where m represents mass and c is the speed of light in vacuum.",
        "docx_text": "The energy output is calculated using where m represents mass and c is the speed of light in vacuum.",
        "expected_hash_match": False,
        "expected_fingerprint_match": True,
        "expected_coverage": 0.9,
    },
    "mixed_content": {
        "description": "Realistic paragraph with multiple elements",
        "typst_text": "According to \\ref{table1}, the average wind speed was 8.5 m/s. The Weibull shape parameter $k$ was estimated at 2.1, indicating a moderately skewed distribution. See \\ref{fig2} for the wind rose diagram.",
        "docx_text": "According to Table 1, the average wind speed was 8.5 m/s. The Weibull shape parameter k was estimated at 2.1, indicating a moderately skewed distribution. See Figure 2 for the wind rose diagram.",
        "expected_hash_match": False,
        "expected_fingerprint_match": True,
        "expected_coverage": 0.75,  # Approximate
    },
    "long_text_with_reference": {
        "description": "Long text with reference - fingerprint should work well",
        "typst_text": "The meteorological tower was installed at the proposed wind farm site in January 2023. Data collection began in February and continued through December of the same year. The tower is equipped with instruments at multiple heights: 30m, 50m, 80m, and 100m above ground level. See \\ref{fig-site-layout} for the tower configuration. Wind speed was measured using cup anemometers at all heights, while wind direction was measured using wind vanes at 50m and 80m. Temperature and pressure sensors were installed at 2m height. All instruments were calibrated before installation and checked monthly for drift.",
        "docx_text": "The meteorological tower was installed at the proposed wind farm site in January 2023. Data collection began in February and continued through December of the same year. The tower is equipped with instruments at multiple heights: 30m, 50m, 80m, and 100m above ground level. See Figure 3 for the tower configuration. Wind speed was measured using cup anemometers at all heights, while wind direction was measured using wind vanes at 50m and 80m. Temperature and pressure sensors were installed at 2m height. All instruments were calibrated before installation and checked monthly for drift.",
        "expected_hash_match": False,
        "expected_fingerprint_match": True,
        "expected_coverage": 0.95,  # High coverage due to long matching text
    },
    "short_text_reference": {
        "description": "Short text with reference - may not match",
        "typst_text": "See \\ref{fig1}.",
        "docx_text": "See Figure 1.",
        "expected_hash_match": False,
        "expected_fingerprint_match": False,  # Too short
        "expected_coverage": 0.0,  # No substring >= 20 chars
    },
    "formatting_difference": {
        "description": "Same content, different formatting",
        "typst_text": "The  wind  speed  was  8.5  m/s  at  80m  height.",  # Extra spaces
        "docx_text": "The wind speed was 8.5 m/s at 80m height.",
        "expected_hash_match": True,  # After normalization
        "expected_fingerprint_match": True,  # After normalization
        "expected_coverage": 1.0,
    },
}


def create_test_cases() -> dict:
    """Create test cases for fingerprint matching."""
    return TEST_CASES


def main() -> int:
    """Save test cases to JSON file."""
    test_cases = create_test_cases()
    
    output_path = Path(__file__).parent / "test_cases.json"
    output_path.write_text(json.dumps(test_cases, indent=2))
    
    print(f"Created {len(test_cases)} test cases")
    print(f"Output: {output_path}")
    
    for name, case in test_cases.items():
        print(f"\n{name}:")
        print(f"  Description: {case['description']}")
        print(f"  Expected hash match: {case['expected_hash_match']}")
        print(f"  Expected fingerprint match: {case['expected_fingerprint_match']}")
        print(f"  Expected coverage: {case['expected_coverage']:.0%}")
    
    return 0


if __name__ == "__main__":
    exit(main())