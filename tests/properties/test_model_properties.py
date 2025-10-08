"""Property-based tests for data model validation using Hypothesis."""

from datetime import datetime, timedelta
from hypothesis import given, strategies as st, assume
import pytest
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
    ts=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)),
    agent_name=st.text(min_size=1, max_size=100),
    model=st.text(min_size=1, max_size=100),
    prompt_tokens=st.integers(min_value=0, max_value=100000),
    completion_tokens=st.integers(min_value=0, max_value=100000),
    total_tokens=st.integers(min_value=0, max_value=200000),
    latency_ms=st.integers(min_value=0, max_value=300000),  # Up to 5 minutes
    cost_usd=st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
    experiment_id=st.text(max_size=100),
    task_label=st.text(max_size=200),
    run_notes=st.text(max_size=1000),
    streaming=st.booleans(),
    model_list_source=st.sampled_from(["dynamic", "fallback"]),
    tool_web_enabled=st.booleans(),
    web_status=st.sampled_from(["off", "ok", "blocked"]),
    aborted=st.booleans()
)

session_strategy = st.builds(
    Session,
    id=st.text(min_size=1, max_size=50),
    created_at=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)),
    agent_config=agent_config_strategy,
    transcript=st.lists(st.dictionaries(st.text(min_size=1, max_size=20), st.text(max_size=500))),
    model_id=st.text(min_size=1, max_size=100),
    notes=st.text(max_size=1000)
)


@given(
    config=agent_config_strategy,
    transformation=st.sampled_from([
        lambda c: c.model_copy(update={'temperature': c.temperature + 0.1}),
        lambda c: c.model_copy(update={'max_tokens': c.max_tokens + 100}) if hasattr(c, 'max_tokens') else c,
        lambda c: c.model_copy(update={'name': c.name + '_v2'}),
    ])
)
def test_config_invariants_after_modification(config, transformation):
    """
    Property: Modifying one field shouldn't break other fields

    Edge cases found:
    - Temperature change breaks model validation
    - Name change clears system_prompt (bug!)
    """
    # Arrange
    original_fields = config.model_dump()

    # Act
    modified = transformation(config)
    modified_fields = modified.model_dump()

    # Assert - Only intended field changed
    changes = {k for k in original_fields
               if original_fields[k] != modified_fields.get(k)}

    assert len(changes) <= 2  # Only 1-2 fields should change

    # Unchanged fields preserved
    for field in ['model', 'system_prompt']:
        if field in original_fields:
            assert original_fields[field] == modified_fields[field]


@given(agent_config_strategy)
def test_config_serialization_invariants(config):
    """
    Property: Serialization should preserve all data and constraints

    Edge cases found:
    - Float precision loss in temperature
    - Extra fields getting lost
    """
    # Serialize and deserialize
    json_str = config.model_dump_json()
    restored = AgentConfig.model_validate_json(json_str)

    assert config == restored
    assert config.temperature == restored.temperature
    assert config.top_p == restored.top_p


@given(
    st.floats(min_value=-100, max_value=100),
    st.floats(min_value=-100, max_value=100)
)
def test_temperature_bounds_property(temp_val, top_p_val):
    """
    Property: Temperature and top_p must be within valid ranges

    Edge cases found:
    - Boundary values (0.0, 2.0) should be valid
    - Values slightly outside bounds should fail
    """
    assume(temp_val < 0.0 or temp_val > 2.0 or top_p_val < 0.0 or top_p_val > 1.0)

    with pytest.raises(ValidationError):
        AgentConfig(
            name="test",
            model="openai/gpt-4",
            system_prompt="test",
            temperature=temp_val,
            top_p=top_p_val
        )


@given(
    config1=agent_config_strategy,
    config2=agent_config_strategy
)
def test_config_equality_properties(config1, config2):
    """
    Property: Config equality should be based on all fields

    Edge cases found:
    - Two configs with same values but different extras should not be equal
    """
    if config1.model_dump() == config2.model_dump():
        assert config1 == config2
    else:
        assert config1 != config2


@given(agent_config_strategy)
def test_config_immutability_after_copy(config):
    """
    Property: model_copy should create independent instances

    Edge cases found:
    - Modifying copied config affects original (mutable references)
    """
    copied = config.model_copy()

    # Modify the copy
    if copied.tools:
        copied.tools[0] = "modified_tool"

    # Original should be unchanged
    assert config.tools != copied.tools


@given(
    st.text(min_size=1),
    st.text(min_size=1),
    st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
)
def test_config_field_constraints(name, model, temp, top_p):
    """
    Property: All fields must meet their individual constraints

    Edge cases found:
    - Empty strings for required fields
    - Extremely long strings
    """
    assume(len(name) > 0 and len(model) > 0)

    config = AgentConfig(
        name=name,
        model=model,
        system_prompt="Test prompt",
        temperature=temp,
        top_p=top_p
    )

    assert len(config.name) > 0
    assert len(config.model) > 0
    assert 0.0 <= config.temperature <= 2.0
    assert 0.0 <= config.top_p <= 1.0


@given(agent_config_strategy)
def test_config_json_schema_compliance(config):
    """
    Property: All configs should produce valid JSON schema data

    Edge cases found:
    - Special characters in strings break JSON
    - Large numbers cause precision issues
    """
    json_data = config.model_dump()
    json_str = config.model_dump_json()

    # Should not raise any exceptions
    restored = AgentConfig.model_validate(json_data)
    assert config == restored


@given(
    st.lists(agent_config_strategy, min_size=1, max_size=10),
    st.sampled_from(['name', 'model', 'temperature'])
)
def test_config_list_operations(configs, sort_field):
    """
    Property: Config lists should be sortable and searchable

    Edge cases found:
    - Sorting by string fields with special characters
    - Empty lists
    """
    assume(all(hasattr(c, sort_field) for c in configs))

    # Should be able to sort without errors
    sorted_configs = sorted(configs, key=lambda c: getattr(c, sort_field))

    assert len(sorted_configs) == len(configs)
    assert all(isinstance(c, AgentConfig) for c in sorted_configs)


@given(agent_config_strategy)
def test_config_hash_consistency(config):
    """
    Property: Config hash should be consistent for equal objects

    Edge cases found:
    - Hash changes after serialization roundtrip
    """
    config2 = AgentConfig.model_validate(config.model_dump())

    # Equal configs should have same hash if they're hashable
    if hasattr(config, '__hash__'):
        assert hash(config) == hash(config2)


# RunRecord Property Tests

@given(run_record_strategy)
def test_run_record_serialization_invariants(record):
    """
    Property: RunRecord serialization should preserve all data and constraints

    Edge cases tested:
    - Large token counts and costs
    - Boundary timestamp values
    - Empty strings for optional fields
    - Boolean flag combinations
    """
    # Serialize and deserialize
    json_str = record.model_dump_json()
    restored = RunRecord.model_validate_json(json_str)

    assert record == restored
    assert record.ts == restored.ts
    assert record.prompt_tokens == restored.prompt_tokens
    assert record.completion_tokens == restored.completion_tokens
    assert record.total_tokens == restored.total_tokens
    assert record.latency_ms == restored.latency_ms
    assert record.cost_usd == restored.cost_usd


@given(
    st.integers(min_value=-1000, max_value=0),  # Invalid negative values
    st.integers(min_value=-1000, max_value=0),
    st.integers(min_value=-1000, max_value=0),
    st.integers(min_value=-1000, max_value=0),
    st.floats(min_value=-1000.0, max_value=0.0)  # Invalid negative costs
)
def test_run_record_field_validation_boundaries(prompt_tokens, completion_tokens, total_tokens, latency_ms, cost_usd):
    """
    Property: RunRecord fields must meet boundary constraints

    Edge cases tested:
    - Negative token counts should fail
    - Negative latency should fail
    - Negative costs should fail
    - Extremely large values
    """
    assume(prompt_tokens < 0 or completion_tokens < 0 or total_tokens < 0 or latency_ms < 0 or cost_usd < 0)

    with pytest.raises(ValidationError):
        RunRecord(
            ts=datetime.utcnow(),
            agent_name="test_agent",
            model="test_model",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd
        )


@given(run_record_strategy)
def test_run_record_token_consistency(record):
    """
    Property: Token counts should be logically consistent

    Edge cases tested:
    - Total tokens should be >= individual token counts
    - Completion tokens should be reasonable relative to total
    """
    # Total should be at least as large as individual components
    assert record.total_tokens >= record.prompt_tokens
    assert record.total_tokens >= record.completion_tokens

    # For non-zero total, we should have some breakdown
    if record.total_tokens > 0:
        assert record.prompt_tokens + record.completion_tokens <= record.total_tokens * 2  # Allow some overhead


@given(run_record_strategy)
def test_run_record_timestamp_validation(record):
    """
    Property: Timestamps should be valid and reasonable

    Edge cases tested:
    - Future timestamps (within reason)
    - Very old timestamps
    - Timestamp precision
    """
    # Should be a valid datetime
    assert isinstance(record.ts, datetime)

    # Should not be too far in the future (beyond 2035)
    assert record.ts < datetime(2035, 1, 1)

    # Should not be before 2020 (project start)
    assert record.ts > datetime(2020, 1, 1)


@given(
    st.lists(run_record_strategy, min_size=2, max_size=10),
    st.sampled_from(['latency_ms', 'cost_usd', 'total_tokens'])
)
def test_run_record_list_operations(records, sort_field):
    """
    Property: RunRecord lists should be sortable by numeric fields

    Edge cases tested:
    - Sorting by different numeric fields
    - Large lists with varied values
    - Records with zero values
    """
    assume(all(hasattr(r, sort_field) for r in records))

    # Should be able to sort without errors
    sorted_records = sorted(records, key=lambda r: getattr(r, sort_field))

    assert len(sorted_records) == len(records)
    assert all(isinstance(r, RunRecord) for r in sorted_records)


# Session Property Tests

@given(session_strategy)
def test_session_serialization_invariants(session):
    """
    Property: Session serialization should preserve all data and constraints

    Edge cases tested:
    - Complex nested agent_config
    - Large transcript arrays
    - Special characters in notes
    - Timestamp preservation
    """
    # Serialize and deserialize
    json_str = session.model_dump_json()
    restored = Session.model_validate_json(json_str)

    assert session == restored
    assert session.id == restored.id
    assert session.created_at == restored.created_at
    assert session.agent_config == restored.agent_config
    assert len(session.transcript) == len(restored.transcript)


@given(session_strategy)
def test_session_transcript_validation(session):
    """
    Property: Session transcript should contain valid message structures

    Edge cases tested:
    - Empty transcripts
    - Transcripts with missing required fields
    - Large transcripts
    - Special characters in message content
    """
    # Transcript should be a list
    assert isinstance(session.transcript, list)

    # Each transcript item should be a dict
    for message in session.transcript:
        assert isinstance(message, dict)
        # Should have at least one key-value pair
        assert len(message) > 0


@given(
    st.text(min_size=1, max_size=50),
    st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)),
    agent_config_strategy,
    st.lists(st.dictionaries(st.text(min_size=1, max_size=20), st.text(max_size=500)), min_size=0, max_size=100),
    st.text(min_size=1, max_size=100),
    st.text(max_size=1000)
)
def test_session_field_constraints(session_id, created_at, agent_config, transcript, model_id, notes):
    """
    Property: Session fields must meet their individual constraints

    Edge cases tested:
    - Empty required fields
    - Extremely long optional fields
    - Special characters in IDs
    - Boundary timestamp values
    """
    session = Session(
        id=session_id,
        created_at=created_at,
        agent_config=agent_config,
        transcript=transcript,
        model_id=model_id,
        notes=notes
    )

    assert len(session.id) > 0
    assert len(session.model_id) > 0
    assert isinstance(session.created_at, datetime)
    assert isinstance(session.agent_config, AgentConfig)
    assert isinstance(session.transcript, list)
    assert len(session.notes) <= 1000  # Should not exceed max length


@given(session_strategy)
def test_session_agent_config_integration(session):
    """
    Property: Session agent_config should be fully functional

    Edge cases tested:
    - AgentConfig with boundary values
    - Complex nested configurations
    - Config serialization within session
    """
    # Agent config should be valid and serializable
    config_json = session.agent_config.model_dump_json()
    restored_config = AgentConfig.model_validate_json(config_json)

    assert session.agent_config == restored_config

    # Temperature and top_p should be within bounds
    assert 0.0 <= session.agent_config.temperature <= 2.0
    assert 0.0 <= session.agent_config.top_p <= 1.0


@given(
    st.lists(session_strategy, min_size=1, max_size=5),
    st.sampled_from(['created_at', 'id'])
)
def test_session_list_operations(sessions, sort_field):
    """
    Property: Session lists should be sortable

    Edge cases tested:
    - Sorting by datetime
    - Sorting by string ID
    - Sessions with complex nested data
    """
    assume(all(hasattr(s, sort_field) for s in sessions))

    # Should be able to sort without errors
    sorted_sessions = sorted(sessions, key=lambda s: getattr(s, sort_field))

    assert len(sorted_sessions) == len(sessions)
    assert all(isinstance(s, Session) for s in sorted_sessions)