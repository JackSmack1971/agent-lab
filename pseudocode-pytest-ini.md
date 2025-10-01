# Pseudocode for pytest.ini

This pseudocode represents the configuration for pytest.ini to enable asyncio support, coverage reporting, and custom markers as per AGENTS.md testing guidelines.

```ini
[tool:pytest]
# Enable automatic asyncio mode for async test functions
asyncio_mode = auto

# Default command-line options for coverage and output
addopts =
    --cov=agents
    --cov=services
    --cov-report=term-missing
    --strict-markers
    -v

# Define custom markers for categorizing tests
markers =
    unit: Unit tests for individual functions and classes
    integration: Integration tests for component interactions
    slow: Slow-running tests requiring special handling
    requires_api_key: Tests that require OPENROUTER_API_KEY environment variable

# Test discovery patterns
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

## Complexity Notes
- **Time Complexity**: O(1) - Configuration loading is constant time
- **Space Complexity**: O(1) - Minimal memory footprint for configuration
- **Execution Notes**: Markers enable selective test running (e.g., `pytest -m "not slow"`); asyncio_mode ensures proper event loop handling for async tests