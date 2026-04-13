"""Tests for Typst content validation."""

from typst_ir.validation import (
    ValidationResult,
    _check_balanced_delimiters,
    _check_escape_sequences,
    _validate_with_regex,
    _validate_with_tree_sitter,
    escape_special_chars,
    validate_typst_content,
)


class TestValidationResult:
    def test_validation_result_creation(self):
        result = ValidationResult(valid=True, errors=[], method="regex")
        assert result.valid is True
        assert result.errors == []
        assert result.method == "regex"

    def test_validation_result_invalid(self):
        result = ValidationResult(
            valid=False, errors=["Syntax error"], method="tree-sitter"
        )
        assert result.valid is False
        assert result.errors == ["Syntax error"]
        assert result.method == "tree-sitter"


class TestEscapeSpecialChars:
    def test_escape_hash(self):
        assert escape_special_chars("Hello #world") == "Hello \\#world"

    def test_escape_dollar(self):
        assert escape_special_chars("Price is $5") == "Price is \\$5"

    def test_escape_at(self):
        assert escape_special_chars("Email: user@example.com") == "Email: user\\@example.com"

    def test_escape_multiple(self):
        input_text = "Cost: $5 #total @store"
        expected = "Cost: \\$5 \\#total \\@store"
        assert escape_special_chars(input_text) == expected

    def test_no_special_chars(self):
        text = "Hello World"
        assert escape_special_chars(text) == text

    def test_empty_string(self):
        assert escape_special_chars("") == ""


class TestValidateTypstContent:
    def test_valid_content(self):
        result = validate_typst_content("Hello World")
        assert result.valid is True
        assert result.errors == []

    def test_returns_tree_sitter_method(self):
        result = validate_typst_content("test")
        assert result.method == "tree-sitter"


class TestValidateWithRegex:
    def test_valid_simple_content(self):
        result = _validate_with_regex("Hello World")
        assert result.valid is True
        assert result.errors == []
        assert result.method == "regex"

    def test_valid_with_braces(self):
        result = _validate_with_regex("{hello: world}")
        assert result.valid is True
        assert result.errors == []

    def test_valid_with_brackets(self):
        result = _validate_with_regex("[1, 2, 3]")
        assert result.valid is True

    def test_valid_with_parentheses(self):
        result = _validate_with_regex("(foo bar)")
        assert result.valid is True

    def test_valid_with_string(self):
        result = _validate_with_regex('"hello world"')
        assert result.valid is True

    def test_unmatched_closing_brace(self):
        result = _validate_with_regex("hello}")
        assert result.valid is False
        assert any("Unmatched closing" in e for e in result.errors)

    def test_unmatched_opening_brace(self):
        result = _validate_with_regex("{hello")
        assert result.valid is False
        assert any("Unclosed" in e for e in result.errors)

    def test_mismatched_delimiters(self):
        result = _validate_with_regex("{hello)")
        assert result.valid is False
        assert any("Mismatched" in e for e in result.errors)

    def test_unclosed_string(self):
        result = _validate_with_regex('"hello')
        assert result.valid is False
        assert any("Unclosed string" in e for e in result.errors)

    def test_escaped_quote_in_string(self):
        result = _validate_with_regex('"hello \\"world\\""')
        assert result.valid is True

    def test_invalid_escape_sequence(self):
        result = _validate_with_regex('"hello \\q"')
        assert result.valid is False
        assert any("Invalid escape sequence" in e for e in result.errors)


class TestCheckBalancedDelimiters:
    def test_balanced_braces(self):
        errors = []
        _check_balanced_delimiters("{hello}", errors)
        assert len(errors) == 0

    def test_balanced_mixed(self):
        errors = []
        _check_balanced_delimiters("{[()]}", errors)
        assert len(errors) == 0

    def test_unbalanced_closing(self):
        errors = []
        _check_balanced_delimiters("}", errors)
        assert len(errors) == 1
        assert "Unmatched closing" in errors[0]

    def test_unbalanced_opening(self):
        errors = []
        _check_balanced_delimiters("{", errors)
        assert len(errors) == 1
        assert "Unclosed" in errors[0]

    def test_ignores_delimiters_in_strings(self):
        errors = []
        _check_balanced_delimiters('"{hello}"', errors)
        assert len(errors) == 0

    def test_ignores_delimiters_in_raw_strings(self):
        errors = []
        _check_balanced_delimiters("`{hello}`", errors)
        assert len(errors) == 0


class TestCheckEscapeSequences:
    def test_valid_backslash(self):
        errors = []
        _check_escape_sequences('"\\\\"', errors)
        assert len(errors) == 0

    def test_valid_quote(self):
        errors = []
        _check_escape_sequences('"\\""', errors)
        assert len(errors) == 0

    def test_valid_newline(self):
        errors = []
        _check_escape_sequences('"\\n"', errors)
        assert len(errors) == 0

    def test_invalid_escape(self):
        errors = []
        _check_escape_sequences('"\\q"', errors)
        assert len(errors) == 1
        assert "Invalid escape sequence" in errors[0]


class TestValidateWithTreeSitter:
    def test_valid_typst_heading(self):
        result = _validate_with_tree_sitter("= Heading")
        assert result.valid is True
        assert result.method == "tree-sitter"

    def test_valid_typst_function(self):
        result = _validate_with_tree_sitter("#emph[hello]")
        assert result.valid is True

    def test_invalid_syntax(self):
        result = _validate_with_tree_sitter("#(")
        assert result.valid is False
        assert len(result.errors) > 0


class TestTreeSitterIntegration:
    def test_tree_sitter_used_when_available(self):
        result = validate_typst_content("= Title")
        assert result.method == "tree-sitter"
