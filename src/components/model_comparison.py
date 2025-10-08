"""Interactive Model Comparison Dashboard component for UX Phase 2."""

from __future__ import annotations

import asyncio
import csv
import io
import time
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from services.catalog import ModelInfo, get_models
from src.services.model_recommender import (
    compare_models,
    get_model_comparison_data,
    ModelComparisonRequest,
    ModelComparisonResult,
)


def create_model_comparison_dashboard() -> gr.Blocks:
    """Create the interactive model comparison dashboard component.

    Returns:
        Gradio Blocks component for the model comparison dashboard.
    """

    with gr.Blocks() as dashboard:
        gr.Markdown("# 📊 Model Comparison Dashboard")
        gr.Markdown("Compare AI models side-by-side with performance metrics, cost analysis, and intelligent recommendations.")

        # State management
        selected_models_state = gr.State([])
        comparison_data_state = gr.State(None)
        loading_state = gr.State(False)

        with gr.Row():
            # Left panel - Model selection and filters
            with gr.Column(scale=1):
                gr.Markdown("### Model Selection")

                # Model selector with checkboxes
                model_checkboxes = gr.CheckboxGroup(
                    label="Select Models to Compare",
                    choices=[],
                    value=[],
                    interactive=True,
                    elem_id="model-selection",
                )

                # Quick selection buttons
                with gr.Row():
                    select_top_btn = gr.Button("Top 3 by Popularity", variant="secondary", size="sm")
                    select_cost_efficient_btn = gr.Button("Cost Efficient", variant="secondary", size="sm")
                    select_fastest_btn = gr.Button("Fastest Models", variant="secondary", size="sm")

                # Filters
                with gr.Accordion("Filters", open=False):
                    provider_filter = gr.CheckboxGroup(
                        label="Providers",
                        choices=["openai", "anthropic", "meta", "google", "mistral"],
                        value=["openai", "anthropic", "meta"],
                        interactive=True,
                    )

                    cost_range_filter = gr.Slider(
                        label="Max Cost per 1K tokens ($)",
                        minimum=0.0,
                        maximum=1.0,
                        value=0.5,
                        step=0.01,
                        interactive=True,
                    )

                # Compare button
                compare_btn = gr.Button(
                    "🔍 Compare Selected Models",
                    variant="primary",
                    size="lg",
                    elem_id="compare-button",
                )

                # Loading indicator
                loading_indicator = gr.HTML(
                    value="",
                    visible=False,
                    elem_id="loading-indicator",
                )

            # Right panel - Comparison results
            with gr.Column(scale=3):
                gr.Markdown("### Comparison Results")

                # Tabs for different views
                with gr.Tabs():
                    with gr.TabItem("📈 Performance Overview"):
                        overview_charts = gr.Plot(
                            label="Performance Charts",
                            elem_id="overview-charts",
                        )

                    with gr.TabItem("💰 Cost Analysis"):
                        cost_charts = gr.Plot(
                            label="Cost Analysis Charts",
                            elem_id="cost-charts",
                        )

                    with gr.TabItem("📊 Detailed Metrics"):
                        metrics_table = gr.Dataframe(
                            headers=["Model", "Provider", "Input Cost", "Output Cost", "Context Window", "Speed"],
                            datatype=["str", "str", "number", "number", "number", "str"],
                            col_count=(6, "fixed"),
                            interactive=False,
                            elem_id="metrics-table",
                        )

                    with gr.TabItem("🎯 Recommendations"):
                        recommendations_display = gr.HTML(
                            value="<div style='text-align: center; color: #666;'>Select models and click 'Compare' to see recommendations.</div>",
                            elem_id="recommendations-display",
                        )

                # Export functionality
                with gr.Row():
                    export_csv_btn = gr.Button(
                        "📥 Export to CSV",
                        variant="secondary",
                        elem_id="export-csv",
                    )
                    export_status = gr.Textbox(
                        label="Export Status",
                        interactive=False,
                        visible=False,
                        elem_id="export-status",
                    )

        # Event handlers
        def load_available_models():
            """Load available models for selection."""
            try:
                models, _, _ = get_models()
                choices = [f"{model.display_name} ({model.provider})" for model in models[:20]]  # Limit for UI
                return gr.update(choices=choices, value=[])
            except Exception as e:
                return gr.update(choices=[], value=[])

        def quick_select_models(selection_type: str) -> List[str]:
            """Quick select models based on criteria."""
            try:
                models, _, _ = get_models()

                if selection_type == "top":
                    # Select top 3 by some criteria (simplified)
                    selected = [f"{model.display_name} ({model.provider})" for model in models[:3]]
                elif selection_type == "cost_efficient":
                    # Select models with lowest costs
                    sorted_models = sorted(models, key=lambda m: (m.input_price or 999, m.output_price or 999))
                    selected = [f"{model.display_name} ({model.provider})" for model in sorted_models[:3]]
                elif selection_type == "fastest":
                    # Select models known for speed (simplified heuristic)
                    fast_providers = ["openai", "anthropic"]
                    fast_models = [m for m in models if m.provider in fast_providers][:3]
                    selected = [f"{model.display_name} ({model.provider})" for model in fast_models]

                return selected
            except Exception:
                return []

        async def perform_comparison(selected_display_names: List[str]) -> Tuple[
            gr.Plot, gr.Plot, gr.Dataframe, str, bool, Optional[ModelComparisonResult]
        ]:
            """Perform model comparison and update all displays."""
            if not selected_display_names or len(selected_display_names) < 2:
                empty_plot = go.Figure()
                empty_plot.add_annotation(text="Select at least 2 models to compare", showarrow=False)
                return (
                    empty_plot, empty_plot,
                    pd.DataFrame(),
                    "<div style='text-align: center; color: #666;'>Select at least 2 models to compare.</div>",
                    False, None
                )

            try:
                # Show loading state
                loading_start = time.time()

                # Parse model IDs from display names
                models, _, _ = get_models()
                model_id_map = {f"{model.display_name} ({model.provider})": model.id for model in models}

                selected_model_ids = []
                for display_name in selected_display_names:
                    if display_name in model_id_map:
                        selected_model_ids.append(model_id_map[display_name])

                if len(selected_model_ids) < 2:
                    raise ValueError("Could not resolve model IDs for selected models")

                # Create comparison request
                request = ModelComparisonRequest(
                    model_ids=selected_model_ids,
                    use_case_description="General purpose AI assistant tasks",  # Default for dashboard
                    include_cost_analysis=True,
                    include_performance_metrics=True,
                )

                # Perform comparison
                comparison_result = await asyncio.get_event_loop().run_in_executor(
                    None, compare_models, request
                )

                # Create visualizations
                overview_fig = create_overview_charts(comparison_result)
                cost_fig = create_cost_analysis_charts(comparison_result)
                metrics_df = create_metrics_table(comparison_result)

                # Create recommendations HTML
                recommendations_html = create_recommendations_display(comparison_result)

                # Check loading time (should be <3 seconds per AC-5.1)
                loading_time = time.time() - loading_start
                performance_ok = loading_time < 3.0

                return (
                    overview_fig, cost_fig, metrics_df, recommendations_html,
                    True, comparison_result
                )

            except Exception as e:
                error_fig = go.Figure()
                error_fig.add_annotation(text=f"Error during comparison: {str(e)}", showarrow=False)

                return (
                    error_fig, error_fig,
                    pd.DataFrame(),
                    f"<div style='color: #d32f2f;'>Error: {str(e)}</div>",
                    False, None
                )

        def create_overview_charts(result: ModelComparisonResult) -> go.Figure:
            """Create overview performance charts."""
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=("Cost Efficiency", "Performance Score", "Context Window", "Provider Distribution"),
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "bar"}, {"type": "pie"}]]
            )

            # Cost efficiency chart
            model_names = [m.model_id.split('/')[-1] for m in result.model_details]
            costs = [m.average_cost_per_1k or 0 for m in result.model_details]

            fig.add_trace(
                go.Bar(x=model_names, y=costs, name="Avg Cost per 1K tokens"),
                row=1, col=1
            )

            # Performance score (placeholder - would need real metrics)
            scores = [0.8, 0.9, 0.7][:len(model_names)]  # Mock data
            fig.add_trace(
                go.Bar(x=model_names, y=scores, name="Performance Score"),
                row=1, col=2
            )

            # Context window
            context_sizes = [m.context_window or 4096 for m in result.model_details]
            fig.add_trace(
                go.Bar(x=model_names, y=context_sizes, name="Context Window"),
                row=2, col=1
            )

            # Provider distribution
            providers = [m.provider for m in result.model_details]
            provider_counts = pd.Series(providers).value_counts()

            fig.add_trace(
                go.Pie(labels=provider_counts.index, values=provider_counts.values, name="Providers"),
                row=2, col=2
            )

            fig.update_layout(height=600, showlegend=False)
            return fig

        def create_cost_analysis_charts(result: ModelComparisonResult) -> go.Figure:
            """Create cost analysis charts."""
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=("Input vs Output Costs", "Cost Efficiency Ranking"),
                specs=[[{"type": "scatter"}, {"type": "bar"}]]
            )

            # Input vs Output costs scatter
            input_costs = [m.input_price or 0 for m in result.model_details]
            output_costs = [m.output_price or 0 for m in result.model_details]
            model_names = [m.model_id.split('/')[-1] for m in result.model_details]

            fig.add_trace(
                go.Scatter(
                    x=input_costs, y=output_costs, mode='markers+text',
                    text=model_names, textposition="top center",
                    name="Cost Comparison"
                ),
                row=1, col=1
            )

            # Cost efficiency ranking (lower cost = higher efficiency)
            avg_costs = [(ic + oc) / 2 for ic, oc in zip(input_costs, output_costs)]
            sorted_indices = sorted(range(len(avg_costs)), key=lambda i: avg_costs[i])

            sorted_names = [model_names[i] for i in sorted_indices]
            sorted_costs = [avg_costs[i] for i in sorted_indices]

            fig.add_trace(
                go.Bar(x=sorted_names, y=sorted_costs, name="Avg Cost Efficiency"),
                row=1, col=2
            )

            fig.update_layout(height=400, showlegend=False)
            return fig

        def create_metrics_table(result: ModelComparisonResult) -> pd.DataFrame:
            """Create detailed metrics table."""
            data = []
            for model in result.model_details:
                data.append({
                    "Model": model.model_id.split('/')[-1],
                    "Provider": model.provider,
                    "Input Cost": model.input_price or 0,
                    "Output Cost": model.output_price or 0,
                    "Context Window": model.context_window or "Unknown",
                    "Speed": "Fast" if model.provider in ["openai", "anthropic"] else "Medium",  # Simplified
                })

            return pd.DataFrame(data)

        def create_recommendations_display(result: ModelComparisonResult) -> str:
            """Create HTML display for recommendations."""
            html = "<div style='margin: 20px 0;'>"
            html += "<h3>🤖 AI Recommendations</h3>"

            if result.recommendations:
                for i, rec in enumerate(result.recommendations[:3], 1):
                    html += f"""
                    <div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 8px 0; background: #f9f9f9;">
                        <h4 style="margin: 0 0 8px 0; color: #2e7d32;">#{i}: {rec.model_id}</h4>
                        <div style="margin-bottom: 8px;">
                            <strong>Confidence:</strong> {rec.confidence_score:.1%}
                        </div>
                        <div style="margin-bottom: 12px;">
                            <strong>Reasoning:</strong><br>
                            {rec.reasoning}
                        </div>
                    </div>
                    """
            else:
                html += "<p>No specific recommendations available.</p>"

            html += "</div>"
            return html

        def export_comparison_data(comparison_data: Optional[ModelComparisonResult]) -> Tuple[str, str]:
            """Export comparison data to CSV."""
            if not comparison_data:
                return "", "No data to export"

            try:
                # Create CSV data
                output = io.StringIO()
                writer = csv.writer(output)

                # Write header
                writer.writerow(["Model", "Provider", "Input Cost", "Output Cost", "Context Window", "Description"])

                # Write data
                for model in comparison_data.model_details:
                    writer.writerow([
                        model.model_id,
                        model.provider,
                        model.input_price or 0,
                        model.output_price or 0,
                        model.context_window or "Unknown",
                        model.description or "",
                    ])

                csv_content = output.getvalue()
                output.close()

                # Return as downloadable content
                return csv_content, "✅ Export completed successfully"

            except Exception as e:
                return "", f"❌ Export failed: {str(e)}"

        # Load models on component initialization
        dashboard.load(
            fn=load_available_models,
            outputs=[model_checkboxes],
        )

        # Quick selection handlers
        select_top_btn.click(
            fn=lambda: quick_select_models("top"),
            outputs=[model_checkboxes],
        )

        select_cost_efficient_btn.click(
            fn=lambda: quick_select_models("cost_efficient"),
            outputs=[model_checkboxes],
        )

        select_fastest_btn.click(
            fn=lambda: quick_select_models("fastest"),
            outputs=[model_checkboxes],
        )

        # Main comparison handler
        compare_btn.click(
            fn=lambda selected, current_data: ("Loading comparison data...", True),
            inputs=[model_checkboxes, comparison_data_state],
            outputs=[loading_indicator, loading_state],
        ).then(
            fn=perform_comparison,
            inputs=[model_checkboxes],
            outputs=[
                overview_charts, cost_charts, metrics_table, recommendations_display,
                loading_state, comparison_data_state
            ],
        ).then(
            fn=lambda: ("", False),
            outputs=[loading_indicator, loading_state],
        )

        # Export handler
        export_csv_btn.click(
            fn=export_comparison_data,
            inputs=[comparison_data_state],
            outputs=[gr.File(label="Download CSV"), export_status],
        )

    return dashboard


if __name__ == "__main__":
    # Test the component
    demo = create_model_comparison_dashboard()
    demo.launch(debug=True)