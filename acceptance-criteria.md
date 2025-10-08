# Phase 2: Coverage Sprint - Acceptance Criteria

## Overview

This document defines the testable acceptance criteria for Phase 2 Coverage Sprint. Each criterion includes specific coverage targets, test patterns, validation scripts, and measurable success conditions.

## Global Acceptance Criteria

### AC-G1: Overall Coverage Achievement
**Given** the complete test suite is executed with coverage analysis
**When** `pytest --cov=agents --cov=services --cov=src --cov-report=term-missing` completes
**Then** overall coverage ≥ 90%
**And** coverage report shows no untested modules in agents/, services/, src/

### AC-G2: Module-Specific Coverage Targets
**Given** individual module coverage is measured
**When** coverage analysis completes for each targeted module
**Then** each module meets its specific coverage target:
- agents/runtime.py ≥ 90%
- agents/models.py ≥ 90%
- All src/components/*.py ≥ 90%
- All src/services/*.py ≥ 90%
- All src/models/*.py ≥ 90%

### AC-G3: Test Suite Integrity
**Given** the complete test suite execution
**When** `pytest tests/ -x --tb=short` completes
**Then** all tests pass (exit code 0)
**And** no tests are skipped except those with legitimate skip markers
**And** no errors or failures are reported

### AC-G4: Test Reliability
**Given** test execution with randomization enabled
**When** `pytest tests/ --randomly-seed=42 -n auto --count=3` completes
**Then** all test runs pass consistently
**And** no flaky behavior is observed
**And** execution time remains < 60 seconds per run

## agents/runtime.py Acceptance Criteria

### AC-RT1: Agent Building Coverage
**Given** the build_agent function with various configurations
**When** tested with different AgentConfig inputs
**Then** line coverage ≥ 95% for build_agent function
**And** branch coverage includes:
- API key validation (present/missing)
- Tool registration (with/without web tools)
- Model settings application
- Client configuration

**Test Patterns**:
```python
# API key validation
def test_build_agent_missing_api_key():
    cfg = AgentConfig(name="test", model="test", system_prompt="test")
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY not set"):
        build_agent(cfg)

# Tool registration
@pytest.mark.parametrize("include_web", [True, False])
def test_build_agent_tool_registration(include_web):
    cfg = AgentConfig(name="test", model="test", system_prompt="test")
    agent = build_agent(cfg, include_web=include_web)
    assert agent is not None
    # Verify tools are registered appropriately
```

### AC-RT2: Synchronous Execution Coverage
**Given** the run_agent function with various scenarios
**When** tested with mock agent and different inputs
**Then** line coverage ≥ 95% for run_agent function
**And** branch coverage includes:
- Successful execution path
- Exception handling path
- Logging verification

**Test Patterns**:
```python
# Successful execution
def test_run_agent_success(mocker):
    mock_agent = mocker.Mock()
    mock_result = mocker.Mock()
    mock_result.data = "response"
    mock_agent.run.return_value = mock_result

    response, usage = await run_agent(mock_agent, "test message")
    assert response == "response"
    assert usage == {}

# Error handling
def test_run_agent_error(mocker):
    mock_agent = mocker.Mock()
    mock_agent.run.side_effect = Exception("API error")

    with pytest.raises(RuntimeError, match="Agent execution failed"):
        await run_agent(mock_agent, "test message")
```

### AC-RT3: Streaming Execution Coverage
**Given** the run_agent_stream function with various streaming scenarios
**When** tested with mock streams and cancellation tokens
**Then** line coverage ≥ 95% for run_agent_stream function
**And** branch coverage includes:
- Normal streaming completion
- Immediate cancellation before consumption
- Cancellation during streaming
- Error handling in stream processing
- Usage dictionary conversion

**Test Patterns**:
```python
# Cancellation handling
def test_streaming_cancellation_immediate(mocker):
    cancel_token = Event()
    cancel_token.set()  # Cancel before starting

    result = await run_agent_stream(mock_agent, "test", lambda x: None, cancel_token)
    assert result.aborted is True
    assert result.text == ""

# Usage conversion
@pytest.mark.parametrize("usage_input,expected", [
    (None, None),
    ({"tokens": 100}, {"tokens": 100}),
    (Mock(model_dump=lambda: {"usage": 50}), {"usage": 50}),
])
def test_usage_to_dict_conversion(usage_input, expected):
    result = _usage_to_dict(usage_input)
    assert result == expected
```

### AC-RT4: Error Path Coverage
**Given** various error conditions in runtime functions
**When** tested with invalid inputs and failure scenarios
**Then** all error handling branches are covered
**And** appropriate exceptions are raised
**And** logging is performed correctly

## agents/models.py Acceptance Criteria

### AC-MD1: Model Validation Coverage
**Given** Pydantic models with hypothesis-generated inputs
**When** tested with property-based testing strategies
**Then** line coverage ≥ 95% for all model classes
**And** branch coverage includes validation failures

**Test Patterns**:
```python
from hypothesis import given, strategies as st

@given(
    name=st.text(min_size=1, max_size=100),
    model=st.text(min_size=1, max_size=50),
    system_prompt=st.text(min_size=1, max_size=1000),
    temperature=st.floats(min_value=0.0, max_value=2.0),
    top_p=st.floats(min_value=0.0, max_value=1.0),
)
def test_agent_config_valid_inputs(name, model, system_prompt, temperature, top_p):
    config = AgentConfig(
        name=name, model=model, system_prompt=system_prompt,
        temperature=temperature, top_p=top_p
    )
    assert config.name == name
    assert config.temperature == temperature

@given(temperature=st.floats(max_value=-0.1).filter(lambda x: x < 0))
def test_agent_config_temperature_validation(temperature):
    with pytest.raises(ValidationError):
        AgentConfig(name="test", model="test", system_prompt="test", temperature=temperature)
```

### AC-MD2: Serialization Coverage
**Given** model instances with various data
**When** JSON serialization/deserialization is performed
**Then** round-trip serialization works correctly
**And** all fields are preserved

**Test Patterns**:
```python
def test_model_serialization_roundtrip():
    original = AgentConfig(
        name="test", model="gpt-4", system_prompt="test prompt",
        temperature=0.8, tools=["tool1"]
    )

    json_str = original.model_dump_json()
    restored = AgentConfig.model_validate_json(json_str)

    assert original == restored
    assert restored.name == "test"
    assert restored.temperature == 0.8
```

### AC-MD3: Field Constraint Coverage
**Given** model fields with boundary values
**When** validation occurs
**Then** constraints are properly enforced
**And** appropriate validation errors are raised

## src/components/* Acceptance Criteria

### AC-CO1: Component Creation Coverage
**Given** each UI component creation function
**When** tested with various configurations
**Then** line coverage ≥ 90% for component creation
**And** all UI elements are properly initialized

**Test Patterns** (per component):
```python
def test_component_creation_basic():
    component = create_component_function()
    assert component is not None
    # Verify component structure and elements

def test_component_with_custom_config():
    config = {"setting": "value"}
    component = create_component_function(config)
    # Verify configuration is applied
```

### AC-CO2: Event Handler Coverage
**Given** component event handlers
**When** triggered with test inputs
**Then** handlers execute without errors
**And** state updates occur correctly
**And** UI updates are triggered

**Test Patterns**:
```python
def test_event_handler_execution():
    component = create_component_function()

    # Simulate event trigger
    result = component.event_handler(input_data)

    # Verify handler logic
    assert result is not None
    # Verify side effects (state changes, UI updates)
```

### AC-CO3: Error Handling Coverage
**Given** components with error conditions
**When** invalid inputs or failures occur
**Then** errors are handled gracefully
**And** user feedback is provided
**And** component remains stable

## src/services/* Acceptance Criteria

### AC-SV1: Business Logic Coverage
**Given** service functions with various inputs
**When** executed with test data
**Then** business logic executes correctly
**And** expected outputs are produced
**And** edge cases are handled

**Test Patterns**:
```python
def test_service_business_logic():
    service = ServiceClass()
    input_data = create_test_input()

    result = service.process(input_data)

    assert result is not None
    # Verify business rules are applied
    assert result.field == expected_value
```

### AC-SV2: External Integration Coverage
**Given** services that integrate with external APIs
**When** tested with mocked external responses
**Then** API calls are made correctly
**And** responses are processed properly
**And** error conditions are handled

**Test Patterns**:
```python
def test_external_api_integration(mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}

    mocker.patch('requests.get', return_value=mock_response)

    service = ServiceClass()
    result = service.call_external_api()

    assert result == {"data": "test"}
```

### AC-SV3: Data Validation Coverage
**Given** service input validation
**When** tested with valid and invalid inputs
**Then** validation passes for valid data
**And** appropriate errors for invalid data
**And** sanitization occurs where required

## src/models/* Acceptance Criteria

### AC-MO1: Model Field Validation
**Given** Pydantic models in src/models/
**When** instantiated with various inputs
**Then** field validation works correctly
**And** type coercion occurs appropriately
**And** custom validators execute

**Test Patterns**:
```python
def test_model_field_validation():
    # Valid input
    model = ModelClass(valid_field="value")
    assert model.valid_field == "value"

    # Invalid input
    with pytest.raises(ValidationError):
        ModelClass(invalid_field="bad_value")
```

### AC-MO2: Model Relationships
**Given** models with relationships or dependencies
**When** tested together
**Then** relationships are maintained
**And** cascading effects work correctly
**And** referential integrity is preserved

### AC-MO3: Serialization Compatibility
**Given** model serialization requirements
**When** models are serialized/deserialized
**Then** data integrity is maintained
**And** version compatibility is preserved
**And** custom serialization logic works

## Validation Scripts

### Coverage Validation Script
```bash
#!/bin/bash
# coverage_validation.sh

echo "Running coverage validation..."

# Run tests with coverage
pytest --cov=agents --cov=services --cov=src \
       --cov-report=term-missing \
       --cov-report=xml \
       --cov-fail-under=90

coverage_status=$?

# Check individual module coverage
echo "Checking individual module coverage..."

python -c "
import xml.etree.ElementTree as ET
tree = ET.parse('coverage.xml')
root = tree.getroot()

modules = {
    'agents.runtime': 90,
    'agents.models': 90,
}

for package in root.findall('.//package'):
    name = package.get('name')
    if name in modules:
        coverage = float(package.get('line-rate', 0)) * 100
        required = modules[name]
        if coverage < required:
            print(f'FAILED: {name} coverage {coverage:.1f}% < {required}%')
            exit(1)
        else:
            print(f'PASSED: {name} coverage {coverage:.1f}% >= {required}%')
"

if [ $coverage_status -eq 0 ]; then
    echo "✅ Coverage validation PASSED"
else
    echo "❌ Coverage validation FAILED"
    exit 1
fi
```

### Test Reliability Validation Script
```bash
#!/bin/bash
# reliability_validation.sh

echo "Running test reliability validation..."

# Run tests multiple times with randomization
for i in {1..3}; do
    echo "Run $i/3..."
    pytest tests/ --randomly-seed=$i -q --tb=line
    if [ $? -ne 0 ]; then
        echo "❌ Test run $i FAILED - potential flakiness"
        exit 1
    fi
done

echo "✅ Reliability validation PASSED"
```

### Performance Validation Script
```bash
#!/bin/bash
# performance_validation.sh

echo "Running performance validation..."

start_time=$(date +%s.%3N)

pytest tests/ -q --tb=no

end_time=$(date +%s.%3N)
duration=$(echo "$end_time - $start_time" | bc)

if (( $(echo "$duration > 60" | bc -l) )); then
    echo "❌ Performance validation FAILED: ${duration}s > 60s"
    exit 1
else
    echo "✅ Performance validation PASSED: ${duration}s"
fi
```

## Success Criteria Summary

### Quantitative Metrics
- **Coverage**: ≥90% overall, ≥90% per targeted module
- **Test Count**: Maintain or increase from baseline
- **Execution Time**: <60 seconds for full suite
- **Failure Rate**: 0% (all tests pass)
- **Flakiness**: 0% (consistent results across runs)

### Qualitative Metrics
- **Test Quality**: All tests are readable, maintainable, and well-documented
- **Code Coverage**: Branch coverage prioritized over line coverage
- **Error Handling**: Comprehensive error scenario coverage
- **Integration**: Proper testing of component interactions

### Validation Process
1. Execute coverage validation script
2. Execute reliability validation script
3. Execute performance validation script
4. Manual review of coverage reports
5. Manual review of new test code quality
6. Integration testing verification

All criteria must pass for Phase 2 acceptance.