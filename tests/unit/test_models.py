"""Unit tests for models module."""

import pytest
from datetime import datetime
from typing import Any
from pydantic import ValidationError

from agents.models import AgentConfig, RunRecord, Session


class TestAgentConfig:
    """Test suite for AgentConfig model."""

    def test_agent_config_creation_with_required_fields(self) -> None:
        """Test AgentConfig creation with required fields."""
        config = AgentConfig(
            name="Test Agent",
            model="openai/gpt-4",
            system_prompt="You are a helpful assistant."
        )

        assert config.name == "Test Agent"
        assert config.model == "openai/gpt-4"
        assert config.system_prompt == "You are a helpful assistant."
        assert config.temperature == 0.7  # default
        assert config.top_p == 1.0  # default
        assert config.tools == []  # default
        assert config.extras == {}  # default

    def test_agent_config_creation_with_all_fields(self) -> None:
        """Test AgentConfig creation with all fields specified."""
        config = AgentConfig(
            name="Full Agent",
            model="anthropic/claude-3",
            system_prompt="You are an expert assistant.",
            temperature=0.5,
            top_p=0.9,
            tools=["calculator", "search"],
            extras={"max_tokens": 1000, "debug": True}
        )

        assert config.name == "Full Agent"
        assert config.model == "anthropic/claude-3"
        assert config.system_prompt == "You are an expert assistant."
        assert config.temperature == 0.5
        assert config.top_p == 0.9
        assert config.tools == ["calculator", "search"]
        assert config.extras == {"max_tokens": 1000, "debug": True}

    def test_agent_config_temperature_validation(self) -> None:
        """Test temperature field validation."""
        # Valid temperatures
        AgentConfig(name="test", model="test", system_prompt="test", temperature=0.0)
        AgentConfig(name="test", model="test", system_prompt="test", temperature=1.0)
        AgentConfig(name="test", model="test", system_prompt="test", temperature=2.0)

        # Invalid temperatures
        with pytest.raises(ValueError):
            AgentConfig(name="test", model="test", system_prompt="test", temperature=-0.1)

        with pytest.raises(ValueError):
            AgentConfig(name="test", model="test", system_prompt="test", temperature=2.1)

    def test_agent_config_top_p_validation(self) -> None:
        """Test top_p field validation."""
        # Valid top_p values
        AgentConfig(name="test", model="test", system_prompt="test", top_p=0.0)
        AgentConfig(name="test", model="test", system_prompt="test", top_p=0.5)
        AgentConfig(name="test", model="test", system_prompt="test", top_p=1.0)

        # Invalid top_p values
        with pytest.raises(ValueError):
            AgentConfig(name="test", model="test", system_prompt="test", top_p=-0.1)

        with pytest.raises(ValueError):
            AgentConfig(name="test", model="test", system_prompt="test", top_p=1.1)

    def test_agent_config_arbitrary_types_allowed(self) -> None:
        """Test that AgentConfig allows arbitrary types in extras."""
        custom_obj = {"callable": lambda x: x, "complex": 1+2j}
        config = AgentConfig(
            name="test",
            model="test",
            system_prompt="test",
            extras=custom_obj
        )
        assert config.extras == custom_obj


class TestRunRecord:
    """Test suite for RunRecord model."""

    def test_run_record_creation_with_required_fields(self) -> None:
        """Test RunRecord creation with required fields."""
        ts = datetime.now()
        record = RunRecord(
            ts=ts,
            agent_name="Test Agent",
            model="openai/gpt-4",
            latency_ms=1000
        )

        assert record.ts == ts
        assert record.agent_name == "Test Agent"
        assert record.model == "openai/gpt-4"
        assert record.latency_ms == 1000
        # Check defaults
        assert record.prompt_tokens == 0
        assert record.completion_tokens == 0
        assert record.total_tokens == 0
        assert record.cost_usd == 0.0
        assert record.experiment_id == ""
        assert record.task_label == ""
        assert record.run_notes == ""
        assert record.streaming is True
        assert record.model_list_source == "fallback"
        assert record.tool_web_enabled is False
        assert record.web_status == "off"
        assert record.aborted is False

    def test_run_record_creation_with_all_fields(self) -> None:
        """Test RunRecord creation with all fields specified."""
        ts = datetime.now()
        record = RunRecord(
            ts=ts,
            agent_name="Full Test Agent",
            model="anthropic/claude-3",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=2000,
            cost_usd=0.015,
            experiment_id="exp_001",
            task_label="classification",
            run_notes="Test run with full data",
            streaming=False,
            model_list_source="dynamic",
            tool_web_enabled=True,
            web_status="ok",
            aborted=False
        )

        assert record.ts == ts
        assert record.agent_name == "Full Test Agent"
        assert record.model == "anthropic/claude-3"
        assert record.prompt_tokens == 100
        assert record.completion_tokens == 50
        assert record.total_tokens == 150
        assert record.latency_ms == 2000
        assert record.cost_usd == 0.015
        assert record.experiment_id == "exp_001"
        assert record.task_label == "classification"
        assert record.run_notes == "Test run with full data"
        assert record.streaming is False
        assert record.model_list_source == "dynamic"
        assert record.tool_web_enabled is True
        assert record.web_status == "ok"
        assert record.aborted is False

    def test_run_record_literal_validation(self) -> None:
        """Test RunRecord literal field validation."""
        from pydantic import ValidationError
        ts = datetime.now()

        # Valid model_list_source values
        RunRecord(ts=ts, agent_name="test", model="test", latency_ms=1, model_list_source="dynamic")
        RunRecord(ts=ts, agent_name="test", model="test", latency_ms=1, model_list_source="fallback")

        # Invalid model_list_source value
        with pytest.raises(ValidationError):
            RunRecord(ts=ts, agent_name="test", model="test", latency_ms=1, model_list_source="invalid")  # type: ignore

        # Valid web_status values
        RunRecord(ts=ts, agent_name="test", model="test", latency_ms=1, web_status="off")
        RunRecord(ts=ts, agent_name="test", model="test", latency_ms=1, web_status="ok")
        RunRecord(ts=ts, agent_name="test", model="test", latency_ms=1, web_status="blocked")

        # Invalid web_status value
        with pytest.raises(ValidationError):
            RunRecord(ts=ts, agent_name="test", model="test", latency_ms=1, web_status="invalid")  # type: ignore

    def test_run_record_arbitrary_types_allowed(self) -> None:
        """Test that RunRecord allows arbitrary types."""
        ts = datetime.now()
        # This should work since arbitrary_types_allowed=True
        record = RunRecord(
            ts=ts,
            agent_name="test",
            model="test",
            latency_ms=1
        )
        # The model_config allows arbitrary types, but we don't have any complex fields here
        assert record.ts == ts


class TestSession:
    """Test suite for Session model."""

    def test_session_creation_with_required_fields(self) -> None:
        """Test Session creation with required fields."""
        created_at = datetime.now()
        agent_config = AgentConfig(name="test", model="test", system_prompt="test")

        session = Session(
            id="session_123",
            created_at=created_at,
            agent_config=agent_config,
            transcript=[],
            model_id="openai/gpt-4"
        )

        assert session.id == "session_123"
        assert session.created_at == created_at
        assert session.agent_config == agent_config
        assert session.transcript == []
        assert session.model_id == "openai/gpt-4"
        assert session.notes == ""  # default

    def test_session_creation_with_all_fields(self) -> None:
        """Test Session creation with all fields specified."""
        created_at = datetime.now()
        agent_config = AgentConfig(
            name="Full Agent",
            model="anthropic/claude-3",
            system_prompt="Full prompt",
            temperature=0.8
        )

        transcript = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        session = Session(
            id="full_session_456",
            created_at=created_at,
            agent_config=agent_config,
            transcript=transcript,
            model_id="anthropic/claude-3",
            notes="Full test session"
        )

        assert session.id == "full_session_456"
        assert session.created_at == created_at
        assert session.agent_config == agent_config
        assert session.transcript == transcript
        assert session.model_id == "anthropic/claude-3"
        assert session.notes == "Full test session"

    def test_session_arbitrary_types_allowed(self) -> None:
        """Test that Session allows arbitrary types in transcript."""
        created_at = datetime.now()
        agent_config = AgentConfig(name="test", model="test", system_prompt="test")

        # Transcript can contain arbitrary types
        transcript = [
            {"role": "user", "content": "Hello", "metadata": {"timestamp": datetime.now()}},
            {"role": "assistant", "content": "Hi", "custom_field": lambda x: x}
        ]

        session = Session(
            id="test_session",
            created_at=created_at,
            agent_config=agent_config,
            transcript=transcript,
            model_id="test/model"
        )

        assert session.transcript == transcript


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_agent_config_serialization(self) -> None:
        """Test AgentConfig JSON serialization."""
        config = AgentConfig(
            name="Test Agent",
            model="openai/gpt-4",
            system_prompt="Test prompt",
            temperature=0.8,
            tools=["tool1"]
        )

        data = config.model_dump()
        assert data["name"] == "Test Agent"
        assert data["model"] == "openai/gpt-4"
        assert data["temperature"] == 0.8

        # Test roundtrip
        config2 = AgentConfig(**data)
        assert config2 == config

    def test_run_record_serialization(self) -> None:
        """Test RunRecord JSON serialization."""
        ts = datetime.now()
        record = RunRecord(
            ts=ts,
            agent_name="Test Agent",
            model="openai/gpt-4",
            latency_ms=1000,
            prompt_tokens=50,
            cost_usd=0.01
        )

        data = record.model_dump()
        assert data["agent_name"] == "Test Agent"
        assert data["latency_ms"] == 1000
        assert data["cost_usd"] == 0.01

        # Test roundtrip
        record2 = RunRecord(**data)
        assert record2.agent_name == record.agent_name
        assert record2.latency_ms == record.latency_ms

    def test_session_serialization(self) -> None:
        """Test Session JSON serialization."""
        created_at = datetime.now()
        agent_config = AgentConfig(name="test", model="test", system_prompt="test")

        session = Session(
            id="test_session",
            created_at=created_at,
            agent_config=agent_config,
            transcript=[{"role": "user", "content": "test"}],
            model_id="test/model",
            notes="test notes"
        )

        data = session.model_dump()
        assert data["id"] == "test_session"
        assert data["notes"] == "test notes"

        # Test roundtrip
        session2 = Session(**data)
        assert session2.id == session.id
        assert session2.notes == session.notes