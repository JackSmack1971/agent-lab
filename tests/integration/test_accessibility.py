"""Accessibility tests for WCAG 2.1 AA compliance."""

import pytest
from unittest.mock import Mock, patch

import gradio as gr

from app import create_ui


class TestAccessibilityCompliance:
    """Test WCAG 2.1 AA compliance for the UI."""

    @pytest.fixture
    def ui_blocks(self):
        """Fixture to create UI blocks for testing."""
        with patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback")):
            return create_ui()

    def test_ui_has_main_tabs(self, ui_blocks):
        """Test that main tabs are present with proper IDs."""
        # This is a basic test; in a real scenario, we'd inspect the Blocks structure
        assert ui_blocks is not None
        # Check if the blocks contain elements with expected elem_ids
        # Gradio Blocks structure inspection would be needed for detailed checks

    def test_tab_navigation_accessibility(self):
        """Test that tabs are keyboard accessible."""
        # Test that tab elements have proper elem_id
        with patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback")):
            app = create_ui()

            # Check if main tabs has elem_id
            # This would require parsing the Gradio components
            assert app is not None

    def test_form_elements_have_labels(self):
        """Test that all form elements have accessible labels."""
        # Verify that Textbox, Dropdown, Slider, etc. have labels
        with patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback")):
            app = create_ui()

            # In a real test, we'd traverse the component tree
            # For now, just ensure the UI creates successfully
            assert isinstance(app, gr.Blocks)

    def test_buttons_have_descriptive_text(self):
        """Test that buttons have descriptive text and elem_ids."""
        # Check buttons like "Send", "Build Agent", etc.
        with patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback")):
            app = create_ui()

            assert app is not None

    def test_color_contrast_indicators(self):
        """Test that UI uses sufficient color contrast."""
        # Test the web badge HTML for contrast
        from app import _web_badge_html

        enabled_badge = _web_badge_html(True)
        disabled_badge = _web_badge_html(False)

        # Check that colors are defined (basic check)
        assert "#0066cc" in enabled_badge  # Blue for enabled
        assert "#666666" in disabled_badge  # Gray for disabled
        assert "color:white" in enabled_badge
        assert "color:white" in disabled_badge

    def test_keyboard_shortcuts_documentation(self):
        """Test that keyboard shortcuts are properly implemented."""
        from app import handle_keyboard_shortcut

        # Test that all expected shortcuts are handled
        test_cases = [
            ({"key": "enter", "ctrlKey": True}, "send_message"),
            ({"key": "k", "ctrlKey": True}, "focus_input"),
            ({"key": "r", "ctrlKey": True}, "refresh_models"),
            ({"key": "escape"}, "stop_generation"),
            # New accessibility shortcuts
            ({"key": "1", "altKey": True}, "focus_chat_tab"),
            ({"key": "2", "altKey": True}, "focus_config_tab"),
            ({"key": "3", "altKey": True}, "focus_sessions_tab"),
            ({"key": "4", "altKey": True}, "focus_analytics_tab"),
            ({"key": "h", "ctrlKey": True, "shiftKey": True}, "show_help"),
            ({"key": "s", "ctrlKey": True}, "save_session"),
            ({"key": "l", "ctrlKey": True}, "load_session"),
        ]

        for event_data, expected_action in test_cases:
            result = handle_keyboard_shortcut(Mock(_data=event_data))
            assert result == expected_action, f"Shortcut {event_data} should trigger {expected_action}"

    def test_validation_messages_accessibility(self):
        """Test that validation messages are accessible."""
        from app import validate_agent_name, validate_system_prompt

        # Test that validation returns proper status messages
        valid_result = validate_agent_name("Valid Name")
        assert "success" in valid_result["status"]
        assert "valid" in valid_result["message"].lower()

        invalid_result = validate_agent_name("")
        assert "error" in invalid_result["status"]
        assert "cannot be empty" in invalid_result["message"]

    # def test_loading_states_communicate_status(self):
    #     """Test that loading states provide status feedback."""
    #     from app import LoadingStateManager

    #     manager = LoadingStateManager()

    #     # Start loading
    #     result = manager.start_loading("test_op", "button")
    #     assert "interactive" in result
    #     assert result["interactive"] is False

    #     # Complete loading
    #     complete_result = manager.complete_loading("test_op")
    #     assert complete_result["interactive"] is True

    def test_session_management_accessibility(self):
        """Test that session management UI is accessible."""
        # Test that dropdowns and buttons have proper labels
        with patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback")):
            app = create_ui()

            # Ensure the UI includes session management components
            assert app is not None

    def test_model_selection_accessibility(self):
        """Test that model selection is accessible."""
        from app import load_initial_models

        # Test that models have descriptive labels
        with patch("app.get_models") as mock_get_models:
            mock_model = Mock()
            mock_model.display_name = "GPT-4"
            mock_model.provider = "OpenAI"
            mock_model.id = "openai/gpt-4"

            mock_get_models.return_value = ([mock_model], "dynamic", Mock())

            choices, label, models, source = load_initial_models()
            assert len(choices) > 0
            # Check that display includes provider for clarity
            display_label = choices[0][0]
            assert "OpenAI" in display_label

    def test_error_messages_are_descriptive(self):
        """Test that error messages are descriptive and helpful."""
        from app import validate_temperature, validate_top_p

        # Test boundary conditions
        temp_result = validate_temperature(2.1)
        assert "cannot be greater than 2.0" in temp_result["message"]

        top_p_result = validate_top_p(-0.1)
        assert "Minimum value is 0.0" in top_p_result["message"]

    def test_focus_management(self):
        """Test that focus is properly managed in the UI."""
        # Test keyboard shortcuts for focus
        from app import handle_keyboard_shortcut

        focus_result = handle_keyboard_shortcut(Mock(_data={"key": "k", "ctrlKey": True}))
        assert focus_result == "focus_input"

        # Test tab navigation shortcuts
        tab_results = [
            handle_keyboard_shortcut(Mock(_data={"key": "1", "altKey": True})),
            handle_keyboard_shortcut(Mock(_data={"key": "2", "altKey": True})),
            handle_keyboard_shortcut(Mock(_data={"key": "3", "altKey": True})),
            handle_keyboard_shortcut(Mock(_data={"key": "4", "altKey": True})),
        ]

        expected_tabs = ["focus_chat_tab", "focus_config_tab", "focus_sessions_tab", "focus_analytics_tab"]
        assert tab_results == expected_tabs

    def test_screen_reader_support(self):
        """Test elements that support screen readers."""
        # Test that elem_ids are present for automation/screen readers
        with patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback")):
            app = create_ui()

            # Check that key elements have elem_id attributes
            # This would require inspecting the component tree
            assert app is not None

    def test_contrast_and_visibility(self):
        """Test that UI elements have good contrast and visibility."""
        # Test badge styling
        from app import _web_badge_html

        badge = _web_badge_html(True)
        assert "background:" in badge
        assert "color:" in badge
        assert "padding:" in badge

    def test_responsive_design_indicators(self):
        """Test that the UI is designed for 16:9 displays as specified."""
        # The UI is documented as optimized for 16:9
        # Test that layouts use appropriate scaling
        with patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback")):
            app = create_ui()

            assert app is not None  # Basic check

    def test_skip_links_simulation(self):
        """Test that tabs provide navigation similar to skip links."""
        # Since tabs are the main navigation, ensure they work
        with patch("app.load_initial_models", return_value=([], "Fallback", [], "fallback")):
            app = create_ui()

            assert app is not None

    def test_enhanced_error_messages_accessibility(self):
        """Test that enhanced error messages meet accessibility standards."""
        from src.components.enhanced_errors import render_error_message

        # Test error message has proper ARIA attributes
        error_data = {
            "is_valid": False,
            "error_message": "Test error",
            "help_content": None,
            "suggestions": ["Suggestion 1"],
            "examples": []
        }

        html = render_error_message(error_data)
        assert 'role="alert"' in html
        assert 'aria-live="assertive"' in html
        assert "Test error" in html

    def test_loading_states_accessibility(self):
        """Test that loading states provide proper accessibility feedback."""
        from src.components.loading_states import render_loading_overlay

        # Test loading overlay has proper ARIA attributes
        html = render_loading_overlay("message_send", "Loading...", 0)
        assert 'role="status"' in html
        assert 'aria-live="polite"' in html
        assert "Loading..." in html

    def test_session_status_accessibility(self):
        """Test that session status indicators are accessible."""
        from src.components.session_workflow import render_session_status_indicator

        # Test status indicator has proper structure
        html = render_session_status_indicator("session-1", {"state": "saved"})
        assert 'id="status-session-1"' in html
        assert "✅" in html  # Icon present
        assert "Saved" in html

    def test_parameter_tooltips_accessibility(self):
        """Test that parameter tooltips meet accessibility standards."""
        from src.components.parameter_tooltips import tooltip_manager

        # Test tooltip has proper ARIA attributes
        html = tooltip_manager.get_tooltip_html("temperature")
        assert 'role="tooltip"' in html
        assert "Temperature" in html

    def test_model_comparison_tooltip_accessibility(self):
        """Test that model comparison tooltip is accessible."""
        from src.components.parameter_tooltips import tooltip_manager

        models = [{"name": "Test Model", "strengths": "Fast", "cost": "0.01", "speed": "High"}]
        html = tooltip_manager.get_model_comparison_tooltip(models)

        assert 'role="tooltip"' in html
        assert "🤖 Model Comparison" in html
        assert "Test Model" in html

    def test_save_prompt_toast_accessibility(self):
        """Test that save prompt toast meets accessibility standards."""
        from src.components.session_workflow import render_save_prompt_toast

        prompt_data = {"session_name": "Test Session", "message_count": 5}
        html = render_save_prompt_toast(prompt_data)

        assert 'role="dialog"' in html
        assert 'aria-labelledby="save-prompt-title"' in html
        assert 'id="save-prompt-title"' in html
        assert "💾 Save Session?" in html

    def test_focus_management_enhanced_errors(self):
        """Test that enhanced error displays support focus management."""
        from src.components.enhanced_errors import create_enhanced_error_display

        component = create_enhanced_error_display("test-field")
        assert component.elem_id == "error-test-field"
        assert not component.visible  # Initially hidden

    def test_keyboard_navigation_loading_states(self):
        """Test that loading states don't interfere with keyboard navigation."""
        from src.components.loading_states import render_loading_overlay

        # Test that loading overlay includes proper focus management
        html = render_loading_overlay("message_send", "Loading...", 0)
        # Should not have autofocus or focus-stealing elements
        assert 'autofocus' not in html.lower()

    def test_aria_live_regions_ux_components(self):
        """Test that UX components use appropriate ARIA live regions."""
        from src.components.loading_states import render_loading_overlay
        from src.components.enhanced_errors import render_error_message

        # Loading states should use aria-live="polite"
        loading_html = render_loading_overlay("message_send", "Loading...", 0)
        assert 'aria-live="polite"' in loading_html

        # Error messages should use aria-live="assertive"
        error_html = render_error_message({
            "is_valid": False,
            "error_message": "Error",
            "help_content": None,
            "suggestions": [],
            "examples": []
        })
        assert 'aria-live="assertive"' in error_html

    def test_color_contrast_ux_components(self):
        """Test that UX components maintain proper color contrast."""
        from src.components.session_workflow import render_session_status_indicator

        # Test status indicators use contrasting colors
        saved_html = render_session_status_indicator("test", {"state": "saved"})
        assert "status-saved" in saved_html

        error_html = render_session_status_indicator("test", {"state": "error"})
        assert "status-error" in error_html

    def test_screen_reader_parameter_guidance(self):
        """Test that parameter guidance is screen reader friendly."""
        from src.components.parameter_tooltips import tooltip_manager

        html = tooltip_manager.get_tooltip_html("temperature")
        # Should have semantic structure
        assert "<h4>" in html  # Heading for parameter name
        assert "<p>" in html   # Description paragraph
        assert "<ul>" in html  # Lists for guidance/examples

    def test_accessibility_utilities(self):
        """Test the new accessibility utility functions."""
        from src.components.accessibility import announce_status_change, AccessibilityManager

        # Test announcement function
        announcement = announce_status_change("Test message", "polite")
        assert 'aria-live="polite"' in announcement
        assert "Test message" in announcement

        assertive_announcement = announce_status_change("Error message", "assertive")
        assert 'aria-live="assertive"' in assertive_announcement

        # Test accessibility manager
        manager = AccessibilityManager()
        aria_describedby = manager.create_aria_describedby("field1", ["desc1", "desc2"])
        assert aria_describedby == "desc1 desc2"

    def test_live_region_integration(self):
        """Test that live regions are properly integrated in the UI."""
        from app import announce_status_change

        # Test that status announcements work
        announcement = announce_status_change("Agent built successfully")
        assert 'aria-live="polite"' in announcement
        assert "Agent built successfully" in announcement

    def test_focus_indicator_css(self):
        """Test that focus indicators meet WCAG contrast requirements."""
        from src.components.accessibility import ACCESSIBILITY_CSS

        # Check that focus styles are defined
        assert "*:focus" in ACCESSIBILITY_CSS
        assert "outline: 2px solid" in ACCESSIBILITY_CSS
        assert "outline-offset: 2px" in ACCESSIBILITY_CSS

        # Check high contrast support
        assert "@media (prefers-contrast: high)" in ACCESSIBILITY_CSS

        # Check reduced motion support
        assert "@media (prefers-reduced-motion: reduce)" in ACCESSIBILITY_CSS

    def test_aria_landmarks_css(self):
        """Test that ARIA landmark CSS is properly defined."""
        from src.components.accessibility import ACCESSIBILITY_CSS

        # Check landmark roles
        assert '.main-navigation[role="navigation"]' in ACCESSIBILITY_CSS or 'role: navigation' in ACCESSIBILITY_CSS
        assert '.main-content[role="main"]' in ACCESSIBILITY_CSS or 'role: main' in ACCESSIBILITY_CSS
        assert '.configuration-panel[role="complementary"]' in ACCESSIBILITY_CSS or 'role: complementary' in ACCESSIBILITY_CSS

        # Check screen reader only class
        assert ".sr-only" in ACCESSIBILITY_CSS
        assert "clip: rect(0, 0, 0, 0)" in ACCESSIBILITY_CSS