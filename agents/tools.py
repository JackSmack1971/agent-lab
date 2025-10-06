"""Utility tools demonstrating the pydantic-ai registration pattern.

Each tool exposes a typed Pydantic schema for validation and an async
function that the agent runtime can register with pydantic-ai's
``RunContext``. This mirrors how future, more complex tools will be
implemented and validated before exposing them to user prompts.
"""

from __future__ import annotations

import unicodedata
import re
import math
import httpx
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import RunContext


def validate_agent_name_comprehensive(name: str) -> dict:
    """
    Comprehensive agent name validation with Unicode and injection protection.

    Handles:
    - Unicode normalization
    - Complex XSS patterns
    - Path traversal attempts
    - SQL injection patterns
    - Length limits
    """
    if not isinstance(name, str):
        return {"is_valid": False, "message": "Name must be a string"}

    # Unicode normalization to catch homoglyph attacks
    normalized_name = unicodedata.normalize('NFKC', name)

    # Length checks
    if len(normalized_name) == 0:
        return {"is_valid": False, "message": "Agent name cannot be empty"}

    if len(normalized_name) > 100:
        return {"is_valid": False, "message": "Agent name cannot exceed 100 characters"}

    # Reject control characters
    if any(ord(c) < 32 for c in normalized_name):
        return {"is_valid": False, "message": "Agent name cannot contain control characters"}

    # XSS patterns (expanded)
    xss_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'javascript:',
        r'vbscript:',
        r'data:',
        r'<[^>]*on\w+\s*=',
        r'expression\s*\(',
        r'vbscript\s*:',
        r'onload\s*=',
        r'onerror\s*=',
    ]

    for pattern in xss_patterns:
        if re.search(pattern, normalized_name, re.IGNORECASE):
            return {"is_valid": False, "message": "Agent name contains potentially unsafe content"}

    # SQL injection patterns
    sql_patterns = [
        r';\s*drop\s+',
        r';\s*delete\s+from\s+',
        r';\s*update\s+.*set\s+',
        r'union\s+select\s+',
        r'\bexec\s*\(',
        r'\beval\s*\(',
    ]

    for pattern in sql_patterns:
        if re.search(pattern, normalized_name, re.IGNORECASE):
            return {"is_valid": False, "message": "Agent name contains potentially unsafe content"}

    # Path traversal patterns
    if '..' in normalized_name or '\\' in normalized_name:
        return {"is_valid": False, "message": "Agent name contains invalid path characters"}

    # Valid name pattern (alphanumeric, spaces, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', normalized_name):
        return {"is_valid": False, "message": "Agent name can only contain letters, numbers, spaces, hyphens, and underscores"}

    return {"is_valid": True, "message": "Valid agent name"}


def validate_system_prompt_comprehensive(prompt: str) -> dict:
    """
    Comprehensive system prompt validation with content analysis.
    """
    if not isinstance(prompt, str):
        return {"is_valid": False, "message": "System prompt must be a string"}

    # Length limit (reasonable for system prompts)
    if len(prompt) > 10000:
        return {"is_valid": False, "message": "Maximum 10,000 characters allowed"}

    # XSS patterns (expanded)
    xss_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'javascript:',
        r'vbscript:',
        r'data:',
        r'<[^>]*on\w+\s*=',
        r'expression\s*\(',
        r'vbscript\s*:',
        r'onload\s*=',
        r'onerror\s*=',
    ]

    for pattern in xss_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            return {"is_valid": False, "message": "System prompt contains potentially unsafe content"}

    # Check for prompt injection patterns
    injection_patterns = [
        r'ignore\s+all\s+previous\s+instructions',
        r'override\s+system\s+prompt',
        r'system\s+prompt\s+override',
        r'you\s+are\s+no\s+longer',
        r'forget\s+your\s+previous',
        r'\[system\]',
        r'\[override\]',
    ]

    prompt_lower = prompt.lower()
    for pattern in injection_patterns:
        if re.search(pattern, prompt_lower):
            return {"is_valid": False, "message": "System prompt contains potentially unsafe override patterns"}

    # Check for code execution patterns
    code_patterns = [
        r'exec\s*\(',
        r'eval\s*\(',
        r'execfile\s*\(',
        r'__import__\s*\(',
        r'subprocess\.',
        r'os\.system\s*\(',
        r'os\.popen\s*\(',
    ]

    for pattern in code_patterns:
        if re.search(pattern, prompt):
            return {"is_valid": False, "message": "System prompt contains code execution patterns"}

    return {"is_valid": True, "message": "Valid system prompt"}


def validate_temperature_robust(value: Any) -> dict:
    """
    Robust temperature validation with comprehensive type checking.
    """
    # Handle None
    if value is None:
        return {"is_valid": False, "message": "Temperature is required"}

    # Handle string inputs
    if isinstance(value, str):
        try:
            # Remove whitespace
            value = value.strip()
            # Try to convert to float
            numeric_value = float(value)
        except ValueError:
            return {"is_valid": False, "message": "Temperature must be a valid number"}
    elif isinstance(value, (int, float)):
        numeric_value = float(value)
    else:
        return {"is_valid": False, "message": "Temperature must be a number"}

    # Check for NaN
    if math.isnan(numeric_value):
        return {"is_valid": False, "message": "Temperature must be a valid number"}

    # Range validation
    if numeric_value < 0.0:
        return {"is_valid": False, "message": "Temperature cannot be less than 0.0"}

    if numeric_value > 2.0:
        return {"is_valid": False, "message": "Temperature cannot be greater than 2.0"}

    # Check for potential issues with extreme precision
    if numeric_value != round(numeric_value, 6):
        return {"is_valid": False, "message": "Temperature precision is too high"}

    return {"is_valid": True, "message": "Valid temperature"}


# Allow-list for secure web access to prevent SSRF attacks
ALLOWED_DOMAINS = {"example.com", "api.github.com", "raw.githubusercontent.com"}


class AddInput(BaseModel):
    """Input schema for adding two numbers."""

    a: float
    b: float


async def add_numbers(ctx: RunContext, input: AddInput) -> float:
    """Add two numbers together. Use this when the user asks for arithmetic addition."""

    # Pydantic validation on ``AddInput`` ensures both operands are numeric.
    return input.a + input.b


class NowInput(BaseModel):
    """Input schema for getting current time with optional format string."""

    fmt: str = Field(default="%Y-%m-%d %H:%M:%S UTC")


async def utc_now(ctx: RunContext, input: NowInput) -> str:
    """Get current UTC time. Use this when the user asks what time it is."""

    # Using UTC avoids timezone ambiguity and leaking server locale data.
    # Return ISO format for consistency with standards
    if input.fmt == "%Y-%m-%d %H:%M:%S UTC":
        return datetime.now(timezone.utc).strftime(input.fmt)
    else:
        return datetime.now(timezone.utc).strftime(input.fmt)


class FetchInput(BaseModel):
    """Input schema for fetching content from a URL with timeout."""

    url: str
    timeout_s: float = Field(default=10.0, ge=1.0, le=30.0)


ALLOWED_CONTENT_TYPES = {
    'text/plain',
    'text/html',
    'text/xml',
    'application/json',
    'application/xml',
    'application/rss+xml',
    'text/markdown',
    'text/x-markdown'
}


def is_allowed_content_type(content_type: str) -> bool:
    """
    Check if content type is allowed for text processing.
    """
    if not content_type:
        return False

    # Extract main type/subtype
    main_type = content_type.split(';')[0].strip().lower()

    # Allow text/* and specific application types
    if main_type.startswith('text/'):
        return True

    return main_type in ALLOWED_CONTENT_TYPES


async def fetch_url(ctx: RunContext, input: FetchInput) -> str:
    """
    Fetch URL content with encoding-aware truncation.

    Properly handles:
    - Character encoding detection
    - Safe truncation at character boundaries
    - Content length limits
    """
    try:
        parsed_url = urlparse(input.url)
        domain = parsed_url.netloc.lower()

        if domain not in ALLOWED_DOMAINS:
            return f"Refused: domain '{domain}' not in allow-list."

        async with httpx.AsyncClient(
            timeout=input.timeout_s,
            follow_redirects=True,
            headers={'User-Agent': 'Agent-Lab/1.0'}
        ) as client:
            response = await client.get(input.url)
            response.raise_for_status()

            # Validate content type
            content_type = response.headers.get('content-type', '').lower()
            if not is_allowed_content_type(content_type):
                return f"Error: Unsupported content type '{content_type}'"

            # Detect encoding
            detected_encoding = response.encoding or 'utf-8'

            try:
                content = response.text
            except UnicodeDecodeError:
                return "Error: Failed to decode response as text."

            # Apply size limits
            if len(content) > 4096:
                content = content[:4096]
                content += "\n\n[Content truncated to 4096 characters]"

            return content

    except httpx.TimeoutException:
        return "Error: Request timed out."
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} - {e.response.reason_phrase}"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":  # pragma: no cover
    import asyncio
    from unittest.mock import Mock

    async def test_tools() -> None:
        ctx = Mock(spec=RunContext)

        # Test addition
        result1 = await add_numbers(ctx, AddInput(a=5.5, b=3.2))
        print(f"5.5 + 3.2 = {result1}")
        assert result1 == 8.7

        # Test clock
        result2 = await utc_now(ctx, NowInput())
        print(f"Current UTC: {result2}")
        assert "UTC" in result2

        print("✅ All tools working")

    asyncio.run(test_tools())
