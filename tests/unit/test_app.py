"""Unit tests for app.py UI functions."""

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
    ThreadSafeLoadingStateManager,
    build_agent_handler,
    refresh_models_handler,
    save_session_handler,
    load_session_handler,
    new_session_handler,
    stop_generation,
    create_ui,
    health_check,
    load_initial_models,
    _format_source_display,
    _web_badge_html,
    handle_keyboard_shortcut,
)


class TestValidationFunctions:
    """Test validation functions."""

    def test_validate_agent_name_valid(self):
        """Test valid agent name."""
        result = validate_agent_name("Test Agent")
        assert result["status"] == "success"
        assert result["is_valid"] is True

    def test_validate_agent_name_empty(self):
        """Test empty agent name."""
        result = validate_agent_name("")
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_agent_name_whitespace(self):
        """Test whitespace-only agent name."""
        result = validate_agent_name("   ")
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_agent_name_too_long(self):
        """Test agent name too long."""
        long_name = "A" * 101
        result = validate_agent_name(long_name)
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_system_prompt_valid(self):
        """Test valid system prompt."""
        result = validate_system_prompt("You are a helpful assistant.")
        assert result["status"] == "success"
        assert result["is_valid"] is True

    def test_validate_system_prompt_empty(self):
        """Test empty system prompt."""
        result = validate_system_prompt("")
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_system_prompt_too_long(self):
        """Test system prompt too long."""
        long_prompt = "A" * 10001
        result = validate_system_prompt(long_prompt)
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_temperature_valid(self):
        """Test valid temperature."""
        result = validate_temperature(0.7)
        assert result["status"] == "success"
        assert result["is_valid"] is True

    def test_validate_temperature_too_low(self):
        """Test temperature too low."""
        result = validate_temperature(-0.1)
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_temperature_too_high(self):
        """Test temperature too high."""
        result = validate_temperature(2.1)
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_temperature_string_valid(self):
        """Test temperature as string valid."""
        result = validate_temperature("1.0")
        assert result["status"] == "success"
        assert result["is_valid"] is True

    def test_validate_temperature_string_invalid(self):
        """Test temperature as invalid string."""
        result = validate_temperature("abc")
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_top_p_valid(self):
        """Test valid top_p."""
        result = validate_top_p(0.9)
        assert result["status"] == "success"
        assert result["is_valid"] is True

    def test_validate_top_p_too_low(self):
        """Test top_p too low."""
        result = validate_top_p(-0.1)
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_top_p_too_high(self):
        """Test top_p too high."""
        result = validate_top_p(1.1)
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_model_selection_valid(self):
        """Test valid model selection."""
        models = [Mock(id="model1"), Mock(id="model2")]
        result = validate_model_selection("model1", models)
        assert result["status"] == "success"
        assert result["is_valid"] is True

    def test_validate_model_selection_invalid(self):
        """Test invalid model selection."""
        models = [Mock(id="model1"), Mock(id="model2")]
        result = validate_model_selection("model3", models)
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_model_selection_no_models(self):
        """Test model selection with no models."""
        result = validate_model_selection("model1", None)
        assert result["status"] == "error"
        assert result["is_valid"] is False

    def test_validate_form_field_agent_name(self):
        """Test validate_form_field for agent_name."""
        result = validate_form_field("agent_name", "Test")
        assert result["status"] == "success"

    def test_validate_form_field_system_prompt(self):
        """Test validate_form_field for system_prompt."""
        result = validate_form_field("system_prompt", "Prompt")
        assert result["status"] == "success"

    def test_validate_form_field_temperature(self):
        """Test validate_form_field for temperature."""
        result = validate_form_field("temperature", 0.8)
        assert result["status"] == "success"

    def test_validate_form_field_top_p(self):
        """Test validate_form_field for top_p."""
        result = validate_form_field("top_p", 0.9)
        assert result["status"] == "success"

    def test_validate_form_field_model(self):
        """Test validate_form_field for model."""
        models = [Mock(id="model1")]
        result = validate_form_field("model", "model1", models)
        assert result["status"] == "success"

    def test_validate_form_field_unknown(self):
        """Test validate_form_field for unknown field."""
        result = validate_form_field("unknown", "value")
        assert result["status"] == "unknown"
        assert result["is_valid"] is True


class TestLoadingStateManager:
    """Test LoadingStateManager class."""

    @pytest.mark.asyncio
    async def test_start_loading_button(self):
        """Test start_loading for button."""
        manager = ThreadSafeLoadingStateManager()
        result = await manager.start_loading("op1", "button")
        assert result["interactive"] is False
        assert "Loading..." in result["value"]

    @pytest.mark.asyncio
    async def test_start_loading_panel(self):
        """Test start_loading for panel."""
        manager = ThreadSafeLoadingStateManager()
        result = await manager.start_loading("op1", "panel")
        assert result["visible"] is True

    @pytest.mark.asyncio
    async def test_complete_loading_button(self):
        """Test complete_loading for button."""
        manager = ThreadSafeLoadingStateManager()
        await manager.start_loading("op1", "button")
        result = await manager.complete_loading("op1")
        assert result["interactive"] is True
        assert result["value"] == "Send Message"

    @pytest.mark.asyncio
    async def test_complete_loading_panel(self):
        """Test complete_loading for panel."""
        manager = ThreadSafeLoadingStateManager()
        await manager.start_loading("op1", "panel")
        result = await manager.complete_loading("op1")
        assert result["visible"] is False


class TestUtilityFunctions:
    """Test utility functions."""

    def test_format_source_display(self):
        """Test _format_source_display."""
        result = _format_source_display("Dynamic")
        assert result == "**Model catalog:** Dynamic"

    def test_web_badge_html_enabled(self):
        """Test _web_badge_html enabled."""
        result = _web_badge_html(True)
        assert "Web Tool: ON" in result
        assert "#0066cc" in result

    def test_web_badge_html_disabled(self):
        """Test _web_badge_html disabled."""
        result = _web_badge_html(False)
        assert "Web Tool: OFF" in result
        assert "#666666" in result

    def test_handle_keyboard_shortcut_send_message(self):
        """Test handle_keyboard_shortcut for send message."""
        event_data = {"key": "enter", "ctrlKey": True}
        result = handle_keyboard_shortcut(Mock(_data=event_data))
        assert result == "send_message"

    def test_handle_keyboard_shortcut_focus_input(self):
        """Test handle_keyboard_shortcut for focus input."""
        event_data = {"key": "k", "ctrlKey": True}
        result = handle_keyboard_shortcut(Mock(_data=event_data))
        assert result == "focus_input"

    def test_handle_keyboard_shortcut_refresh_models(self):
        """Test handle_keyboard_shortcut for refresh models."""
        event_data = {"key": "r", "ctrlKey": True}
        result = handle_keyboard_shortcut(Mock(_data=event_data))
        assert result == "refresh_models"

    def test_handle_keyboard_shortcut_stop_generation(self):
        """Test handle_keyboard_shortcut for stop generation."""
        event_data = {"key": "escape"}
        result = handle_keyboard_shortcut(Mock(_data=event_data))
        assert result == "stop_generation"

    def test_handle_keyboard_shortcut_none(self):
        """Test handle_keyboard_shortcut for unknown shortcut."""
        event_data = {"key": "a"}
        result = handle_keyboard_shortcut(Mock(_data=event_data))
        assert result == "none"


class TestHealthCheck:
    """Test health_check function."""

    @patch("app.getenv")
    @patch("pathlib.Path")
    @patch("httpx.get")
    def test_health_check_healthy(self, mock_get, mock_path_class, mock_getenv):
        """Test health_check when all healthy."""
        mock_getenv.return_value = "key"

        # Mock Path operations properly
        class MockPath:
            def __init__(self, path):
                self.path = path
                self._is_data = path == "data"

            def exists(self):
                return True

            def __truediv__(self, other):
                if self._is_data and other == "runs.csv":
                    mock_csv_file = Mock()
                    mock_csv_file.exists.return_value = True
                    return mock_csv_file
                return Mock()

        mock_path_class.side_effect = MockPath

        # Mock httpx response with proper status code
        class MockResponse:
            status_code = 200

        mock_get.return_value = MockResponse()

        result = health_check()
        assert result["status"] == "healthy"

        result = health_check()
        assert result["status"] == "healthy"

    @patch("app.getenv")
    @patch("app.Path")
    def test_health_check_unhealthy(self, mock_path, mock_getenv):
        """Test health_check when unhealthy."""
        mock_getenv.return_value = None
        mock_path.return_value.exists.return_value = False

        result = health_check()
        assert result["status"] == "unhealthy"


class TestLoadInitialModels:
    """Test load_initial_models function."""

    @patch("app.get_models")
    def test_load_initial_models_success(self, mock_get_models):
        """Test load_initial_models success."""
        mock_model = Mock()
        mock_model.display_name = "Test Model"
        mock_model.provider = "Test Provider"
        mock_model.id = "test/model"

        mock_get_models.return_value = ([mock_model], "dynamic", datetime.now(timezone.utc))

        choices, label, models, source = load_initial_models()
        assert len(choices) == 1
        assert "Test Model (Test Provider)" in choices[0][0]
        assert source == "dynamic"


class TestHandlerFunctions:
    """Test handler functions."""

    @patch("app.build_agent")
    def test_build_agent_handler_success(self, mock_build_agent):
        """Test build_agent_handler success."""
        from agents.models import AgentConfig

        config = AgentConfig(name="Test", model="test", system_prompt="test")
        mock_build_agent.return_value = Mock()

        result_config, message, badge, agent = build_agent_handler(
            "Test Agent", "Display (provider)", "Prompt", 0.7, 1.0, False, config, {"display": "id"}
        )
        assert "successfully" in message
        assert agent is not None

    @patch("app.build_agent")
    def test_build_agent_handler_failure(self, mock_build_agent):
        """Test build_agent_handler failure."""
        from agents.models import AgentConfig

        config = AgentConfig(name="Test", model="test", system_prompt="test")
        mock_build_agent.side_effect = Exception("Error")

        result_config, message, badge, agent = build_agent_handler(
            "Test Agent", "Display (provider)", "Prompt", 0.7, 1.0, False, config, {"display": "id"}
        )
        assert "Error" in message
        assert agent is None

    @patch("app.get_models")
    def test_refresh_models_handler_success(self, mock_get_models):
        """Test refresh_models_handler success."""
        from agents.models import AgentConfig

        mock_model = Mock()
        mock_model.display_name = "New Model"
        mock_model.provider = "Provider"
        mock_model.id = "new/model"

        mock_get_models.return_value = ([mock_model], "dynamic", datetime.now(timezone.utc))

        config = AgentConfig(name="Test", model="test", system_prompt="test")

        result = refresh_models_handler(
            "Old Display", config, [("Old", "old")]
        )
        assert len(result[0]) == 1  # choices

    @patch("services.persist.save_session")
    @patch("services.persist.list_sessions")
    def test_save_session_handler_success(self, mock_list_sessions, mock_save_session):
        """Test save_session_handler success."""
        from agents.models import AgentConfig, Session

        mock_save_session.return_value = Mock(name="saved")
        mock_list_sessions.return_value = [("session1", "path1")]

        config = AgentConfig(name="Test", model="test", system_prompt="test")
        session = Session(id="id", created_at=datetime.now(timezone.utc), agent_config=config, transcript=[], model_id="test")

        result_session, message, sessions_list, update = save_session_handler(
            "Session Name", config, [["user", "msg"]], session
        )
        assert "Saved" in message

    @patch("app.load_session")
    @patch("app.list_sessions")
    def test_load_session_handler_success(self, mock_list_sessions, mock_load_session):
        """Test load_session_handler success."""
        from agents.models import AgentConfig, Session
        from pathlib import Path

        config = AgentConfig(name="Test", model="test", system_prompt="test")
        session = Session(
            id="id",
            created_at=datetime.now(timezone.utc),
            agent_config=config,
            transcript=[
                {"role": "user", "content": "hi", "ts": "2023-01-01T00:00:00Z"},
                {"role": "assistant", "content": "hello", "ts": "2023-01-01T00:00:01Z"}
            ],
            model_id="test",
            notes="test session"
        )

        mock_path = Mock(spec=Path)
        mock_list_sessions.return_value = [("session1", mock_path)]
        mock_load_session.return_value = session

        result = load_session_handler("session1", {"test": "display"})
        assert result[0].id == "id"
        assert len(result[2]) == 1  # history

    def test_new_session_handler(self):
        """Test new_session_handler."""
        result = new_session_handler()
        assert result[0] is None
        assert "New session started" in result[1]
        assert result[2] == []  # history

    def test_stop_generation_with_event(self):
        """Test stop_generation with active event."""
        from threading import Event
        event = Event()
        result = stop_generation(event, True)
        assert "Stopping..." in result[0]
        assert event.is_set()
        assert result[1] is event
        assert result[2] is True
        assert result[3] is not None
        assert result[3]["interactive"] is False
        assert result[4] is not None
        assert result[4]["interactive"] is False

    def test_stop_generation_no_event(self):
        """Test stop_generation without active event."""
        result = stop_generation(None, False)
        assert "No generation in progress" in result[0]
        assert result[1] is None
        assert result[2] is False
        assert result[3] is None
        assert result[4] is not None
        assert result[4]["interactive"] is False

    @patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback"))
    def test_create_ui_basic(self, mock_load):
        """Test create_ui creates a Blocks instance."""
        import gradio as gr
        ui = create_ui()
        assert isinstance(ui, gr.Blocks)