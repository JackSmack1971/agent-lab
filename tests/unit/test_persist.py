"""Unit tests for persist module."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from hypothesis import given, strategies as st
from typing import Any

from agents.models import RunRecord
from services.persist import (
    init_csv,
    append_run,
    load_recent_runs,
    _coerce_bool,
    _coerce_int,
    _coerce_float,
    _parse_row,
    CSV_HEADERS,
)


class TestPersist:
    """Test suite for persist functionality."""

    def test_init_csv_creates_file_with_headers(self, tmp_path: Path) -> None:
        """Test init_csv creates CSV file with correct headers."""
        csv_file = tmp_path / "test_runs.csv"
        with patch('services.persist.CSV_PATH', csv_file):
            init_csv()

        assert csv_file.exists()
        content = csv_file.read_text(encoding="utf-8")
        # Check that headers are written correctly
        expected_headers = ",".join(CSV_HEADERS)
        assert expected_headers in content

    def test_init_csv_idempotent(self, tmp_path: Path) -> None:
        """Test init_csv is idempotent - calling twice doesn't duplicate headers."""
        csv_file = tmp_path / "test_runs.csv"

        # First call
        with patch('services.persist.CSV_PATH', csv_file):
            init_csv()
        first_content = csv_file.read_text(encoding="utf-8")

        # Second call
        with patch('services.persist.CSV_PATH', csv_file):
            init_csv()
        second_content = csv_file.read_text(encoding="utf-8")

        # Content should be identical
        assert first_content == second_content

    def test_append_run_writes_correct_schema(self, tmp_path: Path) -> None:
        """Test append_run writes records with correct CSV schema."""
        csv_file = tmp_path / "test_runs.csv"
        record = RunRecord(
            ts=datetime(2023, 1, 1, 12, 0, 0),
            agent_name="test_agent",
            model="openai/gpt-4",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            latency_ms=1500,
            cost_usd=0.02,
            streaming=True,
            model_list_source="dynamic",
            tool_web_enabled=False,
            web_status="off",
            aborted=False,
        )

        with patch('services.persist.CSV_PATH', csv_file):
            append_run(record)

        assert csv_file.exists()
        content = csv_file.read_text(encoding="utf-8")
        lines = content.strip().split('\n')
        assert len(lines) == 2  # header + 1 data row
        # Check that all expected fields are present in the data row
        data_line = lines[1]
        assert "test_agent" in data_line
        assert "openai/gpt-4" in data_line

    def test_append_run_formats_timestamp_as_iso(self, tmp_path: Path) -> None:
        """Test append_run formats timestamp as ISO string."""
        csv_file = tmp_path / "test_runs.csv"
        record = RunRecord(
            ts=datetime(2023, 1, 1, 12, 0, 0),
            agent_name="test_agent",
            model="openai/gpt-4",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            latency_ms=1500,
            cost_usd=0.02,
            streaming=True,
            model_list_source="dynamic",
            tool_web_enabled=False,
            web_status="off",
            aborted=False,
        )

        with patch('services.persist.CSV_PATH', csv_file):
            append_run(record)

        content = csv_file.read_text(encoding="utf-8")
        # Should contain ISO formatted timestamp
        assert "2023-01-01T12:00:00" in content

    def test_load_recent_runs_roundtrip(self, tmp_path: Path) -> None:
        """Test load_recent_runs can read back what was written."""
        csv_file = tmp_path / "test_runs.csv"
        original_record = RunRecord(
            ts=datetime(2023, 1, 1, 12, 0, 0),
            agent_name="test_agent",
            model="openai/gpt-4",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            latency_ms=1500,
            cost_usd=0.02,
            streaming=True,
            model_list_source="dynamic",
            tool_web_enabled=False,
            web_status="off",
            aborted=False,
        )

        # Write record
        with patch('services.persist.CSV_PATH', csv_file):
            append_run(original_record)

        # Read it back
        with patch('services.persist.CSV_PATH', csv_file):
            result = load_recent_runs(limit=1)

        assert len(result) == 1
        loaded_record = result[0]
        assert loaded_record.agent_name == original_record.agent_name
        assert loaded_record.model == original_record.model
        assert loaded_record.prompt_tokens == original_record.prompt_tokens

    def test_load_recent_runs_skips_malformed_rows(self, tmp_path: Path) -> None:
        """Test load_recent_runs skips malformed rows gracefully."""
        # This test should fail initially since the code doesn't handle malformed rows yet
        csv_file = tmp_path / "test_runs.csv"

        # Write a valid row first
        valid_record = RunRecord(
            ts=datetime(2023, 1, 1, 12, 0, 0),
            agent_name="valid_agent",
            model="openai/gpt-4",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            latency_ms=1500,
            cost_usd=0.02,
            streaming=True,
            model_list_source="dynamic",
            tool_web_enabled=False,
            web_status="off",
            aborted=False,
        )

        with patch('services.persist.CSV_PATH', csv_file):
            append_run(valid_record)

        # Manually add a malformed row (this would cause issues)
        with csv_file.open("a", newline="", encoding="utf-8") as f:
            f.write("malformed,row,data\n")

        with patch('services.persist.CSV_PATH', csv_file):
            # This should handle the malformed row gracefully
            result = load_recent_runs(limit=10)

        # Should still load the valid record
        assert len(result) == 1
        assert result[0].agent_name == "valid_agent"

    @given(st.integers())
    def test_coerce_int_handles_invalid_input(self, value: int) -> None:
        """Property test: _coerce_int handles various integer inputs."""
        # This should work for valid integers
        assert _coerce_int(value) == value

    @given(st.floats(allow_nan=False, allow_infinity=False))
    def test_coerce_float_handles_invalid_input(self, value: float) -> None:
        """Property test: _coerce_float handles various float inputs."""
        # This should work for valid floats
        assert _coerce_float(value) == value

    def test_coerce_bool_recognizes_truthy_strings(self) -> None:
        """Test _coerce_bool recognizes various truthy string representations."""
        # Test various truthy values
        assert _coerce_bool("true") is True
        assert _coerce_bool("1") is True
        assert _coerce_bool("yes") is True
        assert _coerce_bool("y") is True

        # Test falsy values
        assert _coerce_bool("false") is False
        assert _coerce_bool("0") is False
        assert _coerce_bool("") is False
        assert _coerce_bool(None) is False

    def test_parse_row_validates_required_fields(self) -> None:
        """Test _parse_row validates required fields like timestamp."""
        # Test missing timestamp
        row = {header: "" for header in CSV_HEADERS}
        row["ts"] = ""

        with pytest.raises(ValueError):
            _parse_row(row)

    @given(st.integers())
    def test_coerce_int_property_valid_int(self, value: int) -> None:
        """Property test: _coerce_int handles any integer correctly."""
        assert _coerce_int(value) == value

    @given(st.floats(allow_nan=False, allow_infinity=False))
    def test_coerce_int_property_float_to_int(self, value: float) -> None:
        """Property test: _coerce_int truncates floats to int."""
        assert _coerce_int(value) == int(value)

    @given(st.text())
    def test_coerce_int_property_invalid_strings_default_to_zero(self, value: str) -> None:
        """Property test: _coerce_int returns 0 for invalid strings."""
        if value in ("", None):
            assert _coerce_int(value) == 0
        else:
            try:
                expected = int(value)
                assert _coerce_int(value) == expected
            except (TypeError, ValueError):
                assert _coerce_int(value) == 0

    @given(st.floats(allow_nan=False, allow_infinity=False))
    def test_coerce_float_property_valid_float(self, value: float) -> None:
        """Property test: _coerce_float handles any float correctly."""
        assert _coerce_float(value) == value

    @given(st.integers())
    def test_coerce_float_property_int_to_float(self, value: int) -> None:
        """Property test: _coerce_float converts ints to floats."""
        assert _coerce_float(value) == float(value)

    @given(st.text())
    def test_coerce_float_property_invalid_strings_default_to_zero(self, value: str) -> None:
        """Property test: _coerce_float returns 0.0 for invalid strings."""
        import math
        if value in ("", None):
            assert _coerce_float(value) == 0.0
        else:
            try:
                expected = float(value)
                if math.isnan(expected):
                    assert math.isnan(_coerce_float(value))
                else:
                    assert _coerce_float(value) == expected
            except (TypeError, ValueError):
                assert _coerce_float(value) == 0.0

    @given(st.booleans())
    def test_coerce_bool_property_valid_bool(self, value: bool) -> None:
        """Property test: _coerce_bool handles booleans correctly."""
        assert _coerce_bool(value) == value

    @given(st.text())
    def test_coerce_bool_property_string_cases(self, value: str) -> None:
        """Property test: _coerce_bool handles string cases."""
        if value is None:
            assert _coerce_bool(value) == False
        else:
            stripped = value.strip().lower()
            if stripped in {"1", "true", "yes", "y"}:
                assert _coerce_bool(value) == True
            else:
                assert _coerce_bool(value) == False