"""Integration tests for UI components and handlers."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

import gradio as gr

from app import create_ui, send_message_streaming_fixed, stop_generation
from agents.models import AgentConfig


class TestUICreation:
    """Test UI creation and structure."""

    def test_create_ui_returns_blocks(self):
        """Test that create_ui returns a Gradio Blocks instance."""
        with patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback")):
            app = create_ui()
            assert isinstance(app, gr.Blocks)

    def test_create_ui_has_tabs(self):
        """Test that the UI has the expected tabs."""
        with patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback")):
            app = create_ui()
            # Check if tabs are present by inspecting the blocks
            # This is a basic check; more detailed inspection would require parsing the Blocks structure
            assert app is not None


class TestStreamingIntegration:
    """Integration tests for streaming functionality."""

    @pytest.mark.asyncio
    @patch("services.persist.append_run")
    @patch("app.run_agent_stream")
    @patch("app.build_agent", return_value=Mock())
    @patch("asyncio.create_task")
    @patch("asyncio.wait_for", new_callable=AsyncMock)
    @patch("asyncio.Event")
    async def test_send_message_streaming_success(self, mock_event, mock_wait, mock_create_task, mock_build_agent, mock_run_stream, mock_append_run):
        """Test send_message_streaming with successful response."""
        # Mock the streaming task
        mock_task = AsyncMock()
        mock_task.done.return_value = True
        mock_create_task.return_value = mock_task

        # Mock stream result
        mock_stream_result = Mock()
        mock_stream_result.text = "Response"
        mock_stream_result.usage = {}
        mock_stream_result.latency_ms = 100
        mock_stream_result.aborted = False
        mock_run_stream.return_value = mock_stream_result

        # Mock event
        mock_event_instance = Mock()
        mock_event_instance.is_set.return_value = False
        mock_event.return_value = mock_event_instance

        config = AgentConfig(name="Test", model="test", system_prompt="test")

        # Call the function
        generator = send_message_streaming_fixed(
            "Hello",
            [["user", "previous"]],
            config,
            "dynamic",
            Mock(),  # agent_state
            None,    # cancel_event
            False,   # is_generating
            "exp1",
            "reasoning",
            "notes",
            {"test": "display"}
        )

        # Collect all yielded values
        results = []
        async for result in generator:
            results.append(result)

        assert len(results) > 0
        # Check final result has response info
        final_result = results[-1]
        assert "Response generated" in final_result[2]

    @pytest.mark.asyncio
    async def test_stop_generation_integration(self):
        """Test stop_generation handler."""
        mock_event = Mock()
        result = stop_generation(mock_event, True)
        assert "Stopping..." in result[0]
        mock_event.set.assert_called_once()


class TestTabNavigationIntegration:
    """Integration tests for tab-based navigation and state management."""

    @patch("services.persist.save_session")
    @patch("services.persist.list_sessions")
    def test_session_save_load_integration(self, mock_list_sessions, mock_save_session):
        """Test saving and loading sessions across tabs."""
        from app import save_session_handler, load_session_handler
        from agents.models import AgentConfig, Session

        # Mock save
        mock_save_session.return_value = Mock(name="session_file")
        mock_list_sessions.return_value = [("test_session", "path")]

        config = AgentConfig(name="Test", model="test", system_prompt="test")
        history = [["Hello", "Hi"]]

        # Save session
        session, save_msg, sessions_list, update = save_session_handler(
            "Test Session", config, history, None
        )
        assert "Saved" in save_msg
        assert session is not None

        # Mock load
        loaded_session = Session(
            id="test_id",
            created_at=datetime.now(timezone.utc),
            agent_config=config,
            transcript=[
                {"role": "user", "content": "Hello", "ts": datetime.now(timezone.utc).isoformat()},
                {"role": "assistant", "content": "Hi", "ts": datetime.now(timezone.utc).isoformat()}
            ],
            model_id="test"
        )
        mock_list_sessions.return_value = [("Test Session", "path")]
        with patch("app.load_session", return_value=loaded_session):
            result = load_session_handler("Test Session", {"test": "display"})

            loaded_session_result, load_msg, loaded_history, loaded_config, name, display, prompt, temp, top_p, web, preview, metadata = result

            assert loaded_session_result is not None
            assert "Loaded" in load_msg
            assert len(loaded_history) == 1
            assert loaded_history[0] == ["Hello", "Hi"]


class TestModelRefreshIntegration:
    """Integration tests for model refresh across tabs."""

    @patch("app.get_models")
    def test_refresh_models_integration(self, mock_get_models):
        """Test model refresh updates UI state correctly."""
        from app import refresh_models_handler
        from agents.models import AgentConfig

        # Mock new models
        mock_model = Mock()
        mock_model.display_name = "New Model"
        mock_model.provider = "Provider"
        mock_model.id = "new/model"

        mock_get_models.return_value = ([mock_model], "dynamic", datetime.now(timezone.utc))

        config = AgentConfig(name="Test", model="old/model", system_prompt="test")

        result = refresh_models_handler("Old Model (Provider)", config, [("Old Model (Provider)", "old/model")])

        choices, source_label, source_enum, dropdown_update, formatted_source, updated_config, message, id_mapping = result

        assert len(choices) == 1
        assert choices[0][0] == "New Model (Provider)"
        assert "refreshed" in message.lower()
        assert updated_config.model == "old/model"  # Should keep current if not changed


class TestValidationIntegration:
    """Integration tests for form validation across UI."""

    def test_validation_integration_with_form_field(self):
        """Test that validation functions work together."""
        from app import validate_form_field, validate_agent_name, validate_temperature

        # Test agent name validation
        result = validate_form_field("agent_name", "Valid Name")
        assert result["is_valid"] is True

        result = validate_form_field("agent_name", "")
        assert result["is_valid"] is False

        # Test temperature validation
        result = validate_form_field("temperature", 1.5)
        assert result["is_valid"] is True

        result = validate_form_field("temperature", 3.0)
        assert result["is_valid"] is False


class TestLoadingStatesIntegration:
    """Integration tests for loading states in UI operations."""

    @pytest.mark.asyncio
    async def test_loading_state_manager_integration(self):
        """Test LoadingStateManager handles multiple operations."""
        from app import ThreadSafeLoadingStateManager

        manager = ThreadSafeLoadingStateManager()

        # Start multiple operations
        button_result = await manager.start_loading("build_agent", "button")
        panel_result = await manager.start_loading("refresh_models", "panel")

        assert button_result["interactive"] is False
        assert panel_result["visible"] is True

        # Complete operations
        complete_button = await manager.complete_loading("build_agent")
        complete_panel = await manager.complete_loading("refresh_models")

        assert complete_button["interactive"] is True
        assert complete_panel["visible"] is False


class TestKeyboardShortcutsIntegration:
    """Integration tests for keyboard shortcuts across tabs."""

    def test_keyboard_shortcuts_integration(self):
        """Test keyboard shortcuts work in different contexts."""
        from app import handle_keyboard_shortcut

        # Test various shortcuts
        shortcuts = [
            ({"key": "enter", "ctrlKey": True}, "send_message"),
            ({"key": "k", "ctrlKey": True}, "focus_input"),
            ({"key": "r", "ctrlKey": True}, "refresh_models"),
            ({"key": "escape"}, "stop_generation"),
            ({"key": "a"}, "none")
        ]

        for event_data, expected in shortcuts:
            result = handle_keyboard_shortcut(Mock(_data=event_data))
            assert result == expected