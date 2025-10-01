# Agent Lab Test Suite

## Overview
This test suite provides comprehensive coverage for the agent-lab project, following TDD principles and AGENTS.md testing strategy. The suite supports unit tests, integration tests, and manual QA validation.

## TDD Workflow

### Red-Green-Refactor Cycle
1. **Red**: Write a failing test that defines the desired behavior
2. **Green**: Implement the minimal code to make the test pass
3. **Refactor**: Improve code quality while maintaining test coverage

### Test-Driven Development Process
- **Write Test First**: Define expected behavior before implementation
- **Run Test**: Confirm it fails (red) before writing code
- **Implement Code**: Write minimal code to pass the test
- **Run Test Again**: Verify it passes (green)
- **Refactor**: Clean up code, ensuring tests still pass
- **Repeat**: Continue with next requirement

### Test Categories in TDD
- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test component interactions and workflows
- **Acceptance Tests**: Validate end-to-end user scenarios

### Coverage Maintenance
- Maintain >90% coverage across all cycles
- Run coverage checks before committing changes
- Address coverage gaps immediately during refactoring

## Architecture Decisions

### Test Organization
- **Unit Tests**: Located in `test_*.py` files at root level, testing individual functions and classes
- **Integration Tests**: Placed in `integration/` subdirectory for component interaction testing
- **Fixtures**: Shared test data and mocks in `conftest.py` and `fixtures/` directory
- **Markers**: Custom pytest markers for selective test execution (`unit`, `integration`, `slow`, `requires_api_key`)

### Testing Frameworks
- **pytest**: Primary testing framework with asyncio support
- **pytest-asyncio**: Automatic async test detection and execution
- **pytest-mock**: Mocking support for API calls and external dependencies
- **pytest-cov**: Coverage reporting for `agents/` and `services/` directories

### Key Design Principles
- **Type Safety**: All test functions use type hints following AGENTS.md conventions
- **Pydantic Validation**: Test data uses Pydantic models for runtime validation
- **Async Support**: Proper event loop handling for streaming and HTTP operations
- **Security First**: No API keys in test code; environment mocking prevents exposure
- **Isolation**: Each test runs independently with proper fixture cleanup

## Test Categories

### Unit Tests (`pytest -m unit`)
- Tool input validation (Pydantic schemas)
- Pricing math calculations (edge cases: 0 tokens, unknown models)
- CSV header initialization and field validation
- Web tool refusal text exact matching
- Model catalog success/failure scenarios

### Integration Tests (`pytest -m integration`)
- Streaming E2E with cooperative cancellation (<500ms halt time)
- Session persistence save/load with exact config preservation
- Badge state transitions (OFF → ON → OK/BLOCKED)
- CSV telemetry logging with all required fields

### Slow Tests (`pytest -m slow`)
- Real API calls (when API key available)
- Performance regression tests
- Large data set processing

## Running Tests

### Basic Execution
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agents --cov=services

# Run specific test file
pytest tests/test_tools.py

# Run integration tests only
pytest tests/integration/ -m integration
```

### Selective Execution
```bash
# Skip slow tests
pytest -m "not slow"

# Run only unit tests
pytest -m unit

# Run tests requiring API key
pytest -m requires_api_key

# Debug failing test
pytest tests/test_specific.py::TestClass::test_method -s --pdb
```

### CI/CD Integration
```bash
# Generate coverage XML for CI
pytest --cov=agents --cov=services --cov-report=xml

# Strict mode with no warnings
pytest -W error
```

## Fixtures Usage

### Shared Fixtures (conftest.py)
- `tmp_csv`: Temporary CSV file with proper telemetry header
- `mock_openrouter_response`: Mocked API responses for model catalog
- `sample_agent_config`: Valid AgentConfig instance for testing
- `mock_env_vars`: Environment variable mocking (OPENROUTER_API_KEY)
- `async_client`: httpx AsyncClient for HTTP testing

### Example Usage
```python
def test_tool_validation(sample_agent_config: AgentConfig) -> None:
    """Test tool validation with sample config."""
    assert sample_agent_config.name == "test_agent"
    assert "math" in sample_agent_config.tools

@pytest.mark.asyncio
async def test_api_call(async_client: httpx.AsyncClient, mock_openrouter_response: Mock) -> None:
    """Test API interaction with mocked response."""
    # Test implementation here
```

## Test Data Management

### Fixture Files (fixtures/)
- `sample_config.json`: Valid agent configuration examples
- `mock_responses.json`: Mock API response payloads

### Environment Variables
- `OPENROUTER_API_KEY`: Mocked in tests to prevent real API calls
- Test-specific variables set via `mock_env_vars` fixture

## Coverage Requirements
- **Target**: >90% coverage for `agents/` and `services/` directories
- **Reporting**: Terminal output with missing lines
- **CI Integration**: XML reports for coverage tracking

## Debugging and Troubleshooting

### Common Issues
- **Import Errors**: Ensure `PYTHONPATH` includes project root
- **Async Test Failures**: Check event loop configuration in pytest.ini
- **Fixture Errors**: Verify conftest.py is in test directory root
- **Coverage Missing**: Confirm source directories in pytest.ini

### Debug Mode
```bash
# Verbose output
pytest -v -s

# Stop on first failure
pytest --tb=short -x

# Interactive debugging
pytest --pdb
```

## Adding New Tests

### File Naming Convention
- `test_<module_name>.py` for unit tests
- `test_<feature>.py` for integration tests

### Test Structure
```python
import pytest
from typing import Any

class TestFeature:
    """Test suite for specific feature."""
    
    def test_basic_functionality(self, sample_fixture) -> None:
        """Test basic feature behavior."""
        # Arrange
        # Act
        # Assert
    
    @pytest.mark.asyncio
    async def test_async_functionality(self, async_client) -> None:
        """Test async feature behavior."""
        # Async test implementation
```

### Marker Usage
```python
@pytest.mark.unit
def test_unit_case(self) -> None:
    """Unit test with marker."""
    
@pytest.mark.integration
@pytest.mark.slow
def test_integration_case(self) -> None:
    """Integration test with multiple markers."""
```

## Maintenance Guidelines

### Regular Tasks
- Update mock responses when API schemas change
- Review and update coverage targets quarterly
- Clean up obsolete test fixtures
- Validate test execution on all supported Python versions

### Performance Monitoring
- Test collection time <5 seconds
- Individual fixture setup <1 second
- No blocking operations in async tests

## Security Considerations
- Never commit real API keys or credentials
- Mock all external API calls in automated tests
- Validate that test data doesn't contain sensitive information
- Use environment variable mocking for secure testing