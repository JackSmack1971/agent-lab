# Contributing to Agent Lab Testing

## TDD Workflow and Maintenance Guidelines

### Test-Driven Development Process

#### Red-Green-Refactor Cycle
1. **Red**: Write a failing test that defines the desired behavior
2. **Green**: Implement the minimal code to make the test pass
3. **Refactor**: Improve code quality while maintaining test coverage

#### Writing Tests First
- Define expected behavior before implementation
- Use descriptive test names that explain the requirement
- Include edge cases and error conditions
- Mock external dependencies to isolate unit tests

#### Implementation Guidelines
- Write minimal code to pass the test
- Avoid over-engineering during initial implementation
- Focus on correctness over optimization initially

#### Refactoring Phase
- Improve code structure and readability
- Eliminate duplication
- Ensure all tests still pass
- Maintain or improve test coverage

### Test Categories

#### Unit Tests
- Test individual functions and classes
- Mock all external dependencies
- Focus on logic and edge cases
- Fast execution (<1 second per test)

#### Integration Tests
- Test component interactions
- Use realistic data and minimal mocking
- Validate data flow between modules
- Include end-to-end workflows

#### Acceptance Tests
- Validate user requirements
- Test complete features
- May require external services (with proper setup)

### Coverage Maintenance

#### Requirements
- Maintain >90% coverage for `agents/` and `services/` directories
- Run coverage checks before each commit
- Address coverage gaps immediately

#### Coverage Analysis
- Review coverage reports regularly
- Identify untested code paths
- Add tests for missing branches and error conditions

### Code Quality Standards

#### Test Structure
```python
class TestFeature:
    """Test suite for specific feature."""

    def test_basic_functionality(self, fixture) -> None:
        """Test basic feature behavior."""
        # Arrange
        # Act
        # Assert

    def test_edge_cases(self, fixture) -> None:
        """Test edge cases and error conditions."""
        # Test invalid inputs
        # Test boundary conditions
        # Test error handling
```

#### Naming Conventions
- `test_<action>_<condition>_<expected_result>`
- Use descriptive names that explain the test purpose
- Include context in test docstrings

#### Assertions
- Use specific assertions (`assertEqual`, `assertRaises`, etc.)
- Provide clear failure messages
- Test both positive and negative cases

### Maintenance Tasks

#### Regular Activities
- Update mock responses when APIs change
- Review and update test data periodically
- Clean up obsolete test fixtures
- Validate tests on all supported Python versions

#### Performance Monitoring
- Keep test execution time reasonable
- Monitor for slow tests and optimize
- Ensure CI/CD pipelines complete within time limits

#### Test Data Management
- Use realistic but sanitized test data
- Avoid hard-coded values in tests
- Update fixtures when data formats change

### Debugging Test Failures

#### Common Issues
- **Flaky Tests**: Identify and fix non-deterministic behavior
- **Environment Dependencies**: Ensure tests work in CI environment
- **Mock Inconsistencies**: Verify mock setup matches actual usage

#### Debugging Techniques
- Use `pytest --pdb` for interactive debugging
- Add temporary print statements for investigation
- Isolate failing tests with `-k` flag
- Check fixture dependencies and ordering

### Contributing New Tests

#### Process
1. Identify the requirement or bug to test
2. Write a failing test (Red)
3. Implement the feature (Green)
4. Refactor and ensure coverage (Refactor)
5. Submit pull request with test and implementation

#### Pull Request Requirements
- All new code must have corresponding tests
- Maintain >90% coverage
- Tests must pass on all supported environments
- Include documentation updates if needed

### Best Practices

#### Do's
- Write tests before code changes
- Keep tests simple and focused
- Use descriptive names and assertions
- Mock external dependencies appropriately
- Run full test suite before committing

#### Don'ts
- Don't skip tests for "performance" reasons
- Don't write tests that depend on specific timing
- Don't hard-code environment-specific values
- Don't ignore failing tests
- Don't remove tests without justification

### Resources
- [pytest Documentation](https://docs.pytest.org/)
- [Testing in Python](https://docs.python.org/3/library/unittest.html)
- [Mock Library Guide](https://docs.python.org/3/library/unittest.mock.html)
- [Hypothesis for Property Testing](https://hypothesis.readthedocs.io/)