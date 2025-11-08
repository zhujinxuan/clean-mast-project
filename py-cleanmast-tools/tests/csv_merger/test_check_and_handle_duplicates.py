"""Tests for duplicate timestamp handling in csv_merger."""

import pandas as pd
import pytest
from datetime import datetime
from pre_processor_mast_data.csv_merger import check_and_handle_duplicates


def test_no_duplicates():
    """Test that DataFrames without duplicates pass through unchanged."""
    df = pd.DataFrame({
        '_timestamp': pd.to_datetime(['2024-01-01 00:00:00', '2024-01-01 00:10:00', '2024-01-01 00:20:00']),
        'value': [1, 2, 3]
    })

    result = check_and_handle_duplicates(df, None)
    pd.testing.assert_frame_equal(result, df)

    result = check_and_handle_duplicates(df, 'keep_first')
    pd.testing.assert_frame_equal(result, df)

    result = check_and_handle_duplicates(df, 'keep_last')
    pd.testing.assert_frame_equal(result, df)


def test_keep_first():
    """Test that keep_first keeps the first occurrence of duplicate timestamps."""
    df = pd.DataFrame({
        '_timestamp': pd.to_datetime([
            '2024-01-01 00:00:00',
            '2024-01-01 00:10:00',
            '2024-01-01 00:10:00',  # duplicate
            '2024-01-01 00:20:00',
        ]),
        'value': [1, 2, 3, 4]
    })

    result = check_and_handle_duplicates(df, 'keep_first')

    expected = pd.DataFrame({
        '_timestamp': pd.to_datetime([
            '2024-01-01 00:00:00',
            '2024-01-01 00:10:00',
            '2024-01-01 00:20:00',
        ]),
        'value': [1, 2, 4]
    })

    pd.testing.assert_frame_equal(result, expected)


def test_keep_last():
    """Test that keep_last keeps the last occurrence of duplicate timestamps."""
    df = pd.DataFrame({
        '_timestamp': pd.to_datetime([
            '2024-01-01 00:00:00',
            '2024-01-01 00:10:00',
            '2024-01-01 00:10:00',  # duplicate
            '2024-01-01 00:20:00',
        ]),
        'value': [1, 2, 3, 4]
    })

    result = check_and_handle_duplicates(df, 'keep_last')

    expected = pd.DataFrame({
        '_timestamp': pd.to_datetime([
            '2024-01-01 00:00:00',
            '2024-01-01 00:10:00',
            '2024-01-01 00:20:00',
        ]),
        'value': [1, 3, 4]
    })

    pd.testing.assert_frame_equal(result, expected)


def test_keep_none():
    """Test that None keeps all duplicates."""
    df = pd.DataFrame({
        '_timestamp': pd.to_datetime([
            '2024-01-01 00:00:00',
            '2024-01-01 00:10:00',
            '2024-01-01 00:10:00',  # duplicate
            '2024-01-01 00:20:00',
        ]),
        'value': [1, 2, 3, 4]
    })

    result = check_and_handle_duplicates(df, None)

    pd.testing.assert_frame_equal(result, df)


def test_multiple_duplicates():
    """Test handling of multiple duplicate timestamps."""
    df = pd.DataFrame({
        '_timestamp': pd.to_datetime([
            '2024-01-01 00:00:00',
            '2024-01-01 00:10:00',
            '2024-01-01 00:10:00',  # duplicate 1
            '2024-01-01 00:10:00',  # duplicate 2
            '2024-01-01 00:20:00',
            '2024-01-01 00:20:00',  # duplicate 3
        ]),
        'value': [1, 2, 3, 4, 5, 6]
    })

    result_first = check_and_handle_duplicates(df, 'keep_first')
    expected_first = pd.DataFrame({
        '_timestamp': pd.to_datetime([
            '2024-01-01 00:00:00',
            '2024-01-01 00:10:00',
            '2024-01-01 00:20:00',
        ]),
        'value': [1, 2, 5]
    })
    pd.testing.assert_frame_equal(result_first, expected_first)

    result_last = check_and_handle_duplicates(df, 'keep_last')
    expected_last = pd.DataFrame({
        '_timestamp': pd.to_datetime([
            '2024-01-01 00:00:00',
            '2024-01-01 00:10:00',
            '2024-01-01 00:20:00',
        ]),
        'value': [1, 4, 6]
    })
    pd.testing.assert_frame_equal(result_last, expected_last)


def test_invalid_duplicate_handling():
    """Test that invalid duplicate_handling values raise ValueError."""
    df = pd.DataFrame({
        '_timestamp': pd.to_datetime(['2024-01-01 00:00:00', '2024-01-01 00:00:00']),
        'value': [1, 2]
    })

    with pytest.raises(ValueError, match="Invalid duplicate_handling value"):
        check_and_handle_duplicates(df, 'invalid_option')


def test_preserves_columns():
    """Test that all columns are preserved during duplicate handling."""
    df = pd.DataFrame({
        '_timestamp': pd.to_datetime([
            '2024-01-01 00:00:00',
            '2024-01-01 00:10:00',
            '2024-01-01 00:10:00',
        ]),
        'value1': [1, 2, 3],
        'value2': [10, 20, 30],
        'value3': ['a', 'b', 'c']
    })

    result = check_and_handle_duplicates(df, 'keep_first')

    assert list(result.columns) == ['_timestamp', 'value1', 'value2', 'value3']
    assert len(result) == 2
