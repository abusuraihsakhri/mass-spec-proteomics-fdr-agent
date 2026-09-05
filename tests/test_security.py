"""
Security-focused tests for mass-spec-proteomics-fdr-agent.
Validates input validation, path traversal protection, and audit key enforcement.
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import (
    validate_identifier,
    validate_file_path,
    ValidationException,
    AuditTrail,
    SecurityException,
)


class TestIdentifierValidation:
    """Tests for validate_identifier function."""

    def test_valid_simple_identifier(self):
        assert validate_identifier("TASK-001") == "TASK-001"

    def test_valid_alphanumeric(self):
        assert validate_identifier("ABC123") == "ABC123"

    def test_valid_with_dots_and_underscores(self):
        assert validate_identifier("TARGET.GEN_01") == "TARGET.GEN_01"

    def test_empty_string_raises(self):
        with pytest.raises(ValidationException, match="cannot be empty"):
            validate_identifier("")

    def test_control_characters_raise(self):
        with pytest.raises(ValidationException, match="control characters"):
            validate_identifier("TASK\nINJECT")

    def test_newline_raises(self):
        with pytest.raises(ValidationException, match="control characters"):
            validate_identifier("TASK\r\nINJECT")

    def test_tab_raises(self):
        with pytest.raises(ValidationException, match="control characters"):
            validate_identifier("TASK\tINJECT")

    def test_path_traversal_chars_raise(self):
        with pytest.raises(ValidationException, match="invalid characters"):
            validate_identifier("../../etc/passwd")

    def test_special_chars_raise(self):
        with pytest.raises(ValidationException, match="invalid characters"):
            validate_identifier("TASK;rm -rf")

    def test_spaces_raise(self):
        with pytest.raises(ValidationException, match="invalid characters"):
            validate_identifier("TASK 001")

    def test_exceeds_max_length_raises(self):
        with pytest.raises(ValidationException, match="exceeds maximum length"):
            validate_identifier("A" * 200)

    def test_non_string_raises(self):
        with pytest.raises(ValidationException, match="must be a string"):
            validate_identifier(12345)


class TestFilePathValidation:
    """Tests for validate_file_path function."""

    def test_valid_existing_file(self, tmp_path):
        test_file = tmp_path / "test.csv"
        test_file.write_text("data")
        result = validate_file_path(str(test_file), must_exist=True)
        assert os.path.isabs(result)

    def test_valid_nonexistent_output_path(self, tmp_path):
        test_file = tmp_path / "output.csv"
        result = validate_file_path(str(test_file), must_exist=False)
        assert os.path.isabs(result)

    def test_path_traversal_raises(self):
        with pytest.raises(ValidationException, match="Path traversal"):
            validate_file_path("../../../etc/passwd")

    def test_tilde_raises(self):
        with pytest.raises(ValidationException, match="Path traversal"):
            validate_file_path("~/.ssh/id_rsa")

    def test_null_byte_raises(self):
        with pytest.raises(ValidationException, match="Null bytes"):
            validate_file_path("file\x00name.csv")

    def test_nonexistent_input_raises(self):
        with pytest.raises(ValidationException, match="File not found"):
            validate_file_path("/nonexistent/path/file.csv", must_exist=True)

    def test_empty_path_raises(self):
        with pytest.raises(ValidationException, match="cannot be empty"):
            validate_file_path("")

    def test_non_string_raises(self):
        with pytest.raises(ValidationException, match="must be a string"):
            validate_file_path(123)


class TestAuditSecretKey:
    """Tests for audit secret key enforcement."""

    def test_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("AUDIT_SECRET_KEY", raising=False)
        with pytest.raises(SecurityException, match="AUDIT_SECRET_KEY"):
            AuditTrail()

    def test_short_key_raises(self, monkeypatch):
        monkeypatch.setenv("AUDIT_SECRET_KEY", "short")
        with pytest.raises(SecurityException, match="at least 16 characters"):
            AuditTrail()

    def test_valid_key_works(self, monkeypatch):
        monkeypatch.setenv("AUDIT_SECRET_KEY", "this-is-a-valid-key-1234567890")
        trail = AuditTrail()
        assert trail.secret_key == b"this-is-a-valid-key-1234567890"

    def test_explicit_key_parameter_works(self):
        trail = AuditTrail(secret_key="explicit-valid-key-1234567890")
        assert trail.secret_key == b"explicit-valid-key-1234567890"
