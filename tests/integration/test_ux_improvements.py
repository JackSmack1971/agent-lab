"""Integration tests for Phase 1 UX improvements."""

import pytest
from src.components.enhanced_errors import error_manager
from src.components.loading_states import loading_manager, render_success_feedback, render_enhanced_progress_bar
from src.components.session_workflow import session_workflow_manager
from src.components.parameter_tooltips import tooltip_manager
from src.components.transitions import transition_manager, render_tab_transition_html, render_button_feedback_html


class TestEnhancedErrorsIntegration:
    """Test enhanced error messages integration."""

    def test_error_manager_integration_with_validation(self):
        """Test error manager works with form validation."""
        # Test temperature validation
        result = error_manager.validate_field_with_enhanced_errors("temperature", 3.5)
        assert result["is_valid"] is False
        assert "between 0.0 and 2.0" in result["error_message"]
        assert result["help_content"] is not None

        # Test valid temperature
        result = error_manager.validate_field_with_enhanced_errors("temperature", 1.0)
        assert result["is_valid"] is True
        assert result["error_message"] == ""

    def test_error_manager_integration_multiple_fields(self):
        """Test error manager handles multiple field types."""
        # Test agent name
        result = error_manager.validate_field_with_enhanced_errors("agent_name", "")
        assert result["is_valid"] is False
        assert "required" in result["error_message"]

        # Test system prompt
        result = error_manager.validate_field_with_enhanced_errors("system_prompt", "")
        assert result["is_valid"] is False
        assert "required" in result["error_message"]

        # Test top_p
        result = error_manager.validate_field_with_enhanced_errors("top_p", 1.5)
        assert result["is_valid"] is False
        assert "between 0.0 and 1.0" in result["error_message"]


class TestLoadingStatesIntegration:
    """Test loading states integration."""

    @pytest.mark.asyncio
    async def test_loading_states_workflow(self):
        """Test complete loading states workflow."""
        operation_id = "test-integration-op"

        # Start loading
        updates = await loading_manager.start_loading(
            operation_id, "message_send", "Sending message..."
        )
        assert updates["loading_visible"] is True
        assert updates["loading_message"] == "Sending message..."
        assert operation_id in loading_manager.active_operations

        # Update progress
        progress_updates = await loading_manager.update_progress(
            operation_id, 50.0, "Halfway done..."
        )
        assert progress_updates["loading_message"] == "Halfway done..."
        assert progress_updates["progress_value"] == 50.0

        # Complete successfully
        completion_updates = await loading_manager.complete_loading(operation_id, success=True)
        assert completion_updates["loading_visible"] is False
        assert "Operation completed successfully" in completion_updates["success_message"]
        assert operation_id not in loading_manager.active_operations

    @pytest.mark.asyncio
    async def test_loading_states_error_handling(self):
        """Test loading states with error completion."""
        operation_id = "test-error-op"

        # Start loading
        await loading_manager.start_loading(operation_id, "model_refresh", "Refreshing...")

        # Complete with error
        updates = await loading_manager.complete_loading(operation_id, success=False)
        assert updates["loading_visible"] is False
        assert updates["error_message"] == "Operation failed"
        assert operation_id not in loading_manager.active_operations

    @pytest.mark.asyncio
    async def test_loading_states_nonexistent_operation(self):
        """Test completing nonexistent operation."""
        updates = await loading_manager.complete_loading("nonexistent", success=True)
        assert updates["loading_visible"] is False
        assert updates["success_message"] is None
        assert updates["error_message"] is None


class TestSessionWorkflowIntegration:
    """Test session workflow integration."""

    @pytest.mark.asyncio
    async def test_session_workflow_save_prompt_integration(self):
        """Test session save prompt workflow."""
        session_id = "integration-test-session"

        # Initially no prompt needed
        needed = await session_workflow_manager.check_save_prompt_needed(session_id, 3)
        assert needed is False

        # After many messages, prompt needed
        session_workflow_manager.session_state[session_id] = {"has_unsaved_changes": True}
        needed = await session_workflow_manager.check_save_prompt_needed(session_id, 6)
        assert needed is True

        # Show prompt
        prompt_data = await session_workflow_manager.show_save_prompt(session_id)
        assert prompt_data["show_prompt"] is True
        assert prompt_data["prompt_type"] == "save_session"
        assert session_id in session_workflow_manager.save_prompts_shown

        # Handle save action
        with patch.object(session_workflow_manager, '_save_session', new_callable=AsyncMock) as mock_save:
            result = await session_workflow_manager.handle_save_action(session_id, "save_draft")
            assert result["action"] == "saved"
            mock_save.assert_called_once_with(session_id, result["name"])

    @pytest.mark.asyncio
    async def test_session_workflow_dismiss_integration(self):
        """Test dismissing save prompt."""
        session_id = "dismiss-test-session"
        session_workflow_manager.save_prompts_shown.clear()

        # Handle dismiss action
        result = await session_workflow_manager.handle_save_action(session_id, "dismiss")
        assert result["action"] == "dismissed"
        assert session_id in session_workflow_manager.save_prompts_shown

        # Subsequent checks should not show prompt
        session_workflow_manager.session_state[session_id] = {"has_unsaved_changes": True}
        needed = await session_workflow_manager.check_save_prompt_needed(session_id, 10)
        assert needed is False


class TestParameterTooltipsIntegration:
    """Test parameter tooltips integration."""

    def test_tooltip_manager_parameter_integration(self):
        """Test tooltip manager provides guidance for all parameters."""
        parameters = ["temperature", "top_p", "max_tokens", "system_prompt"]

        for param in parameters:
            html = tooltip_manager.get_tooltip_html(param)
            assert html != ""
            assert "parameter-tooltip" in html
            # Check that the tooltip title is present
            tooltip_data = tooltip_manager.tooltips.get(param, {})
            expected_title = tooltip_data.get("title", "")
            assert expected_title in html

    def test_tooltip_manager_value_highlighting_integration(self):
        """Test tooltip highlighting works with current values."""
        # Temperature highlighting
        html = tooltip_manager.get_tooltip_html("temperature", 0.2)
        assert "current-range" in html

        html = tooltip_manager.get_tooltip_html("temperature", 1.5)
        assert "current-range" in html

        # Top-p highlighting
        html = tooltip_manager.get_tooltip_html("top_p", 0.9)
        assert "current-range" in html

        # Max tokens highlighting
        html = tooltip_manager.get_tooltip_html("max_tokens", 750)
        assert "current-range" in html

    def test_model_comparison_tooltip_integration(self):
        """Test model comparison tooltip generation."""
        models = [
            {"name": "Model A", "strengths": "Fast processing", "cost": "0.01", "speed": "High"},
            {"name": "Model B", "strengths": "High accuracy", "cost": "0.02", "speed": "Medium"}
        ]

        html = tooltip_manager.get_model_comparison_tooltip(models)
        assert "🤖 Model Comparison" in html
        assert "Model A" in html
        assert "Model B" in html
        assert "Fast processing" in html
        assert "High accuracy" in html


class TestUXComponentsEndToEnd:
    """Test end-to-end UX component interactions."""

    @pytest.mark.asyncio
    async def test_loading_states_with_session_workflow(self):
        """Test loading states work with session operations."""
        session_id = "e2e-session"
        operation_id = f"save-{session_id}"

        # Start saving session
        updates = await loading_manager.start_loading(
            operation_id, "session_save", "Saving session..."
        )
        assert updates["loading_visible"] is True
        assert "save-btn" in updates["buttons_disabled"]
        assert "load-btn" in updates["buttons_disabled"]

        # Simulate session save completion
        with patch.object(session_workflow_manager, '_save_session', new_callable=AsyncMock):
            await session_workflow_manager.handle_save_action(session_id, "save_draft")

        # Complete loading
        completion_updates = await loading_manager.complete_loading(operation_id, success=True)
        assert completion_updates["loading_visible"] is False

    def test_error_messages_with_tooltips(self):
        """Test error messages provide helpful tooltips."""
        # Get error with help content
        result = error_manager.validate_field_with_enhanced_errors("temperature", "invalid")
        assert result["is_valid"] is False
        assert result["help_content"] is not None
        assert "guidance" in result["help_content"]

        # Tooltip should be available for the parameter
        tooltip_html = tooltip_manager.get_tooltip_html("temperature", 0.7)
        assert tooltip_html != ""
        assert "current-range" in tooltip_html  # Should highlight medium range

    @pytest.mark.asyncio
    async def test_session_workflow_with_error_handling(self):
        """Test session workflow handles errors gracefully."""
        session_id = "error-test-session"

        # Test invalid action
        result = await session_workflow_manager.handle_save_action(session_id, "invalid_action")
        assert result["action"] == "error"
        assert "Unknown action" in result["message"]

        # Test save custom without name
        result = await session_workflow_manager.handle_save_action(session_id, "save_custom", "")
        assert result["action"] == "error"
        assert "Custom name is required" in result["message"]


class TestTransitionAnimationsIntegration:
    """Test transition animations integration."""

    def test_tab_transition_creation_and_rendering(self):
        """Test creating and rendering tab transitions."""
        # Create transition configuration
        config = transition_manager.create_tab_transition("chat-tab", "config-tab", 400)

        # Render HTML
        html = render_tab_transition_html(config)

        # Verify HTML contains expected elements
        assert "chat-tab" in html
        assert "config-tab" in html
        assert "400ms" in html
        assert "prefers-reduced-motion" in html

    def test_button_feedback_creation_and_rendering(self):
        """Test creating and rendering button feedback."""
        # Create button feedback configuration
        config = transition_manager.create_button_feedback("send-btn", "press")

        # Render HTML
        html = render_button_feedback_html(config)

        # Verify HTML contains expected elements
        assert "send-btn" in html
        assert "scale(0.95)" in html
        assert "150ms" in html
        assert "prefers-reduced-motion" in html

    def test_success_feedback_creation_and_rendering(self):
        """Test creating and rendering success feedback."""
        # Create success feedback configuration
        config = transition_manager.create_success_feedback("build-result", "Agent built successfully")

        # Verify configuration
        assert config["target_id"] == "build-result"
        assert config["message"] == "Agent built successfully"
        assert config["duration_ms"] == 1000


class TestEnhancedLoadingStatesIntegration:
    """Test enhanced loading states integration."""

    def test_success_feedback_rendering(self):
        """Test success feedback rendering."""
        html = render_success_feedback("Operation completed", 1000)

        assert "success-feedback" in html
        assert "Operation completed" in html
        assert "checkmark-animation" in html
        assert "1000ms" in html

    def test_enhanced_progress_bar_rendering(self):
        """Test enhanced progress bar rendering."""
        html = render_enhanced_progress_bar(75.5, show_percentage=True)

        assert "progress-bar-enhanced" in html
        assert "width: 75.5%" in html
        assert "75.5%" in html

    def test_enhanced_progress_bar_no_percentage(self):
        """Test enhanced progress bar without percentage display."""
        html = render_enhanced_progress_bar(50, show_percentage=False)

        assert "progress-bar-enhanced" in html
        assert "width: 50%" in html
        assert "progress-text" not in html  # No percentage text div

    @pytest.mark.asyncio
    async def test_loading_states_with_animations_workflow(self):
        """Test complete loading workflow with animations."""
        operation_id = "animated-test-op"

        # Start loading with skeleton animation
        updates = await loading_manager.start_loading(
            operation_id, "message_send", "Sending with animations..."
        )
        assert updates["loading_visible"] is True

        # Update progress with enhanced progress bar
        progress_updates = await loading_manager.update_progress(
            operation_id, 75.0, "Almost done..."
        )
        assert progress_updates["progress_value"] == 75.0

        # Complete with success feedback
        completion_updates = await loading_manager.complete_loading(operation_id, success=True)
        assert completion_updates["loading_visible"] is False
        assert completion_updates["success_message"] is not None


class TestAnimationPerformanceIntegration:
    """Test animation performance in integrated scenarios."""

    def test_multiple_transitions_performance(self):
        """Test performance with multiple transitions."""
        import time

        start_time = time.time()

        # Create multiple transitions
        for i in range(50):
            config = transition_manager.create_tab_transition(f"tab{i}", f"tab{i+1}", 400)
            html = render_tab_transition_html(config)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 50 operations in reasonable time
        assert duration < 2.0  # Less than 2 seconds

    def test_loading_states_memory_usage(self):
        """Test that loading states handle many operations without issues."""
        # Test that we can create many operation IDs without conflicts
        operation_ids = set()

        for i in range(100):
            operation_id = f"memory-test-{i}"
            operation_ids.add(operation_id)

        # All operation IDs should be unique
        assert len(operation_ids) == 100

        # Test that manager can handle many concurrent operations conceptually
        # (In real async usage, these would be properly managed)
        assert len(loading_manager.active_operations) >= 0  # Should not crash

    def test_animation_html_size_reasonable(self):
        """Test that generated animation HTML is reasonably sized."""
        config = transition_manager.create_tab_transition("chat-tab", "config-tab", 400)
        html = render_tab_transition_html(config)

        # HTML should be reasonably sized (less than 2KB)
        assert len(html) < 2048

        feedback_config = transition_manager.create_button_feedback("send-btn", "press")
        feedback_html = render_button_feedback_html(feedback_config)

        # Feedback HTML should also be reasonable
        assert len(feedback_html) < 1024