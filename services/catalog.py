"""Model catalog service integrations and fallbacks."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, ValidationError

# Logger configured at module level to avoid leaking sensitive data.
logger = logging.getLogger(__name__)


class ModelInfo(BaseModel):
    """Representation of a single model entry returned by OpenRouter."""

    id: str
    display_name: str
    provider: str
    description: Optional[str] = None
    input_price: Optional[float] = None
    output_price: Optional[float] = None


OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
REQUEST_TIMEOUT = 10.0
CACHE_TTL = timedelta(hours=1)

FALLBACK_MODELS: list[ModelInfo] = [
    ModelInfo(
        id="openai/gpt-4-turbo",
        display_name="GPT-4 Turbo",
        provider="openai",
        description="OpenAI's GPT-4 Turbo general-purpose model.",
        input_price=0.01,
        output_price=0.03,
    ),
    ModelInfo(
        id="anthropic/claude-3-opus",
        display_name="Claude 3 Opus",
        provider="anthropic",
        description="Anthropic's Claude 3 Opus flagship reasoning model.",
        input_price=0.015,
        output_price=0.075,
    ),
    ModelInfo(
        id="meta-llama/llama-3-70b-instruct",
        display_name="Llama 3 70B",
        provider="meta",
        description="Meta's Llama 3 70B instruction-tuned model via OpenRouter.",
        input_price=0.002,
        output_price=0.002,
    ),
]

_cached_models: Optional[list[ModelInfo]] = None
_cache_timestamp: Optional[datetime] = None
_cache_source: Literal["dynamic", "fallback"] = "fallback"


def _parse_price(value: Optional[str | float]) -> Optional[float]:
    """Coerce API price fields into floats when possible."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip().replace("$", "")
        try:
            return float(normalized)
        except ValueError:
            return None
    return None


def fetch_models() -> tuple[list[ModelInfo], Literal["dynamic", "fallback"], datetime]:
    """Fetch current models from OpenRouter with fallback."""

    global _cached_models, _cache_timestamp, _cache_source

    timestamp = datetime.now(timezone.utc)
    headers: dict[str, str] = {"Accept": "application/json"}

    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        # Authorization header is optional but improves access to private/paid models.
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(OPENROUTER_MODELS_URL, headers=headers)
            response.raise_for_status()
            payload = response.json()

        data = payload.get("data")
        if not isinstance(data, list):
            raise ValueError("Unexpected OpenRouter response format: 'data' not list")

        models: list[ModelInfo] = []
        for entry in data:
            if not isinstance(entry, dict):
                logger.debug("Skipping malformed entry in OpenRouter data: %r", entry)
                continue

            model_id = entry.get("id")
            if not isinstance(model_id, str) or not model_id:
                logger.debug("Skipping entry missing 'id': %r", entry)
                continue

            name = entry.get("name") or entry.get("display_name") or model_id
            provider = entry.get("provider") or model_id.split("/", 1)[0]
            description = entry.get("description")
            pricing = entry.get("pricing") or {}

            input_price = _parse_price(pricing.get("prompt") if isinstance(pricing, dict) else None)
            output_price = _parse_price(pricing.get("completion") if isinstance(pricing, dict) else None)

            try:
                model = ModelInfo(
                    id=model_id,
                    display_name=str(name),
                    provider=str(provider),
                    description=str(description) if description is not None else None,
                    input_price=input_price,
                    output_price=output_price,
                )
            except ValidationError as exc:
                logger.debug("Validation error constructing ModelInfo: %s", exc)
                continue

            models.append(model)

        if not models:
            raise ValueError("OpenRouter returned no valid models")

        timestamp = datetime.now(timezone.utc)
        _cached_models = models
        _cache_timestamp = timestamp
        _cache_source = "dynamic"
        return models, "dynamic", timestamp

    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Failed to fetch models from OpenRouter, using fallback: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unexpected error fetching models from OpenRouter: %s", exc)

    timestamp = datetime.now(timezone.utc)
    _cached_models = list(FALLBACK_MODELS)
    _cache_timestamp = timestamp
    _cache_source = "fallback"
    return _cached_models, "fallback", timestamp


def get_models(force_refresh: bool = False) -> tuple[list[ModelInfo], Literal["dynamic", "fallback"], datetime]:
    """Return cached models when fresh, otherwise refresh from OpenRouter."""

    global _cached_models, _cache_timestamp, _cache_source

    if not force_refresh and _cached_models is not None and _cache_timestamp is not None:
        age = datetime.now(timezone.utc) - _cache_timestamp
        if age < CACHE_TTL:
            return _cached_models, _cache_source, _cache_timestamp

    return fetch_models()


def get_model_choices() -> list[tuple[str, str]]:
    """Provide display-friendly choices for UI dropdowns."""

    models, _, _ = get_models()
    return [(model.display_name, model.id) for model in models]


def get_pricing(model_id: str) -> Optional[tuple[float, float]]:
    """Return pricing tuple for a specific model when known."""

    models, _, _ = get_models()
    for model in models:
        if model.id == model_id:
            if model.input_price is not None and model.output_price is not None:
                return model.input_price, model.output_price
            return None
    return None


if __name__ == "__main__":
    fetched_models, source, fetched_ts = fetch_models()
    print(f"Fetched {len(fetched_models)} models (source={source}) at {fetched_ts.isoformat()}")
    for info in fetched_models[:5]:
        print(f" - {info.display_name} [{info.id}] provider={info.provider}")

    sample_id = fetched_models[0].id if fetched_models else FALLBACK_MODELS[0].id
    pricing = get_pricing(sample_id)
    if pricing:
        print(f"Pricing for {sample_id}: prompt={pricing[0]} / completion={pricing[1]}")
    else:
        print(f"Pricing unavailable for {sample_id}")
