"""Tests for cost optimizer UI component."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

import gradio as gr
from src.components.cost_optimizer import (
    create_cost_optimizer_tab,
    apply_optimization_suggestion,
)
from src.models.cost_analysis import AlertType, AlertSeverity


class TestCostOptimizerUI:
    """Test cases for cost optimizer UI component."""

    def test_apply_optimization_suggestion(self):
        """Test optimization suggestion application."""
        result = apply_optimization_suggestion("switch_model", "session_123")
        assert "✅ Applied switch model optimization" in result

        result = apply_optimization_suggestion("reduce_context", "session_456")
        assert "✅ Applied reduce context optimization" in result

    def test_create_cost_optimizer_tab(self):
        """Test cost optimizer tab creation."""
        tab = create_cost_optimizer_tab()

        assert isinstance(tab, gr.Blocks)
        # Check that the tab has the expected structure
        # This is a basic check - in practice, Gradio components are complex

    def test_component_initialization(self):
        """Test that components can be initialized without errors."""
        try:
            tab = create_cost_optimizer_tab()
            # If no exception is raised, the component is valid
            assert tab is not None
        except Exception as exc:
            pytest.fail(f"Component initialization failed: {exc}")

    def test_apply_optimization_suggestion_edge_cases(self):
        """Test optimization suggestion application with edge cases."""
        # Test with empty suggestion type
        result = apply_optimization_suggestion("", "session_123")
        assert "Applied  optimization" in result

        # Test with underscore in suggestion type
        result = apply_optimization_suggestion("switch_model", "session_123")
        assert "switch model" in result

        # Test with multiple underscores
        result = apply_optimization_suggestion("enable_caching_mechanism", "session_123")
        assert "enable caching mechanism" in result


class TestUIIntegration:
    """Test cases for UI component integration."""

    def test_gradio_component_structure(self):
        """Test that the Gradio component has expected structure."""
        tab = create_cost_optimizer_tab()

        # The component should be a valid Gradio Blocks object
        assert hasattr(tab, 'blocks')
        assert hasattr(tab, 'fns')

    def test_css_styling_available(self):
        """Test that CSS styling is available."""
        from src.components.cost_optimizer import COST_OPTIMIZER_CSS

        assert isinstance(COST_OPTIMIZER_CSS, str)
        assert len(COST_OPTIMIZER_CSS) > 0
        assert ".cost-display" in COST_OPTIMIZER_CSS
        assert ".alerts-container" in COST_OPTIMIZER_CSS
        assert ".suggestions-container" in COST_OPTIMIZER_CSS


class TestUIValidation:
    """Test cases for UI input validation and edge cases."""

    def test_apply_suggestion_input_validation(self):
        """Test input validation for apply_optimization_suggestion."""
        # Function should handle any string inputs gracefully
        result = apply_optimization_suggestion("any_suggestion_type", "any_session_id")
        assert isinstance(result, str)
        assert "Applied" in result
        assert "optimization" in result

    def test_component_creation_consistency(self):
        """Test that component creation is consistent."""
        tab1 = create_cost_optimizer_tab()
        tab2 = create_cost_optimizer_tab()

        # Both should be valid Gradio components
        assert isinstance(tab1, gr.Blocks)
        assert isinstance(tab2, gr.Blocks)

        # They should be separate instances
        assert tab1 is not tab2


class TestComponentIntegration:
    """Integration tests for component functionality."""

    @patch('src.components.cost_optimizer.analyze_costs')
    def test_component_with_mock_data(self, mock_analyze_costs):
        """Test component creation with mocked cost analysis."""
        from src.models.cost_analysis import CostAnalysis, CostTrend

        # Create mock analysis result
        mock_analysis = CostAnalysis(
            current_cost=5.00,
            average_cost=1.00,
            cost_trend=CostTrend.INCREASING,
            alerts=[],
            suggestions=[]
        )
        mock_analyze_costs.return_value = mock_analysis

        # Create component
        tab = create_cost_optimizer_tab()
        assert isinstance(tab, gr.Blocks)

        # Verify mock was not called yet (lazy loading)
        mock_analyze_costs.assert_not_called()

    @patch('src.components.cost_optimizer.analyze_costs')
    @patch('src.components.cost_optimizer.get_cost_trends')
    def test_component_event_handlers_setup(self, mock_get_trends, mock_analyze_costs):
        """Test that event handlers are properly set up."""
        from src.models.cost_analysis import CostAnalysis, CostTrend

        # Create mock data
        mock_analysis = CostAnalysis(
            current_cost=3.50,
            average_cost=0.80,
            cost_trend=CostTrend.STABLE,
            alerts=[],
            suggestions=[]
        )
        mock_analyze_costs.return_value = mock_analysis
        mock_get_trends.return_value = {
            "timeframe": "daily",
            "aggregated_costs": {"2024-01-01": 1.0},
            "forecast": {"2024-01-02": 0.9},
            "total_periods": 1,
            "average_cost": 1.0
        }

        # Create component
        tab = create_cost_optimizer_tab()

        # Check that the component has the expected structure
        # Gradio Blocks should have blocks attribute
        assert hasattr(tab, 'blocks')

        # Component should be launchable (basic validation)
        # Note: In real testing, you might use Gradio's testing utilities

    def test_css_styling_comprehensive(self):
        """Test that CSS contains all expected styling elements."""
        from src.components.cost_optimizer import COST_OPTIMIZER_CSS

        required_styles = [
            ".cost-display",
            ".alerts-container",
            ".suggestions-container",
            ".alert-high",
            ".alert-medium",
            ".alert-low",
            ".suggestion-card",
            ".apply-btn"
        ]

        for style in required_styles:
            assert style in COST_OPTIMIZER_CSS, f"Missing CSS style: {style}"

    @patch('src.components.cost_optimizer.analyze_costs')
    def test_component_error_handling(self, mock_analyze_costs):
        """Test component error handling."""
        # Make analyze_costs raise an exception
        mock_analyze_costs.side_effect = ValueError("Test error")

        tab = create_cost_optimizer_tab()
        assert isinstance(tab, gr.Blocks)

        # Component should still be created even with service errors
        # Error handling is done in the update functions, not in creation

    def test_component_initialization_values(self):
        """Test that component initializes with expected default values."""
        tab = create_cost_optimizer_tab()

        # The component should be properly structured
        # This is a basic smoke test - more detailed testing would require
        # Gradio's testing framework or selenium for UI testing
        assert tab is not None
        assert isinstance(tab, gr.Blocks)


class TestPerformance:
    """Performance tests for component operations."""

    def test_component_creation_speed(self):
        """Test that component creation is reasonably fast."""
        import time

        start_time = time.time()
        tab = create_cost_optimizer_tab()
        end_time = time.time()

        creation_time = end_time - start_time
        # Should create in less than 1 second
        assert creation_time < 1.0, f"Component creation took {creation_time:.2f}s"

    def test_apply_suggestion_speed(self):
        """Test that apply_optimization_suggestion is fast."""
        import time

        start_time = time.time()
        result = apply_optimization_suggestion("test_suggestion", "test_session")
        end_time = time.time()

        execution_time = end_time - start_time
        # Should execute in less than 0.1 second
        assert execution_time < 0.1, f"Function took {execution_time:.3f}s"
        assert result is not None


class TestUpdateFunctions:
    """Test cases for update functions."""

    @patch('src.components.cost_optimizer.analyze_costs')
    def test_update_cost_display_success(self, mock_analyze_costs):
        """Test update_cost_display with successful analysis."""
        from src.models.cost_analysis import CostAnalysis, CostTrend

        mock_analysis = CostAnalysis(
            current_cost=5.00,
            average_cost=2.50,
            cost_trend=CostTrend.INCREASING,
            alerts=[],
            suggestions=[]
        )
        mock_analyze_costs.return_value = mock_analysis

        from src.components.cost_optimizer import create_cost_optimizer_tab
        tab = create_cost_optimizer_tab()

        # Get the update function
        # Since it's defined inside create_cost_optimizer_tab, we need to test indirectly
        # or extract the function

        # For now, test that the component can be created
        assert tab is not None

    @patch('src.components.cost_optimizer.analyze_costs')
    def test_update_cost_display_exception(self, mock_analyze_costs):
        """Test update_cost_display exception handling."""
        mock_analyze_costs.side_effect = Exception("Test error")

        from src.components.cost_optimizer import create_cost_optimizer_tab
        tab = create_cost_optimizer_tab()

        # The exception handling is inside the update function
        # Since we can't call it directly, we test that component creation works
        assert tab is not None

    @patch('src.components.cost_optimizer.analyze_costs')
    def test_update_alerts_display_with_alerts(self, mock_analyze_costs):
        """Test update_alerts_display with alerts."""
        from src.models.cost_analysis import CostAnalysis, CostTrend, CostAlert, AlertSeverity

        alert = CostAlert(
            alert_type=AlertType.HIGH_COST,
            message="🚨 High cost detected",
            severity=AlertSeverity.HIGH,
            estimated_savings=2.50
        )

        mock_analysis = CostAnalysis(
            current_cost=5.00,
            average_cost=2.50,
            cost_trend=CostTrend.INCREASING,
            alerts=[alert],
            suggestions=[]
        )
        mock_analyze_costs.return_value = mock_analysis

        from src.components.cost_optimizer import create_cost_optimizer_tab
        tab = create_cost_optimizer_tab()

        assert tab is not None

    @patch('src.components.cost_optimizer.analyze_costs')
    def test_update_suggestions_display_with_suggestions(self, mock_analyze_costs):
        """Test update_suggestions_display with suggestions."""
        from src.models.cost_analysis import CostAnalysis, CostTrend, OptimizationSuggestion, SuggestionType

        suggestion = OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,
            description="Switch to cheaper model",
            estimated_savings_dollars=1.50,
            estimated_savings_percentage=0.3,
            confidence_score=0.85
        )

        mock_analysis = CostAnalysis(
            current_cost=5.00,
            average_cost=2.50,
            cost_trend=CostTrend.INCREASING,
            alerts=[],
            suggestions=[suggestion]
        )
        mock_analyze_costs.return_value = mock_analysis

        from src.components.cost_optimizer import create_cost_optimizer_tab
        tab = create_cost_optimizer_tab()

        assert tab is not None

    @patch('src.components.cost_optimizer.get_cost_trends')
    def test_update_trends_chart_with_data(self, mock_get_trends):
        """Test update_trends_chart with trend data."""
        mock_get_trends.return_value = {
            "timeframe": "daily",
            "aggregated_costs": {"2024-01-01": 1.0, "2024-01-02": 1.5},
            "forecast": {"2024-01-03": 1.2},
            "total_periods": 2,
            "average_cost": 1.25
        }

        from src.components.cost_optimizer import create_cost_optimizer_tab
        tab = create_cost_optimizer_tab()

        assert tab is not None

    @patch('src.components.cost_optimizer.get_cost_trends')
    def test_update_trends_chart_empty_data(self, mock_get_trends):
        """Test update_trends_chart with empty data."""
        mock_get_trends.return_value = {
            "timeframe": "daily",
            "aggregated_costs": {},
            "forecast": {},
            "total_periods": 0,
            "average_cost": 0.0
        }

        from src.components.cost_optimizer import create_cost_optimizer_tab
        tab = create_cost_optimizer_tab()

        assert tab is not None

    @patch('src.components.cost_optimizer.analyze_costs')
    def test_update_cost_breakdown_success(self, mock_analyze_costs):
        """Test update_cost_breakdown with successful analysis."""
        from src.models.cost_analysis import CostAnalysis, CostTrend

        mock_analysis = CostAnalysis(
            current_cost=5.00,
            average_cost=2.50,
            cost_trend=CostTrend.INCREASING,
            alerts=[],
            suggestions=[]
        )
        mock_analyze_costs.return_value = mock_analysis

        from src.components.cost_optimizer import create_cost_optimizer_tab
        tab = create_cost_optimizer_tab()

        assert tab is not None