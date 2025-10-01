import pytest
from pathlib import Path
from typing import Dict, Any, AsyncGenerator
from unittest.mock import Mock
import os
from pydantic import BaseModel
import httpx
from datetime import datetime

# Import required models (following AGENTS.md patterns)
from agents.models import AgentConfig

@pytest.fixture
def tmp_csv(tmp_path: Path) -> Path:
    """
    Create temporary CSV file with proper header for telemetry logging.

    Args:
        tmp_path: Pytest-provided temporary directory path

    Returns:
        Path to initialized CSV file
    """
    csv_path: Path = tmp_path / "test_runs.csv"
    header: str = "ts,agent_name,model,prompt_tokens,completion_tokens,total_tokens,latency_ms,cost_usd,experiment_id,task_label,run_notes,streaming,model_list_source,tool_web_enabled,web_status,aborted\n"
    csv_path.write_text(header, encoding="utf-8")
    return csv_path

@pytest.fixture
def mock_openrouter_response() -> Mock:
    """
    Mock HTTP response for OpenRouter API calls.

    Returns:
        Mock object simulating successful API response
    """
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
    """
    Provide valid AgentConfig instance for testing.

    Returns:
        Sample AgentConfig with realistic values
    """
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
    """
    Mock environment variables for testing, ensuring no real API keys are used.

    Args:
        monkeypatch: Pytest fixture for environment manipulation
    """
    # Mock API key without exposing real values
    monkeypatch.setenv("OPENROUTER_API_KEY", "mock_api_key_for_testing")

    # Mock other potential environment variables
    monkeypatch.setenv("TEST_ENV", "test_value")

@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Provide httpx AsyncClient for API testing with proper cleanup.

    Yields:
        Configured AsyncClient instance
    """
    # Configure client with test-appropriate settings
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(10.0, connect=5.0)

    async with httpx.AsyncClient(
        limits=limits,
        timeout=timeout,
        follow_redirects=True
    ) as client:
        yield client