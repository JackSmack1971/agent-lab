"""Integration tests for web fetch tool domain blocking and functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from agents.tools import fetch_url, FetchInput
from agents.runtime import build_agent
from agents.models import AgentConfig
from pydantic_ai import RunContext


@pytest.mark.integration
class TestWebToolIntegration:
    """Integration tests for web fetch tool."""

    @pytest.mark.asyncio
    async def test_fetch_url_blocks_non_allowed_domains(self):
        """Test that fetch_url blocks requests to non-allowed domains."""
        ctx = Mock(spec=RunContext)
        input_data = FetchInput(url="https://malicious-site.com/data.json")

        result = await fetch_url(ctx, input_data)

        assert result == "Refused: domain 'malicious-site.com' not in allow-list."

    @pytest.mark.asyncio
    async def test_fetch_url_allows_example_com_with_mock(self):
        """Test that fetch_url allows requests to example.com with mocked response."""
        ctx = Mock(spec=RunContext)
        input_data = FetchInput(url="https://example.com/api/data")

        mock_response = Mock()
        mock_response.text = "Example API response data"
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "text/plain"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await fetch_url(ctx, input_data)

            assert result == "Example API response data"
            mock_client.assert_called_once_with(timeout=10.0, follow_redirects=True, headers={'User-Agent': 'Agent-Lab/1.0'})

    @pytest.mark.asyncio
    async def test_agent_build_with_web_tools_registers_fetch_url(self, monkeypatch):
        """Test that building agent with web tools registers the fetch_url tool."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")
        config = AgentConfig(
            name="Test Agent",
            model="openai/gpt-3.5-turbo",
            system_prompt="You are a helpful assistant.",
            temperature=0.7,
            top_p=1.0
        )

        with patch("agents.runtime.OpenAI"), patch("agents.runtime.Agent") as mock_agent_class:
            mock_agent_instance = Mock()
            mock_agent_class.return_value = mock_agent_instance

            agent = build_agent(config, include_web=True)

            # Verify fetch_url was registered
            assert mock_agent_instance.tool.call_count == 3  # add_numbers, utc_now, fetch_url

    @pytest.mark.asyncio
    async def test_fetch_url_truncates_long_content(self):
        """Test that fetch_url truncates content to 4096 characters with truncation message."""
        ctx = Mock(spec=RunContext)
        input_data = FetchInput(url="https://api.github.com/repos/octocat/Hello-World")

        long_content = "A" * 5000
        mock_response = Mock()
        mock_response.text = long_content
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-type": "text/plain"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await fetch_url(ctx, input_data)

            assert len(result) == 4096 + len("\n\n[Content truncated to 4096 characters]")
            assert result == "A" * 4096 + "\n\n[Content truncated to 4096 characters]"