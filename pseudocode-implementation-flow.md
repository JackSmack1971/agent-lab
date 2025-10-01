# Pseudocode for Implementation Flow

This pseudocode represents the step-by-step implementation process for the test infrastructure, including git commit strategy for clean state management.

```python
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import os

def implement_test_infrastructure(base_path: Path) -> None:
    """
    Execute the complete test infrastructure implementation following AGENTS.md git workflow.
    
    Args:
        base_path: Project root directory
    """
    # Phase 1: Pytest Configuration
    print("Phase 1: Creating pytest.ini configuration")
    create_pytest_ini(base_path)
    
    # Verify pytest.ini
    if not run_pytest_collect_only():
        raise RuntimeError("pytest.ini configuration invalid")
    
    # Commit configuration
    git_commit("test: Add pytest.ini with asyncio and coverage configuration")
    
    # Phase 2: Shared Fixtures
    print("Phase 2: Implementing conftest.py with typed fixtures")
    create_conftest_py(base_path)
    
    # Test fixture loading
    if not test_fixture_loading():
        raise RuntimeError("conftest.py fixtures failed to load")
    
    # Commit fixtures
    git_commit("test: Add conftest.py with shared fixtures for tmp_path, mocks, configs, env vars")
    
    # Phase 3: Directory Structure
    print("Phase 3: Creating test directory structure")
    create_test_directories(base_path)
    create_placeholder_test_files(base_path)
    
    # Verify structure
    if not verify_directory_structure(base_path):
        raise RuntimeError("Test directory structure incomplete")
    
    # Commit structure
    git_commit("test: Create test directory structure following Python conventions")
    
    # Phase 4: Documentation
    print("Phase 4: Adding tests/README.md documentation")
    create_test_readme(base_path)
    
    # Commit documentation
    git_commit("test: Add tests/README.md documenting architecture decisions")
    
    # Phase 5: Final Verification
    print("Phase 5: Running final verification")
    if not run_final_verification():
        raise RuntimeError("Final verification failed")
    
    # Final commit
    git_commit("test: Initialize pytest infrastructure and fixtures")
    
    print("Test infrastructure implementation complete")

def create_pytest_ini(base_path: Path) -> None:
    """Create pytest.ini with asyncio and coverage configuration."""
    pytest_ini_path: Path = base_path / "pytest.ini"
    config_content: str = """[tool:pytest]
asyncio_mode = auto
addopts =
    --cov=agents
    --cov=services
    --cov-report=term-missing
    --strict-markers
    -v
markers =
    unit: Unit tests for individual functions and classes
    integration: Integration tests for component interactions
    slow: Slow-running tests requiring special handling
    requires_api_key: Tests that require OPENROUTER_API_KEY environment variable
python_files = test_*.py
python_classes = Test*
python_functions = test_*
"""
    pytest_ini_path.write_text(config_content, encoding="utf-8")

def create_conftest_py(base_path: Path) -> None:
    """Create conftest.py with all required typed fixtures."""
    conftest_path: Path = base_path / "tests" / "conftest.py"
    fixtures_content: str = """import pytest
from pathlib import Path
from typing import Dict, Any, AsyncGenerator
from unittest.mock import Mock
import os
from pydantic import BaseModel
import httpx
from datetime import datetime

class AgentConfig(BaseModel):
    name: str
    model: str
    system_prompt: str
    temperature: float
    top_p: float
    tools: list[str] = []
    extras: dict[str, Any] = {}

@pytest.fixture
def tmp_csv(tmp_path: Path) -> Path:
    csv_path: Path = tmp_path / "test_runs.csv"
    header: str = "ts,agent_name,model,prompt_tokens,completion_tokens,total_tokens,latency_ms,cost_usd,experiment_id,task_label,run_notes,streaming,model_list_source,tool_web_enabled,web_status,aborted\\n"
    csv_path.write_text(header, encoding="utf-8")
    return csv_path

@pytest.fixture
def mock_openrouter_response() -> Mock:
    mock_resp: Mock = Mock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.json.return_value = {
        "data": [
            {"id": "openai/gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "anthropic/claude-3-opus", "name": "Claude 3 Opus"},
            {"id": "meta-llama/llama-3-70b-instruct", "name": "Llama 3 70B"}
        ]
    }
    return mock_resp

@pytest.fixture
def sample_agent_config() -> AgentConfig:
    return AgentConfig(
        name="test_agent",
        model="openai/gpt-4-turbo",
        system_prompt="You are a helpful AI assistant for testing.",
        temperature=0.7,
        top_p=0.9,
        tools=["math", "clock"],
        extras={"max_tokens": 1000}
    )

@pytest.fixture
def mock_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock_api_key_for_testing")
    monkeypatch.setenv("TEST_ENV", "test_value")

@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        follow_redirects=True
    ) as client:
        yield client
"""
    conftest_path.write_text(fixtures_content, encoding="utf-8")

def create_test_directories(base_path: Path) -> None:
    """Create test subdirectories with __init__.py files."""
    test_dir: Path = base_path / "tests"
    
    # Create subdirectories
    subdirs: List[str] = ["integration", "fixtures"]
    for subdir in subdirs:
        dir_path: Path = test_dir / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        init_file: Path = dir_path / "__init__.py"
        init_file.write_text('"""Test package marker."""\\n', encoding="utf-8")

def create_placeholder_test_files(base_path: Path) -> None:
    """Create placeholder test files with basic structure."""
    test_dir: Path = base_path / "tests"
    
    # Unit test files
    unit_tests: List[str] = [
        "test_tools.py", "test_models.py", "test_runtime.py",
        "test_persist.py", "test_catalog.py"
    ]
    
    for test_file in unit_tests:
        file_path: Path = test_dir / test_file
        module_name: str = test_file.replace("test_", "").replace(".py", "")
        content: str = f'''"""Unit tests for {module_name} module."""

import pytest
from typing import Any

class Test{module_name.title()}:
    """Test suite for {module_name} functionality."""
    
    def test_placeholder(self) -> None:
        """Placeholder test - replace with actual test cases."""
        assert True
'''
        file_path.write_text(content, encoding="utf-8")
    
    # Integration test
    integration_path: Path = test_dir / "integration" / "test_streaming.py"
    integration_content: str = '''"""Integration tests for streaming functionality."""

import pytest
from typing import Any

@pytest.mark.integration
class TestStreaming:
    """Integration tests for streaming and cancellation."""
    
    @pytest.mark.asyncio
    async def test_placeholder_streaming(self) -> None:
        """Placeholder integration test - replace with streaming tests."""
        assert True
'''
    integration_path.write_text(integration_content, encoding="utf-8")

def create_test_readme(base_path: Path) -> None:
    """Create tests/README.md with architecture documentation."""
    readme_path: Path = base_path / "tests" / "README.md"
    readme_content: str = """# Agent Lab Test Suite

## Overview
This test suite provides comprehensive coverage for the agent-lab project...

## Architecture Decisions
- **pytest**: Primary testing framework with asyncio support
- **Markers**: Custom markers for selective execution
- **Fixtures**: Shared test data and mocks in conftest.py

## Running Tests
```bash
pytest  # Run all tests
pytest -m unit  # Run unit tests only
pytest --cov=agents --cov=services  # With coverage
```
"""
    readme_path.write_text(readme_content, encoding="utf-8")

def run_pytest_collect_only() -> bool:
    """Run pytest --collect-only to verify configuration."""
    try:
        result: subprocess.CompletedProcess = subprocess.run(
            ["pytest", "--collect-only"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def test_fixture_loading() -> bool:
    """Test that fixtures load without errors."""
    try:
        result: subprocess.CompletedProcess = subprocess.run(
            ["python", "-c", "import tests.conftest"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def verify_directory_structure(base_path: Path) -> bool:
    """Verify all required directories and files exist."""
    test_dir: Path = base_path / "tests"
    required_paths: List[Path] = [
        test_dir / "__init__.py",
        test_dir / "conftest.py",
        test_dir / "integration" / "__init__.py",
        test_dir / "fixtures",
        test_dir / "README.md"
    ]
    return all(path.exists() for path in required_paths)

def run_final_verification() -> bool:
    """Run final pytest --collect-only and basic coverage check."""
    try:
        # Test collection
        collect_result: subprocess.CompletedProcess = subprocess.run(
            ["pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if collect_result.returncode != 0:
            return False
        
        # Test coverage generation (dry run)
        cov_result: subprocess.CompletedProcess = subprocess.run(
            ["pytest", "--cov=agents", "--cov=services", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return cov_result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def git_commit(message: str) -> None:
    """
    Create a clean git commit with the specified message.
    
    Args:
        message: Commit message following AGENTS.md format
    """
    try:
        # Add all changes
        subprocess.run(["git", "add", "."], check=True)
        
        # Commit with message
        subprocess.run(["git", "commit", "-m", message], check=True)
        
        print(f"Committed: {message}")
    except subprocess.CalledProcessError as e:
        print(f"Git commit failed: {e}")
        raise

# Execution example:
# implement_test_infrastructure(Path("/path/to/agent-lab"))
```

## Function Specifications

### implement_test_infrastructure
- **Purpose**: Orchestrate complete test infrastructure setup
- **Input**: base_path (Path) - Project root
- **Output**: None
- **Error Handling**: Raises RuntimeError on verification failures

### create_pytest_ini
- **Purpose**: Generate pytest configuration file
- **Input**: base_path (Path)
- **Output**: None
- **Error Handling**: File write errors

### create_conftest_py
- **Purpose**: Generate shared fixtures file
- **Input**: base_path (Path)
- **Output**: None
- **Error Handling**: File write errors

### create_test_directories
- **Purpose**: Create test subdirectories
- **Input**: base_path (Path)
- **Output**: None
- **Error Handling**: Directory creation errors

### run_pytest_collect_only
- **Purpose**: Verify pytest configuration
- **Input**: None
- **Output**: bool - Success status
- **Error Handling**: Subprocess errors return False

### git_commit
- **Purpose**: Create clean git commits
- **Input**: message (str) - Commit message
- **Output**: None
- **Error Handling**: Git command failures

## Complexity Notes
- **Time Complexity**: O(n) where n is number of files created - linear in setup size
- **Space Complexity**: O(1) - fixed template sizes for generated files
- **Execution Notes**: Phased approach ensures each component works before proceeding; git commits provide rollback points; verification steps prevent broken states; follows AGENTS.md commit message format