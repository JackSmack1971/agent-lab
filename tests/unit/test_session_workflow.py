"""Unit tests for session workflow component."""

import pytest
from datetime import datetime, timezone, timedelta
from src.components.session_workflow import (
    SessionWorkflowManager,
    render_session_status_indicator,
    render_session_switcher,
    format_relative_time,
    render_save_prompt_toast,
    session_workflow_manager
)


class TestSessionWorkflowManager:
    """Test the SessionWorkflowManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh SessionWorkflowManager instance."""
        return SessionWorkflowManager()

    @pytest.mark.asyncio
    async def test_check_save_prompt_needed_false_for_few_messages(self, manager):
        """Test save prompt not needed for sessions with few messages."""
        session_id = "test-session"
        result = await manager.check_save_prompt_needed(session_id, 3)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_save_prompt_needed_false_already_shown(self, manager):
        """Test save prompt not shown again for same session."""
        session_id = "test-session"
        manager.save_prompts_shown.add(session_id)

        result = await manager.check_save_prompt_needed(session_id, 10)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_save_prompt_needed_true_for_many_messages_unsaved(self, manager):
        """Test save prompt needed for sessions with many messages and unsaved changes."""
        session_id = "test-session"
        manager.session_state[session_id] = {"has_unsaved_changes": True}

        result = await manager.check_save_prompt_needed(session_id, 5)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_save_prompt_needed_false_for_saved_session(self, manager):
        """Test save prompt not needed for saved sessions."""
        session_id = "test-session"
        manager.session_state[session_id] = {"has_unsaved_changes": False}

        result = await manager.check_save_prompt_needed(session_id, 10)
        assert result is False

    @pytest.mark.asyncio
    async def test_show_save_prompt(self, manager):
        """Test showing save prompt for a session."""
        session_id = "test-session"
        manager.session_state[session_id] = {
            "name": "Test Session",
            "message_count": 8,
            "last_modified": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        }

        result = await manager.show_save_prompt(session_id)

        assert result["show_prompt"] is True
        assert result["prompt_type"] == "save_session"
        assert result["data"]["session_name"] == "Test Session"
        assert result["data"]["message_count"] == 8
        assert session_id in manager.save_prompts_shown

    @pytest.mark.asyncio
    async def test_handle_save_action_save_draft(self, manager):
        """Test handling save draft action."""
        session_id = "test-session"

        # Mock the _save_session method
        with patch.object(manager, '_save_session', new_callable=AsyncMock) as mock_save:
            result = await manager.handle_save_action(session_id, "save_draft")

            assert result["action"] == "saved"
            assert "Draft_" in result["name"]
            mock_save.assert_called_once_with(session_id, result["name"])

    @pytest.mark.asyncio
    async def test_handle_save_action_save_custom_with_name(self, manager):
        """Test handling save custom action with valid name."""
        session_id = "test-session"
        custom_name = "My Custom Session"

        with patch.object(manager, '_save_session', new_callable=AsyncMock) as mock_save:
            result = await manager.handle_save_action(session_id, "save_custom", custom_name)

            assert result["action"] == "saved"
            assert result["name"] == custom_name
            mock_save.assert_called_once_with(session_id, custom_name)

    @pytest.mark.asyncio
    async def test_handle_save_action_save_custom_empty_name(self, manager):
        """Test handling save custom action with empty name."""
        session_id = "test-session"

        result = await manager.handle_save_action(session_id, "save_custom", "")

        assert result["action"] == "error"
        assert result["message"] == "Custom name is required"

    @pytest.mark.asyncio
    async def test_handle_save_action_dismiss(self, manager):
        """Test handling dismiss action."""
        session_id = "test-session"

        result = await manager.handle_save_action(session_id, "dismiss")

        assert result["action"] == "dismissed"
        assert session_id in manager.save_prompts_shown

    @pytest.mark.asyncio
    async def test_handle_save_action_unknown(self, manager):
        """Test handling unknown action."""
        session_id = "test-session"

        result = await manager.handle_save_action(session_id, "unknown_action")

        assert result["action"] == "error"
        assert result["message"] == "Unknown action"

    @pytest.mark.asyncio
    async def test_get_session_state_existing(self, manager):
        """Test getting state for existing session."""
        session_id = "test-session"
        manager.session_state[session_id] = {"has_unsaved_changes": False}

        result = await manager._get_session_state(session_id)
        assert result["has_unsaved_changes"] is False

    @pytest.mark.asyncio
    async def test_get_session_state_nonexistent(self, manager):
        """Test getting state for nonexistent session."""
        session_id = "nonexistent"

        result = await manager._get_session_state(session_id)
        assert result["has_unsaved_changes"] is True

    @pytest.mark.asyncio
    async def test_get_session_info_existing(self, manager):
        """Test getting info for existing session."""
        session_id = "test-session"
        test_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        manager.session_state[session_id] = {
            "name": "Test Session",
            "message_count": 5,
            "last_modified": test_time
        }

        result = await manager._get_session_info(session_id)
        assert result["name"] == "Test Session"
        assert result["message_count"] == 5
        assert result["last_modified"] == test_time

    @pytest.mark.asyncio
    async def test_get_session_info_nonexistent(self, manager):
        """Test getting info for nonexistent session."""
        session_id = "nonexistent"

        result = await manager._get_session_info(session_id)
        assert result["name"] == f"Session {session_id[:8]}"
        assert result["message_count"] == 0
        assert isinstance(result["last_modified"], datetime)

    @pytest.mark.asyncio
    async def test_save_session_existing(self, manager):
        """Test saving existing session."""
        session_id = "test-session"
        name = "Saved Session"
        initial_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        manager.session_state[session_id] = {
            "has_unsaved_changes": True,
            "name": "Old Name",
            "last_modified": initial_time
        }

        await manager._save_session(session_id, name)

        state = manager.session_state[session_id]
        assert state["has_unsaved_changes"] is False
        assert state["name"] == name
        assert state["last_modified"] > initial_time

    @pytest.mark.asyncio
    async def test_save_session_nonexistent(self, manager):
        """Test saving nonexistent session."""
        session_id = "nonexistent"
        name = "New Session"

        await manager._save_session(session_id, name)

        # Should not crash, but state remains unchanged
        assert session_id not in manager.session_state


class TestRenderSessionStatusIndicator:
    """Test the render_session_status_indicator function."""

    def test_render_saved_status(self):
        """Test rendering saved status."""
        status = {"state": "saved", "last_modified": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}
        html = render_session_status_indicator("session-1", status)

        assert "✅" in html
        assert "status-saved" in html
        assert "Saved" in html

    def test_render_unsaved_status(self):
        """Test rendering unsaved status."""
        status = {"state": "unsaved"}
        html = render_session_status_indicator("session-1", status)

        assert "🟠" in html
        assert "status-unsaved" in html
        assert "Unsaved changes" in html

    def test_render_saving_status(self):
        """Test rendering saving status."""
        status = {"state": "saving"}
        html = render_session_status_indicator("session-1", status)

        assert "⏳" in html
        assert "status-saving" in html
        assert "Saving..." in html

    def test_render_error_status(self):
        """Test rendering error status."""
        status = {"state": "error"}
        html = render_session_status_indicator("session-1", status)

        assert "❌" in html
        assert "status-error" in html
        assert "Save failed" in html

    def test_render_unknown_status(self):
        """Test rendering unknown status."""
        status = {"state": "unknown"}
        html = render_session_status_indicator("session-1", status)

        assert "❓" in html
        assert "status-unknown" in html
        assert "Unknown" in html

    def test_render_with_last_modified(self):
        """Test rendering with last modified time."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        status = {"state": "saved", "last_modified": past_time}
        html = render_session_status_indicator("session-1", status)

        assert "2 hours ago" in html


class TestRenderSessionSwitcher:
    """Test the render_session_switcher function."""

    def test_render_with_current_session(self):
        """Test rendering switcher with current session."""
        current_id = "session-1"
        sessions = [
            {"id": "session-1", "name": "Current Session", "last_modified": datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)},
            {"id": "session-2", "name": "Other Session", "last_modified": datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)}
        ]

        html = render_session_switcher(current_id, sessions)

        assert "Current Session:" in html
        assert "Current Session" in html
        assert "session-1" in html
        assert "session-2" in html
        assert "selected" in html

    def test_render_empty_sessions(self):
        """Test rendering switcher with no sessions."""
        html = render_session_switcher("", [])

        assert "Current Session" in html
        assert "Switch Session..." in html


class TestFormatRelativeTime:
    """Test the format_relative_time function."""

    def test_format_just_now(self):
        """Test formatting very recent time."""
        now = datetime.now(timezone.utc)
        result = format_relative_time(now)
        assert result == "just now"

    def test_format_minutes_ago(self):
        """Test formatting minutes ago."""
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        result = format_relative_time(past)
        assert "5 minutes ago" in result

    def test_format_hours_ago(self):
        """Test formatting hours ago."""
        past = datetime.now(timezone.utc) - timedelta(hours=3)
        result = format_relative_time(past)
        assert "3 hours ago" in result

    def test_format_days_ago(self):
        """Test formatting days ago."""
        past = datetime.now(timezone.utc) - timedelta(days=2)
        result = format_relative_time(past)
        assert "2 days ago" in result

    def test_format_weeks_ago(self):
        """Test formatting weeks ago."""
        past = datetime.now(timezone.utc) - timedelta(days=10)
        result = format_relative_time(past)
        # Should be formatted as month day
        assert len(result) <= 6  # "Jan 01" format

    def test_format_non_datetime(self):
        """Test formatting non-datetime input."""
        result = format_relative_time("not a datetime")
        assert result == "recently"


class TestRenderSavePromptToast:
    """Test the render_save_prompt_toast function."""

    def test_render_basic_toast(self):
        """Test rendering basic save prompt toast."""
        prompt_data = {
            "session_name": "Test Session",
            "message_count": 7
        }

        html = render_save_prompt_toast(prompt_data)

        assert "💾 Save Session?" in html
        assert "Test Session" in html
        assert "7 messages" in html
        assert "saveAsDraft" in html
        assert "saveWithCustomName" in html
        assert "dismissSavePrompt" in html

    def test_render_toast_missing_data(self):
        """Test rendering toast with missing data."""
        prompt_data = {}

        html = render_save_prompt_toast(prompt_data)

        assert "Untitled Session" in html
        assert "0 messages" in html


class TestGlobalManager:
    """Test the global session workflow manager."""

    def test_global_manager_instance(self):
        """Test that global manager is properly instantiated."""
        assert isinstance(session_workflow_manager, SessionWorkflowManager)
        assert hasattr(session_workflow_manager, 'session_state')
        assert hasattr(session_workflow_manager, 'save_prompts_shown')