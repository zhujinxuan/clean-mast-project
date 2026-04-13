"""Typst content validation with tree-sitter."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import tree_sitter_typst as _tst_module
from tree_sitter import Language as _Lang
from tree_sitter import Parser as _Parse
from tree_sitter import Tree

# Suppress deprecation warning from tree-sitter-typst returning int pointer
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    _Language = _Lang(_tst_module.language())

_Parser = _Parse


@dataclass(frozen=True)
class ValidationResult:
    """Result of Typst content validation.

    Immutable data class containing validation status, any error messages,
    and the validation method used.

    Attributes:
        valid: True if content is valid, False otherwise
        errors: List of error messages if invalid, empty list if valid
        method: Validation method used ("tree-sitter" or "regex")

    Example:
        >>> result = validate_typst_content("= Heading")
        >>> result.valid
        True
        >>> result.errors
        []
        >>> result.method
        'tree-sitter'
    """

    valid: bool
    errors: list[str]
    method: str


def validate_typst_content(content: str) -> ValidationResult:
    """Validate Typst content using tree-sitter parser."""
    return _validate_with_tree_sitter(content)


def _validate_with_tree_sitter(content: str) -> ValidationResult:
    """Validate Typst content using tree-sitter parser.

    Parses the content using tree-sitter-typst grammar and checks for parse errors.

    Args:
        content: Typst markup string to validate

    Returns:
        ValidationResult with valid status and any parse errors

    Raises:
        RuntimeError: If tree-sitter modules are not available

    Note:
        This function requires tree-sitter and tree-sitter-typst to be installed.
        Falls back to regex validation if tree-sitter is not available.
    """
    errors: list[str] = []

    try:
        parser = _Parser(_Language)
        tree = parser.parse(bytes(content, "utf8"))
        _check_tree_for_errors(tree, errors)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            method="tree-sitter",
        )
    except Exception as e:  # noqa: BLE001
        return ValidationResult(
            valid=False,
            errors=[f"Tree-sitter parsing error: {e}"],
            method="tree-sitter",
        )


def _check_tree_for_errors(tree: Tree, errors: list[str]) -> None:
    """Traverse tree-sitter parse tree to find ERROR nodes.

    Recursively walks the parse tree looking for nodes with type "ERROR"
    and collects their positions as error messages.

    Args:
        tree: Tree-sitter parse tree from parser
        errors: List to append error messages to (modified in-place)
    """
    cursor = tree.walk()

    def traverse():
        node = cursor.node
        if node is None:
            return
        if node.type == "ERROR":
            start_point = node.start_point
            errors.append(
                f"Parse error at line {start_point[0] + 1}, "
                f"column {start_point[1] + 1}"
            )

        if cursor.goto_first_child():
            traverse()
            while cursor.goto_next_sibling():
                traverse()
            cursor.goto_parent()

    traverse()


def _validate_with_regex(content: str) -> ValidationResult:
    """Validate Typst content using regex-based checks.

    Fallback validation method when tree-sitter is not available.
    Checks for balanced delimiters and valid escape sequences.

    Args:
        content: Typst markup string to validate

    Returns:
        ValidationResult with valid status and any errors found
    """
    errors: list[str] = []

    _check_balanced_delimiters(content, errors)
    _check_escape_sequences(content, errors)

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        method="regex",
    )


def _check_balanced_delimiters(content: str, errors: list[str]) -> None:
    """Check for balanced brackets, braces, and parentheses.

    Validates that all opening delimiters have matching closing delimiters
    and vice versa. Handles strings and raw strings correctly.

    Args:
        content: Typst markup string to check
        errors: List to append error messages to (modified in-place)

    Checks:
        - Unmatched closing delimiters
        - Mismatched delimiter pairs
        - Unclosed opening delimiters
        - Unclosed string literals
    """
    stack: list[tuple[str, int, int]] = []
    lines = content.split("\n")
    line_starts = [0]
    for line in lines[:-1]:
        line_starts.append(line_starts[-1] + len(line) + 1)

    in_string = False
    in_raw_string = False
    escape_next = False

    for i, char in enumerate(content):
        line_num = 0
        col_num = i
        for j, start in enumerate(line_starts):
            if i >= start:
                line_num = j
                col_num = i - start
            else:
                break

        if escape_next:
            escape_next = False
            continue

        if char == "\\" and not in_raw_string:
            escape_next = True
            continue

        if char == "`" and not in_string:
            in_raw_string = not in_raw_string
            continue

        if char == '"' and not in_raw_string:
            in_string = not in_string
            continue

        if in_string or in_raw_string:
            continue

        if char in "{[(":
            stack.append((char, line_num, col_num))
        elif char in "}])":
            if not stack:
                errors.append(
                    f"Unmatched closing '{char}' at line {line_num + 1}, "
                    f"column {col_num + 1}"
                )
            else:
                opening, open_line, open_col = stack.pop()
                expected_opening = {"}": "{", "]": "[", ")": "("}[char]
                if opening != expected_opening:
                    errors.append(
                        f"Mismatched delimiters: '{opening}' at line "
                        f"{open_line + 1}, column {open_col + 1} and "
                        f"'{char}' at line {line_num + 1}, column {col_num + 1}"
                    )

    for opening, line, col in stack:
        errors.append(
            f"Unclosed '{opening}' at line {line + 1}, column {col + 1}"
        )

    if in_string:
        errors.append("Unclosed string literal")
    if in_raw_string:
        errors.append("Unclosed raw string literal")


def _check_escape_sequences(content: str, errors: list[str]) -> None:
    """Check for valid escape sequences in strings.

    Validates that backslash escapes are followed by valid escape characters.

    Args:
        content: Typst markup string to check
        errors: List to append error messages to (modified in-place)

    Valid escapes: backslash, quote, n, r, t, 0, u, hash, at, dollar
    """
    valid_escapes = {"\\", '"', "n", "r", "t", "0", "u", "#", "@", "$"}

    in_string = False
    escape_next = False

    for i, char in enumerate(content):
        if escape_next:
            if char not in valid_escapes:
                line_num = content[:i].count("\n") + 1
                errors.append(
                    f"Invalid escape sequence '\\{char}' at line {line_num}"
                )
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string


def escape_special_chars(text: str) -> str:
    """Escape special Typst characters (#, $, @) in text."""
    return text.replace("#", "\\#").replace("$", "\\$").replace("@", "\\@")
