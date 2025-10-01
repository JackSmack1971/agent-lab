# Test Infrastructure User Scenarios

## Scenario 1: Developer Setting Up Local Testing
**Given** a developer clones the agent-lab repository  
**When** they run `pip install -r requirements.txt`  
**And** execute `pytest --collect-only`  
**Then** all test files are discovered without errors  
**And** fixtures load correctly  

**Acceptance Criteria:**
- No import errors during test collection
- All configured markers are recognized
- Coverage configuration is applied automatically

## Scenario 2: Running Unit Tests for Tools Module
**Given** the test infrastructure is set up  
**When** a developer runs `pytest tests/test_tools.py -v`  
**Then** all unit tests for `agents/tools.py` execute  
**And** input validation tests pass using Pydantic schemas  
**And** coverage report shows tool functions are tested  

**Acceptance Criteria:**
- Tests validate tool inputs with typed schemas (F:AGENTS.md†L<tools_example>)
- Pricing math edge cases are covered (0 tokens, unknown models)
- Web tool refusal returns exact standardized text

## Scenario 3: Integration Testing Streaming Functionality
**Given** integration tests are implemented in `tests/integration/test_streaming.py`  
**When** a developer runs `pytest tests/integration/ -m integration`  
**Then** streaming E2E tests execute with cancellation support  
**And** Stop button behavior is verified  
**And** token deltas are emitted correctly  

**Acceptance Criteria:**
- Cooperative cancellation halts within 500ms (F:AGENTS.md†L<streaming_requirements>)
- Usage aggregation works on completion and abort
- Gradio event handlers remain non-blocking

## Scenario 4: Session Persistence Testing
**Given** fixtures provide sample session data  
**When** tests run for `services/persist.py`  
**Then** session save/load maintains exact config structure  
**And** UUID4 session IDs are generated  
**And** timestamps use ISO format  

**Acceptance Criteria:**
- JSON serialization preserves transcript structure
- Load failures handle legacy formats gracefully
- CSV append includes all required fields (F:AGENTS.md†L<csv_schema>)

## Scenario 5: Model Catalog Testing with API Mocking
**Given** `mock_openrouter_response` fixture is configured  
**When** catalog tests run without real API calls  
**Then** dynamic fetch logic is tested  
**And** fallback to static models works on failure  
**And** refresh action updates dropdown immediately  

**Acceptance Criteria:**
- Fallback includes minimum required models (F:AGENTS.md†L<fallback_models>)
- Cache timestamp is validated
- UI displays correct source indicator ("Dynamic" or "Fallback")

## Scenario 6: CI/CD Pipeline Integration
**Given** pytest configuration is established  
**When** CI pipeline runs `pytest --cov=agents --cov=services --cov-report=xml`  
**Then** tests execute in parallel if configured  
**And** coverage reports are generated in XML format  
**And** test results integrate with CI dashboard  

**Acceptance Criteria:**
- Async tests run with proper event loop management
- Slow tests can be skipped with `-m "not slow"`
- Exit codes reflect test status correctly

## Scenario 7: Debugging Failed Tests
**Given** a test failure occurs  
**When** developer runs `pytest tests/test_specific.py::test_function -s --pdb`  
**Then** interactive debugging session starts  
**And** fixtures are available in debug context  
**And** mock objects can be inspected  

**Acceptance Criteria:**
- Fixtures provide realistic test data
- Mock responses include appropriate headers and status codes
- Error messages are descriptive and actionable

## Scenario 8: Adding New Test Cases
**Given** a developer adds a new feature to `agents/runtime.py`  
**When** they create `tests/test_runtime.py`  
**And** use shared fixtures from `conftest.py`  
**Then** new tests integrate seamlessly  
**And** coverage includes the new code  
**And** existing tests remain unaffected  

**Acceptance Criteria:**
- New test files follow naming conventions
- Fixtures are reusable across test modules
- Test isolation prevents side effects

## Scenario 9: Security Testing for Web Tool
**Given** web fetch tool tests are implemented  
**When** tests validate allow-list enforcement  
**Then** blocked domains return exact refusal text  
**And** allowed domains succeed with truncated content  
**And** timeout behavior is tested  

**Acceptance Criteria:**
- Allow-list is strictly enforced (F:AGENTS.md†L<web_tool_security>)
- Response truncation to 4,000 characters
- Badge state transitions are testable

## Scenario 10: Performance Regression Testing
**Given** baseline performance metrics exist  
**When** tests measure latency and token processing  
**Then** regressions are detected early  
**And** streaming performance meets <90s target  
**And** resource usage is monitored  

**Acceptance Criteria:**
- Latency measurements match stopwatch accuracy
- Token counting handles missing usage data
- Performance tests use appropriate markers