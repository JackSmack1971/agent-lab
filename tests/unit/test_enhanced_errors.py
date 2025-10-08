"""Unit tests for enhanced error messages component."""

import pytest
from src.components.enhanced_errors import (
    EnhancedErrorManager,
    render_error_message,
    error_manager
)


class TestEnhancedErrorManager:
    """Test the EnhancedErrorManager class."""

    def test_agent_name_validation_valid(self):
        """Test valid agent name validation."""
        result = error_manager.validate_field_with_enhanced_errors("agent_name", "TestAgent")
        assert result["is_valid"] is True
        assert result["error_message"] == ""
        assert result["help_content"] is None

    def test_agent_name_validation_empty(self):
        """Test empty agent name validation."""
        result = error_manager.validate_field_with_enhanced_errors("agent_name", "")
        assert result["is_valid"] is False
        assert "required" in result["error_message"]
        assert result["help_content"] is not None
        assert "Agent Name Requirements" in result["help_content"]["title"]

    def test_agent_name_validation_too_long(self):
        """Test agent name too long validation."""
        long_name = "A" * 101
        result = error_manager.validate_field_with_enhanced_errors("agent_name", long_name)
        assert result["is_valid"] is False
        assert "100 characters" in result["error_message"]

    def test_agent_name_validation_invalid_chars(self):
        """Test agent name with invalid characters."""
        result = error_manager.validate_field_with_enhanced_errors("agent_name", "Test Agent!")
        assert result["is_valid"] is False
        assert "Invalid characters" in result["error_message"]

    def test_temperature_validation_valid(self):
        """Test valid temperature validation."""
        result = error_manager.validate_field_with_enhanced_errors("temperature", 0.7)
        assert result["is_valid"] is True

    def test_temperature_validation_too_high(self):
        """Test temperature too high validation."""
        result = error_manager.validate_field_with_enhanced_errors("temperature", 3.0)
        assert result["is_valid"] is False
        assert "between 0.0 and 2.0" in result["error_message"]

    def test_temperature_validation_invalid_type(self):
        """Test temperature with invalid type."""
        result = error_manager.validate_field_with_enhanced_errors("temperature", "invalid")
        assert result["is_valid"] is False
        assert "Must be a number between 0.0 and 2.0" in result["error_message"]

    def test_top_p_validation_valid(self):
        """Test valid top_p validation."""
        result = error_manager.validate_field_with_enhanced_errors("top_p", 0.9)
        assert result["is_valid"] is True

    def test_top_p_validation_too_high(self):
        """Test top_p too high validation."""
        result = error_manager.validate_field_with_enhanced_errors("top_p", 1.5)
        assert result["is_valid"] is False
        assert "between 0.0 and 1.0" in result["error_message"]

    def test_unknown_field_validation(self):
        """Test validation of unknown field."""
        result = error_manager.validate_field_with_enhanced_errors("unknown_field", "value")
        assert result["is_valid"] is True

    def test_validation_error_handling(self):
        """Test error handling in validation."""
        # This should not raise an exception
        result = error_manager.validate_field_with_enhanced_errors("agent_name", None)
        assert result["is_valid"] is False
        assert "This field is required" in result["error_message"]


class TestRenderErrorMessage:
    """Test the render_error_message function."""

    def test_render_valid_message(self):
        """Test rendering valid (no error) message."""
        html = render_error_message({"is_valid": True})
        assert html == ""

    def test_render_error_message_basic(self):
        """Test rendering basic error message."""
        error_data = {
            "is_valid": False,
            "error_message": "Test error",
            "help_content": None,
            "suggestions": [],
            "examples": []
        }
        html = render_error_message(error_data)
        assert "Test error" in html
        assert "enhanced-error" in html
        assert "❌" in html

    def test_render_error_with_suggestions(self):
        """Test rendering error message with suggestions."""
        error_data = {
            "is_valid": False,
            "error_message": "Test error",
            "help_content": None,
            "suggestions": ["Try this", "Or this"],
            "examples": []
        }
        html = render_error_message(error_data)
        assert "Try this" in html
        assert "Or this" in html
        assert "💡" in html

    def test_render_error_with_help(self):
        """Test rendering error message with help content."""
        error_data = {
            "is_valid": False,
            "error_message": "Test error",
            "help_content": {
                "title": "Help Title",
                "description": "Help description",
                "rules": ["Rule 1", "Rule 2"],
                "examples": ["Example 1"]
            },
            "suggestions": [],
            "examples": []
        }
        html = render_error_message(error_data, show_help_button=True)
        assert "Help Title" in html
        assert "Help description" in html
        assert "Rule 1" in html
        assert "Learn More ▼" in html

    def test_render_error_without_help_button(self):
        """Test rendering error message without help button."""
        error_data = {
            "is_valid": False,
            "error_message": "Test error",
            "help_content": {"title": "Help"},
            "suggestions": [],
            "examples": []
        }
        html = render_error_message(error_data, show_help_button=False)
        assert "Learn More ▼" not in html