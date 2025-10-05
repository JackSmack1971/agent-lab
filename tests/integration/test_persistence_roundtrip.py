"""Integration tests for CSV persistence roundtrip validation."""

import csv
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from agents.models import RunRecord
from services.persist import (CSV_HEADERS, CSV_PATH, _coerce_bool,
                              _coerce_float, _coerce_int, _parse_row,
                              append_run, init_csv, load_recent_runs)


@pytest.mark.integration
class TestPersistenceRoundtrip:
    """Integration tests for CSV persistence and roundtrip validation."""

    @pytest.fixture
    def temp_csv_file(self, tmp_path):
        """Create temporary CSV file for testing."""
        csv_file = tmp_path / "test_runs.csv"
        return csv_file

    @pytest.fixture
    def sample_run_records(self):
        """Create sample RunRecord instances for testing."""
        base_time = datetime.now()

        return [
            RunRecord(
                ts=base_time,
                agent_name="TestAgent1",
                model="openai/gpt-4-turbo",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=1200,
                cost_usd=0.012,
                experiment_id="exp_001",
                task_label="math_task",
                run_notes="First test run",
                streaming=True,
                model_list_source="dynamic",
                tool_web_enabled=False,
                web_status="off",
                aborted=False,
            ),
            RunRecord(
                ts=base_time.replace(microsecond=base_time.microsecond + 1000),
                agent_name="TestAgent2",
                model="anthropic/claude-3-opus",
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                latency_ms=2500,
                cost_usd=0.0375,
                experiment_id="exp_002",
                task_label="coding_task",
                run_notes="Second test run with web tools",
                streaming=True,
                model_list_source="fallback",
                tool_web_enabled=True,
                web_status="ok",
                aborted=False,
            ),
            RunRecord(
                ts=base_time.replace(microsecond=base_time.microsecond + 2000),
                agent_name="TestAgent1",
                model="openai/gpt-4-turbo",
                prompt_tokens=50,
                completion_tokens=25,
                total_tokens=75,
                latency_ms=800,
                cost_usd=0.006,
                experiment_id="exp_001",
                task_label="quick_test",
                run_notes="Aborted run test",
                streaming=True,
                model_list_source="dynamic",
                tool_web_enabled=False,
                web_status="off",
                aborted=True,
            ),
        ]

    def test_persistence_roundtrip_basic_csv_operations_integration(
        self, temp_csv_file, sample_run_records
    ):
        """Test basic CSV write and read roundtrip."""
        # Override CSV path for testing
        with patch("services.persist.CSV_PATH", temp_csv_file):
            # Initialize CSV
            init_csv()

            # Write records
            for record in sample_run_records:
                append_run(record)

            # Read records back
            loaded_records = load_recent_runs(limit=10)

            # Verify roundtrip
            assert len(loaded_records) == 3

            # Check that all records are loaded and data is preserved
            # Convert to dicts for easier comparison
            loaded_data = {(r.agent_name, r.model): r for r in loaded_records}
            original_data = {(r.agent_name, r.model): r for r in sample_run_records}

            assert len(loaded_data) == len(original_data)

            # Check each original record is preserved
            for key, original in original_data.items():
                assert key in loaded_data
                loaded = loaded_data[key]

                assert loaded.prompt_tokens == original.prompt_tokens
                assert loaded.completion_tokens == original.completion_tokens
                assert loaded.total_tokens == original.total_tokens
                assert loaded.latency_ms == original.latency_ms
                assert (
                    abs(loaded.cost_usd - original.cost_usd) < 0.001
                )  # Float precision
                assert loaded.streaming == original.streaming
                assert loaded.aborted == original.aborted
                assert loaded.experiment_id == original.experiment_id
                assert loaded.task_label == original.task_label

    def test_persistence_roundtrip_csv_header_integrity_integration(
        self, temp_csv_file, sample_run_records
    ):
        """Test CSV header matches expected schema."""
        with patch("services.persist.CSV_PATH", temp_csv_file):
            # Initialize and write data
            init_csv()
            append_run(sample_run_records[0])

            # Read raw CSV to verify header
            with open(temp_csv_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)

            assert header == CSV_HEADERS
            assert len(header) == len(CSV_HEADERS)

            # Verify all expected columns are present
            expected_headers = [
                "ts",
                "agent_name",
                "model",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "latency_ms",
                "cost_usd",
                "experiment_id",
                "task_label",
                "run_notes",
                "streaming",
                "model_list_source",
                "tool_web_enabled",
                "web_status",
                "aborted",
            ]
            assert header == expected_headers

    def test_persistence_roundtrip_data_type_preservation_integration(
        self, temp_csv_file
    ):
        """Test that data types are preserved through CSV roundtrip."""
        with patch("services.persist.CSV_PATH", temp_csv_file):
            # Create record with specific data types
            record = RunRecord(
                ts=datetime.now(),
                agent_name="TypeTestAgent",
                model="test/model",
                prompt_tokens=123,
                completion_tokens=456,
                total_tokens=579,
                latency_ms=999,
                cost_usd=0.123456,
                streaming=True,
                model_list_source="dynamic",
                tool_web_enabled=False,
                web_status="blocked",
                aborted=False,
                experiment_id="type_test",
                task_label="data_types",
            )

            # Write and read back
            init_csv()
            append_run(record)
            loaded_records = load_recent_runs(limit=1)

            loaded = loaded_records[0]

            # Verify integer types
            assert isinstance(loaded.prompt_tokens, int)
            assert isinstance(loaded.completion_tokens, int)
            assert isinstance(loaded.total_tokens, int)
            assert isinstance(loaded.latency_ms, int)

            # Verify float types
            assert isinstance(loaded.cost_usd, float)

            # Verify boolean types
            assert isinstance(loaded.streaming, bool)
            assert isinstance(loaded.tool_web_enabled, bool)
            assert isinstance(loaded.aborted, bool)

            # Verify string types
            assert isinstance(loaded.agent_name, str)
            assert isinstance(loaded.model, str)
            assert isinstance(loaded.experiment_id, str)
            assert isinstance(loaded.task_label, str)
            assert isinstance(loaded.model_list_source, str)
            assert isinstance(loaded.web_status, str)

            # Verify datetime type
            assert isinstance(loaded.ts, datetime)

    def test_persistence_roundtrip_edge_case_values_integration(self, temp_csv_file):
        """Test roundtrip with edge case and boundary values."""
        with patch("services.persist.CSV_PATH", temp_csv_file):
            # Test with zero values
            zero_record = RunRecord(
                ts=datetime.now(),
                agent_name="ZeroAgent",
                model="zero/model",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=0,
                cost_usd=0.0,
                streaming=False,
                model_list_source="fallback",
                tool_web_enabled=False,
                web_status="off",
                aborted=False,
            )

            # Test with maximum reasonable values
            max_record = RunRecord(
                ts=datetime.now(),
                agent_name="MaxAgent",
                model="max/model",
                prompt_tokens=999999,
                completion_tokens=999999,
                total_tokens=1999998,
                latency_ms=300000,  # 5 minutes
                cost_usd=999.99,
                streaming=True,
                model_list_source="dynamic",
                tool_web_enabled=True,
                web_status="ok",
                aborted=True,
                experiment_id="edge_case_test",
                task_label="maximum_values",
                run_notes="Testing boundary conditions",
            )

            init_csv()
            append_run(zero_record)
            append_run(max_record)

            loaded = load_recent_runs(limit=2)

            # Check that both records are loaded with correct data
            loaded_data = {r.agent_name: r for r in loaded}

            # Verify max values
            assert "MaxAgent" in loaded_data
            max_loaded = loaded_data["MaxAgent"]
            assert max_loaded.prompt_tokens == 999999
            assert max_loaded.completion_tokens == 999999
            assert max_loaded.total_tokens == 1999998
            assert max_loaded.latency_ms == 300000
            assert max_loaded.cost_usd == 999.99
            assert max_loaded.streaming is True
            assert max_loaded.aborted is True
            assert max_loaded.experiment_id == "edge_case_test"

            # Verify zero values
            assert "ZeroAgent" in loaded_data
            zero_loaded = loaded_data["ZeroAgent"]
            assert zero_loaded.prompt_tokens == 0
            assert zero_loaded.completion_tokens == 0
            assert zero_loaded.total_tokens == 0
            assert zero_loaded.latency_ms == 0
            assert zero_loaded.cost_usd == 0.0
            assert zero_loaded.streaming is False
            assert zero_loaded.aborted is False

    def test_persistence_roundtrip_malformed_data_handling_integration(
        self, temp_csv_file
    ):
        """Test handling of malformed CSV data."""
        with patch("services.persist.CSV_PATH", temp_csv_file):
            # Create CSV with some malformed data
            init_csv()

            # Manually add malformed row
            with open(temp_csv_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                # Row with invalid timestamp
                writer.writerow(
                    {
                        **{header: "" for header in CSV_HEADERS},
                        "ts": "invalid-timestamp",
                        "agent_name": "MalformedAgent",
                        "latency_ms": "not-a-number",
                    }
                )

            # Valid row
            valid_record = RunRecord(
                ts=datetime.now(),
                agent_name="ValidAgent",
                model="valid/model",
                latency_ms=1000,
                streaming=True,
                model_list_source="dynamic",
                tool_web_enabled=False,
                web_status="off",
                aborted=False,
            )
            append_run(valid_record)

            # Load records - malformed row should be skipped
            loaded = load_recent_runs(limit=10)

            # Should only have the valid record
            assert len(loaded) == 1
            assert loaded[0].agent_name == "ValidAgent"

    def test_persistence_roundtrip_empty_and_missing_fields_integration(
        self, temp_csv_file
    ):
        """Test handling of empty and missing optional fields."""
        with patch("services.persist.CSV_PATH", temp_csv_file):
            # Record with minimal required fields
            minimal_record = RunRecord(
                ts=datetime.now(),
                agent_name="MinimalAgent",
                model="minimal/model",
                latency_ms=500,
                streaming=False,
                model_list_source="fallback",
                tool_web_enabled=False,
                web_status="off",
                aborted=False,
                # All optional fields left as defaults
            )

            init_csv()
            append_run(minimal_record)

            loaded = load_recent_runs(limit=1)

            assert len(loaded) == 1
            record = loaded[0]

            # Required fields should be preserved
            assert record.agent_name == "MinimalAgent"
            assert record.model == "minimal/model"
            assert record.latency_ms == 500

            # Optional fields should have sensible defaults
            assert record.experiment_id == ""
            assert record.task_label == ""
            assert record.run_notes == ""
            assert record.prompt_tokens == 0
            assert record.completion_tokens == 0
            assert record.total_tokens == 0
            assert record.cost_usd == 0.0

    def test_persistence_roundtrip_large_dataset_performance_integration(
        self, temp_csv_file
    ):
        """Test roundtrip performance with larger dataset."""
        with patch("services.persist.CSV_PATH", temp_csv_file):
            init_csv()

            # Create multiple records
            base_time = datetime.now()
            records = []

            for i in range(100):
                # Create timestamp with incremental microseconds (reset every 1000)
                microsecond_offset = (i * 1000) % 1000000
                record_time = base_time.replace(microsecond=microsecond_offset)
                if i >= 1000:  # If we exceed microsecond range, add seconds
                    record_time = record_time.replace(
                        second=record_time.second + (i // 1000)
                    )

                record = RunRecord(
                    ts=record_time,
                    agent_name=f"PerfAgent{i:03d}",
                    model="openai/gpt-4-turbo",
                    prompt_tokens=100 + i,
                    completion_tokens=50 + i,
                    total_tokens=150 + 2 * i,
                    latency_ms=1000 + i * 10,
                    cost_usd=0.01 + i * 0.001,
                    streaming=True,
                    model_list_source="dynamic",
                    tool_web_enabled=False,
                    web_status="off",
                    aborted=False,
                    experiment_id=f"perf_exp_{i:03d}",
                    task_label="performance_test",
                )
                records.append(record)
                append_run(record)

            # Load all records
            loaded = load_recent_runs(limit=200)

            # Verify all records loaded
            assert len(loaded) == 100

            # Verify data integrity - check that all records are loaded
            loaded_by_name = {r.agent_name: r for r in loaded}

            # Check first and last records by name
            assert "PerfAgent000" in loaded_by_name
            assert "PerfAgent099" in loaded_by_name

            first_loaded = loaded_by_name["PerfAgent000"]
            assert first_loaded.prompt_tokens == 100

            last_loaded = loaded_by_name["PerfAgent099"]
            assert last_loaded.prompt_tokens == 199

    def test_persistence_roundtrip_csv_append_consistency_integration(
        self, temp_csv_file, sample_run_records
    ):
        """Test that appending maintains CSV consistency."""
        with patch("services.persist.CSV_PATH", temp_csv_file):
            init_csv()

            # Append records one by one
            for record in sample_run_records:
                append_run(record)

            # Verify CSV structure after each append
            with open(temp_csv_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Should have header + 3 data rows
            assert len(lines) == 4

            # Verify each line has correct number of fields
            reader = csv.reader(lines)
            for row in reader:
                assert len(row) == len(CSV_HEADERS)

            # Verify data integrity
            loaded = load_recent_runs(limit=10)
            assert len(loaded) == 3

            # Verify all records are loaded by checking unique identifiers
            loaded_names = {r.agent_name for r in loaded}
            expected_names = {r.agent_name for r in sample_run_records}
            assert loaded_names == expected_names
