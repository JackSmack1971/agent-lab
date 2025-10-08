"""Unit tests for transitions component."""

import pytest
from src.components.transitions import (
    TransitionManager,
    render_tab_transition_html,
    render_button_feedback_html,
    render_success_feedback_html,
    transition_manager
)


class TestTransitionManager:
    """Test the TransitionManager class."""

    def test_create_tab_transition(self):
        """Test creating tab transition configuration."""
        manager = TransitionManager()

        config = manager.create_tab_transition("chat-tab", "config-tab", 400)

        assert config["type"] == "tab_transition"
        assert config["from_tab"] == "chat-tab"
        assert config["to_tab"] == "config-tab"
        assert config["duration_ms"] == 400
        assert config["animation"] == "fade"
        assert config["respect_reduced_motion"] is True

    def test_create_tab_transition_duration_clamp(self):
        """Test that tab transition duration is clamped to valid range."""
        manager = TransitionManager()

        # Test minimum clamp
        config = manager.create_tab_transition("tab1", "tab2", 200)
        assert config["duration_ms"] == 300

        # Test maximum clamp
        config = manager.create_tab_transition("tab1", "tab2", 600)
        assert config["duration_ms"] == 500

    def test_create_button_feedback(self):
        """Test creating button feedback configuration."""
        manager = TransitionManager()

        config = manager.create_button_feedback("send-btn", "press")

        assert config["type"] == "button_feedback"
        assert config["button_id"] == "send-btn"
        assert config["feedback_type"] == "press"
        assert config["duration_ms"] == 150
        assert config["animation"] == "scale"
        assert config["respect_reduced_motion"] is True

    def test_create_button_feedback_hover(self):
        """Test creating hover button feedback."""
        manager = TransitionManager()

        config = manager.create_button_feedback("send-btn", "hover")

        assert config["feedback_type"] == "hover"
        assert config["duration_ms"] == 200
        assert config["animation"] == "glow"

    def test_create_success_feedback(self):
        """Test creating success feedback configuration."""
        manager = TransitionManager()

        config = manager.create_success_feedback("target-div", "Success!")

        assert config["type"] == "success_feedback"
        assert config["target_id"] == "target-div"
        assert config["message"] == "Success!"
        assert config["duration_ms"] == 1000
        assert config["animation"] == "checkmark"
        assert config["respect_reduced_motion"] is True


class TestRenderFunctions:
    """Test rendering functions."""

    def test_render_tab_transition_html(self):
        """Test rendering tab transition HTML."""
        config = {
            "from_tab": "chat-tab",
            "to_tab": "config-tab",
            "duration_ms": 400
        }

        html = render_tab_transition_html(config)

        assert "chat-tab" in html
        assert "config-tab" in html
        assert "400ms" in html
        assert "prefers-reduced-motion" in html

    def test_render_button_feedback_html_scale(self):
        """Test rendering button feedback HTML with scale animation."""
        config = {
            "button_id": "send-btn",
            "feedback_type": "press",
            "duration_ms": 150,
            "animation": "scale"
        }

        html = render_button_feedback_html(config)

        assert "send-btn" in html
        assert "scale(0.95)" in html
        assert "150ms" in html
        assert "prefers-reduced-motion" in html

    def test_render_button_feedback_html_glow(self):
        """Test rendering button feedback HTML with glow animation."""
        config = {
            "button_id": "send-btn",
            "feedback_type": "hover",
            "duration_ms": 200,
            "animation": "glow"
        }

        html = render_button_feedback_html(config)

        assert "brightness(1.1)" in html
        assert "200ms" in html

    def test_render_success_feedback_html(self):
        """Test rendering success feedback HTML."""
        config = {
            "target_id": "success-target",
            "message": "Operation completed",
            "duration_ms": 1000
        }

        html = render_success_feedback_html(config)

        assert "success-target" in html
        assert "Operation completed" in html
        assert "checkmark-animation" in html
        assert "1000ms" in html
        assert "prefers-reduced-motion" in html


class TestPerformance:
    """Test performance aspects of transitions."""

    def test_transition_manager_singleton(self):
        """Test that transition_manager is a singleton instance."""
        assert isinstance(transition_manager, TransitionManager)

    def test_html_generation_performance(self):
        """Test that HTML generation is reasonably fast."""
        import time

        manager = TransitionManager()

        start_time = time.time()
        for _ in range(100):
            config = manager.create_tab_transition("tab1", "tab2", 400)
            html = render_tab_transition_html(config)
        end_time = time.time()

        duration = end_time - start_time
        # Should complete 100 operations in less than 1 second
        assert duration < 1.0

    def test_memory_usage_stability(self):
        """Test that repeated operations don't cause memory leaks."""
        manager = TransitionManager()

        # Create many transitions
        configs = []
        for i in range(1000):
            config = manager.create_tab_transition(f"tab{i}", f"tab{i+1}", 400)
            configs.append(config)

        # Check that manager doesn't accumulate excessive state
        # This is a basic check - in real scenarios we'd use memory profiling
        assert len(manager.active_transitions) == 0  # Should be empty after creation