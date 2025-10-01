# Pseudocode for Test Directory Structure

This pseudocode represents the creation and organization of the test directory structure following Python testing conventions and AGENTS.md guidelines.

```python
from pathlib import Path
import os
from typing import List

def create_test_directory_structure(base_path: Path) -> None:
    """
    Create the complete test directory structure for agent-lab.
    
    Args:
        base_path: Root directory of the project (contains agent-lab/)
    """
    test_dir: Path = base_path / "tests"
    
    # Create main test directories
    directories: List[str] = [
        "integration",  # Integration tests subdirectory
        "fixtures"      # Test data files subdirectory
    ]
    
    for dir_name in directories:
        dir_path: Path = test_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        # Create __init__.py for Python package recognition
        init_file: Path = dir_path / "__init__.py"
        init_file.write_text('"""Test package marker."""\n', encoding="utf-8")
    
    # Create test files with proper naming
    test_files: List[str] = [
        "test_tools.py",       # Unit tests for agents/tools.py
        "test_models.py",      # Unit tests for agents/models.py
        "test_runtime.py",     # Unit tests for agents/runtime.py
        "test_persist.py",     # Unit tests for services/persist.py
        "test_catalog.py"      # Unit tests for services/catalog.py
    ]
    
    for test_file in test_files:
        file_path: Path = test_dir / test_file
        # Create empty test file with basic structure
        content: str = f'''"""Unit tests for {test_file.replace("test_", "").replace(".py", "")} module."""

import pytest
from typing import Any

class Test{test_file.replace("test_", "").replace(".py", "").title()}:
    """Test suite for {test_file.replace("test_", "").replace(".py", "")} functionality."""
    
    def test_placeholder(self) -> None:
        """Placeholder test - replace with actual test cases."""
        assert True  # Replace with meaningful assertions
'''
        file_path.write_text(content, encoding="utf-8")
    
    # Create integration test file
    integration_test: Path = test_dir / "integration" / "test_streaming.py"
    integration_content: str = '''"""Integration tests for streaming functionality."""

import pytest
from typing import Any

@pytest.mark.integration
class TestStreaming:
    """Integration tests for streaming and cancellation."""
    
    @pytest.mark.asyncio
    async def test_placeholder_streaming(self) -> None:
        """Placeholder integration test - replace with streaming tests."""
        assert True  # Replace with streaming assertions
'''
    integration_test.write_text(integration_content, encoding="utf-8")
    
    # Create fixture files
    fixture_files: List[str] = [
        "sample_config.json",
        "mock_responses.json"
    ]
    
    for fixture_file in fixture_files:
        fixture_path: Path = test_dir / "fixtures" / fixture_file
        # Create basic JSON structure
        if "config" in fixture_file:
            content = '''{
    "name": "sample_agent",
    "model": "openai/gpt-4-turbo",
    "system_prompt": "Sample system prompt for testing",
    "temperature": 0.7,
    "top_p": 0.9,
    "tools": ["math", "clock"],
    "extras": {}
}'''
        else:
            content = '''{
    "models_response": {
        "data": [
            {"id": "openai/gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus"}
        ]
    },
    "error_response": {
        "error": "Mock API error for testing"
    }
}'''
        fixture_path.write_text(content, encoding="utf-8")

# Final directory structure after execution:
"""
tests/
├── __init__.py              # Package marker with imports
├── README.md                # Test architecture documentation
├── conftest.py              # Shared fixtures and configuration
├── test_tools.py            # Unit tests for agents/tools.py
├── test_models.py           # Unit tests for agents/models.py
├── test_runtime.py          # Unit tests for agents/runtime.py
├── test_persist.py          # Unit tests for services/persist.py
├── test_catalog.py          # Unit tests for services/catalog.py
├── integration/             # Integration tests directory
│   ├── __init__.py
│   └── test_streaming.py
└── fixtures/                # Test data files
    ├── sample_config.json
    └── mock_responses.json
"""
```

## Function Specifications

### create_test_directory_structure
- **Purpose**: Set up complete test directory hierarchy with files
- **Input**: base_path (Path) - Project root directory
- **Output**: None
- **Error Handling**: FileExistsError if directories exist (exist_ok=True handles); OSError for permission issues

## Complexity Notes
- **Time Complexity**: O(n) where n is number of files created - linear in file count
- **Space Complexity**: O(1) additional space - fixed template sizes
- **Execution Notes**: Uses pathlib for cross-platform compatibility; creates package markers for proper Python import handling; templates provide starting points for actual test implementation