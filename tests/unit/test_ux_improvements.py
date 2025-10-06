"""Tests for UX improvements: inline validation, keyboard shortcuts, loading states."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from app import (
    validate_agent_name,
    validate_system_prompt,
    validate_temperature,
    validate_top_p,
    validate_model_selection,
    validate_form_field,
    handle_keyboard_shortcut,
)


class TestInlineValidation:
    """Test inline validation functions."""

    def test_validate_agent_name_valid(self):
        """Test valid agent name validation."""
        result = validate_agent_name("Test Agent")
        assert result["status"] == "success"
        assert "Agent Name is valid" in result["message"]
        assert result["is_valid"] is True

    def test_validate_agent_name_empty(self):
        """Test empty agent name validation."""
        result = validate_agent_name("")
        assert result["status"] == "error"
        assert "cannot be empty" in result["message"]
        assert result["is_valid"] is False

    def test_validate_agent_name_whitespace(self):
        """Test whitespace-only agent name validation."""
        result = validate_agent_name("   ")
        assert result["status"] == "error"
        assert "required" in result["message"]
        assert result["is_valid"] is False

    def test_validate_agent_name_too_long(self):
        """Test agent name exceeding max length."""
        long_name = "A" * 101
        result = validate_agent_name(long_name)
        assert result["status"] == "error"
        assert "100 characters" in result["message"]
        assert result["is_valid"] is False

    def test_validate_system_prompt_valid(self):
        """Test valid system prompt validation."""
        result = validate_system_prompt("You are a helpful assistant.")
        assert result["status"] == "success"
        assert result["message"] == "✅ System Prompt is valid"
        assert result["is_valid"] is True

    def test_validate_system_prompt_empty(self):
        """Test empty system prompt validation."""
        result = validate_system_prompt("")
        assert result["status"] == "error"
        assert "required" in result["message"]
        assert result["is_valid"] is False

    def test_validate_system_prompt_too_long(self):
        """Test system prompt exceeding max length."""
        long_prompt = "A" * 10001
        result = validate_system_prompt(long_prompt)
        assert result["status"] == "error"
        assert "10,000 characters" in result["message"]
        assert result["is_valid"] is False

    @pytest.mark.parametrize("temp,expected_valid", [
        (0.0, True),
        (1.0, True),
        (2.0, True),
        (1.5, True),
        (-0.1, False),
        (2.1, False),
        ("invalid", False),
        (None, False),
    ])
    def test_validate_temperature(self, temp, expected_valid):
        """Test temperature validation with various inputs."""
        result = validate_temperature(temp)
        assert result["is_valid"] is expected_valid

        if expected_valid:
            assert result["status"] == "success"
            assert "valid" in result["message"]
        else:
            assert result["status"] == "error"
            assert "Temperature" in result["message"]

    @pytest.mark.parametrize("top_p,expected_valid", [
        (0.0, True),
        (0.5, True),
        (1.0, True),
        (0.9, True),
        (-0.1, False),
        (1.1, False),
        ("invalid", False),
        (None, False),
    ])
    def test_validate_top_p(self, top_p, expected_valid):
        """Test top_p validation with various inputs."""
        result = validate_top_p(top_p)
        assert result["is_valid"] is expected_valid

        if expected_valid:
            assert result["status"] == "success"
            assert "valid" in result["message"]
        else:
            assert result["status"] == "error"
            assert "Top P" in result["message"]

    def test_validate_model_selection_valid(self):
        """Test valid model selection."""
        mock_models = [Mock(id="gpt-4"), Mock(id="claude")]
        result = validate_model_selection("gpt-4", mock_models)
        assert result["status"] == "success"
        assert result["message"] == "✅ Model is valid"
        assert result["is_valid"] is True

    def test_validate_model_selection_invalid(self):
        """Test invalid model selection."""
        mock_models = [Mock(id="gpt-4"), Mock(id="claude")]
        result = validate_model_selection("invalid-model", mock_models)
        assert result["status"] == "error"
        assert "valid model" in result["message"]
        assert result["is_valid"] is False

    def test_validate_model_selection_no_models(self):
        """Test model selection with no available models."""
        result = validate_model_selection("any-model", None)
        assert result["status"] == "error"
        assert "No models available" in result["message"]
        assert result["is_valid"] is False

    def test_validate_form_field_agent_name(self):
        """Test form field validation dispatch for agent name."""
        result = validate_form_field("agent_name", "Test Agent")
        assert result["status"] == "success"
        assert "Agent Name" in result["message"]

    def test_validate_form_field_system_prompt(self):
        """Test form field validation dispatch for system prompt."""
        result = validate_form_field("system_prompt", "Test prompt")
        assert result["status"] == "success"
        assert "System Prompt" in result["message"]

    def test_validate_form_field_temperature(self):
        """Test form field validation dispatch for temperature."""
        result = validate_form_field("temperature", 1.0)
        assert result["status"] == "success"
        assert "Temperature" in result["message"]

    def test_validate_form_field_top_p(self):
        """Test form field validation dispatch for top_p."""
        result = validate_form_field("top_p", 0.9)
        assert result["status"] == "success"
        assert "Top P" in result["message"]

    def test_validate_form_field_model(self):
        """Test form field validation dispatch for model."""
        mock_models = [Mock(id="gpt-4")]
        result = validate_form_field("model", "gpt-4", mock_models)
        assert result["status"] == "success"
        assert "Model" in result["message"]

    def test_validate_form_field_unknown(self):
        """Test form field validation dispatch for unknown field."""
        result = validate_form_field("unknown_field", "value")
        assert result["status"] == "unknown"
        assert result["message"] == ""
        assert result["is_valid"] is True


class TestKeyboardShortcuts:
    """Test keyboard shortcut handling."""

    def test_handle_keyboard_shortcut_ctrl_enter(self):
        """Test Ctrl+Enter shortcut detection."""
        mock_event = Mock()
        mock_event._data = {
            'key': 'Enter',
            'ctrlKey': True,
            'metaKey': False,
            'shiftKey': False
        }

        result = handle_keyboard_shortcut(mock_event)
        assert result == 'send_message'

    def test_handle_keyboard_shortcut_cmd_enter(self):
        """Test Cmd+Enter shortcut detection (macOS)."""
        mock_event = Mock()
        mock_event._data = {
            'key': 'Enter',
            'ctrlKey': False,
            'metaKey': True,
            'shiftKey': False
        }

        result = handle_keyboard_shortcut(mock_event)
        assert result == 'send_message'

    def test_handle_keyboard_shortcut_ctrl_k(self):
        """Test Ctrl+K shortcut detection."""
        mock_event = Mock()
        mock_event._data = {
            'key': 'k',
            'ctrlKey': True,
            'metaKey': False,
            'shiftKey': False
        }

        result = handle_keyboard_shortcut(mock_event)
        assert result == 'focus_input'

    def test_handle_keyboard_shortcut_ctrl_r(self):
        """Test Ctrl+R shortcut detection."""
        mock_event = Mock()
        mock_event._data = {
            'key': 'r',
            'ctrlKey': True,
            'metaKey': False,
            'shiftKey': False
        }

        result = handle_keyboard_shortcut(mock_event)
        assert result == 'refresh_models'

    def test_handle_keyboard_shortcut_escape(self):
        """Test Escape shortcut detection."""
        mock_event = Mock()
        mock_event._data = {
            'key': 'Escape',
            'ctrlKey': False,
            'metaKey': False,
            'shiftKey': False
        }

        result = handle_keyboard_shortcut(mock_event)
        assert result == 'stop_generation'

    def test_handle_keyboard_shortcut_no_match(self):
        """Test unrecognized key combination."""
        mock_event = Mock()
        mock_event._data = {
            'key': 'a',
            'ctrlKey': False,
            'metaKey': False,
            'shiftKey': False
        }

        result = handle_keyboard_shortcut(mock_event)
        assert result == 'none'

    def test_handle_keyboard_shortcut_exception(self):
        """Test keyboard shortcut handling with exception."""
        mock_event = Mock()
        # Missing _data attribute should cause exception
        mock_event._data = None

        result = handle_keyboard_shortcut(mock_event)
        assert result == 'none'

    def test_handle_keyboard_shortcut_case_insensitive(self):
        """Test keyboard shortcut case insensitivity."""
        mock_event = Mock()
        mock_event._data = {
            'key': 'ENTER',  # uppercase
            'ctrlKey': True,
            'metaKey': False,
            'shiftKey': False
        }

        result = handle_keyboard_shortcut(mock_event)
        assert result == 'send_message'


# class TestLoadingStateManager:
#     """Test loading state management."""

#     def setup_method(self):
#         """Set up test fixtures."""
#         self.manager = LoadingStateManager()

#     def test_start_loading_button(self):
#         """Test starting loading state for button."""
#         updates = self.manager.start_loading('test_op', 'button')
#         assert updates['interactive'] is False
#         assert 'Loading' in updates['value']

#     def test_start_loading_panel(self):
#         """Test starting loading state for panel."""
#         updates = self.manager.start_loading('test_op', 'panel')
#         assert updates['visible'] is True
#         assert updates['__type__'] == 'update'

#     def test_complete_loading_button(self):
#         """Test completing loading state for button."""
#         # Start loading
#         self.manager.start_loading('test_op', 'button')

#         # Complete loading
#         updates = self.manager.complete_loading('test_op', True)
#         assert updates['interactive'] is True
#         assert updates['value'] == ''  # Should be default text for unknown operation

#     def test_complete_loading_panel(self):
#         """Test completing loading state for panel."""
#         # Start loading
#         self.manager.start_loading('test_op', 'panel')

#         # Complete loading
#         updates = self.manager.complete_loading('test_op', True)
#         assert updates['visible'] is False
#         assert updates['__type__'] == 'update'

#     def test_complete_loading_nonexistent(self):
#         """Test completing loading for non-existent operation."""
#         updates = self.manager.complete_loading('nonexistent', True)
#         assert updates == {}

#     def test_get_loading_text_agent_build(self):
#         """Test loading text for agent build."""
#         text = self.manager._get_loading_text('agent_build')
#         assert text == 'Building...'

#     def test_get_loading_text_model_refresh(self):
#         """Test loading text for model refresh."""
#         text = self.manager._get_loading_text('model_refresh')
#         assert text == 'Refreshing...'

#     def test_get_loading_text_unknown(self):
#         """Test loading text for unknown operation."""
#         text = self.manager._get_loading_text('unknown')
#         assert text == 'Loading...'

#     def test_get_default_text_agent_build(self):
#         """Test default text for agent build."""
#         text = self.manager._get_default_text('agent_build')
#         assert text == 'Build Agent'

#     def test_get_default_text_unknown(self):
#         """Test default text for unknown operation."""
#         text = self.manager._get_default_text('unknown')
#         assert text == ''

#     @patch('app.datetime')
#     def test_start_loading_records_timestamp(self, mock_datetime):
#         """Test that start_loading records timestamp."""
#         mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
#         mock_datetime.now.return_value = mock_now

#         self.manager.start_loading('test_op', 'button')

#         assert 'test_op' in self.manager.active_operations
#         assert self.manager.active_operations['test_op']['start_time'] == mock_now

#     def test_multiple_operations(self):
#         """Test managing multiple concurrent operations."""
#         # Start multiple operations
#         self.manager.start_loading('op1', 'button')
#         self.manager.start_loading('op2', 'panel')

#         assert len(self.manager.active_operations) == 2
#         assert 'op1' in self.manager.active_operations
#         assert 'op2' in self.manager.active_operations

#         # Complete one operation
#         self.manager.complete_loading('op1', True)

#         assert len(self.manager.active_operations) == 1
#         assert 'op1' not in self.manager.active_operations
#         assert 'op2' in self.manager.active_operations

#     def test_complete_loading_success_vs_failure(self):
#         """Test that success/failure doesn't affect completion logic."""
#         self.manager.start_loading('test_op', 'button')

#         # Both success and failure should complete the operation
#         updates_success = self.manager.complete_loading('test_op', True)
#         assert updates_success['interactive'] is True

#         # Reset for failure test
#         self.manager.start_loading('test_op2', 'button')
#         updates_failure = self.manager.complete_loading('test_op2', False)
#         assert updates_failure['interactive'] is True