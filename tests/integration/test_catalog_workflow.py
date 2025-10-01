"""Integration tests for model catalog refresh workflow."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
import time

from services.catalog import (
    fetch_models, get_models, get_model_choices, get_pricing,
    ModelInfo, FALLBACK_MODELS, CACHE_TTL
)


@pytest.mark.integration
class TestCatalogWorkflow:
    """Integration tests for model catalog refresh and caching workflow."""

    @pytest.fixture
    def mock_openrouter_success_response(self):
        """Mock successful OpenRouter API response."""
        return {
            "data": [
                {
                    "id": "openai/gpt-4-turbo",
                    "name": "GPT-4 Turbo",
                    "provider": "openai",
                    "description": "Latest GPT-4 model",
                    "pricing": {"prompt": "0.01", "completion": "0.03"}
                },
                {
                    "id": "anthropic/claude-3-opus",
                    "name": "Claude 3 Opus",
                    "provider": "anthropic",
                    "description": "Claude 3 flagship model",
                    "pricing": {"prompt": "0.015", "completion": "0.075"}
                },
                {
                    "id": "new-model/test-v1",
                    "name": "New Test Model",
                    "provider": "new-model",
                    "description": "A new model for testing",
                    "pricing": {"prompt": "0.005", "completion": "0.01"}
                }
            ]
        }

    @pytest.fixture
    def mock_openrouter_error_response(self):
        """Mock failed OpenRouter API response."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        return mock_response

    def test_catalog_workflow_successful_fetch_integration(self, mock_openrouter_success_response, mock_env_vars):
        """Test successful catalog fetch from OpenRouter API."""
        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value.json.return_value = mock_openrouter_success_response

            # Fetch models
            models, source, timestamp = fetch_models()

            # Verify successful fetch
            assert source == "dynamic"
            assert isinstance(timestamp, datetime)
            assert len(models) == 3

            # Verify model data
            model_ids = [m.id for m in models]
            assert "openai/gpt-4-turbo" in model_ids
            assert "anthropic/claude-3-opus" in model_ids
            assert "new-model/test-v1" in model_ids

            # Verify pricing data
            gpt4 = next(m for m in models if m.id == "openai/gpt-4-turbo")
            assert gpt4.input_price == 0.01
            assert gpt4.output_price == 0.03
            assert gpt4.provider == "openai"

    def test_catalog_workflow_fallback_on_api_failure_integration(self, mock_openrouter_error_response, mock_env_vars):
        """Test fallback to static models when OpenRouter API fails."""
        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Connection failed")

            # Fetch models - should fallback
            models, source, timestamp = fetch_models()

            # Verify fallback behavior
            assert source == "fallback"
            assert isinstance(timestamp, datetime)
            assert len(models) == len(FALLBACK_MODELS)

            # Verify fallback models
            model_ids = [m.id for m in models]
            assert "openai/gpt-4-turbo" in model_ids
            assert "anthropic/claude-3-opus" in model_ids
            assert "meta-llama/llama-3-70b-instruct" in model_ids

    def test_catalog_workflow_caching_behavior_integration(self, mock_openrouter_success_response, mock_env_vars):
        """Test catalog caching prevents unnecessary API calls."""
        # Clear any cached data first
        import services.catalog
        services.catalog._cached_models = None
        services.catalog._cache_timestamp = None

        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value.json.return_value = mock_openrouter_success_response

            # First call - should fetch from API
            models1, source1, ts1 = get_models()
            assert source1 == "dynamic"
            assert mock_client.get.call_count == 1

            # Second call immediately after - should use cache
            models2, source2, ts2 = get_models()
            assert source2 == "dynamic"
            assert ts1 == ts2  # Same timestamp
            assert mock_client.get.call_count == 1  # No additional API call

            # Verify cached data is identical
            assert len(models1) == len(models2)
            assert [m.id for m in models1] == [m.id for m in models2]

    def test_catalog_workflow_force_refresh_integration(self, mock_openrouter_success_response, mock_env_vars):
        """Test force refresh bypasses cache."""
        # Clear any cached data first
        import services.catalog
        services.catalog._cached_models = None
        services.catalog._cache_timestamp = None

        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value.json.return_value = mock_openrouter_success_response

            # First call
            get_models()
            assert mock_client.get.call_count == 1

            # Force refresh - should make API call despite cache
            get_models(force_refresh=True)
            assert mock_client.get.call_count == 2

    def test_catalog_workflow_cache_expiry_integration(self, mock_openrouter_success_response, mock_env_vars):
        """Test cache expiry triggers refresh."""
        # Clear any cached data first
        import services.catalog
        services.catalog._cached_models = None
        services.catalog._cache_timestamp = None

        with patch('services.catalog.httpx.Client') as mock_client_class, \
             patch('services.catalog.datetime') as mock_datetime:

            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value.json.return_value = mock_openrouter_success_response

            # Mock time progression
            base_time = datetime.now(timezone.utc)
            mock_datetime.now.return_value = base_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            # First call - cache models
            get_models()
            assert mock_client.get.call_count == 1

            # Advance time past cache TTL
            mock_datetime.now.return_value = base_time + CACHE_TTL + timedelta(seconds=1)

            # Second call - should refresh cache
            get_models()
            assert mock_client.get.call_count == 2

    def test_catalog_workflow_model_choices_ui_integration(self, mock_openrouter_success_response, mock_env_vars):
        """Test model choices generation for UI dropdowns."""
        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value.json.return_value = mock_openrouter_success_response

            # Get model choices
            choices = get_model_choices()

            # Verify format for UI consumption
            assert isinstance(choices, list)
            assert all(isinstance(choice, tuple) and len(choice) == 2 for choice in choices)

            # Verify expected models are present
            choice_ids = [choice[1] for choice in choices]
            assert "openai/gpt-4-turbo" in choice_ids
            assert "anthropic/claude-3-opus" in choice_ids

            # Verify display names are user-friendly
            gpt4_choice = next(c for c in choices if c[1] == "openai/gpt-4-turbo")
            assert gpt4_choice[0] == "GPT-4 Turbo"

    def test_catalog_workflow_pricing_lookup_integration(self, mock_openrouter_success_response, mock_env_vars):
        """Test pricing lookup for specific models."""
        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value.json.return_value = mock_openrouter_success_response

            # Test known model pricing
            pricing = get_pricing("openai/gpt-4-turbo")
            assert pricing == (0.01, 0.03)

            pricing_opus = get_pricing("anthropic/claude-3-opus")
            assert pricing_opus == (0.015, 0.075)

            # Test unknown model
            unknown_pricing = get_pricing("unknown/model")
            assert unknown_pricing is None

            # Test model without pricing
            with patch('services.catalog.httpx.Client') as mock_client_class2:
                mock_client2 = Mock()
                mock_client_class2.return_value.__enter__.return_value = mock_client2
                mock_client2.get.return_value.json.return_value = {
                    "data": [{"id": "no-price/model", "name": "No Price Model"}]
                }

                pricing_none = get_pricing("no-price/model")
                assert pricing_none is None

    def test_catalog_workflow_mixed_source_timestamps_integration(self, mock_env_vars):
        """Test that timestamps correctly indicate data source."""
        # Test dynamic source timestamp
        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value.json.return_value = {
                "data": [{"id": "test/model", "name": "Test Model"}]
            }

            models, source, ts = get_models(force_refresh=True)
            assert source == "dynamic"
            assert isinstance(ts, datetime)

        # Test fallback source timestamp
        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.side_effect = Exception("API down")

            # Clear any cached data first
            import services.catalog
            services.catalog._cached_models = None
            services.catalog._cache_timestamp = None

            models, source, ts = get_models(force_refresh=True)
            assert source == "fallback"
            assert isinstance(ts, datetime)

    def test_catalog_workflow_error_resilience_integration(self, mock_env_vars):
        """Test catalog handles various error conditions gracefully."""
        # Test malformed JSON response
        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value.json.side_effect = ValueError("Invalid JSON")

            models, source, ts = fetch_models()
            assert source == "fallback"
            assert len(models) == len(FALLBACK_MODELS)

        # Test missing data field
        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value.json.return_value = {"status": "ok"}  # No data field

            models, source, ts = fetch_models()
            assert source == "fallback"
            assert len(models) == len(FALLBACK_MODELS)

        # Test empty data array
        with patch('services.catalog.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client.get.return_value.json.return_value = {"data": []}

            models, source, ts = fetch_models()
            assert source == "fallback"
            assert len(models) == len(FALLBACK_MODELS)