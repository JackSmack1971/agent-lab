"""Pydantic data models for Cost Optimizer feature."""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class AlertType(Enum):
    """Types of cost alerts."""

    HIGH_COST = "high_cost"
    BUDGET_WARNING = "budget_warning"
    OPTIMIZATION_OPPORTUNITY = "optimization_opportunity"


class AlertSeverity(Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SuggestionType(Enum):
    """Types of optimization suggestions."""

    SWITCH_MODEL = "switch_model"
    REDUCE_CONTEXT = "reduce_context"
    ENABLE_CACHING = "enable_caching"


class CostTrend(Enum):
    """Cost trend directions."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"


class CostAlert(BaseModel):
    """Alert for cost-related issues and opportunities."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    alert_type: AlertType = Field(..., description="Type of cost alert")
    message: str = Field(..., description="Human-readable alert message")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    estimated_savings: float = Field(..., ge=0.0, description="Potential cost savings in dollars")

    def __init__(self, **data):
        """Initialize cost alert with validation.

        Args:
            **data: Model field data

        Raises:
            ValueError: If validation fails
        """
        super().__init__(**data)
        self._validate_alert_data()

    def _validate_alert_data(self) -> None:
        """Validate alert data consistency.

        Raises:
            ValueError: If alert data is invalid
        """
        if (
            self.alert_type == AlertType.OPTIMIZATION_OPPORTUNITY
            and self.estimated_savings <= 0
        ):
            raise ValueError(
                "Optimization opportunities must have positive estimated savings"
            )
        if self.severity == AlertSeverity.HIGH and not self.message.startswith(
            ("🚨", "HIGH:")
        ):
            raise ValueError(
                "High severity alerts must have appropriate visual indicators"
            )


class OptimizationSuggestion(BaseModel):
    """Suggestion for cost optimization with confidence and savings estimates."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    suggestion_type: SuggestionType = Field(..., description="Type of optimization suggestion")
    description: str = Field(..., description="Detailed suggestion description")
    estimated_savings_percentage: float = Field(
        ..., ge=0.0, le=1.0, description="Percentage cost reduction"
    )
    estimated_savings_dollars: float = Field(
        ..., ge=0.0, description="Absolute dollar savings"
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="AI confidence in suggestion (0.0-1.0)"
    )

    def __init__(self, **data):
        """Initialize suggestion with validation.

        Args:
            **data: Model field data

        Raises:
            ValueError: If validation fails
        """
        super().__init__(**data)
        self._validate_suggestion_data()

    def get_priority_score(self) -> float:
        """Calculate priority score for suggestion ordering.

        Returns:
            Float between 0.0 and 1.0 representing suggestion priority
        """
        base_priority = {
            SuggestionType.SWITCH_MODEL: 0.8,
            SuggestionType.REDUCE_CONTEXT: 0.6,
            SuggestionType.ENABLE_CACHING: 0.4,
        }.get(self.suggestion_type, 0.5)

        return base_priority * self.confidence_score * min(self.estimated_savings_percentage, 0.5)

    def _validate_suggestion_data(self) -> None:
        """Validate suggestion data consistency.

        Raises:
            ValueError: If suggestion data is invalid
        """
        if self.estimated_savings_percentage > 0.9:
            raise ValueError("Savings percentage cannot exceed 90%")
        if self.confidence_score < 0.1:
            raise ValueError("Confidence score must be at least 0.1")


class CostAnalysis(BaseModel):
    """Complete cost analysis result for a session."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_cost: float = Field(..., ge=0.0, description="Session running total cost")
    average_cost: float = Field(..., ge=0.0, description="User's historical average cost per conversation")
    cost_trend: CostTrend = Field(..., description="Cost trend direction")
    alerts: List[CostAlert] = Field(
        default_factory=list, description="Active cost alerts"
    )
    suggestions: List[OptimizationSuggestion] = Field(
        default_factory=list, description="Optimization suggestions"
    )

    def __init__(self, **data):
        """Initialize cost analysis with data validation.

        Args:
            **data: Model field data

        Raises:
            ValueError: If validation fails
        """
        super().__init__(**data)
        self._validate_cost_analysis_data()

    def get_high_priority_alerts(self) -> List[CostAlert]:
        """Get alerts sorted by severity and potential savings.

        Returns:
            List of CostAlert objects sorted by priority
        """
        return sorted(
            [alert for alert in self.alerts if alert.severity == AlertSeverity.HIGH],
            key=lambda x: x.estimated_savings,
            reverse=True
        )

    def get_top_suggestions(self, limit: int = 3) -> List[OptimizationSuggestion]:
        """Get top optimization suggestions by priority score.

        Args:
            limit: Maximum number of suggestions to return (default: 3)

        Returns:
            List of top OptimizationSuggestion objects
        """
        return sorted(
            self.suggestions,
            key=lambda x: x.get_priority_score(),
            reverse=True
        )[:limit]

    def _validate_cost_analysis_data(self) -> None:
        """Validate cost analysis data consistency.

        Raises:
            ValueError: If cost analysis data is invalid
        """
        if self.current_cost < 0:
            raise ValueError("Current cost cannot be negative")
        if len(self.alerts) > 10:
            raise ValueError("Cannot have more than 10 active alerts")
        if len(self.suggestions) > 5:
            raise ValueError("Cannot have more than 5 optimization suggestions")


if __name__ == "__main__":
    # Example usage and testing
    sample_alert = CostAlert(
        alert_type=AlertType.HIGH_COST,
        message="🚨 Current session cost is 5x higher than average",
        severity=AlertSeverity.HIGH,
        estimated_savings=2.50
    )

    sample_suggestion = OptimizationSuggestion(
        suggestion_type=SuggestionType.SWITCH_MODEL,
        description="Switch to GPT-3.5-Turbo for better cost-efficiency",
        estimated_savings_percentage=0.80,
        estimated_savings_dollars=1.20,
        confidence_score=0.75
    )

    sample_analysis = CostAnalysis(
        current_cost=3.45,
        average_cost=0.67,
        cost_trend=CostTrend.INCREASING,
        alerts=[sample_alert],
        suggestions=[sample_suggestion]
    )

    print("CostAlert:")
    print(sample_alert.model_dump())

    print("\nOptimizationSuggestion:")
    print(sample_suggestion.model_dump())
    print(f"Priority score: {sample_suggestion.get_priority_score()}")

    print("\nCostAnalysis:")
    print(sample_analysis.model_dump())
    print(f"High priority alerts: {len(sample_analysis.get_high_priority_alerts())}")
    print(f"Top suggestions: {len(sample_analysis.get_top_suggestions())}")