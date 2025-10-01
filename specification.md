# Test Infrastructure Specification

## Overview
This specification defines the requirements for establishing a comprehensive test infrastructure for the agent-lab project, following Python testing conventions and the guidelines outlined in AGENTS.md.

## Current State Analysis
- `tests/__init__.py`: Currently an empty placeholder file (F:tests/__init__.py†L1-2)
- `requirements.txt`: Includes pytest>=7.4.0 (F:requirements.txt†L6)
- AGENTS.md Testing Strategy: Defines unit tests for tool validation, pricing math, CSV operations, and web tool refusal; integration tests for streaming, badges, session persistence; manual QA for streaming behavior (F:AGENTS.md†L<testing_strategy_section>)

## Test Directory Structure
```
tests/
├── __init__.py          # Package marker with basic imports
├── README.md            # Test architecture documentation
├── conftest.py          # Shared fixtures and configuration
├── test_tools.py        # Unit tests for agents/tools.py
├── test_models.py       # Unit tests for agents/models.py
├── test_runtime.py      # Unit tests for agents/runtime.py
├── test_persist.py      # Unit tests for services/persist.py
├── test_catalog.py      # Unit tests for services/catalog.py
├── integration/         # Integration tests directory
│   ├── __init__.py
│   └── test_streaming.py
└── fixtures/            # Test data files
    ├── sample_config.json
    └── mock_responses.json
```

## Pytest Configuration
- `pytest.ini`: Configure asyncio mode, coverage settings, markers for different test types (unit, integration, slow), and output formatting
- Coverage: Target >=80% coverage for agents/ and services/ directories
- Markers: `unit`, `integration`, `slow`, `requires_api_key`

## Shared Fixtures (conftest.py)
- `tmp_csv`: Temporary CSV file fixture using tmp_path
- `mock_openrouter_response`: Mock HTTP responses for OpenRouter API calls
- `sample_agent_config`: Valid AgentConfig instance for testing
- `mock_env_vars`: Environment variable mocking for OPENROUTER_API_KEY
- `async_client`: httpx AsyncClient for API testing

## Test Architecture Decisions
- Use pytest-asyncio for async test support
- Leverage pytest-mock for API mocking
- Implement fixture composition for complex test scenarios
- Follow naming convention: `test_<function_name>.py` for unit tests
- Use descriptive test names with Given-When-Then structure where applicable

## Dependencies
- pytest>=7.4.0 (already in requirements.txt)
- pytest-asyncio
- pytest-mock
- pytest-cov
- httpx (for async HTTP testing)

## Success Criteria
- pytest --collect-only discovers all test files without errors
- All fixtures load correctly
- Coverage reporting generates valid output
- Test execution completes without import errors