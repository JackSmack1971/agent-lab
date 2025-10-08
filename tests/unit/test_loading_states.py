"""Unit tests for loading states component."""

import pytest
import asyncio
from src.components.loading_states import (
    LoadingStateManager,
    render_loading_overlay,
    render_skeleton_loader,
    render_success_feedback,
    render_enhanced_progress_bar,
    get_animation_for_operation,
    is_cancellable,
    loading_manager
)


class TestLoadingStateManager:
    """Test the LoadingStateManager class."""

    @pytest.mark.asyncio
    async def test_start_loading(self):
        """Test starting a loading operation."""
        manager = LoadingStateManager()

        updates = await manager.start_loading("test_op", "message_send", "Testing...")

        assert updates["loading_visible"] is True
        assert updates["loading_message"] == "Testing..."
        assert "buttons_disabled" in updates

        # Check that operation is tracked
        assert "test_op" in manager.active_operations

    @pytest.mark.asyncio
    async def test_complete_loading_success(self):
        """Test completing a loading operation successfully."""
        manager = LoadingStateManager()
        await manager.start_loading("test_op", "message_send", "Testing...")

        updates = await manager.complete_loading("test_op", success=True)

        assert updates["loading_visible"] is False
        assert updates["success_message"] == "Operation completed successfully"
        assert "test_op" not in manager.active_operations

    @pytest.mark.asyncio
    async def test_complete_loading_failure(self):
        """Test completing a loading operation with failure."""
        manager = LoadingStateManager()
        await manager.start_loading("test_op", "message_send", "Testing...")

        updates = await manager.complete_loading("test_op", success=False)

        assert updates["loading_visible"] is False
        assert updates["error_message"] == "Operation failed"
        assert "test_op" not in manager.active_operations

    @pytest.mark.asyncio
    async def test_complete_nonexistent_operation(self):
        """Test completing a non-existent operation."""
        manager = LoadingStateManager()

        updates = await manager.complete_loading("nonexistent", success=True)

        assert updates["loading_visible"] is False

    @pytest.mark.asyncio
    async def test_update_progress(self):
        """Test updating progress for an operation."""
        manager = LoadingStateManager()
        await manager.start_loading("test_op", "model_refresh", "Refreshing...")

        updates = await manager.update_progress("test_op", 50.0, "Halfway done...")

        assert updates["loading_message"] == "Halfway done..."
        assert updates["progress_value"] == 50.0

    def test_should_show_progress(self):
        """Test progress bar visibility logic."""
        manager = LoadingStateManager()

        assert manager._should_show_progress("session_load") is True
        assert manager._should_show_progress("model_refresh") is True
        assert manager._should_show_progress("message_send") is True
        assert manager._should_show_progress("session_save") is False

    def test_get_buttons_to_disable(self):
        """Test button disabling logic."""
        manager = LoadingStateManager()

        disabled = manager._get_buttons_to_disable("message_send")
        assert "send-btn" in disabled
        assert "stop-btn" in disabled

        disabled = manager._get_buttons_to_disable("unknown_op")
        assert disabled == []


class TestRenderFunctions:
    """Test rendering functions."""

    def test_render_loading_overlay_spinner(self):
        """Test rendering loading overlay with spinner."""
        html = render_loading_overlay("session_save", "Saving...", 0)
        assert "loading-overlay" in html
        assert "loading-spinner" in html
        assert "Saving..." in html

    def test_render_loading_overlay_progress(self):
        """Test rendering loading overlay with progress bar."""
        html = render_loading_overlay("model_refresh", "Refreshing...", 75)
        assert "progress-bar" in html
        assert "width: 75%" in html

    def test_render_loading_overlay_cancellable(self):
        """Test rendering cancellable loading overlay."""
        html = render_loading_overlay("message_send", "Sending...", 0)
        assert "cancel-btn" in html

    def test_render_skeleton_loader_message_send(self):
        """Test rendering skeleton for message send."""
        html = render_skeleton_loader("message_send")
        assert "skeleton-chat" in html
        assert "skeleton-line short" in html
        assert "skeleton-line medium" in html

    def test_render_skeleton_loader_session_load(self):
        """Test rendering skeleton for session load."""
        html = render_skeleton_loader("session_load")
        assert "skeleton-session" in html
        assert "skeleton-line wide" in html

    def test_get_animation_for_operation(self):
        """Test animation type selection."""
        assert get_animation_for_operation("message_send") == "skeleton"
        assert get_animation_for_operation("model_refresh") == "progress"
        assert get_animation_for_operation("session_save") == "spinner"
        assert get_animation_for_operation("unknown") == "spinner"

    def test_is_cancellable(self):
        """Test cancellable operation detection."""
        assert is_cancellable("message_send") is True
        assert is_cancellable("model_refresh") is True
        assert is_cancellable("session_save") is False
        assert is_cancellable("unknown") is False

    def test_render_success_feedback(self):
        """Test rendering success feedback animation."""
        html = render_success_feedback("Agent built successfully", 1000)
        assert "success-feedback" in html
        assert "Agent built successfully" in html
        assert "checkmark-animation" in html
        assert "1000" in html  # duration

    def test_render_enhanced_progress_bar(self):
        """Test rendering enhanced progress bar."""
        html = render_enhanced_progress_bar(75.5, show_percentage=True)
        assert "progress-bar-enhanced" in html
        assert "width: 75.5%" in html
        assert "75.5%" in html  # percentage text

    def test_render_enhanced_progress_bar_no_percentage(self):
        """Test rendering enhanced progress bar without percentage."""
        html = render_enhanced_progress_bar(50, show_percentage=False)
        assert "progress-bar-enhanced" in html
        assert "width: 50%" in html
        assert "progress-text" not in html  # no percentage text div

    def test_render_skeleton_loader_model_refresh(self):
        """Test rendering skeleton for model refresh."""
        html = render_skeleton_loader("model_refresh")
        assert "skeleton-models" in html
        assert "skeleton-model-card" in html

    def test_render_skeleton_loader_with_avatar(self):
        """Test that message send skeleton includes avatar."""
        html = render_skeleton_loader("message_send")
        assert "skeleton-avatar" in html
        assert "skeleton-content" in html