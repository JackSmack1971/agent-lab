"""Tests for cost analysis service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from agents.models import RunRecord
from src.models.cost_analysis import (
    AlertSeverity,
    AlertType,
    CostAlert,
    CostAnalysis,
    CostTrend,
    OptimizationSuggestion,
    SuggestionType,
)
from src.services.cost_analysis_service import (
    aggregate_costs_by_period,
    analyze_context_usage,
    analyze_cost_trend,
    analyze_costs,
    analyze_model_switch_opportunity,
    calculate_average_cost,
    calculate_caching_savings,
    calculate_context_confidence,
    calculate_context_savings,
    calculate_cost_forecast,
    calculate_session_cost,
    detect_query_patterns,
    generate_cost_alerts,
    generate_optimization_suggestions,
    get_cost_trends,
    get_session_telemetry,
    get_user_budget,
    get_user_cost_history,
    get_user_cost_history_detailed,
    get_user_from_session,
    should_suggest_caching,
    should_suggest_context_summarization,
    should_suggest_model_switch,
)


class TestCostAnalysisService:
    """Test cases for cost analysis service functions."""

    @pytest.fixture
    def sample_run_records(self) -> list[RunRecord]:
        """Create sample run records for testing."""
        return [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.03,
                experiment_id="session_123",
                task_label="chat",
                run_notes="Hello world",
                streaming=True,
                model_list_source="dynamic",
            ),
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 1, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=80,
                completion_tokens=40,
                total_tokens=120,
                latency_ms=1800,
                cost_usd=0.025,
                experiment_id="session_123",
                task_label="chat",
                run_notes="How are you?",
                streaming=True,
                model_list_source="dynamic",
            ),
        ]

    def test_calculate_session_cost(self, sample_run_records: list[RunRecord]):
        """Test session cost calculation."""
        total_cost = calculate_session_cost(sample_run_records)
        assert total_cost == 0.055  # 0.03 + 0.025

    def test_calculate_average_cost(self):
        """Test average cost calculation using median."""
        # Test with odd number of costs
        costs = [0.01, 0.02, 0.03, 0.04, 0.05]
        avg = calculate_average_cost(costs)
        assert avg == 0.03  # median

        # Test with even number of costs
        costs = [0.01, 0.02, 0.03, 0.04]
        avg = calculate_average_cost(costs)
        assert avg == 0.025  # (0.02 + 0.03) / 2

        # Test with empty list
        avg = calculate_average_cost([])
        assert avg == 0.0

    def test_analyze_cost_trend(self):
        """Test cost trend analysis."""
        # Test increasing trend
        current_cost = 0.10
        historical_costs = [0.05, 0.06, 0.07]
        trend = analyze_cost_trend(current_cost, historical_costs)
        assert trend == CostTrend.INCREASING

        # Test decreasing trend
        current_cost = 0.03
        historical_costs = [0.05, 0.06, 0.07]
        trend = analyze_cost_trend(current_cost, historical_costs)
        assert trend == CostTrend.DECREASING

        # Test stable trend
        current_cost = 0.065
        historical_costs = [0.05, 0.06, 0.07]
        trend = analyze_cost_trend(current_cost, historical_costs)
        assert trend == CostTrend.STABLE

        # Test with no historical data
        trend = analyze_cost_trend(0.10, [])
        assert trend == CostTrend.STABLE

    def test_generate_cost_alerts(self, sample_run_records: list[RunRecord]):
        """Test cost alert generation."""
        current_cost = 0.055
        average_cost = 0.01  # Very low average to trigger high cost alert

        alerts = generate_cost_alerts(current_cost, average_cost, sample_run_records)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HIGH_COST
        assert alerts[0].severity == AlertSeverity.HIGH
        assert "5x higher" in alerts[0].message

    def test_generate_cost_alerts_budget_warning(
        self, sample_run_records: list[RunRecord]
    ):
        """Test budget warning alert generation."""
        current_cost = 0.055

        with patch(
            "src.services.cost_analysis_service.get_user_budget", return_value=0.05
        ):
            alerts = generate_cost_alerts(current_cost, 0.02, sample_run_records)

            # Should have budget warning (current_cost > budget * 0.8)
            # HIGH_COST not triggered since current_cost is not > average_cost * 5
            alert_types = [alert.alert_type for alert in alerts]
            assert AlertType.BUDGET_WARNING in alert_types
            assert len(alerts) == 1

    def test_generate_optimization_suggestions_context(
        self, sample_run_records: list[RunRecord]
    ):
        """Test context summarization suggestion generation."""
        # Create records with high token usage
        high_usage_records = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=15001,
                completion_tokens=5000,
                total_tokens=20001,
                latency_ms=5000,
                cost_usd=1.50,
                experiment_id="session_123",
                task_label="chat",
                run_notes="Long message",
                streaming=True,
                model_list_source="dynamic",
            )
        ]

        suggestions = generate_optimization_suggestions(high_usage_records, 1.50)

        assert len(suggestions) >= 1
        context_suggestion = next(
            (
                s
                for s in suggestions
                if s.suggestion_type == SuggestionType.REDUCE_CONTEXT
            ),
            None,
        )
        assert context_suggestion is not None
        assert "summarize" in context_suggestion.description.lower()

    def test_generate_optimization_suggestions_model_switch(
        self, sample_run_records: list[RunRecord]
    ):
        """Test model switching suggestion generation."""
        # Create records with expensive model usage
        expensive_records = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.15,  # High cost per message
                experiment_id="session_123",
                task_label="chat",
                run_notes="Hello",
                streaming=True,
                model_list_source="dynamic",
            )
        ]

        suggestions = generate_optimization_suggestions(expensive_records, 0.15)

        model_suggestion = next(
            (
                s
                for s in suggestions
                if s.suggestion_type == SuggestionType.SWITCH_MODEL
            ),
            None,
        )
        assert model_suggestion is not None
        assert "switch" in model_suggestion.description.lower()

    def test_analyze_context_usage(self, sample_run_records: list[RunRecord]):
        """Test context usage analysis."""
        stats = analyze_context_usage(sample_run_records)

        assert stats["max_context_length"] == 150  # max of total_tokens
        assert stats["average_context_length"] == 135.0  # (150 + 120) / 2
        assert stats["current_cost"] == 0.055
        assert stats["message_count"] == 2

    def test_detect_query_patterns(self):
        """Test query pattern detection."""
        # Test with similar messages
        similar_messages = ["Hello world", "Hello there", "Hi world"]
        similarity = detect_query_patterns(similar_messages)
        assert similarity > 0.0

        # Test with no messages
        similarity = detect_query_patterns([])
        assert similarity == 0.0

        # Test with single message
        similarity = detect_query_patterns(["Hello"])
        assert similarity == 0.0

    @patch("src.services.cost_analysis_service.get_session_telemetry")
    @patch("src.services.cost_analysis_service.get_user_from_session")
    @patch("src.services.cost_analysis_service.get_user_cost_history")
    def test_analyze_costs_success(
        self,
        mock_get_history: MagicMock,
        mock_get_user: MagicMock,
        mock_get_telemetry: MagicMock,
        sample_run_records: list[RunRecord],
    ):
        """Test successful cost analysis."""
        mock_get_telemetry.return_value = sample_run_records
        mock_get_user.return_value = "test_user"
        mock_get_history.return_value = [0.01, 0.02, 0.03]

        result = analyze_costs("session_123")

        assert isinstance(result, CostAnalysis)
        assert result.current_cost == 0.055
        assert result.average_cost == 0.02  # median of [0.01, 0.02, 0.03]
        assert result.cost_trend == CostTrend.INCREASING
        assert len(result.alerts) > 0
        assert len(result.suggestions) > 0

    def test_analyze_costs_invalid_session(self):
        """Test cost analysis with invalid session ID."""
        with pytest.raises(ValueError, match="session_id must be a non-empty string"):
            analyze_costs("")

    @patch("src.services.cost_analysis_service.get_session_telemetry")
    def test_analyze_costs_no_telemetry(self, mock_get_telemetry: MagicMock):
        """Test cost analysis with no telemetry data."""
        mock_get_telemetry.return_value = []

        with pytest.raises(ValueError, match="No telemetry data found"):
            analyze_costs("session_123")

    @patch("src.services.cost_analysis_service.calculate_cost_forecast")
    @patch("src.services.cost_analysis_service.aggregate_costs_by_period")
    @patch("src.services.cost_analysis_service.get_user_cost_history_detailed")
    def test_get_cost_trends(
        self,
        mock_get_detailed: MagicMock,
        mock_aggregate: MagicMock,
        mock_forecast: MagicMock,
    ):
        """Test cost trends retrieval."""
        mock_get_detailed.return_value = {"2024-01-01": [0.10, 0.20]}
        mock_aggregate.return_value = {"2024-01-01": 0.30}
        mock_forecast.return_value = {"2024-01-02": 0.25}

        result = get_cost_trends("user_123", "daily")

        assert result["timeframe"] == "daily"
        assert result["aggregated_costs"] == {"2024-01-01": 0.30}
        assert result["forecast"] == {"2024-01-02": 0.25}
        assert result["total_periods"] == 1
        assert result["average_cost"] == 0.30

    def test_get_cost_trends_invalid_timeframe(self):
        """Test cost trends with invalid timeframe."""
        with pytest.raises(ValueError, match="timeframe must be"):
            get_cost_trends("user_123", "invalid")


class TestDataModels:
    """Test cases for data model validation."""

    def test_cost_alert_validation(self):
        """Test CostAlert model validation."""
        # Valid alert
        alert = CostAlert(
            alert_type=AlertType.HIGH_COST,
            message="🚨 High cost detected",
            severity=AlertSeverity.HIGH,
            estimated_savings=2.50,
        )
        assert alert.alert_type == AlertType.HIGH_COST

        # Invalid optimization opportunity without savings
        with pytest.raises(ValueError):
            CostAlert(
                alert_type=AlertType.OPTIMIZATION_OPPORTUNITY,
                message="Optimization opportunity",
                severity=AlertSeverity.MEDIUM,
                estimated_savings=0.0,
            )

    def test_optimization_suggestion_validation(self):
        """Test OptimizationSuggestion model validation."""
        # Valid suggestion
        suggestion = OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,
            description="Switch to cheaper model",
            estimated_savings_percentage=0.80,
            estimated_savings_dollars=1.20,
            confidence_score=0.75,
        )
        assert suggestion.confidence_score == 0.75

        # Invalid high savings percentage
        with pytest.raises(ValueError):
            OptimizationSuggestion(
                suggestion_type=SuggestionType.SWITCH_MODEL,
                description="Too much savings",
                estimated_savings_percentage=1.50,  # > 100%
                estimated_savings_dollars=1.20,
                confidence_score=0.75,
            )

        # Invalid low confidence
        with pytest.raises(ValueError):
            OptimizationSuggestion(
                suggestion_type=SuggestionType.SWITCH_MODEL,
                description="Low confidence",
                estimated_savings_percentage=0.50,
                estimated_savings_dollars=1.20,
                confidence_score=0.05,  # < 0.1
            )

    def test_cost_analysis_validation(self):
        """Test CostAnalysis model validation."""
        # Valid analysis
        analysis = CostAnalysis(
            current_cost=5.00,
            average_cost=1.00,
            cost_trend=CostTrend.INCREASING,
            alerts=[],
            suggestions=[],
        )
        assert analysis.current_cost == 5.00

        # Invalid negative cost
        with pytest.raises(ValueError):
            CostAnalysis(
                current_cost=-1.00,
                average_cost=1.00,
                cost_trend=CostTrend.STABLE,
                alerts=[],
                suggestions=[],
            )

        # Invalid negative average cost
        with pytest.raises(ValueError):
            CostAnalysis(
                current_cost=5.00,
                average_cost=-1.00,
                cost_trend=CostTrend.STABLE,
                alerts=[],
                suggestions=[],
            )

        # Too many alerts
        with pytest.raises(ValueError):
            CostAnalysis(
                current_cost=5.00,
                average_cost=1.00,
                cost_trend=CostTrend.STABLE,
                alerts=[
                    CostAlert(
                        alert_type=AlertType.HIGH_COST,
                        message="Alert",
                        severity=AlertSeverity.LOW,
                        estimated_savings=1.0,
                    )
                ]
                * 11,  # 11 alerts > 10 limit
                suggestions=[],
            )

        # Too many suggestions
        with pytest.raises(ValueError):
            CostAnalysis(
                current_cost=5.00,
                average_cost=1.00,
                cost_trend=CostTrend.STABLE,
                alerts=[],
                suggestions=[
                    OptimizationSuggestion(
                        suggestion_type=SuggestionType.SWITCH_MODEL,
                        description="Suggestion",
                        estimated_savings_percentage=0.1,
                        estimated_savings_dollars=0.1,
                        confidence_score=0.5,
                    )
                ]
                * 6,  # 6 suggestions > 5 limit
            )

    def test_cost_analysis_methods(self):
        """Test CostAnalysis helper methods."""
        alerts = [
            CostAlert(
                alert_type=AlertType.HIGH_COST,
                message="🚨 High cost",
                severity=AlertSeverity.HIGH,
                estimated_savings=2.0,
            ),
            CostAlert(
                alert_type=AlertType.BUDGET_WARNING,
                message="Budget warning",
                severity=AlertSeverity.MEDIUM,
                estimated_savings=1.0,
            ),
        ]

        suggestions = [
            OptimizationSuggestion(
                suggestion_type=SuggestionType.SWITCH_MODEL,
                description="Switch model",
                estimated_savings_percentage=0.8,
                estimated_savings_dollars=1.2,
                confidence_score=0.9,
            ),
            OptimizationSuggestion(
                suggestion_type=SuggestionType.REDUCE_CONTEXT,
                description="Reduce context",
                estimated_savings_percentage=0.5,
                estimated_savings_dollars=0.8,
                confidence_score=0.7,
            ),
        ]

        analysis = CostAnalysis(
            current_cost=5.00,
            average_cost=1.00,
            cost_trend=CostTrend.INCREASING,
            alerts=alerts,
            suggestions=suggestions,
        )

        # Test high priority alerts
        high_alerts = analysis.get_high_priority_alerts()
        assert len(high_alerts) == 1
        assert high_alerts[0].severity == AlertSeverity.HIGH

        # Test top suggestions
        top_suggestions = analysis.get_top_suggestions(1)
        assert len(top_suggestions) == 1
        assert top_suggestions[0].confidence_score == 0.9  # Highest priority score

        # Test top suggestions with limit
        top_suggestions_all = analysis.get_top_suggestions()
        assert len(top_suggestions_all) == 2

        # Test with empty suggestions
        empty_analysis = CostAnalysis(
            current_cost=1.00,
            average_cost=1.00,
            cost_trend=CostTrend.STABLE,
            alerts=[],
            suggestions=[],
        )
        empty_top = empty_analysis.get_top_suggestions()
        assert len(empty_top) == 0

        # Test with low priority suggestions
        low_priority_suggestions = [
            OptimizationSuggestion(
                suggestion_type=SuggestionType.ENABLE_CACHING,
                description="Enable caching",
                estimated_savings_percentage=0.1,
                estimated_savings_dollars=0.1,
                confidence_score=0.2,
            )
        ]
        low_analysis = CostAnalysis(
            current_cost=1.00,
            average_cost=1.00,
            cost_trend=CostTrend.STABLE,
            alerts=[],
            suggestions=low_priority_suggestions,
        )
        low_top = low_analysis.get_top_suggestions(3)
        assert len(low_top) == 1
        assert low_top[0].get_priority_score() < 0.5  # Low priority

    def test_optimization_suggestion_priority_score(self):
        """Test priority score calculation."""
        suggestion = OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,  # base_priority = 0.8
            description="Switch model",
            estimated_savings_percentage=0.6,  # min(0.6, 0.5) = 0.5
            estimated_savings_dollars=1.2,
            confidence_score=0.8,
        )

        # priority = 0.8 * 0.8 * 0.5 = 0.32
        expected_priority = 0.8 * 0.8 * 0.5
        assert suggestion.get_priority_score() == expected_priority


class TestOptimizationSuggestionHelpers:
    """Test cases for optimization suggestion helper functions."""

    def test_should_suggest_context_summarization(self):
        """Test context summarization suggestion logic."""
        # Should suggest when context is large and cost is high
        context_stats_large = {"max_context_length": 25000}
        assert should_suggest_context_summarization(context_stats_large, 2.0) is True

        # Should not suggest when context is small
        context_stats_small = {"max_context_length": 15000}
        assert should_suggest_context_summarization(context_stats_small, 2.0) is False

        # Should not suggest when cost is low
        assert should_suggest_context_summarization(context_stats_large, 0.5) is False

    def test_calculate_context_savings(self):
        """Test context savings calculation."""
        context_stats = {"max_context_length": 30000, "current_cost": 3.0}
        savings_pct, savings_dollars = calculate_context_savings(context_stats)

        # Expected: reduction = min(30000 * 0.4, 15000) = 12000
        # savings_pct = min(12000 / 30000, 0.5) = 0.4
        # savings_dollars = 3.0 * 0.4 = 1.2
        assert savings_pct == 0.4
        assert savings_dollars == 1.2

    def test_calculate_context_confidence(self):
        """Test context confidence calculation."""
        # High context length
        context_stats_high = {"max_context_length": 40000}
        confidence = calculate_context_confidence(context_stats_high)
        assert confidence == 0.9  # 0.6 + (40000/40000) * 0.3 = 0.9

        # Low context length
        context_stats_low = {"max_context_length": 10000}
        confidence = calculate_context_confidence(context_stats_low)
        assert confidence == 0.675  # 0.6 + (10000/40000) * 0.3 = 0.675

    def test_should_suggest_model_switch(self, sample_run_records):
        """Test model switching suggestion logic."""
        # Records with expensive model
        expensive_records = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.15,
                experiment_id="session_123",
                task_label="chat",
                run_notes="Hello",
                streaming=True,
                model_list_source="dynamic",
            )
        ]
        assert should_suggest_model_switch(expensive_records, 0.15) is True

        # Records with cheap model
        cheap_records = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-3.5-turbo",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.02,
                experiment_id="session_123",
                task_label="chat",
                run_notes="Hello",
                streaming=True,
                model_list_source="dynamic",
            )
        ]
        assert should_suggest_model_switch(cheap_records, 0.02) is False

    def test_analyze_model_switch_opportunity(self, sample_run_records):
        """Test model switch opportunity analysis."""
        # High cost per message
        high_cost_records = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.20,
                experiment_id="session_123",
                task_label="chat",
                run_notes="Hello",
                streaming=True,
                model_list_source="dynamic",
            )
        ]
        savings_pct, savings_dollars, target_model = analyze_model_switch_opportunity(
            high_cost_records
        )
        assert savings_pct == 0.8
        assert savings_dollars == 0.16  # 0.20 * 0.8
        assert target_model == "GPT-3.5-Turbo"

        # Low cost per message
        low_cost_records = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-3.5-turbo",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.05,
                experiment_id="session_123",
                task_label="chat",
                run_notes="Hello",
                streaming=True,
                model_list_source="dynamic",
            )
        ]
        savings_pct, savings_dollars, target_model = analyze_model_switch_opportunity(
            low_cost_records
        )
        assert savings_pct == 0.0
        assert savings_dollars == 0.0
        assert target_model == ""

    def test_should_suggest_caching(self, sample_run_records):
        """Test caching suggestion logic."""
        # Records with similar messages
        similar_records = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.03,
                experiment_id="session_123",
                task_label="chat",
                run_notes="Hello world test",
                streaming=True,
                model_list_source="dynamic",
            ),
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 1, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.03,
                experiment_id="session_123",
                task_label="chat",
                run_notes="Hello world example",
                streaming=True,
                model_list_source="dynamic",
            ),
        ]
        assert should_suggest_caching(similar_records) is True

        # Records with dissimilar messages
        dissimilar_records = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.03,
                experiment_id="session_123",
                task_label="chat",
                run_notes="Completely different topic",
                streaming=True,
                model_list_source="dynamic",
            )
        ]
        assert should_suggest_caching(dissimilar_records) is False

    def test_calculate_caching_savings(self, sample_run_records):
        """Test caching savings calculation."""
        # Mock similar messages for high similarity
        with patch(
            "src.services.cost_analysis_service.detect_query_patterns", return_value=0.8
        ):
            savings_pct, savings_dollars = calculate_caching_savings(sample_run_records)
            expected_savings_pct = min(0.8 * 0.4, 0.25)  # 0.32, but capped at 0.25
            expected_savings_dollars = 0.055 * expected_savings_pct
            assert savings_pct == expected_savings_pct
            assert savings_dollars == expected_savings_dollars


class TestDataRetrievalFunctions:
    """Test cases for data retrieval helper functions."""

    @patch("src.services.cost_analysis_service.load_recent_runs")
    def test_get_session_telemetry(self, mock_load_runs):
        """Test session telemetry retrieval."""
        mock_runs = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.03,
                experiment_id="session_123",
                task_label="chat",
                run_notes="session_123 data",
                streaming=True,
                model_list_source="dynamic",
            )
        ]
        mock_load_runs.return_value = mock_runs

        result = get_session_telemetry("session_123")
        assert len(result) == 1
        assert result[0].experiment_id == "session_123"

    def test_get_user_from_session(self):
        """Test user ID retrieval from session."""
        user_id = get_user_from_session("session_123")
        assert user_id == "default_user"

    @patch("src.services.cost_analysis_service.load_recent_runs")
    def test_get_user_cost_history(self, mock_load_runs):
        """Test user cost history retrieval."""
        mock_runs = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.10,
                experiment_id="session_1",
                task_label="chat",
                run_notes="",
                streaming=True,
                model_list_source="dynamic",
            ),
            RunRecord(
                ts=datetime(
                    2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc
                ),  # Within 5 minutes
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.05,
                experiment_id="session_1",
                task_label="chat",
                run_notes="",
                streaming=True,
                model_list_source="dynamic",
            ),
        ]
        mock_load_runs.return_value = mock_runs

        history = get_user_cost_history("user_123")
        assert len(history) == 1  # One conversation
        assert history[0] == 0.15  # 0.10 + 0.05

    def test_get_user_budget(self):
        """Test user budget retrieval."""
        budget = get_user_budget()
        assert budget is None


class TestTrendAnalysisFunctions:
    """Test cases for trend analysis functions."""

    @patch("src.services.cost_analysis_service.load_recent_runs")
    def test_get_user_cost_history_detailed_daily(self, mock_load_runs):
        """Test detailed cost history for daily timeframe."""
        mock_runs = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.10,
                experiment_id="session_1",
                task_label="chat",
                run_notes="",
                streaming=True,
                model_list_source="dynamic",
            )
        ]
        mock_load_runs.return_value = mock_runs

        history = get_user_cost_history_detailed("user_123", "daily")
        assert "2024-01-01" in history
        assert history["2024-01-01"] == [0.10]

    @patch("src.services.cost_analysis_service.load_recent_runs")
    def test_get_user_cost_history_detailed_weekly(self, mock_load_runs):
        """Test detailed cost history for weekly timeframe."""
        mock_runs = [
            RunRecord(
                ts=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),  # Monday
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.10,
                experiment_id="session_1",
                task_label="chat",
                run_notes="",
                streaming=True,
                model_list_source="dynamic",
            )
        ]
        mock_load_runs.return_value = mock_runs

        history = get_user_cost_history_detailed("user_123", "weekly")
        # Should have week start date
        week_start = datetime(2024, 1, 1).date() - timedelta(days=0)  # Already Monday
        expected_key = week_start.isoformat()
        assert expected_key in history

    @patch("src.services.cost_analysis_service.load_recent_runs")
    def test_get_user_cost_history_detailed_monthly(self, mock_load_runs):
        """Test detailed cost history for monthly timeframe."""
        mock_runs = [
            RunRecord(
                ts=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                agent_name="TestAgent",
                model="openai/gpt-4",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=2000,
                cost_usd=0.10,
                experiment_id="session_1",
                task_label="chat",
                run_notes="",
                streaming=True,
                model_list_source="dynamic",
            )
        ]
        mock_load_runs.return_value = mock_runs

        history = get_user_cost_history_detailed("user_123", "monthly")
        assert "2024-01" in history
        assert history["2024-01"] == [0.10]

    def test_aggregate_costs_by_period(self):
        """Test cost aggregation by period."""
        historical_data = {"2024-01-01": [0.10, 0.20], "2024-01-02": [0.30]}
        aggregated = aggregate_costs_by_period(historical_data, "daily")
        assert aggregated["2024-01-01"] == 0.30  # 0.10 + 0.20
        assert aggregated["2024-01-02"] == 0.30

    def test_calculate_cost_forecast(self):
        """Test cost forecast calculation."""
        aggregated_costs = {"2024-01-01": 1.0, "2024-01-02": 1.2, "2024-01-03": 1.1}
        forecast = calculate_cost_forecast(aggregated_costs)

        # Simple moving average forecast
        expected_forecast = sum(aggregated_costs.values()) / len(aggregated_costs)
        assert "2024-01-04" in forecast
        assert forecast["2024-01-04"] == expected_forecast
