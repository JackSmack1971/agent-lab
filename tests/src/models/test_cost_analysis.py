# tests/src/models/test_cost_analysis.py

"""Unit tests for cost_analysis.py module.

Tests cover all models, enums, methods, and validation logic to achieve >=90% coverage.
"""

import pytest
from typing import List

from src.models.cost_analysis import (
    AlertType,
    AlertSeverity,
    SuggestionType,
    CostTrend,
    CostAlert,
    OptimizationSuggestion,
    CostAnalysis,
)


class TestEnums:
    """Test enum classes."""

    def test_alert_type_values(self):
        """Test AlertType enum values."""
        assert AlertType.HIGH_COST.value == "high_cost"
        assert AlertType.BUDGET_WARNING.value == "budget_warning"
        assert AlertType.OPTIMIZATION_OPPORTUNITY.value == "optimization_opportunity"

    def test_alert_severity_values(self):
        """Test AlertSeverity enum values."""
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.HIGH.value == "high"

    def test_suggestion_type_values(self):
        """Test SuggestionType enum values."""
        assert SuggestionType.SWITCH_MODEL.value == "switch_model"
        assert SuggestionType.REDUCE_CONTEXT.value == "reduce_context"
        assert SuggestionType.ENABLE_CACHING.value == "enable_caching"

    def test_cost_trend_values(self):
        """Test CostTrend enum values."""
        assert CostTrend.INCREASING.value == "increasing"
        assert CostTrend.DECREASING.value == "decreasing"
        assert CostTrend.STABLE.value == "stable"


class TestCostAlert:
    """Test CostAlert model."""

    def test_valid_creation(self):
        """Test creating a valid CostAlert."""
        alert = CostAlert(
            alert_type=AlertType.HIGH_COST,
            message="Session cost is high",
            severity=AlertSeverity.MEDIUM,
            estimated_savings=1.50,
        )
        assert alert.alert_type == AlertType.HIGH_COST
        assert alert.message == "Session cost is high"
        assert alert.severity == AlertSeverity.MEDIUM
        assert alert.estimated_savings == 1.50

    def test_invalid_negative_savings(self):
        """Test creation with negative savings raises error."""
        with pytest.raises(Exception):
            CostAlert(
                alert_type=AlertType.HIGH_COST,
                message="Test",
                severity=AlertSeverity.LOW,
                estimated_savings=-1.0,
            )

    def test_optimization_opportunity_zero_savings(self):
        """Test optimization opportunity with zero savings raises error."""
        with pytest.raises(ValueError, match="positive estimated savings"):
            CostAlert(
                alert_type=AlertType.OPTIMIZATION_OPPORTUNITY,
                message="Test",
                severity=AlertSeverity.LOW,
                estimated_savings=0.0,
            )

    def test_high_severity_without_indicator(self):
        """Test high severity without visual indicator raises error to cover line 81."""
        with pytest.raises(ValueError, match="visual indicators"):
            CostAlert(
                alert_type=AlertType.HIGH_COST,
                message="High cost alert without indicator",
                severity=AlertSeverity.HIGH,
                estimated_savings=1.0,
            )

    def test_high_severity_with_correct_indicator(self):
        """Test high severity with correct visual indicator."""
        alert = CostAlert(
            alert_type=AlertType.HIGH_COST,
            message="🚨 High cost alert",
            severity=AlertSeverity.HIGH,
            estimated_savings=1.0,
        )
        assert alert.severity == AlertSeverity.HIGH

    def test_high_severity_with_high_prefix(self):
        """Test high severity with HIGH: prefix."""
        alert = CostAlert(
            alert_type=AlertType.HIGH_COST,
            message="HIGH: High cost alert",
            severity=AlertSeverity.HIGH,
            estimated_savings=1.0,
        )
        assert alert.severity == AlertSeverity.HIGH


class TestOptimizationSuggestion:
    """Test OptimizationSuggestion model."""

    def test_valid_creation(self):
        """Test creating a valid OptimizationSuggestion."""
        suggestion = OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,
            description="Switch to cheaper model",
            estimated_savings_percentage=0.5,
            estimated_savings_dollars=2.0,
            confidence_score=0.8,
        )
        assert suggestion.suggestion_type == SuggestionType.SWITCH_MODEL
        assert suggestion.description == "Switch to cheaper model"
        assert suggestion.estimated_savings_percentage == 0.5
        assert suggestion.estimated_savings_dollars == 2.0
        assert suggestion.confidence_score == 0.8

    def test_invalid_percentage_over_limit(self):
        """Test creation with percentage over 1.0 raises error."""
        with pytest.raises(Exception):
            OptimizationSuggestion(
                suggestion_type=SuggestionType.SWITCH_MODEL,
                description="Test",
                estimated_savings_percentage=1.5,
                estimated_savings_dollars=1.0,
                confidence_score=0.8,
            )

    def test_invalid_percentage_negative(self):
        """Test creation with negative percentage raises error."""
        with pytest.raises(Exception):
            OptimizationSuggestion(
                suggestion_type=SuggestionType.SWITCH_MODEL,
                description="Test",
                estimated_savings_percentage=-0.1,
                estimated_savings_dollars=1.0,
                confidence_score=0.8,
            )

    def test_invalid_dollars_negative(self):
        """Test creation with negative dollars raises error."""
        with pytest.raises(Exception):
            OptimizationSuggestion(
                suggestion_type=SuggestionType.SWITCH_MODEL,
                description="Test",
                estimated_savings_percentage=0.5,
                estimated_savings_dollars=-1.0,
                confidence_score=0.8,
            )

    def test_invalid_confidence_over_limit(self):
        """Test creation with confidence over 1.0 raises error."""
        with pytest.raises(Exception):
            OptimizationSuggestion(
                suggestion_type=SuggestionType.SWITCH_MODEL,
                description="Test",
                estimated_savings_percentage=0.5,
                estimated_savings_dollars=1.0,
                confidence_score=1.5,
            )

    def test_invalid_confidence_negative(self):
        """Test creation with negative confidence raises error."""
        with pytest.raises(Exception):
            OptimizationSuggestion(
                suggestion_type=SuggestionType.SWITCH_MODEL,
                description="Test",
                estimated_savings_percentage=0.5,
                estimated_savings_dollars=1.0,
                confidence_score=-0.1,
            )

    def test_percentage_over_90_raises_error(self):
        """Test percentage over 90% raises error to cover line 136."""
        with pytest.raises(ValueError, match="cannot exceed 90%"):
            OptimizationSuggestion(
                suggestion_type=SuggestionType.SWITCH_MODEL,
                description="Test",
                estimated_savings_percentage=0.95,
                estimated_savings_dollars=1.0,
                confidence_score=0.8,
            )

    def test_confidence_below_10_raises_error(self):
        """Test confidence below 0.1 raises error."""
        with pytest.raises(ValueError, match="must be at least 0.1"):
            OptimizationSuggestion(
                suggestion_type=SuggestionType.SWITCH_MODEL,
                description="Test",
                estimated_savings_percentage=0.5,
                estimated_savings_dollars=1.0,
                confidence_score=0.05,
            )

    def test_get_priority_score_switch_model(self):
        """Test get_priority_score for SWITCH_MODEL."""
        suggestion = OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,
            description="Test",
            estimated_savings_percentage=0.5,
            estimated_savings_dollars=1.0,
            confidence_score=0.8,
        )
        expected = 0.8 * 0.8 * 0.5  # base 0.8 * confidence 0.8 * min(percentage, 0.5)
        assert suggestion.get_priority_score() == expected

    def test_get_priority_score_reduce_context(self):
        """Test get_priority_score for REDUCE_CONTEXT."""
        suggestion = OptimizationSuggestion(
            suggestion_type=SuggestionType.REDUCE_CONTEXT,
            description="Test",
            estimated_savings_percentage=0.3,
            estimated_savings_dollars=1.0,
            confidence_score=0.9,
        )
        expected = 0.6 * 0.9 * 0.3
        assert suggestion.get_priority_score() == expected

    def test_get_priority_score_enable_caching(self):
        """Test get_priority_score for ENABLE_CACHING."""
        suggestion = OptimizationSuggestion(
            suggestion_type=SuggestionType.ENABLE_CACHING,
            description="Test",
            estimated_savings_percentage=0.2,
            estimated_savings_dollars=1.0,
            confidence_score=0.7,
        )
        expected = 0.4 * 0.7 * 0.2
        assert suggestion.get_priority_score() == expected

    def test_get_priority_score_unknown_type(self):
        """Test get_priority_score for unknown type."""
        # Mock the enum to have unknown value
        suggestion = OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,
            description="Test",
            estimated_savings_percentage=0.4,
            estimated_savings_dollars=1.0,
            confidence_score=0.6,
        )
        # Change to unknown after creation
        suggestion.suggestion_type = "unknown"  # type: ignore
        expected = 0.5 * 0.6 * 0.4
        assert suggestion.get_priority_score() == expected

    def test_get_priority_score_high_percentage_cap(self):
        """Test get_priority_score caps percentage at 0.5."""
        suggestion = OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,
            description="Test",
            estimated_savings_percentage=0.8,
            estimated_savings_dollars=1.0,
            confidence_score=0.8,
        )
        expected = 0.8 * 0.8 * 0.5
        assert suggestion.get_priority_score() == expected


class TestCostAnalysis:
    """Test CostAnalysis model."""

    def test_valid_creation(self):
        """Test creating a valid CostAnalysis."""
        analysis = CostAnalysis(
            current_cost=5.0,
            average_cost=1.0,
            cost_trend=CostTrend.INCREASING,
            alerts=[],
            suggestions=[],
        )
        assert analysis.current_cost == 5.0
        assert analysis.average_cost == 1.0
        assert analysis.cost_trend == CostTrend.INCREASING
        assert analysis.alerts == []
        assert analysis.suggestions == []

    def test_invalid_negative_current_cost(self):
        """Test creation with negative current cost raises error to cover line 202."""
        with pytest.raises(ValueError, match="cannot be negative"):
            CostAnalysis(
                current_cost=-1.0,
                average_cost=1.0,
                cost_trend=CostTrend.STABLE,
                alerts=[],
                suggestions=[],
            )

    def test_invalid_negative_average_cost(self):
        """Test creation with negative average cost raises error."""
        with pytest.raises(Exception):
            CostAnalysis(
                current_cost=5.0,
                average_cost=-1.0,
                cost_trend=CostTrend.STABLE,
                alerts=[],
                suggestions=[],
            )

    def test_too_many_alerts(self):
        """Test creation with too many alerts raises error."""
        alerts = [CostAlert(
            alert_type=AlertType.HIGH_COST,
            message="🚨 Alert",
            severity=AlertSeverity.HIGH,
            estimated_savings=1.0,
        )] * 11
        with pytest.raises(ValueError, match="more than 10 active alerts"):
            CostAnalysis(
                current_cost=5.0,
                average_cost=1.0,
                cost_trend=CostTrend.STABLE,
                alerts=alerts,
                suggestions=[],
            )

    def test_too_many_suggestions(self):
        """Test creation with too many suggestions raises error."""
        suggestions = [OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,
            description="Test",
            estimated_savings_percentage=0.5,
            estimated_savings_dollars=1.0,
            confidence_score=0.8,
        )] * 6
        with pytest.raises(ValueError, match="more than 5 optimization suggestions"):
            CostAnalysis(
                current_cost=5.0,
                average_cost=1.0,
                cost_trend=CostTrend.STABLE,
                alerts=[],
                suggestions=suggestions,
            )

    def test_get_high_priority_alerts(self):
        """Test get_high_priority_alerts."""
        high_alert = CostAlert(
            alert_type=AlertType.HIGH_COST,
            message="🚨 High alert",
            severity=AlertSeverity.HIGH,
            estimated_savings=2.0,
        )
        medium_alert = CostAlert(
            alert_type=AlertType.BUDGET_WARNING,
            message="Medium alert",
            severity=AlertSeverity.MEDIUM,
            estimated_savings=1.0,
        )
        analysis = CostAnalysis(
            current_cost=5.0,
            average_cost=1.0,
            cost_trend=CostTrend.STABLE,
            alerts=[medium_alert, high_alert],
            suggestions=[],
        )
        high_priority = analysis.get_high_priority_alerts()
        assert len(high_priority) == 1
        assert high_priority[0] == high_alert

    def test_get_high_priority_alerts_sorted_by_savings(self):
        """Test get_high_priority_alerts sorted by savings descending."""
        high_alert1 = CostAlert(
            alert_type=AlertType.HIGH_COST,
            message="🚨 High alert 1",
            severity=AlertSeverity.HIGH,
            estimated_savings=1.0,
        )
        high_alert2 = CostAlert(
            alert_type=AlertType.HIGH_COST,
            message="🚨 High alert 2",
            severity=AlertSeverity.HIGH,
            estimated_savings=3.0,
        )
        analysis = CostAnalysis(
            current_cost=5.0,
            average_cost=1.0,
            cost_trend=CostTrend.STABLE,
            alerts=[high_alert1, high_alert2],
            suggestions=[],
        )
        high_priority = analysis.get_high_priority_alerts()
        assert len(high_priority) == 2
        assert high_priority[0].estimated_savings == 3.0
        assert high_priority[1].estimated_savings == 1.0

    def test_get_top_suggestions(self):
        """Test get_top_suggestions."""
        suggestion1 = OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,
            description="Test 1",
            estimated_savings_percentage=0.5,
            estimated_savings_dollars=1.0,
            confidence_score=0.8,
        )
        suggestion2 = OptimizationSuggestion(
            suggestion_type=SuggestionType.REDUCE_CONTEXT,
            description="Test 2",
            estimated_savings_percentage=0.3,
            estimated_savings_dollars=1.0,
            confidence_score=0.9,
        )
        analysis = CostAnalysis(
            current_cost=5.0,
            average_cost=1.0,
            cost_trend=CostTrend.STABLE,
            alerts=[],
            suggestions=[suggestion1, suggestion2],
        )
        top = analysis.get_top_suggestions(1)
        assert len(top) == 1
        assert top[0] == suggestion1  # Higher priority

    def test_get_top_suggestions_default_limit(self):
        """Test get_top_suggestions with default limit."""
        suggestions = [OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,
            description=f"Test {i}",
            estimated_savings_percentage=0.5,
            estimated_savings_dollars=1.0,
            confidence_score=0.8,
        ) for i in range(5)]
        analysis = CostAnalysis(
            current_cost=5.0,
            average_cost=1.0,
            cost_trend=CostTrend.STABLE,
            alerts=[],
            suggestions=suggestions,
        )
        top = analysis.get_top_suggestions()
        assert len(top) == 3