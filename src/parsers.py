"""Response parsing utilities for API responses."""

import json
from typing import Any, Dict, Literal
from pydantic import BaseModel, ValidationError


class ParsedResponse(BaseModel):
    """Parsed API response structure."""

    status: Literal["success", "error", "partial"]
    content: str
    tokens: int = 0
    metadata: Dict[str, Any] = {}


class ResponseParser:
    """Parser for API response data."""

    @staticmethod
    def parse(response_data: Dict[str, Any]) -> ParsedResponse:
        """
        Parse API response data into a structured format.

        Args:
            response_data: Raw response data from API

        Returns:
            ParsedResponse: Structured response object

        Raises:
            ValidationError: If response data doesn't match expected schema
        """
        try:
            # Handle different response formats
            if isinstance(response_data, dict):
                # Standard API response format
                if "status" in response_data:
                    return ParsedResponse(
                        status=response_data.get("status", "success"),
                        content=response_data.get("content", ""),
                        tokens=response_data.get("tokens", 0),
                        metadata=response_data.get("metadata", {})
                    )
                # OpenAI-style response
                elif "choices" in response_data:
                    choice = response_data["choices"][0]
                    message = choice.get("message", {})
                    content = message.get("content", "")

                    # Extract usage if available
                    usage = response_data.get("usage", {})
                    tokens = usage.get("total_tokens", len(content.split()) * 4)  # Rough estimate

                    return ParsedResponse(
                        status="success",
                        content=content,
                        tokens=tokens,
                        metadata={"usage": usage, "finish_reason": choice.get("finish_reason")}
                    )
                # Error response
                elif "error" in response_data:
                    return ParsedResponse(
                        status="error",
                        content=str(response_data["error"]),
                        tokens=0,
                        metadata=response_data
                    )
                else:
                    # Generic response - assume success with content
                    content = response_data.get("content", json.dumps(response_data))
                    return ParsedResponse(
                        status="success",
                        content=content,
                        tokens=len(content.split()) * 4,  # Rough token estimate
                        metadata=response_data
                    )
            else:
                # Handle non-dict responses
                return ParsedResponse(
                    status="success",
                    content=str(response_data),
                    tokens=len(str(response_data).split()) * 4,
                    metadata={"original_type": type(response_data).__name__}
                )

        except Exception as e:
            # Fallback for any parsing errors
            return ParsedResponse(
                status="error",
                content=f"Parsing failed: {str(e)}",
                tokens=0,
                metadata={"error": str(e), "original_data": str(response_data)[:500]}
            )