"""Cost analysis service for real-time cost monitoring and optimization suggestions."""

from __future__ import annotations

import csv
import logging
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

from agents.models import RunRecord
from services.persist import CSV_PATH, load_recent_runs
from src.models.cost_analysis import (
    AlertSeverity,
    AlertType,
    CostAlert,
    CostAnalysis,
    CostTrend,
    OptimizationSuggestion,
    SuggestionType,
)

logger = logging.getLogger(__name__)


def analyze_costs(session_id: str) -> CostAnalysis:
    """Analyze costs for a session and generate alerts/suggestions.

    Args:
        session_id: Unique session identifier

    Returns:
        CostAnalysis with current costs, alerts, and suggestions

    Raises:
        ValueError: If session_id is invalid or data unavailable
    """
    if not session_id or not isinstance(session_id, str):
        raise ValueError("session_id must be a non-empty string")

    # Retrieve telemetry data for session
    telemetry_data = get_session_telemetry(session_id)
    if not telemetry_data:
        raise ValueError(f"No telemetry data found for session {session_id}")

    # Calculate current session cost
    current_cost = calculate_session_cost(telemetry_data)

    # Get user's historical cost data
    user_id = get_user_from_session(session_id)
    historical_costs = get_user_cost_history(user_id)
    average_cost = calculate_average_cost(historical_costs)

    # Determine cost trend
    cost_trend = analyze_cost_trend(current_cost, historical_costs)

    # Generate alerts
    alerts = generate_cost_alerts(current_cost, average_cost, telemetry_data)

    # Generate optimization suggestions
    suggestions = generate_optimization_suggestions(telemetry_data, current_cost)

    return CostAnalysis(
        current_cost=current_cost,
        average_cost=average_cost,
        cost_trend=cost_trend,
        alerts=alerts,
        suggestions=suggestions
    )


def get_cost_trends(user_id: str, timeframe: str = "daily") -> Dict:
    """Aggregate cost data over time periods for visualization.

    Args:
        user_id: User identifier
        timeframe: Time period ("daily", "weekly", "monthly")

    Returns:
        Dictionary with trend data and forecasts
    """
    if timeframe not in ["daily", "weekly", "monthly"]:
        raise ValueError("timeframe must be 'daily', 'weekly', or 'monthly'")

    # Get historical cost data
    historical_data = get_user_cost_history_detailed(user_id, timeframe)

    # Aggregate by time period
    aggregated_costs = aggregate_costs_by_period(historical_data, timeframe)

    # Calculate moving averages for forecasting
    forecast = calculate_cost_forecast(aggregated_costs)

    return {
        "timeframe": timeframe,
        "aggregated_costs": aggregated_costs,
        "forecast": forecast,
        "total_periods": len(aggregated_costs),
        "average_cost": sum(aggregated_costs.values()) / len(aggregated_costs) if aggregated_costs else 0
    }


def calculate_session_cost(telemetry_records: List[RunRecord]) -> float:
    """Calculate total cost for a session from telemetry data.

    Args:
        telemetry_records: List of RunRecord objects for the session

    Returns:
        Total cost in dollars (float)
    """
    total_cost = 0.0

    for record in telemetry_records:
        if hasattr(record, 'cost_usd') and record.cost_usd is not None:
            total_cost += record.cost_usd

    return round(total_cost, 4)


def calculate_average_cost(historical_costs: List[float]) -> float:
    """Calculate user's average conversation cost using median.

    Args:
        historical_costs: List of previous conversation costs

    Returns:
        Median cost value (float), or 0.0 if no historical data
    """
    if not historical_costs:
        return 0.0

    # Use median to avoid outlier influence
    sorted_costs = sorted(historical_costs)
    n = len(sorted_costs)
    if n % 2 == 1:
        return sorted_costs[n // 2]
    else:
        return (sorted_costs[n // 2 - 1] + sorted_costs[n // 2]) / 2


def analyze_cost_trend(current_cost: float, historical_costs: List[float]) -> CostTrend:
    """Analyze cost trend based on current vs historical data.

    Args:
        current_cost: Current session cost
        historical_costs: List of previous conversation costs

    Returns:
        CostTrend enum value
    """
    if not historical_costs:
        return CostTrend.STABLE

    recent_avg = sum(historical_costs[-5:]) / min(5, len(historical_costs))

    if current_cost > recent_avg * 1.2:
        return CostTrend.INCREASING
    elif current_cost < recent_avg * 0.8:
        return CostTrend.DECREASING
    else:
        return CostTrend.STABLE


def generate_cost_alerts(
    current_cost: float,
    average_cost: float,
    telemetry_data: List[RunRecord]
) -> List[CostAlert]:
    """Generate cost alerts based on current session data.

    Args:
        current_cost: Current session cost
        average_cost: User's average conversation cost
        telemetry_data: Session telemetry records

    Returns:
        List of CostAlert objects
    """
    alerts = []

    # High cost anomaly alert
    if average_cost > 0 and current_cost > average_cost * 5:
        alerts.append(CostAlert(
            alert_type=AlertType.HIGH_COST,
            message=f"🚨 Current session cost (${current_cost:.2f}) is 5x higher than your average (${average_cost:.2f})",
            severity=AlertSeverity.HIGH,
            estimated_savings=current_cost - average_cost
        ))

    # Budget warning (assuming user budget is available)
    user_budget = get_user_budget()
    if user_budget and current_cost > user_budget * 0.8:
        alerts.append(CostAlert(
            alert_type=AlertType.BUDGET_WARNING,
            message=f"⚠️ Session cost (${current_cost:.2f}) exceeds 80% of budget (${user_budget:.2f})",
            severity=AlertSeverity.MEDIUM,
            estimated_savings=max(0, current_cost - user_budget)
        ))

    return alerts


def generate_optimization_suggestions(
    telemetry_data: List[RunRecord],
    current_cost: float
) -> List[OptimizationSuggestion]:
    """Generate optimization suggestions based on usage patterns.

    Args:
        telemetry_data: Session telemetry records
        current_cost: Current session cost

    Returns:
        List of OptimizationSuggestion objects
    """
    suggestions = []

    # Analyze context usage
    context_stats = analyze_context_usage(telemetry_data)

    # Suggestion 1: Context summarization
    if should_suggest_context_summarization(context_stats, current_cost):
        savings_pct, savings_dollars = calculate_context_savings(context_stats)
        suggestions.append(OptimizationSuggestion(
            suggestion_type=SuggestionType.REDUCE_CONTEXT,
            description="Summarize earlier messages to reduce context length and API costs",
            estimated_savings_percentage=savings_pct,
            estimated_savings_dollars=savings_dollars,
            confidence_score=calculate_context_confidence(context_stats)
        ))

    # Suggestion 2: Model switching
    if should_suggest_model_switch(telemetry_data, current_cost):
        savings_pct, savings_dollars, target_model = analyze_model_switch_opportunity(telemetry_data)
        suggestions.append(OptimizationSuggestion(
            suggestion_type=SuggestionType.SWITCH_MODEL,
            description=f"Switch to {target_model} for better cost-efficiency while maintaining quality",
            estimated_savings_percentage=savings_pct,
            estimated_savings_dollars=savings_dollars,
            confidence_score=0.75  # Conservative confidence for model switches
        ))

    # Suggestion 3: Context caching
    if should_suggest_caching(telemetry_data):
        savings_pct, savings_dollars = calculate_caching_savings(telemetry_data)
        suggestions.append(OptimizationSuggestion(
            suggestion_type=SuggestionType.ENABLE_CACHING,
            description="Enable semantic caching for repeated queries to reduce API calls",
            estimated_savings_percentage=savings_pct,
            estimated_savings_dollars=savings_dollars,
            confidence_score=0.65  # Moderate confidence for caching benefits
        ))

    return suggestions


def should_suggest_context_summarization(
    context_stats: Dict,
    current_cost: float
) -> bool:
    """Determine if context summarization should be suggested."""
    return (context_stats.get('max_context_length', 0) > 20000 and
            current_cost > 1.0)


def calculate_context_savings(context_stats: Dict) -> tuple[float, float]:
    """Calculate estimated savings from context summarization."""
    current_length = context_stats.get('max_context_length', 0)
    estimated_reduction = min(current_length * 0.4, 15000)  # Estimate 40% reduction
    savings_pct = min(estimated_reduction / current_length, 0.5)
    savings_dollars = context_stats.get('current_cost', 0) * savings_pct
    return savings_pct, savings_dollars


def calculate_context_confidence(context_stats: Dict) -> float:
    """Calculate confidence score for context summarization."""
    length_ratio = min(context_stats.get('max_context_length', 0) / 40000, 1.0)
    return 0.6 + (length_ratio * 0.3)  # 0.6 to 0.9 confidence


def should_suggest_model_switch(
    telemetry_data: List[RunRecord],
    current_cost: float
) -> bool:
    """Determine if model switching should be suggested."""
    # Check if using expensive model with low utilization
    expensive_models = ['gpt-4', 'claude-3-opus']
    return any(record.model in expensive_models and record.cost_usd > 0.10
               for record in telemetry_data if hasattr(record, 'model'))


def analyze_model_switch_opportunity(
    telemetry_data: List[RunRecord]
) -> tuple[float, float, str]:
    """Analyze potential savings from switching to cheaper model."""
    # Simplified analysis - in real implementation would compare quality metrics
    current_cost_per_message = sum(r.cost_usd for r in telemetry_data) / len(telemetry_data)
    if current_cost_per_message > 0.10:
        # Assume switching to GPT-3.5 saves 80%
        savings_pct = 0.80
        savings_dollars = sum(r.cost_usd for r in telemetry_data) * savings_pct
        return savings_pct, savings_dollars, "GPT-3.5-Turbo"
    return 0.0, 0.0, ""


def should_suggest_caching(telemetry_data: List[RunRecord]) -> bool:
    """Determine if caching should be suggested."""
    # Look for repeated similar queries
    messages = [r.run_notes for r in telemetry_data if hasattr(r, 'run_notes') and r.run_notes]
    return detect_query_patterns(messages) > 0.3  # 30% similarity threshold


def calculate_caching_savings(telemetry_data: List[RunRecord]) -> tuple[float, float]:
    """Calculate estimated savings from semantic caching."""
    messages = [r.run_notes for r in telemetry_data if hasattr(r, 'run_notes') and r.run_notes]
    pattern_similarity = detect_query_patterns(messages)
    savings_pct = min(pattern_similarity * 0.4, 0.25)  # Up to 25% savings
    total_cost = sum(r.cost_usd for r in telemetry_data)
    savings_dollars = total_cost * savings_pct
    return savings_pct, savings_dollars


# Helper functions for data retrieval

def get_session_telemetry(session_id: str) -> List[RunRecord]:
    """Retrieve telemetry data for a session.

    Args:
        session_id: Session identifier

    Returns:
        List of RunRecord objects for the session
    """
    # For now, load recent runs and filter by session_id
    # In a real implementation, this would query by session_id
    all_runs = load_recent_runs(limit=1000)  # Load more to find session data

    # Filter by experiment_id or task_label that might contain session_id
    session_runs = []
    for run in all_runs:
        if (run.experiment_id == session_id or
            run.task_label == session_id or
            session_id in run.run_notes):
            session_runs.append(run)

    return session_runs


def get_user_from_session(session_id: str) -> str:
    """Get user ID associated with a session.

    Args:
        session_id: Session identifier

    Returns:
        User ID string
    """
    # For now, return a default user_id
    # In a real implementation, this would look up the user from session data
    return "default_user"


def get_user_cost_history(user_id: str) -> List[float]:
    """Get historical conversation costs for a user.

    Args:
        user_id: User identifier

    Returns:
        List of conversation costs (floats)
    """
    # Load all runs and group by some user identifier
    # For now, return some sample historical costs
    all_runs = load_recent_runs(limit=100)

    # Group runs into "conversations" (simplified: runs within 5 minutes of each other)
    conversations = []
    current_conversation = []

    for run in sorted(all_runs, key=lambda x: x.ts):
        if not current_conversation:
            current_conversation.append(run)
        else:
            time_diff = (run.ts - current_conversation[-1].ts).total_seconds()
            if time_diff < 300:  # 5 minutes
                current_conversation.append(run)
            else:
                if current_conversation:
                    conv_cost = sum(r.cost_usd for r in current_conversation)
                    conversations.append(conv_cost)
                current_conversation = [run]

    if current_conversation:
        conv_cost = sum(r.cost_usd for r in current_conversation)
        conversations.append(conv_cost)

    return conversations[-20:]  # Last 20 conversations


def get_user_budget() -> Optional[float]:
    """Get user's current budget setting.

    Returns:
        Budget amount in dollars, or None if not set
    """
    # For now, return None (no budget set)
    # In a real implementation, this would retrieve from user settings
    return None


def analyze_context_usage(telemetry_data: List[RunRecord]) -> Dict:
    """Analyze context usage patterns from telemetry.

    Args:
        telemetry_data: Session telemetry records

    Returns:
        Dictionary with context statistics
    """
    total_tokens = sum(r.total_tokens for r in telemetry_data)
    max_tokens = max((r.total_tokens for r in telemetry_data), default=0)
    total_cost = sum(r.cost_usd for r in telemetry_data)

    return {
        'max_context_length': max_tokens,
        'average_context_length': total_tokens / len(telemetry_data) if telemetry_data else 0,
        'current_cost': total_cost,
        'message_count': len(telemetry_data)
    }


def detect_query_patterns(messages: List[str]) -> float:
    """Detect similarity patterns in message queries.

    Args:
        messages: List of message strings

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if len(messages) < 2:
        return 0.0

    # Simple similarity detection based on common words
    similarity_scores = []

    for i in range(len(messages)):
        for j in range(i + 1, len(messages)):
            msg1_words = set(messages[i].lower().split())
            msg2_words = set(messages[j].lower().split())
            if msg1_words and msg2_words:
                intersection = len(msg1_words & msg2_words)
                union = len(msg1_words | msg2_words)
                jaccard = intersection / union if union > 0 else 0
                similarity_scores.append(jaccard)

    return sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0


def get_user_cost_history_detailed(user_id: str, timeframe: str) -> Dict:
    """Get detailed historical cost data for trend analysis.

    Args:
        user_id: User identifier
        timeframe: Aggregation period

    Returns:
        Dictionary of date -> cost_list
    """
    all_runs = load_recent_runs(limit=1000)
    history = {}

    for run in all_runs:
        # Group by date based on timeframe
        if timeframe == "daily":
            key = run.ts.date().isoformat()
        elif timeframe == "weekly":
            # Get week start (Monday)
            week_start = run.ts.date() - timedelta(days=run.ts.weekday())
            key = week_start.isoformat()
        else:  # monthly
            key = run.ts.strftime("%Y-%m")

        if key not in history:
            history[key] = []
        history[key].append(run.cost_usd)

    return history


def aggregate_costs_by_period(historical_data: Dict, timeframe: str) -> Dict:
    """Aggregate cost data by time periods.

    Args:
        historical_data: Dictionary of date -> cost_list
        timeframe: Aggregation period

    Returns:
        Dictionary of period -> total_cost
    """
    aggregated = {}
    for period, costs in historical_data.items():
        aggregated[period] = sum(costs)

    return dict(sorted(aggregated.items()))


def calculate_cost_forecast(aggregated_costs: Dict) -> Dict:
    """Calculate cost forecast using moving averages.

    Args:
        aggregated_costs: Dictionary of period -> cost

    Returns:
        Dictionary of future_period -> forecasted_cost
    """
    if len(aggregated_costs) < 3:
        return {}

    # Simple moving average forecast
    values = list(aggregated_costs.values())
    avg_change = sum(values[-3:]) / 3  # Average of last 3 periods

    # Forecast next period
    forecast_value = max(0, avg_change)  # Don't forecast negative costs

    # Get next period key
    periods = list(aggregated_costs.keys())
    last_period = periods[-1]

    # Simple next period calculation (would be more sophisticated in real implementation)
    next_period = f"{last_period}_forecast"

    return {next_period: forecast_value}