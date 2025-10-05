"""Gradio component for Cost Optimizer feature."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.models.cost_analysis import CostAlert, OptimizationSuggestion
from src.services.cost_analysis_service import analyze_costs, get_cost_trends

logger = logging.getLogger(__name__)


def create_cost_optimizer_tab() -> gr.Blocks:
    """Create the Cost Optimizer Gradio tab component.

    Returns:
        Gradio Blocks component for the cost optimizer tab
    """
    with gr.Blocks() as cost_tab:
        gr.Markdown("# 💰 Cost Optimizer")
        gr.Markdown(
            "Monitor your AI costs and get optimization suggestions in real-time."
        )

        # Session ID input (for demo purposes - in real app this would be automatic)
        session_id_input = gr.Textbox(
            label="Session ID",
            value="demo_session_123",
            placeholder="Enter session ID to analyze",
            visible=False,  # Hide in production
        )

        # Real-time cost display section
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Current Session")
                current_cost_display = gr.Textbox(
                    label="Session Cost",
                    value="$0.00",
                    interactive=False,
                    elem_classes=["cost-display"],
                )
                cost_trend_indicator = gr.Textbox(
                    label="Cost Trend", value="📊 Analyzing...", interactive=False
                )

            with gr.Column(scale=1):
                gr.Markdown("### Budget Status")
                budget_progress = gr.Slider(
                    label="Budget Used",
                    minimum=0,
                    maximum=100,
                    value=0,
                    interactive=False,
                )
                budget_text = gr.Textbox(
                    label="Budget Status", value="No budget set", interactive=False
                )

        # Alerts section
        with gr.Row():
            alerts_display = gr.HTML(
                value="<div class='alerts-container'>No active alerts</div>",
                label="Cost Alerts",
            )

        # Optimization suggestions section
        with gr.Row():
            suggestions_display = gr.HTML(
                value="<div class='suggestions-container'>Analyzing usage patterns...</div>",
                label="Optimization Suggestions",
            )

        # Cost trends visualization
        with gr.Row():
            timeframe_selector = gr.Radio(
                label="Time Period",
                choices=["daily", "weekly", "monthly"],
                value="daily",
            )
            trends_chart = gr.Plot(label="Cost Trends")

        # Cost breakdown
        with gr.Row():
            breakdown_display = gr.Dataframe(
                headers=["Category", "Cost", "Percentage"], label="Cost Breakdown"
            )

        # Settings section
        with gr.Accordion("Cost Settings", open=False):
            budget_input = gr.Number(
                label="Daily Budget ($)", minimum=0, maximum=100, value=None
            )
            save_budget_btn = gr.Button("Save Budget")

        # Event handlers
        def update_cost_display(session_id: str) -> tuple[str, str, float, str]:
            """Update real-time cost display components.

            Args:
                session_id: Current session identifier

            Returns:
                Tuple of (cost_text, trend_text, budget_percentage, budget_status)
            """
            try:
                analysis = analyze_costs(session_id)
                cost_text = f"${analysis.current_cost:.2f}"
                trend_text = f"📊 {analysis.cost_trend.value.title()}"

                # Budget calculation (simplified)
                budget_pct = 0.0
                budget_status = "No budget set"
                if analysis.average_cost > 0:
                    budget_pct = min(
                        (analysis.current_cost / (analysis.average_cost * 2)) * 100, 100
                    )
                    budget_status = f"${analysis.current_cost:.2f} / ${analysis.average_cost * 2:.2f}"

                return cost_text, trend_text, budget_pct, budget_status

            except Exception as exc:
                logger.error(f"Failed to update cost display: {exc}")
                return "$0.00", "📊 Error", 0.0, "Error loading data"

        def update_alerts_display(session_id: str) -> str:
            """Update alerts display.

            Args:
                session_id: Current session identifier

            Returns:
                HTML string for alerts display
            """
            try:
                analysis = analyze_costs(session_id)
                if not analysis.alerts:
                    return "<div class='alerts-container'>✅ No active alerts</div>"

                alerts_html = "<div class='alerts-container'>"
                for alert in analysis.alerts:
                    severity_class = {
                        "low": "alert-low",
                        "medium": "alert-medium",
                        "high": "alert-high",
                    }.get(alert.severity.value, "alert-low")

                    alerts_html += f"""
                    <div class='alert {severity_class}'>
                        <strong>{alert.message}</strong><br>
                        Estimated savings: ${alert.estimated_savings:.2f}
                    </div>
                    """
                alerts_html += "</div>"
                return alerts_html

            except Exception as exc:
                logger.error(f"Failed to update alerts: {exc}")
                return "<div class='alerts-container'>Error loading alerts</div>"

        def update_suggestions_display(session_id: str) -> str:
            """Update optimization suggestions display.

            Args:
                session_id: Current session identifier

            Returns:
                HTML string for suggestions display
            """
            try:
                analysis = analyze_costs(session_id)
                if not analysis.suggestions:
                    return "<div class='suggestions-container'>No optimization suggestions available</div>"

                suggestions_html = "<div class='suggestions-container'>"
                for suggestion in analysis.get_top_suggestions(3):
                    confidence_pct = int(suggestion.confidence_score * 100)

                    suggestions_html += f"""
                    <div class='suggestion-card'>
                        <h4>{suggestion.suggestion_type.value.replace('_', ' ').title()}</h4>
                        <p>{suggestion.description}</p>
                        <div class='suggestion-metrics'>
                            <span>💰 Save ${suggestion.estimated_savings_dollars:.2f} ({suggestion.estimated_savings_percentage:.1%})</span>
                            <span>🎯 Confidence: {confidence_pct}%</span>
                        </div>
                        <button class='apply-btn' onclick='applySuggestion("{suggestion.suggestion_type.value}")'>
                            Apply Suggestion
                        </button>
                    </div>
                    """
                suggestions_html += "</div>"
                return suggestions_html

            except Exception as exc:
                logger.error(f"Failed to update suggestions: {exc}")
                return (
                    "<div class='suggestions-container'>Error loading suggestions</div>"
                )

        def update_trends_chart(session_id: str, timeframe: str) -> go.Figure:
            """Update cost trends chart.

            Args:
                session_id: Current session identifier
                timeframe: Time period for aggregation

            Returns:
                Plotly Figure object
            """
            try:
                user_id = "default_user"  # In real app, get from session
                trends_data = get_cost_trends(user_id, timeframe)

                if not trends_data["aggregated_costs"]:
                    # Create empty chart
                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(x=[], y=[], mode="lines+markers", name="Costs")
                    )
                    fig.update_layout(
                        title="No cost data available",
                        xaxis_title="Time Period",
                        yaxis_title="Cost ($)",
                    )
                    return fig

                # Create chart from aggregated data
                periods = list(trends_data["aggregated_costs"].keys())
                costs = list(trends_data["aggregated_costs"].values())

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=periods,
                        y=costs,
                        mode="lines+markers",
                        name="Historical Costs",
                        line=dict(color="blue", width=2),
                    )
                )

                # Add forecast if available
                if trends_data["forecast"]:
                    forecast_periods = list(trends_data["forecast"].keys())
                    forecast_costs = list(trends_data["forecast"].values())
                    fig.add_trace(
                        go.Scatter(
                            x=forecast_periods,
                            y=forecast_costs,
                            mode="markers",
                            name="Forecast",
                            marker=dict(color="red", size=8, symbol="diamond"),
                        )
                    )

                fig.update_layout(
                    title=f"Cost Trends - {timeframe.title()}",
                    xaxis_title="Time Period",
                    yaxis_title="Cost ($)",
                    hovermode="x unified",
                )

                return fig

            except Exception as exc:
                logger.error(f"Failed to update trends chart: {exc}")
                # Return empty chart
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(x=[], y=[], mode="lines+markers", name="Costs")
                )
                fig.update_layout(title="Error loading chart")
                return fig

        def update_cost_breakdown(session_id: str) -> pd.DataFrame:
            """Update cost breakdown table.

            Args:
                session_id: Current session identifier

            Returns:
                DataFrame with cost breakdown
            """
            try:
                analysis = analyze_costs(session_id)

                # Create sample breakdown (in real implementation, would analyze by model/feature)
                breakdown_data = [
                    ["Total Session Cost", f"${analysis.current_cost:.2f}", "100%"],
                    ["Average Cost", f"${analysis.average_cost:.2f}", "-"],
                    ["Trend", analysis.cost_trend.value.title(), "-"],
                ]

                return pd.DataFrame(
                    breakdown_data, columns=["Category", "Cost", "Percentage"]
                )

            except Exception as exc:
                logger.error(f"Failed to update cost breakdown: {exc}")
                return pd.DataFrame(
                    [["Error", "N/A", "N/A"]],
                    columns=["Category", "Cost", "Percentage"],
                )

        # Connect event handlers
        session_id_input.change(
            fn=update_cost_display,
            inputs=[session_id_input],
            outputs=[
                current_cost_display,
                cost_trend_indicator,
                budget_progress,
                budget_text,
            ],
        )

        session_id_input.change(
            fn=update_alerts_display,
            inputs=[session_id_input],
            outputs=[alerts_display],
        )

        session_id_input.change(
            fn=update_suggestions_display,
            inputs=[session_id_input],
            outputs=[suggestions_display],
        )

        timeframe_selector.change(
            fn=update_trends_chart,
            inputs=[session_id_input, timeframe_selector],
            outputs=[trends_chart],
        )

        session_id_input.change(
            fn=update_cost_breakdown,
            inputs=[session_id_input],
            outputs=[breakdown_display],
        )

        # Initialize displays
        cost_tab.load(
            fn=lambda: update_cost_display("demo_session_123"),
            outputs=[
                current_cost_display,
                cost_trend_indicator,
                budget_progress,
                budget_text,
            ],
        )

        cost_tab.load(
            fn=lambda: update_alerts_display("demo_session_123"),
            outputs=[alerts_display],
        )

        cost_tab.load(
            fn=lambda: update_suggestions_display("demo_session_123"),
            outputs=[suggestions_display],
        )

        cost_tab.load(
            fn=lambda: update_trends_chart("demo_session_123", "daily"),
            outputs=[trends_chart],
        )

        cost_tab.load(
            fn=lambda: update_cost_breakdown("demo_session_123"),
            outputs=[breakdown_display],
        )

    return cost_tab


def apply_optimization_suggestion(suggestion_type: str, session_id: str) -> str:
    """Apply an optimization suggestion.

    Args:
        suggestion_type: Type of suggestion to apply
        session_id: Current session ID

    Returns:
        Success message
    """
    # In a real implementation, this would apply the suggestion
    # For now, just return a success message
    return f"✅ Applied {suggestion_type.replace('_', ' ')} optimization"


# CSS styling for the component
COST_OPTIMIZER_CSS = """
.cost-display {
    font-size: 24px;
    font-weight: bold;
    color: #1976d2;
    text-align: center;
}

.alerts-container {
    padding: 10px;
    border-radius: 5px;
    background-color: #f5f5f5;
}

.alert {
    padding: 10px;
    margin: 5px 0;
    border-radius: 5px;
    border-left: 4px solid;
}

.alert-high {
    background-color: #ffebee;
    border-left-color: #f44336;
    color: #c62828;
}

.alert-medium {
    background-color: #fff3e0;
    border-left-color: #ff9800;
    color: #ef6c00;
}

.alert-low {
    background-color: #e8f5e8;
    border-left-color: #4caf50;
    color: #2e7d32;
}

.suggestions-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.suggestion-card {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    background-color: #fafafa;
}

.suggestion-card h4 {
    margin: 0 0 10px 0;
    color: #1976d2;
}

.suggestion-metrics {
    display: flex;
    justify-content: space-between;
    margin: 10px 0;
    font-size: 14px;
}

.apply-btn {
    background-color: #1976d2;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}

.apply-btn:hover {
    background-color: #1565c0;
}
"""


if __name__ == "__main__":
    # Test the component
    demo = create_cost_optimizer_tab()
    demo.launch(debug=True)
