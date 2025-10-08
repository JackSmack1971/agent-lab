"""Unit tests for parameter tooltips component."""

import pytest
from src.components.parameter_tooltips import (
    TooltipManager,
    create_parameter_tooltip_component,
    create_model_comparison_component,
    tooltip_manager,
    SAMPLE_MODEL_DATA
)


class TestTooltipManager:
    """Test the TooltipManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh TooltipManager instance."""
        return TooltipManager()

    def test_initialization(self, manager):
        """Test tooltip manager initialization."""
        assert isinstance(manager.tooltips, dict)
        assert isinstance(manager.active_tooltips, set)
        assert "temperature" in manager.tooltips
        assert "top_p" in manager.tooltips
        assert "max_tokens" in manager.tooltips
        assert "system_prompt" in manager.tooltips

    def test_register_tooltip(self, manager):
        """Test registering a custom tooltip."""
        custom_tooltip = {
            "title": "Custom Parameter",
            "description": "A custom parameter tooltip",
            "examples": ["example1", "example2"]
        }

        manager.register_tooltip("custom_param", custom_tooltip)

        assert "custom_param" in manager.tooltips
        assert manager.tooltips["custom_param"] == custom_tooltip

    def test_get_tooltip_html_known_parameter(self, manager):
        """Test getting tooltip HTML for known parameter."""
        html = manager.get_tooltip_html("temperature")

        assert "parameter-tooltip" in html
        assert "Temperature" in html
        assert "Controls creativity vs consistency" in html
        assert "guidance-section" in html
        assert "use-cases-section" in html
        assert "examples-section" in html

    def test_get_tooltip_html_unknown_parameter(self, manager):
        """Test getting tooltip HTML for unknown parameter."""
        html = manager.get_tooltip_html("unknown_param")
        assert html == ""

    def test_get_tooltip_html_with_current_value_temperature(self, manager):
        """Test tooltip HTML with current temperature value."""
        html = manager.get_tooltip_html("temperature", 0.2)

        assert "current-range" in html  # Should highlight low range for 0.2

    def test_get_tooltip_html_with_current_value_top_p(self, manager):
        """Test tooltip HTML with current top_p value."""
        html = manager.get_tooltip_html("top_p", 0.9)

        assert "current-range" in html  # Should highlight high range for 0.9

    def test_get_tooltip_html_with_current_value_max_tokens(self, manager):
        """Test tooltip HTML with current max_tokens value."""
        html = manager.get_tooltip_html("max_tokens", 300)

        assert "current-range" in html  # Should highlight medium range for 300

    def test_get_tooltip_html_with_invalid_value(self, manager):
        """Test tooltip HTML with invalid current value."""
        html = manager.get_tooltip_html("temperature", "invalid")

        # Should not crash and not highlight any range
        assert "parameter-tooltip" in html
        # Should not contain current-range class
        assert "current-range" not in html

    def test_get_model_comparison_tooltip(self, manager):
        """Test getting model comparison tooltip HTML."""
        models = [
            {"name": "Model A", "strengths": "Fast", "cost": "0.01", "speed": "High"},
            {"name": "Model B", "strengths": "Accurate", "cost": "0.02", "speed": "Medium"}
        ]

        html = manager.get_model_comparison_tooltip(models)

        assert "model-comparison-tooltip" in html
        assert "🤖 Model Comparison" in html
        assert "Model A" in html
        assert "Model B" in html
        assert "Fast" in html
        assert "Accurate" in html

    def test_get_model_comparison_tooltip_empty(self, manager):
        """Test model comparison tooltip with empty model list."""
        html = manager.get_model_comparison_tooltip([])

        assert "model-comparison-tooltip" in html
        assert "🤖 Model Comparison" in html
        # Should still have basic structure even with no models

    def test_get_temperature_highlight_low(self, manager):
        """Test temperature highlighting for low range."""
        assert manager._get_temperature_highlight(0.2, "low") == "current-range"
        assert manager._get_temperature_highlight(0.4, "low") == ""

    def test_get_temperature_highlight_medium(self, manager):
        """Test temperature highlighting for medium range."""
        assert manager._get_temperature_highlight(0.5, "medium") == "current-range"
        assert manager._get_temperature_highlight(0.2, "medium") == ""

    def test_get_temperature_highlight_high(self, manager):
        """Test temperature highlighting for high range."""
        assert manager._get_temperature_highlight(1.0, "high") == "current-range"
        assert manager._get_temperature_highlight(0.5, "high") == ""

    def test_get_top_p_highlight_low(self, manager):
        """Test top_p highlighting for low range."""
        assert manager._get_top_p_highlight(0.3, "low") == "current-range"
        assert manager._get_top_p_highlight(0.7, "low") == ""

    def test_get_top_p_highlight_medium(self, manager):
        """Test top_p highlighting for medium range."""
        assert manager._get_top_p_highlight(0.7, "medium") == "current-range"
        assert manager._get_top_p_highlight(0.9, "medium") == ""

    def test_get_top_p_highlight_high(self, manager):
        """Test top_p highlighting for high range."""
        assert manager._get_top_p_highlight(0.95, "high") == "current-range"
        assert manager._get_top_p_highlight(0.7, "high") == ""

    def test_get_max_tokens_highlight_short(self, manager):
        """Test max_tokens highlighting for short range."""
        assert manager._get_max_tokens_highlight(100, "short") == "current-range"
        assert manager._get_max_tokens_highlight(300, "short") == ""

    def test_get_max_tokens_highlight_medium(self, manager):
        """Test max_tokens highlighting for medium range."""
        assert manager._get_max_tokens_highlight(300, "medium") == "current-range"
        assert manager._get_max_tokens_highlight(100, "medium") == ""

    def test_get_max_tokens_highlight_long(self, manager):
        """Test max_tokens highlighting for long range."""
        assert manager._get_max_tokens_highlight(700, "long") == "current-range"
        assert manager._get_max_tokens_highlight(300, "long") == ""

    def test_get_highlight_class_for_value_none(self, manager):
        """Test highlight class with None value."""
        assert manager._get_highlight_class_for_value(None, "low", "temperature") == ""

    def test_get_highlight_class_for_value_invalid_type(self, manager):
        """Test highlight class with invalid value type."""
        assert manager._get_highlight_class_for_value("invalid", "low", "temperature") == ""

    def test_get_highlight_class_for_value_unknown_parameter(self, manager):
        """Test highlight class for unknown parameter."""
        assert manager._get_highlight_class_for_value(0.5, "low", "unknown_param") == ""


class TestComponentCreation:
    """Test component creation functions."""

    def test_create_parameter_tooltip_component(self):
        """Test creating parameter tooltip component."""
        component = create_parameter_tooltip_component("temperature")

        assert hasattr(component, 'value')
        assert component.value == ""
        assert component.elem_id == "tooltip-temperature"
        assert not component.visible
        assert component.elem_classes is not None
        assert "parameter-tooltip-component" in component.elem_classes

    def test_create_model_comparison_component(self):
        """Test creating model comparison component."""
        component = create_model_comparison_component()

        assert hasattr(component, 'value')
        assert component.value == ""
        assert component.elem_id == "model-comparison-tooltip"
        assert not component.visible
        assert component.elem_classes is not None
        assert "model-comparison-component" in component.elem_classes


class TestGlobalManager:
    """Test the global tooltip manager."""

    def test_global_manager_instance(self):
        """Test that global manager is properly instantiated."""
        assert isinstance(tooltip_manager, TooltipManager)
        assert hasattr(tooltip_manager, 'tooltips')
        assert hasattr(tooltip_manager, 'active_tooltips')

    def test_global_manager_has_default_tooltips(self):
        """Test that global manager has default tooltips loaded."""
        assert "temperature" in tooltip_manager.tooltips
        assert "top_p" in tooltip_manager.tooltips
        assert "max_tokens" in tooltip_manager.tooltips
        assert "system_prompt" in tooltip_manager.tooltips


class TestSampleData:
    """Test sample model data."""

    def test_sample_model_data_structure(self):
        """Test that sample model data has correct structure."""
        assert isinstance(SAMPLE_MODEL_DATA, list)
        assert len(SAMPLE_MODEL_DATA) == 3

        for model in SAMPLE_MODEL_DATA:
            assert "name" in model
            assert "strengths" in model
            assert "cost" in model
            assert "speed" in model

    def test_sample_model_data_values(self):
        """Test sample model data contains expected values."""
        model_names = [model["name"] for model in SAMPLE_MODEL_DATA]
        assert "GPT-4 Turbo" in model_names
        assert "Claude 3.5 Sonnet" in model_names
        assert "Gemini 1.5 Pro" in model_names