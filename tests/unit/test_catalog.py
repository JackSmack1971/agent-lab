"""Unit tests for catalog module."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from services.catalog import (
    FALLBACK_MODELS,
    ModelInfo,
    _cache_source,
    _cache_timestamp,
    _cached_models,
    _parse_price,
    fetch_models,
    get_model_choices,
    get_models,
    get_pricing,
)


class TestParsePrice:
    """Test price parsing functionality."""

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            (None, None),
            (1.5, 1.5),
            ("1.5", 1.5),
            ("$1.5", 1.5),
            ("  $2.0  ", 2.0),
            ("invalid", None),
            ("", None),
            (0, 0.0),
        ],
    )
    def test_parse_price_various_inputs(
        self, input_value: Any, expected: float | None
    ) -> None:
        """Test _parse_price handles various input formats."""
        result = _parse_price(input_value)
        assert result == expected

    def test_parse_price_edge_cases(self) -> None:
        """Test _parse_price edge cases."""
        # Test string that looks like number but has extra chars
        assert _parse_price("1.5extra") is None
        # Test empty string after stripping
        assert _parse_price("   ") is None
        # Test boolean (converts to float in Python)
        assert _parse_price(True) == 1.0
        assert _parse_price(False) == 0.0
        # Test unsupported type (should return None)
        assert _parse_price([]) is None  # type: ignore
        assert _parse_price({}) is None  # type: ignore


class TestFetchModels:
    """Test model fetching functionality."""

    def setup_method(self) -> None:
        """Clear global cache before each test."""
        # Clear module-level cache variables
        import services.catalog

        services.catalog._cached_models = None
        services.catalog._cache_timestamp = None
        services.catalog._cache_source = "fallback"

    @patch("services.catalog.httpx.Client")
    def test_fetch_models_success(self, mock_client_class) -> None:
        """Test successful fetch from OpenRouter API."""
        mock_response_data = {
            "data": [
                {
                    "id": "openai/gpt-4",
                    "name": "GPT-4",
                    "provider": "openai",
                    "description": "Advanced model",
                    "pricing": {"prompt": "0.03", "completion": "0.06"},
                },
                {
                    "id": "anthropic/claude",
                    "name": "Claude",
                    "provider": "anthropic",
                    "pricing": {"prompt": 0.015, "completion": 0.075},
                },
            ]
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        models, source, timestamp = fetch_models()

        assert len(models) == 2
        assert source == "dynamic"
        assert isinstance(timestamp, datetime)

        # Check first model
        model1 = models[0]
        assert model1.id == "openai/gpt-4"
        assert model1.display_name == "GPT-4"
        assert model1.provider == "openai"
        assert model1.input_price == 0.03
        assert model1.output_price == 0.06

        # Check second model
        model2 = models[1]
        assert model2.id == "anthropic/claude"
        assert model2.input_price == 0.015
        assert model2.output_price == 0.075

    @patch("services.catalog.httpx.Client")
    def test_fetch_models_with_api_key(self, mock_client_class, monkeypatch) -> None:
        """Test fetch includes Authorization header when API key is set."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "test_key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "test/model", "name": "Test"}]
        }

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        fetch_models()

        # Check that Authorization header was set
        call_args = mock_client.get.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_key"

    @patch("services.catalog.httpx.Client")
    def test_fetch_models_network_failure_fallback(self, mock_client_class) -> None:
        """Test fallback when network request fails."""
        mock_client = Mock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        models, source, timestamp = fetch_models()

        assert models == FALLBACK_MODELS
        assert source == "fallback"
        assert isinstance(timestamp, datetime)

    @patch("services.catalog.httpx.Client")
    def test_fetch_models_malformed_response_fallback(self, mock_client_class) -> None:
        """Test fallback when API returns malformed data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "not_a_list"}

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        models, source, timestamp = fetch_models()

        assert models == FALLBACK_MODELS
        assert source == "fallback"

    @patch("services.catalog.httpx.Client")
    def test_fetch_models_empty_data_fallback(self, mock_client_class) -> None:
        """Test fallback when API returns empty data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        models, source, timestamp = fetch_models()

        assert models == FALLBACK_MODELS
        assert source == "fallback"

    @patch("services.catalog.httpx.Client")
    def test_fetch_models_malformed_entries(self, mock_client_class) -> None:
        """Test fetch handles malformed entries in response data."""
        mock_response_data = {
            "data": [
                {"id": "good/model", "name": "Good Model"},
                {"not": "a dict"},  # Malformed entry
                {"id": "", "name": "Empty ID"},  # Missing id
                {"name": "No ID field"},  # Missing id field
            ]
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        models, source, timestamp = fetch_models()

        # Should only get the valid model
        assert len(models) == 1
        assert models[0].id == "good/model"
        assert source == "dynamic"

    @patch("services.catalog.httpx.Client")
    def test_fetch_models_validation_error(self, mock_client_class) -> None:
        """Test fetch handles ValidationError in ModelInfo construction."""
        from pydantic import ValidationError as PydanticValidationError

        mock_response_data = {
            "data": [
                {"id": "good/model", "name": "Good Model"},
                {
                    "id": 123,
                    "name": "Bad Model",
                },  # Invalid id type, will be skipped earlier
            ]
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        models, source, timestamp = fetch_models()

        # Should skip the invalid model but include the good one
        assert len(models) == 1
        assert models[0].id == "good/model"
        assert source == "dynamic"


class TestGetModels:
    """Test get_models caching functionality."""

    def setup_method(self) -> None:
        """Clear global cache before each test."""
        # Clear module-level cache variables
        import services.catalog

        services.catalog._cached_models = None
        services.catalog._cache_timestamp = None
        services.catalog._cache_source = "fallback"

    @patch("services.catalog.httpx.Client")
    def test_get_models_initial_fetch(self, mock_client_class) -> None:
        """Test initial call fetches models."""
        mock_response_data = {"data": [{"id": "test/model", "name": "Test Model"}]}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        models, source, timestamp = get_models()

        assert len(models) == 1
        assert source == "dynamic"

    @patch("services.catalog.datetime")
    @patch("services.catalog.httpx.Client")
    def test_get_models_cached_within_ttl(
        self, mock_client_class, mock_datetime
    ) -> None:
        """Test cached models returned when within TTL."""
        # Set up fixed timestamp
        fixed_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_time

        # First call to populate cache
        mock_response_data = {"data": [{"id": "test/model", "name": "Test Model"}]}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        models1, source1, timestamp1 = get_models()

        # Second call should use cache (time still within TTL)
        models2, source2, timestamp2 = get_models()

        assert models1 == models2
        assert source1 == source2 == "dynamic"
        assert timestamp1 == timestamp2

        # httpx.Client should only be called once
        mock_client.get.assert_called_once()

    @patch("services.catalog.datetime")
    @patch("services.catalog.httpx.Client")
    def test_get_models_force_refresh(self, mock_client_class, mock_datetime) -> None:
        """Test force_refresh bypasses cache."""
        # Set up timestamps - need enough for all datetime.now calls
        time1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        time2 = datetime(2025, 1, 1, 12, 1, 0, tzinfo=timezone.utc)
        time3 = datetime(2025, 1, 1, 12, 2, 0, tzinfo=timezone.utc)
        time4 = datetime(2025, 1, 1, 12, 3, 0, tzinfo=timezone.utc)
        mock_datetime.now.side_effect = [time1, time2, time3, time4]

        # Mock response
        mock_response_data = {"data": [{"id": "test/model", "name": "Test Model"}]}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        models1, source1, timestamp1 = get_models()

        # Force refresh should call again
        models2, source2, timestamp2 = get_models(force_refresh=True)

        assert models1 == models2
        assert source1 == source2 == "dynamic"
        assert timestamp1 != timestamp2  # Different timestamps

        # httpx.Client should be called twice
        assert mock_client.get.call_count == 2


class TestModelChoices:
    """Test model choices functionality."""

    def setup_method(self) -> None:
        """Clear global cache before each test."""
        # Clear module-level cache variables
        import services.catalog

        services.catalog._cached_models = None
        services.catalog._cache_timestamp = None
        services.catalog._cache_source = "fallback"

    @patch("services.catalog.httpx.Client")
    def test_get_model_choices(self, mock_client_class) -> None:
        """Test get_model_choices returns proper format."""
        mock_response_data = {
            "data": [
                {"id": "model1", "name": "Model One"},
                {"id": "model2", "name": "Model Two"},
            ]
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        choices = get_model_choices()

        expected = [("Model One", "model1"), ("Model Two", "model2")]
        assert choices == expected


class TestGetPricing:
    """Test pricing lookup functionality."""

    def setup_method(self) -> None:
        """Clear global cache before each test."""
        # Clear module-level cache variables
        import services.catalog

        services.catalog._cached_models = None
        services.catalog._cache_timestamp = None
        services.catalog._cache_source = "fallback"

    @patch("services.catalog.httpx.Client")
    def test_get_pricing_existing_model(self, mock_client_class) -> None:
        """Test pricing lookup for existing model."""
        mock_response_data = {
            "data": [
                {
                    "id": "priced/model",
                    "name": "Priced Model",
                    "pricing": {"prompt": "0.01", "completion": "0.02"},
                }
            ]
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        pricing = get_pricing("priced/model")

        assert pricing == (0.01, 0.02)

    @patch("services.catalog.httpx.Client")
    def test_get_pricing_nonexistent_model(self, mock_client_class) -> None:
        """Test pricing lookup for nonexistent model."""
        mock_response_data = {"data": [{"id": "other/model", "name": "Other"}]}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        pricing = get_pricing("nonexistent/model")

        assert pricing is None

    @patch("services.catalog.httpx.Client")
    def test_get_pricing_model_without_pricing(self, mock_client_class) -> None:
        """Test pricing lookup for model without pricing info."""
        mock_response_data = {"data": [{"id": "no_price/model", "name": "No Price"}]}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        pricing = get_pricing("no_price/model")

        assert pricing is None
