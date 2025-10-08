"""Property-based tests for models module using Hypothesis."""

import pytest
from datetime import datetime
from typing import Any

from hypothesis import given, strategies as st, settings, HealthCheck
from pydantic import ValidationError

from agents.models import AgentConfig, RunRecord, Session


# Hypothesis strategies for model generation
agent_config_strategy = st.builds(
    AgentConfig,
    name=st.text(min_size=1, max_size=100),
    model=st.sampled_from(["anthropic/claude-3-opus", "openai/gpt-4-turbo", "meta-llama/llama-3-70b"]),
    system_prompt=st.text(min_size=1, max_size=1000),
    temperature=st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
    top_p=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    tools=st.lists(st.text()),
    extras=st.dictionaries(st.text(), st.text())
)

run_record_strategy = st.builds(
    RunRecord,
    ts=st.datetimes(),
    agent_name=st.text(min_size=1),
    model=st.text(min_size=1),
    prompt_tokens=st.integers(min_value=0),
    completion_tokens=st.integers(min_value=0),
    total_tokens=st.integers(min_value=0),
    latency_ms=st.integers(min_value=0),
    cost_usd=st.floats(min_value=0.0),
    experiment_id=st.text(),
    task_label=st.text(),
    run_notes=st.text(),
    streaming=st.booleans(),
    model_list_source=st.sampled_from(["dynamic", "fallback"]),
    tool_web_enabled=st.booleans(),
    web_status=st.sampled_from(["off", "ok", "blocked"]),
    aborted=st.booleans()
)

session_strategy = st.builds(
    Session,
    id=st.text(min_size=1),
    created_at=st.datetimes(),
    agent_config=agent_config_strategy,
    transcript=st.lists(st.dictionaries(st.text(), st.text())),
    model_id=st.text(min_size=1),
    notes=st.text()
)


class TestAgentConfigProperties:
    """Property-based tests for AgentConfig model."""

    @given(agent_config_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_agent_config_serialization_roundtrip(self, config: AgentConfig) -> None:
        """Test that AgentConfig can be serialized and deserialized without data loss."""
        json_data = config.model_dump_json()
        restored_config = AgentConfig.model_validate_json(json_data)
        assert config == restored_config

    @given(st.floats(min_value=-10.0, max_value=-0.1).filter(lambda x: x < 0.0))
    def test_agent_config_temperature_validation_property(self, invalid_temp: float) -> None:
        """Test that invalid temperature values raise ValidationError."""
        with pytest.raises(ValidationError):
            AgentConfig(
                name="test",
                model="test",
                system_prompt="test",
                temperature=invalid_temp
            )

    @given(st.floats(min_value=2.1, max_value=10.0))
    def test_agent_config_temperature_upper_bound_property(self, invalid_temp: float) -> None:
        """Test that temperature values above 2.0 raise ValidationError."""
        with pytest.raises(ValidationError):
            AgentConfig(
                name="test",
                model="test",
                system_prompt="test",
                temperature=invalid_temp
            )

    @given(st.floats(min_value=-10.0, max_value=-0.1).filter(lambda x: x < 0.0))
    def test_agent_config_top_p_lower_bound_property(self, invalid_top_p: float) -> None:
        """Test that top_p values below 0.0 raise ValidationError."""
        with pytest.raises(ValidationError):
            AgentConfig(
                name="test",
                model="test",
                system_prompt="test",
                top_p=invalid_top_p
            )

    @given(st.floats(min_value=1.1, max_value=10.0))
    def test_agent_config_top_p_upper_bound_property(self, invalid_top_p: float) -> None:
        """Test that top_p values above 1.0 raise ValidationError."""
        with pytest.raises(ValidationError):
            AgentConfig(
                name="test",
                model="test",
                system_prompt="test",
                top_p=invalid_top_p
            )

    @given(agent_config_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_agent_config_boundary_values(self, config: AgentConfig) -> None:
        """Test that boundary values for temperature and top_p are accepted."""
        # Test boundary values are accepted
        boundary_configs = [
            AgentConfig(name=config.name, model=config.model, system_prompt=config.system_prompt, temperature=0.0),
            AgentConfig(name=config.name, model=config.model, system_prompt=config.system_prompt, temperature=2.0),
            AgentConfig(name=config.name, model=config.model, system_prompt=config.system_prompt, top_p=0.0),
            AgentConfig(name=config.name, model=config.model, system_prompt=config.system_prompt, top_p=1.0),
        ]
        for boundary_config in boundary_configs:
            assert isinstance(boundary_config, AgentConfig)

    @given(agent_config_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_agent_config_type_coercion(self, config: AgentConfig) -> None:
        """Test that AgentConfig handles type coercion properly."""
        # Test with string representations of numbers
        str_temp = str(config.temperature)
        str_top_p = str(config.top_p)

        coerced_config = AgentConfig(
            name=config.name,
            model=config.model,
            system_prompt=config.system_prompt,
            temperature=str_temp,  # type: ignore
            top_p=str_top_p,  # type: ignore
            tools=config.tools,
            extras=config.extras
        )

        assert abs(coerced_config.temperature - config.temperature) < 1e-6
        assert abs(coerced_config.top_p - config.top_p) < 1e-6


class TestRunRecordProperties:
    """Property-based tests for RunRecord model."""

    @given(run_record_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_run_record_serialization_roundtrip(self, record: RunRecord) -> None:
        """Test that RunRecord can be serialized and deserialized without data loss."""
        json_data = record.model_dump_json()
        restored_record = RunRecord.model_validate_json(json_data)
        assert record == restored_record

    @given(st.text().filter(lambda x: x not in ["dynamic", "fallback"]))
    def test_run_record_model_list_source_validation(self, invalid_source: str) -> None:
        """Test that invalid model_list_source values raise ValidationError."""
        ts = datetime.now()
        with pytest.raises(ValidationError):
            RunRecord(
                ts=ts,
                agent_name="test",
                model="test",
                latency_ms=1,
                model_list_source=invalid_source  # type: ignore
            )

    @given(st.text().filter(lambda x: x not in ["off", "ok", "blocked"]))
    def test_run_record_web_status_validation(self, invalid_status: str) -> None:
        """Test that invalid web_status values raise ValidationError."""
        ts = datetime.now()
        with pytest.raises(ValidationError):
            RunRecord(
                ts=ts,
                agent_name="test",
                model="test",
                latency_ms=1,
                web_status=invalid_status  # type: ignore
            )

    @given(run_record_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_run_record_numeric_constraints(self, record: RunRecord) -> None:
        """Test that numeric fields maintain their constraints."""
        assert record.prompt_tokens >= 0
        assert record.completion_tokens >= 0
        assert record.total_tokens >= 0
        assert record.latency_ms >= 0
        assert record.cost_usd >= 0.0

    @given(st.integers(max_value=-1))
    def test_run_record_negative_tokens_validation(self, negative_value: int) -> None:
        """Test that negative token values raise ValidationError."""
        ts = datetime.now()
        with pytest.raises(ValidationError):
            RunRecord(
                ts=ts,
                agent_name="test",
                model="test",
                latency_ms=1,
                prompt_tokens=negative_value
            )

    @given(st.integers(max_value=-1))
    def test_run_record_negative_latency_validation(self, negative_value: int) -> None:
        """Test that negative latency values raise ValidationError."""
        ts = datetime.now()
        with pytest.raises(ValidationError):
            RunRecord(
                ts=ts,
                agent_name="test",
                model="test",
                latency_ms=negative_value
            )

    @given(st.floats(max_value=-0.01))
    def test_run_record_negative_cost_validation(self, negative_value: float) -> None:
        """Test that negative cost values raise ValidationError."""
        ts = datetime.now()
        with pytest.raises(ValidationError):
            RunRecord(
                ts=ts,
                agent_name="test",
                model="test",
                latency_ms=1,
                cost_usd=negative_value
            )


class TestSessionProperties:
    """Property-based tests for Session model."""

    @given(session_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_session_serialization_roundtrip(self, session: Session) -> None:
        """Test that Session can be serialized and deserialized without data loss."""
        json_data = session.model_dump_json()
        restored_session = Session.model_validate_json(json_data)
        assert session == restored_session

    @given(session_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_session_nested_agent_config_validation(self, session: Session) -> None:
        """Test that Session properly validates nested AgentConfig."""
        assert isinstance(session.agent_config, AgentConfig)
        assert session.agent_config.name != ""
        assert session.agent_config.model != ""
        assert session.agent_config.system_prompt != ""

    @given(session_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_session_transcript_arbitrary_types(self, session: Session) -> None:
        """Test that Session transcript can contain arbitrary types."""
        # Add some arbitrary data to transcript
        arbitrary_transcript = session.transcript + [
            {"role": "user", "content": "test", "metadata": {"timestamp": datetime.now()}},
            {"role": "assistant", "content": "response", "custom_field": 42}
        ]

        session_with_arbitrary = Session(
            id=session.id,
            created_at=session.created_at,
            agent_config=session.agent_config,
            transcript=arbitrary_transcript,
            model_id=session.model_id,
            notes=session.notes
        )

        assert session_with_arbitrary.transcript == arbitrary_transcript

    @given(session_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_session_datetime_fields(self, session: Session) -> None:
        """Test that Session datetime fields are properly handled."""
        assert isinstance(session.created_at, datetime)
        # Test that datetime is preserved through serialization
        json_data = session.model_dump_json()
        restored = Session.model_validate_json(json_data)
        assert session.created_at == restored.created_at


class TestCrossModelProperties:
    """Property-based tests that span multiple models."""

    @given(agent_config_strategy, st.datetimes(), st.text(min_size=1), st.lists(st.dictionaries(st.text(), st.text())))
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_agent_config_to_session_integration(self, config: AgentConfig, created_at: datetime, session_id: str, transcript: list[dict[str, Any]]) -> None:
        """Test integration between AgentConfig and Session models."""
        session = Session(
            id=session_id,
            created_at=created_at,
            agent_config=config,
            transcript=transcript,
            model_id=config.model
        )

        assert session.agent_config == config
        assert session.model_id == config.model

        # Test roundtrip serialization
        json_data = session.model_dump_json()
        restored_session = Session.model_validate_json(json_data)
        assert restored_session.agent_config == config
        assert restored_session.model_id == config.model

    @given(run_record_strategy, agent_config_strategy)
    @settings(suppress_health_check=[HealthCheck.too_slow])
    def test_run_record_agent_config_consistency(self, record: RunRecord, config: AgentConfig) -> None:
        """Test that RunRecord fields are consistent with AgentConfig when appropriate."""
        # The model field should be consistent if using the same config
        consistent_record = RunRecord(
            ts=record.ts,
            agent_name=config.name,
            model=config.model,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            total_tokens=record.total_tokens,
            latency_ms=record.latency_ms,
            cost_usd=record.cost_usd,
            experiment_id=record.experiment_id,
            task_label=record.task_label,
            run_notes=record.run_notes,
            streaming=record.streaming,
            model_list_source=record.model_list_source,
            tool_web_enabled=record.tool_web_enabled,
            web_status=record.web_status,
            aborted=record.aborted
        )

        assert consistent_record.agent_name == config.name
        assert consistent_record.model == config.model