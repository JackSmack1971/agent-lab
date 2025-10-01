"""Unit tests for persist module."""

import csv
import pytest
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch, mock_open
from hypothesis import given, strategies as st

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
    CSV_PATH,
)


class TestPersist:
    """Test suite for persist functionality."""

    def test_init_csv_creates_file_when_not_exists(self, tmp_path: Path) -> None:
        """Test init_csv creates CSV with headers when file doesn't exist."""
        csv_file = tmp_path / "test_runs.csv"
        with patch('services.persist.CSV_PATH', csv_file):
            init_csv()

        assert csv_file.exists()
        content = csv_file.read_text(encoding="utf-8")
        assert "ts,agent_name,model," in content  # Check header is written

    def test_init_csv_does_nothing_when_exists(self, tmp_path: Path) -> None:
        """Test init_csv does nothing when CSV already exists."""
        csv_file = tmp_path / "test_runs.csv"
        csv_file.write_text("existing content", encoding="utf-8")

        with patch('services.persist.CSV_PATH', csv_file):
            init_csv()

        # File should still have original content
        content = csv_file.read_text(encoding="utf-8")
        assert content == "existing content"

    def test_append_run_calls_init_and_writes_row(self, tmp_path: Path) -> None:
        """Test append_run initializes CSV and appends record."""
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

        with patch('services.persist.CSV_PATH', csv_file), \
             patch('services.persist.init_csv') as mock_init:
            append_run(record)

        mock_init.assert_called_once()
        assert csv_file.exists()
        content = csv_file.read_text(encoding="utf-8")
        assert "test_agent" in content
        assert "2023-01-01T12:00:00" in content

    def test_load_recent_runs_returns_empty_when_no_file(self, tmp_path: Path) -> None:
        """Test load_recent_runs returns empty list when CSV doesn't exist."""
        csv_file = tmp_path / "test_runs.csv"

        with patch('services.persist.CSV_PATH', csv_file):
            result = load_recent_runs()

        assert result == []

    def test_load_recent_runs_with_valid_csv(self, tmp_path: Path) -> None:
        """Test load_recent_runs parses valid CSV rows."""
        csv_file = tmp_path / "test_runs.csv"
        # Write header and one valid row
        with csv_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerow({
                "ts": "2023-01-01T12:00:00",
                "agent_name": "test_agent",
                "model": "openai/gpt-4",
                "prompt_tokens": "100",
                "completion_tokens": "200",
                "total_tokens": "300",
                "latency_ms": "1500",
                "cost_usd": "0.02",
                "experiment_id": "",
                "task_label": "",
                "run_notes": "",
                "streaming": "true",
                "model_list_source": "dynamic",
                "tool_web_enabled": "false",
                "web_status": "off",
                "aborted": "false",
            })

        with patch('services.persist.CSV_PATH', csv_file):
            result = load_recent_runs(limit=10)

        assert len(result) == 1
        record = result[0]
        assert record.agent_name == "test_agent"
        assert record.prompt_tokens == 100
        assert record.streaming is True

    def test_parse_row_missing_timestamp_raises_value_error(self) -> None:
        """Test _parse_row raises ValueError for missing timestamp."""
        row = {header: "" for header in CSV_HEADERS}
        row["ts"] = ""

        with pytest.raises(ValueError, match="Missing timestamp"):
            _parse_row(row)

    def test_parse_row_invalid_timestamp_raises_value_error(self) -> None:
        """Test _parse_row raises ValueError for invalid timestamp format."""
        row = {header: "" for header in CSV_HEADERS}
        row["ts"] = "invalid-timestamp"

        with pytest.raises(ValueError, match="Invalid timestamp format"):
            _parse_row(row)

    @pytest.mark.parametrize("value,expected", [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("y", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("n", False),
        ("", False),
        (None, False),
        (True, True),
        (False, False),
    ])
    def test_coerce_bool(self, value: Any, expected: bool) -> None:
        """Test _coerce_bool handles various inputs."""
        assert _coerce_bool(value) == expected

    @pytest.mark.parametrize("value,expected", [
        ("123", 123),
        ("0", 0),
        ("-1", -1),
        ("", 0),
        (None, 0),
        ("abc", 0),
        (123, 123),
        (0.5, 0),
    ])
    def test_coerce_int(self, value: Any, expected: int) -> None:
        """Test _coerce_int handles various inputs."""
        assert _coerce_int(value) == expected

    @pytest.mark.parametrize("value,expected", [
        ("1.5", 1.5),
        ("0.0", 0.0),
        ("-1.23", -1.23),
        ("", 0.0),
        (None, 0.0),
        ("abc", 0.0),
        (1.5, 1.5),
        (0, 0.0),
    ])
    def test_coerce_float(self, value: Any, expected: float) -> None:
        """Test _coerce_float handles various inputs."""
        assert _coerce_float(value) == expected

    def test_load_recent_runs_skips_malformed_rows(self, tmp_path: Path) -> None:
        """Test load_recent_runs skips rows that cannot be parsed."""
        csv_file = tmp_path / "test_runs.csv"
        with csv_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            # Valid row
            writer.writerow({
                "ts": "2023-01-01T12:00:00",
                "agent_name": "test_agent",
                "model": "openai/gpt-4",
                "prompt_tokens": "100",
                "completion_tokens": "200",
                "total_tokens": "300",
                "latency_ms": "1500",
                "cost_usd": "0.02",
                "experiment_id": "",
                "task_label": "",
                "run_notes": "",
                "streaming": "true",
                "model_list_source": "dynamic",
                "tool_web_enabled": "false",
                "web_status": "off",
                "aborted": "false",
            })
            # Malformed row - missing timestamp
            writer.writerow({
                "ts": "",
                "agent_name": "bad_agent",
                "model": "openai/gpt-4",
                "prompt_tokens": "100",
                "completion_tokens": "200",
                "total_tokens": "300",
                "latency_ms": "1500",
                "cost_usd": "0.02",
                "experiment_id": "",
                "task_label": "",
                "run_notes": "",
                "streaming": "true",
                "model_list_source": "dynamic",
                "tool_web_enabled": "false",
                "web_status": "off",
                "aborted": "false",
            })

        with patch('services.persist.CSV_PATH', csv_file):
            result = load_recent_runs(limit=10)

        # Should only load the valid row
        assert len(result) == 1
        assert result[0].agent_name == "test_agent"

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
        if value in ("", None):
            assert _coerce_float(value) == 0.0
        else:
            try:
                expected = float(value)
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