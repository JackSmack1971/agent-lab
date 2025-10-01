## Sequential Prompt Chain for TDD Implementation

### **Prompt 1: Assessment & Test Infrastructure Planning**

```
Analyze the current test infrastructure in the agent-lab codebase and create a comprehensive test implementation plan.

CONTEXT:
- Review tests/__init__.py (currently empty placeholder)
- Review requirements.txt to confirm pytest>=7.4.0 is available
- Review AGENTS.md testing guidelines (Section: "Testing Strategy")
- Examine agents/tools.py, agents/models.py, agents/runtime.py, services/persist.py, services/catalog.py

TASKS:
1. Create a detailed test directory structure in tests/ following Python conventions
2. Design pytest.ini configuration for the project (include coverage settings, markers, asyncio mode)
3. Create conftest.py with shared fixtures for:
   - Temporary CSV files (using tmp_path)
   - Mock OpenRouter API responses
   - Sample AgentConfig instances
   - Mock environment variables (OPENROUTER_API_KEY)
4. Document the test architecture decisions in tests/README.md

CONSTRAINTS:
- Work on current branch (do not create new branches)
- Follow code style from AGENTS.md (Section: "Code Style and Conventions")
- Use type hints for all fixtures and helper functions
- After implementation, run: pytest --collect-only to verify test discovery
- Commit changes with message: "test: Initialize pytest infrastructure and fixtures"
- Ensure git status is clean after commit

CITATIONS:
- Cite relevant lines from AGENTS.md using F:AGENTS.md†L<line> format
- Cite the empty tests/__init__.py file: F:tests/__init__.py†L1-2
- Cite pytest requirement: F:requirements.txt†L6

OUTPUT:
Provide the complete file contents for pytest.ini, conftest.py, tests/README.md, and updated tests/__init__.py.
Include terminal output citations showing pytest --collect-only results.
```

**Expected Context for Next Prompt:**
- Test infrastructure exists and is verified
- conftest.py provides reusable fixtures
- pytest configuration is established
- Test discovery works correctly

---

### **Prompt 2: TDD Cycle 1 - Tool Function Tests (RED-GREEN-REFACTOR)**

```
Implement comprehensive tests for agent tools following TDD methodology, starting with failing tests.

CONTEXT FROM PROMPT 1:
- Test infrastructure is established with fixtures in conftest.py
- pytest.ini is configured with asyncio_mode and coverage settings
- We have fixtures for: tmp_path, mock_env, sample_config

CURRENT CODE TO TEST:
- agents/tools.py contains add_numbers (F:agents/tools.py†L17-28) and utc_now (F:agents/tools.py†L31-41)
- Both functions are async and use pydantic_ai.RunContext
- Manual smoke test exists at F:agents/tools.py†L44-53

TASKS - RED PHASE:
1. Create tests/test_tools.py
2. Write FAILING tests first (they should fail because test harness needs adjustment):
   - test_add_numbers_returns_correct_sum
   - test_add_numbers_handles_negative_numbers
   - test_add_numbers_returns_float_type
   - test_utc_now_includes_utc_suffix
   - test_utc_now_respects_custom_format
   - test_utc_now_returns_current_time (within 1 second tolerance)

3. Run tests and capture failure output: pytest tests/test_tools.py -v
4. Commit with: "test(RED): Add failing tests for tool functions"

TASKS - GREEN PHASE:
5. Fix test harness to properly handle async functions (use @pytest.mark.asyncio or asyncio.run)
6. Verify tools.py implementation is correct (no changes needed to tools.py)
7. Run tests until green: pytest tests/test_tools.py -v --cov=agents.tools
8. Commit with: "test(GREEN): Fix async test harness for tool functions"

TASKS - REFACTOR PHASE:
9. Improve test clarity: extract magic numbers, add property-based tests using hypothesis
10. Add parametrized tests for edge cases (zero, infinity, very large numbers)
11. Run full test suite: pytest tests/test_tools.py -v --cov=agents.tools --cov-report=term-missing
12. Commit with: "test(REFACTOR): Enhance tool tests with property-based testing"

CONSTRAINTS:
- Follow AGENTS.md "Testing Instructions" (F:AGENTS.md†L45-56)
- Use Pydantic models for input validation (F:agents/tools.py†L17-20, L31-34)
- All tests must be hermetic (no external dependencies)
- Coverage target: 100% for agents/tools.py
- After all phases, check git status and ensure clean worktree

CITATIONS:
- Cite tool function implementations from agents/tools.py
- Cite relevant AGENTS.md testing patterns
- Include terminal output citations for pytest runs (use chunk_id format)

OUTPUT:
Provide complete tests/test_tools.py with all RED, GREEN, and REFACTOR phases.
Show terminal output for each pytest run demonstrating the TDD cycle.
Include coverage report showing 100% coverage of agents/tools.py.
```

**Expected Context for Next Prompt:**
- Tool functions have comprehensive test coverage
- Property-based tests validate invariants (commutativity, type safety)
- Async testing patterns are established
- Coverage baseline is set

---

### **Prompt 3: TDD Cycle 2 - CSV Persistence Tests (Critical Path)**

```
Implement robust tests for CSV persistence and data parsing, focusing on risk areas identified in the codebase assessment.

CONTEXT FROM PROMPT 2:
- Async testing patterns are established in tests/test_tools.py
- conftest.py provides tmp_path fixture for temporary file operations
- Coverage tooling is configured and working
- TDD RED-GREEN-REFACTOR cycle is proven effective

RISK AREAS FROM ASSESSMENT:
- services/persist.py CSV operations are critical but untested (F:services/persist.py†L1-156)
- _parse_row function has type coercion that could fail (F:services/persist.py†L128-156)
- CSV_HEADERS schema must remain stable (F:services/persist.py†L22-31)
- Literal fields like web_status expect specific values (F:agents/models.py†L45)

TASKS - RED PHASE:
1. Create tests/test_persist.py
2. Write FAILING tests for critical behaviors:
   - test_init_csv_creates_file_with_headers
   - test_init_csv_idempotent (calling twice doesn't duplicate headers)
   - test_append_run_writes_correct_schema
   - test_append_run_formats_timestamp_as_iso
   - test_load_recent_runs_roundtrip (write then read)
   - test_load_recent_runs_skips_malformed_rows (NEW BEHAVIOR)
   - test_coerce_int_handles_invalid_input (property-based)
   - test_coerce_float_handles_invalid_input (property-based)
   - test_coerce_bool_recognizes_truthy_strings
   - test_parse_row_validates_required_fields

3. Run and capture failures: pytest tests/test_persist.py -v
4. Commit with: "test(RED): Add failing tests for CSV persistence critical path"

TASKS - GREEN PHASE:
5. Fix services/persist.py to handle malformed rows gracefully:
   - Wrap RunRecord(**parsed) in try/except for ValidationError
   - Add logging for skipped rows (use logger.warning)
   - Update load_recent_runs to continue on parsing errors

6. Ensure all coercion functions (_coerce_int, _coerce_float, _coerce_bool) never throw
7. Run tests until green: pytest tests/test_persist.py -v --cov=services.persist
8. Commit with: "fix: Handle malformed CSV rows gracefully in load_recent_runs"

TASKS - REFACTOR PHASE:
9. Extract CSV path injection for testability (optional: use environment variable)
10. Add mutation testing targets for _coerce_bool (ensure tests catch string set changes)
11. Add integration test: full roundtrip with all RunRecord fields populated
12. Run full coverage: pytest tests/test_persist.py -v --cov=services.persist --cov-report=term-missing
13. Commit with: "test(REFACTOR): Add property-based tests for CSV coercion functions"

CONSTRAINTS:
- Use tmp_path fixture from conftest.py for all file operations
- Follow CSV schema from F:services/persist.py†L22-31 exactly
- Monkeypatch persist.CSV_PATH to tmp_path / "test_runs.csv" in tests
- Target coverage: >95% for services/persist.py (exclude __main__ block)
- After changes, run all checks: pytest tests/ -v --cov=agents --cov=services
- Follow AGENTS.md "Critical Data Contracts" (F:AGENTS.md†L85-95)
- Ensure clean git status after all commits

CITATIONS:
- Cite CSV_HEADERS definition: F:services/persist.py†L22-31
- Cite RunRecord model: F:agents/models.py†L30-53
- Cite coercion functions: F:services/persist.py†L79-103
- Include terminal output for pytest runs showing coverage improvements

OUTPUT:
Provide complete tests/test_persist.py with RED-GREEN-REFACTOR phases.
Provide the refactored services/persist.py with improved error handling.
Show terminal output demonstrating >95% coverage.
Include example of property-based test output from hypothesis.
```

**Expected Context for Next Prompt:**
- CSV persistence has robust error handling
- Property-based tests validate coercion functions
- Roundtrip tests ensure data integrity
- Coverage of critical persistence layer is >95%

---

### **Prompt 4: TDD Cycle 3 - Agent Runtime & Configuration Tests**

```
Implement tests for agent initialization, configuration, and runtime execution with focus on error handling and security.

CONTEXT FROM PROMPT 3:
- Persistence layer is tested and robust
- Property-based testing patterns are established
- Async testing and monkeypatching patterns proven
- Coverage is >95% for tested modules

RISK AREAS FROM ASSESSMENT:
- agents/runtime.py depends on OPENROUTER_API_KEY (F:agents/runtime.py†L47-55)
- build_agent has optional tool registration (F:agents/runtime.py†L66-74)
- run_agent_stream has complex cancellation logic (F:agents/runtime.py†L154-163)
- Agent execution can fail with various exceptions (F:agents/runtime.py†L108-115)

TASKS - RED PHASE:
1. Create tests/test_runtime.py
2. Write FAILING tests for security and error handling:
   - test_build_agent_requires_api_key (monkeypatch to remove key)
   - test_build_agent_raises_on_missing_web_tool
   - test_build_agent_registers_base_tools (mock Agent class)
   - test_build_agent_includes_web_tool_when_enabled
   - test_run_agent_wraps_execution_exceptions
   - test_run_agent_stream_handles_cancellation (Event-based)
   - test_run_agent_stream_aggregates_usage_correctly
   - test_run_agent_stream_returns_partial_on_abort

3. Run and document failures: pytest tests/test_runtime.py -v
4. Commit with: "test(RED): Add failing tests for agent runtime security"

TASKS - GREEN PHASE:
5. Verify agents/runtime.py error handling is correct (likely already implemented)
6. Add any missing error handling for edge cases discovered by tests
7. Mock external dependencies (OpenAI client, Agent class) in tests
8. Implement cooperative cancellation test using threading.Event
9. Run until green: pytest tests/test_runtime.py -v --cov=agents.runtime
10. Commit with: "test(GREEN): Verify agent runtime error handling and security"

TASKS - REFACTOR PHASE:
11. Create test fixture for DummyAgent class (move to conftest.py)
12. Add integration-style test with real Agent but stubbed HTTP responses
13. Add contract test for OpenRouter API usage metadata parsing
14. Run full test suite: pytest tests/ -v --cov=agents --cov=services
15. Commit with: "test(REFACTOR): Add contract tests for agent runtime"

CONSTRAINTS:
- Use monkeypatch for environment variables (F:conftest.py fixture)
- Mock OpenAI client to avoid actual API calls: monkeypatch.setattr(runtime, "OpenAI", MockClient)
- Mock pydantic_ai.Agent class for tool registration tests
- Test cancellation with threading.Event and asyncio patterns
- Follow AGENTS.md "Security and Privacy" (F:AGENTS.md†L98-108)
- Target coverage: >90% for agents/runtime.py (exclude __main__)
- Ensure all tests are hermetic and deterministic
- Check git status clean after commits

CITATIONS:
- Cite build_agent function: F:agents/runtime.py†L30-74
- Cite run_agent_stream function: F:agents/runtime.py†L119-184
- Cite error handling: F:agents/runtime.py†L47-55, L108-115
- Cite AGENTS.md security sections
- Include terminal output showing coverage >90%

OUTPUT:
Provide complete tests/test_runtime.py with mocking patterns.
Provide updated conftest.py with DummyAgent and MockClient fixtures.
Show terminal output demonstrating security tests passing.
Include coverage report for agents/runtime.py.
```

**Expected Context for Next Prompt:**
- Agent runtime has comprehensive security tests
- Error handling is validated for all failure modes
- Cancellation logic is tested
- Mocking patterns for external dependencies are established

---

### **Prompt 5: Model Catalog Tests & Network Resilience**

```
Implement tests for model catalog fetching, caching, and fallback behavior with simulated network conditions.

CONTEXT FROM PROMPT 4:
- Mocking patterns are established in conftest.py
- Security and error handling tests are proven effective
- Async and property-based testing patterns are mature
- Coverage is >90% for agent runtime

RISK AREAS FROM ASSESSMENT:
- services/catalog.py fetches from OpenRouter API (F:services/catalog.py†L88-97)
- Fallback to static model list on failure (F:services/catalog.py†L146-154)
- Caching with TTL must work correctly (F:services/catalog.py†L42-43, L173-176)
- Price parsing handles various formats (F:services/catalog.py†L48-64)

TASKS - RED PHASE:
1. Create tests/test_catalog.py
2. Write FAILING tests for network resilience:
   - test_fetch_models_success_returns_dynamic_source
   - test_fetch_models_network_error_returns_fallback
   - test_fetch_models_malformed_json_returns_fallback
   - test_fetch_models_empty_data_returns_fallback
   - test_get_models_uses_cache_within_ttl
   - test_get_models_refreshes_after_ttl_expires
   - test_get_models_force_refresh_bypasses_cache
   - test_parse_price_handles_various_formats (property-based)
   - test_get_pricing_returns_none_for_unknown_model
   - test_get_model_choices_formats_display_names

3. Run and capture failures: pytest tests/test_catalog.py -v
4. Commit with: "test(RED): Add failing tests for model catalog resilience"

TASKS - GREEN PHASE:
5. Mock httpx.Client with success and failure scenarios:
   - Create MockResponse class in conftest.py
   - Simulate HTTPError, timeout, ConnectionError
   - Simulate malformed JSON responses

6. Mock datetime for TTL expiration tests (use freezegun or monkeypatch)
7. Verify catalog.py fallback logic is correct
8. Run until green: pytest tests/test_catalog.py -v --cov=services.catalog
9. Commit with: "test(GREEN): Verify model catalog fallback and caching logic"

TASKS - REFACTOR PHASE:
10. Add contract test for OpenRouter /api/v1/models response schema
11. Test price parsing with hypothesis strategies (various string formats)
12. Add integration test with real (but cached) API response fixture
13. Run full coverage: pytest tests/ -v --cov=agents --cov=services --cov-report=html
14. Commit with: "test(REFACTOR): Add contract tests for OpenRouter API"

CONSTRAINTS:
- Mock OPENROUTER_MODELS_URL to prevent actual HTTP calls
- Use monkeypatch for httpx.Client: monkeypatch.setattr(catalog, "httpx.Client", MockClient)
- Test cache behavior by manipulating _cache_timestamp
- Verify fallback list contains at least 3 models (F:services/catalog.py†L30-47)
- Follow AGENTS.md "Model Catalog" section (F:AGENTS.md†L73-83)
- Target coverage: >90% for services/catalog.py
- Ensure git status is clean after commits

CITATIONS:
- Cite fetch_models function: F:services/catalog.py†L67-154
- Cite caching logic: F:services/catalog.py†L157-176
- Cite fallback models: F:services/catalog.py†L30-47
- Cite price parsing: F:services/catalog.py†L48-64
- Include terminal output showing network error handling

OUTPUT:
Provide complete tests/test_catalog.py with network simulation.
Provide updated conftest.py with MockResponse and MockClient fixtures.
Show terminal output demonstrating fallback behavior.
Include coverage report showing >90% coverage.
Generate HTML coverage report: pytest --cov=services --cov-report=html
```

**Expected Context for Next Prompt:**
- Model catalog has network resilience tests
- Caching behavior is validated
- Fallback mechanisms are proven
- Contract tests ensure API compatibility

---

### **Prompt 6: Integration Tests & End-to-End Validation**

```
Create integration tests that validate end-to-end workflows and cross-module interactions.

CONTEXT FROM PROMPT 5:
- All individual modules have >90% unit test coverage
- Mocking and fixture patterns are mature
- Network resilience is tested
- Security and error handling are validated

INTEGRATION TEST SCENARIOS:
- Full agent lifecycle: build ? configure ? run ? persist results
- Streaming with cancellation and telemetry capture
- Model catalog refresh ? agent rebuild ? execution
- CSV persistence ? load ? validation roundtrip

TASKS - INTEGRATION TEST 1: Agent Lifecycle
1. Create tests/integration/test_agent_lifecycle.py
2. Test scenario:
   - Mock OPENROUTER_API_KEY
   - Build agent with valid config (F:agents/models.py†L12-23)
   - Mock OpenRouter streaming response
   - Execute run_agent_stream with sample prompt
   - Verify RunRecord is created with correct fields
   - Append to CSV (using tmp_path)
   - Load back and verify all fields match

3. Run: pytest tests/integration/test_agent_lifecycle.py -v
4. Commit with: "test(integration): Add agent lifecycle end-to-end test"

TASKS - INTEGRATION TEST 2: Streaming Cancellation
5. Create tests/integration/test_streaming_cancellation.py
6. Test scenario:
   - Build agent with mock streaming response (10 chunks)
   - Start run_agent_stream in asyncio task
   - Set cancel_token after 3 chunks received
   - Verify aborted=True in result
   - Verify partial text is preserved
   - Verify latency_ms is measured
   - Verify CSV row has aborted=true flag

7. Run: pytest tests/integration/test_streaming_cancellation.py -v
8. Commit with: "test(integration): Validate streaming cancellation behavior"

TASKS - INTEGRATION TEST 3: Model Catalog Workflow
9. Create tests/integration/test_catalog_workflow.py
10. Test scenario:
    - Mock httpx to return dynamic model list
    - Call get_models() and verify dynamic source
    - Simulate cache expiry
    - Force refresh with network error
    - Verify fallback source is used
    - Verify agent can be built with fallback model

11. Run: pytest tests/integration/test_catalog_workflow.py -v
12. Commit with: "test(integration): Validate model catalog refresh workflow"

TASKS - INTEGRATION TEST 4: Persistence Roundtrip
13. Create tests/integration/test_persistence_roundtrip.py
14. Test scenario:
    - Create RunRecord with all fields populated
    - Append to CSV in tmp_path
    - Load using load_recent_runs(limit=1)
    - Verify all field values match exactly
    - Test with edge case values (0 tokens, empty strings)
    - Verify CSV schema matches CSV_HEADERS

15. Run: pytest tests/integration/ -v
16. Commit with: "test(integration): Add persistence roundtrip validation"

CONSTRAINTS:
- All integration tests use mocked external dependencies (no real API calls)
- Use tmp_path for all file operations
- Tests should complete in <5 seconds each
- Follow AGENTS.md "Testing Strategy" (F:AGENTS.md†L110-123)
- Create integration/ subdirectory in tests/
- Add tests/integration/__init__.py
- Run full test suite: pytest tests/ -v --cov=agents --cov=services
- Target overall coverage: >90% for agents/ and services/
- Ensure git status is clean after all commits

CITATIONS:
- Cite relevant functions from all modules tested
- Cite AGENTS.md integration testing guidance
- Include terminal output showing integration tests passing
- Show final coverage report with >90% overall coverage

OUTPUT:
Provide all integration test files with complete scenarios.
Show terminal output for each integration test run.
Provide final coverage summary showing >90% for agents/ and services/.
Include pytest.ini markers configuration for integration tests.
```

**Expected Context for Next Prompt:**
- Integration tests validate cross-module workflows
- End-to-end scenarios are proven functional
- Overall coverage exceeds 90%
- All tests are passing and fast

---

### **Prompt 7: Documentation, Verification & Test Maintenance**

```
Update documentation, verify complete test coverage, and establish test maintenance guidelines.

CONTEXT FROM PROMPT 6:
- Comprehensive unit tests for all modules (>90% coverage)
- Integration tests for cross-module workflows
- All tests passing with fast execution (<30 seconds total)
- TDD cycles completed for tools, persistence, runtime, and catalog

FINAL VERIFICATION TASKS:
1. Run complete test suite with verbose output:
   - pytest tests/ -v --cov=agents --cov=services --cov-report=term-missing --cov-report=html
   - Capture and analyze coverage gaps (any <90% modules)
   - Identify untested lines and add targeted tests if needed

2. Run mutation testing (if mutmut installed):
   - mutmut run --paths-to-mutate=agents/,services/
   - Verify high mutation kill rate (>80%)
   - Add tests for any surviving mutants

3. Verify test quality metrics:
   - All tests hermetic (no external dependencies)
   - All tests deterministic (can run in any order)
   - All tests fast (<1 second each)
   - All tests follow naming convention: test_<module>_<behavior>

DOCUMENTATION UPDATES:
4. Update tests/README.md with:
   - Test architecture overview
   - How to run different test suites (unit vs integration)
   - Coverage requirements and how to check them
   - Adding new tests guidelines
   - Mocking patterns and fixtures documentation

5. Update AGENTS.md "Testing Strategy" section:
   - Add reference to tests/README.md
   - Document TDD workflow for future development
   - Add pytest command examples
   - Document coverage requirements (>90%)

6. Create tests/CONTRIBUTING.md:
   - TDD workflow (RED-GREEN-REFACTOR)
   - Test categorization (unit, integration, property-based)
   - Fixture usage guidelines
   - Mocking best practices
   - How to run tests locally before committing

7. Update root README.md:
   - Add "Running Tests" section after "Running the Application"
   - Include pytest installation if not in requirements.txt
   - Add coverage badge (if using CI)
   - Link to tests/README.md for details

TEST MAINTENANCE GUIDELINES:
8. Create .github/workflows/tests.yml (CI configuration):
   - Run pytest on push and PR
   - Require >90% coverage
   - Generate and upload coverage reports
   - Fail build on any test failure

9. Add pre-commit hook recommendation to CONTRIBUTING.md:
   - pytest tests/ --cov=agents --cov=services --cov-fail-under=90
   - Ensure all tests pass before commit

FINAL VALIDATION:
10. Run full validation sequence:
    - pytest tests/ -v --cov=agents --cov=services --cov-fail-under=90
    - pytest tests/ -v --tb=short (verify no warnings)
    - pytest tests/ -v --durations=10 (check for slow tests)

11. Review all commits in this TDD implementation:
    - Ensure commit messages follow convention
    - Verify git history is clean
    - Check that all files are committed

12. Final commit sequence:
    - git add tests/README.md tests/CONTRIBUTING.md
    - git add AGENTS.md README.md (if updated)
    - git add .github/workflows/tests.yml (if created)
    - git commit -m "docs: Add comprehensive testing documentation and guidelines"
    - git status (verify clean worktree)

CONSTRAINTS:
- Follow AGENTS.md "Git Workflow" conventions (F:AGENTS.md†L137-154)
- Ensure all documentation is accurate and up-to-date
- Verify all file paths and code examples in docs are correct
- Test all pytest commands in documentation work correctly
- Follow AGENTS.md "PR Instructions" format (F:AGENTS.md†L57-60)
- Ensure final coverage report shows >90% for agents/ and services/
- All commits should have clean git status after

CITATIONS:
- Cite updated AGENTS.md sections with line numbers
- Cite coverage report showing >90% coverage
- Include terminal output for final test runs
- Show mutmut results if mutation testing performed
- Cite all documentation updates with file paths

OUTPUT:
Provide updated tests/README.md with complete testing guide.
Provide updated tests/CONTRIBUTING.md with TDD workflow.
Provide updated AGENTS.md testing section.
Provide updated root README.md with testing instructions.
Show final coverage report (both terminal and HTML preview).
Include terminal output for all validation commands.
Provide CI configuration file (.github/workflows/tests.yml) if applicable.
Show final git log with all TDD implementation commits.
```

**Expected Final State:**
- ? Comprehensive test suite with >90% coverage
- ? All TDD cycles completed (RED-GREEN-REFACTOR)
- ? Property-based tests for critical invariants
- ? Integration tests for workflows
- ? Complete documentation for test maintenance
- ? CI/CD configuration for automated testing
- ? Clean git history with descriptive commits
- ? Mutation testing validates test quality

---

## Prompt Chain Summary

This 7-prompt sequence implements the complete TDD strategy from Codebase Assessment.docx:

1. **Prompt 1**: Infrastructure setup (pytest, fixtures, configuration)
2. **Prompt 2**: TDD Cycle 1 - Tool functions with property-based tests
3. **Prompt 3**: TDD Cycle 2 - CSV persistence with robust error handling
4. **Prompt 4**: TDD Cycle 3 - Agent runtime with security tests
5. **Prompt 5**: Model catalog with network resilience tests
6. **Prompt 6**: Integration tests for cross-module workflows
7. **Prompt 7**: Documentation, verification, and maintenance setup

Each prompt:
- ? References specific code with file paths and line numbers
- ? Follows Git constraints (no new branches, commit changes, clean worktree)
- ? Follows AGENTS.md conventions and testing guidelines
- ? Requires citations for all code references and outputs
- ? Builds on context from previous prompts
- ? Provides complete, actionable implementation steps
- ? Validates work at each stage

The chain addresses all risk areas identified in the assessment and achieves the 90%+ coverage goal with robust, maintainable tests.