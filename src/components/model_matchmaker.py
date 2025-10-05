"""Gradio component for AI Model Matchmaker feature."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

import gradio as gr

from src.models.recommendation import (
    ModelRecommendation,
    RecommendationResponse,
    UseCaseInput,
)
from src.services.recommendation_service import analyze_use_case


def validate_use_case_description(description: str) -> dict:
    """Validate use case description field."""
    if not description or not description.strip():
        return {
            "status": "error",
            "message": "❌ Use Case: This field is required",
            "is_valid": False,
        }
    if len(description) > 500:
        return {
            "status": "error",
            "message": "❌ Use Case: Maximum 500 characters allowed",
            "is_valid": False,
        }
    return {"status": "success", "message": "✅ Use Case is valid", "is_valid": True}


def validate_max_cost(cost: str) -> dict:
    """Validate maximum cost field."""
    if not cost or cost.strip() == "":
        return {"status": "success", "message": "", "is_valid": True}  # Optional field
    try:
        cost_val = float(cost)
        if cost_val <= 0:
            return {
                "status": "error",
                "message": "❌ Max Cost: Must be greater than 0",
                "is_valid": False,
            }
        if cost_val > 1.0:
            return {
                "status": "error",
                "message": "❌ Max Cost: Maximum $1.00 per 1K tokens",
                "is_valid": False,
            }
        return {
            "status": "success",
            "message": "✅ Max Cost is valid",
            "is_valid": True,
        }
    except (ValueError, TypeError):
        return {
            "status": "error",
            "message": "❌ Max Cost: Must be a number",
            "is_valid": False,
        }


def validate_min_speed(speed: str) -> dict:
    """Validate minimum speed field."""
    if not speed or speed.strip() == "":
        return {"status": "success", "message": "", "is_valid": True}  # Optional field
    try:
        speed_val = float(speed)
        if speed_val <= 0:
            return {
                "status": "error",
                "message": "❌ Min Speed: Must be greater than 0",
                "is_valid": False,
            }
        if speed_val > 1000:
            return {
                "status": "error",
                "message": "❌ Min Speed: Maximum 1000 tokens/second",
                "is_valid": False,
            }
        return {
            "status": "success",
            "message": "✅ Min Speed is valid",
            "is_valid": True,
        }
    except (ValueError, TypeError):
        return {
            "status": "error",
            "message": "❌ Min Speed: Must be a number",
            "is_valid": False,
        }


def validate_context_length(length: str) -> dict:
    """Validate context length field."""
    if not length or length.strip() == "":
        return {"status": "success", "message": "", "is_valid": True}  # Optional field
    try:
        length_val = int(length)
        if length_val <= 0:
            return {
                "status": "error",
                "message": "❌ Context Length: Must be greater than 0",
                "is_valid": False,
            }
        if length_val > 200000:
            return {
                "status": "error",
                "message": "❌ Context Length: Maximum 200,000 tokens",
                "is_valid": False,
            }
        return {
            "status": "success",
            "message": "✅ Context Length is valid",
            "is_valid": True,
        }
    except (ValueError, TypeError):
        return {
            "status": "error",
            "message": "❌ Context Length: Must be a whole number",
            "is_valid": False,
        }


def format_recommendation_card(recommendation: ModelRecommendation, index: int) -> str:
    """Format a single recommendation as HTML card."""
    config = recommendation.suggested_config

    return f"""
<div style="border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin: 8px 0; background: #f9f9f9;">
    <h4 style="margin: 0 0 8px 0; color: #2e7d32;">#{index + 1}: {recommendation.model_id}</h4>
    <div style="margin-bottom: 8px;">
        <strong>Confidence:</strong> {recommendation.confidence_score:.1%} |
        <strong>Est. Cost:</strong> ${recommendation.estimated_cost_per_1k:.4f}/1K tokens
    </div>
    <div style="margin-bottom: 12px;">
        <strong>Suggested Config:</strong><br>
        Temperature: {config.temperature} | Top-P: {config.top_p} | Max Tokens: {config.max_tokens}
    </div>
    <div style="margin-bottom: 12px;">
        <strong>Reasoning:</strong><br>
        {recommendation.reasoning}
    </div>
    <button onclick="applyConfig_{index}()" style="background: #1976d2; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
        Apply Config
    </button>
</div>
    """.strip()


async def get_recommendations_async(
    description: str,
    max_cost: str,
    min_speed: str,
    context_length: str,
) -> tuple[str, str]:
    """Async function to get recommendations with proper error handling."""

    try:
        # Validate inputs
        desc_validation = validate_use_case_description(description)
        if not desc_validation["is_valid"]:
            return "", desc_validation["message"]

        cost_validation = validate_max_cost(max_cost)
        if not cost_validation["is_valid"]:
            return "", cost_validation["message"]

        speed_validation = validate_min_speed(min_speed)
        if not speed_validation["is_valid"]:
            return "", speed_validation["message"]

        length_validation = validate_context_length(context_length)
        if not length_validation["is_valid"]:
            return "", length_validation["message"]

        # Parse optional constraints
        max_cost_val = float(max_cost) if max_cost and max_cost.strip() else None
        min_speed_val = float(min_speed) if min_speed and min_speed.strip() else None
        context_length_val = (
            int(context_length) if context_length and context_length.strip() else None
        )

        # Create use case input
        use_case = UseCaseInput(
            description=description,
            max_cost=max_cost_val,
            min_speed=min_speed_val,
            context_length_required=context_length_val,
        )

        # Get recommendations (this may take time, hence async)
        response = await asyncio.get_event_loop().run_in_executor(
            None, analyze_use_case, use_case
        )

        # Format results
        result_html = f"""
<div style="margin-bottom: 16px;">
    <h3 style="color: #1976d2;">Analysis Summary</h3>
    <p>{response.analysis_summary}</p>
</div>
<div>
    <h3 style="color: #1976d2;">Top Recommendations</h3>
"""

        for i, rec in enumerate(response.recommendations):
            result_html += format_recommendation_card(rec, i)

        result_html += "</div>"

        return result_html, ""

    except Exception as exc:
        error_msg = f"❌ Failed to get recommendations: {str(exc)}"
        return "", error_msg


def create_model_matchmaker_tab(
    apply_config_callback: Optional[Callable[[ModelRecommendation], None]] = None,
) -> gr.Blocks:
    """Create the Model Matchmaker Gradio tab component.

    Args:
        apply_config_callback: Optional callback function to handle "Apply Config" button clicks.
                               Should accept a ModelRecommendation and update the main agent config.

    Returns:
        Gradio Blocks component for the Model Matchmaker tab.
    """

    with gr.Blocks() as matchmaker_tab:
        gr.Markdown("# 🤖 AI Model Matchmaker")
        gr.Markdown(
            "Describe your use case and get personalized model recommendations with optimal configurations."
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Use Case Description")
                use_case_input = gr.Textbox(
                    label="Describe your AI use case",
                    placeholder="e.g., 'I need a fast, affordable chatbot for customer support'",
                    lines=3,
                    max_lines=5,
                )

                gr.Markdown("### Optional Constraints (leave empty for no constraints)")
                with gr.Row():
                    max_cost_input = gr.Textbox(
                        label="Max Cost ($/1K tokens)",
                        placeholder="e.g., 0.01",
                        scale=1,
                    )
                    min_speed_input = gr.Textbox(
                        label="Min Speed (tokens/sec)",
                        placeholder="e.g., 50",
                        scale=1,
                    )
                    context_length_input = gr.Textbox(
                        label="Context Length (tokens)",
                        placeholder="e.g., 4096",
                        scale=1,
                    )

                # Validation outputs
                validation_outputs = [
                    gr.Textbox(
                        label="Use Case Validation", interactive=False, visible=False
                    ),
                    gr.Textbox(
                        label="Max Cost Validation", interactive=False, visible=False
                    ),
                    gr.Textbox(
                        label="Min Speed Validation", interactive=False, visible=False
                    ),
                    gr.Textbox(
                        label="Context Length Validation",
                        interactive=False,
                        visible=False,
                    ),
                ]

                find_button = gr.Button(
                    "🔍 Find Best Models",
                    variant="primary",
                    size="lg",
                )

            with gr.Column(scale=2):
                gr.Markdown("### Recommendations")
                results_display = gr.HTML(
                    value="<div style='text-align: center; color: #666;'>Enter your use case and click 'Find Best Models' to get recommendations.</div>",
                )

                error_display = gr.Textbox(
                    label="Errors",
                    interactive=False,
                    visible=False,
                    lines=2,
                )

        # Event handlers
        def validate_inputs(description, max_cost, min_speed, context_length):
            """Validate all inputs and return validation messages."""
            desc_val = validate_use_case_description(description)
            cost_val = validate_max_cost(max_cost)
            speed_val = validate_min_speed(min_speed)
            length_val = validate_context_length(context_length)

            return [
                desc_val["message"],
                cost_val["message"],
                speed_val["message"],
                length_val["message"],
            ]

        # Connect validation
        input_components = [
            use_case_input,
            max_cost_input,
            min_speed_input,
            context_length_input,
        ]
        for i, component in enumerate(input_components):
            component.change(
                fn=lambda *args, idx=i: validate_inputs(*args[:4])[idx],
                inputs=input_components,
                outputs=validation_outputs[i],
            )

        # Handle button click
        find_button.click(
            fn=get_recommendations_async,
            inputs=input_components,
            outputs=[results_display, error_display],
            api_name="get_recommendations",
        )

        # Keyboard shortcut (Ctrl/Cmd + M)
        matchmaker_tab.load(
            fn=None,
            inputs=None,
            outputs=None,
            js="""
            function() {
                document.addEventListener('keydown', function(event) {
                    if ((event.ctrlKey || event.metaKey) && event.key === 'm') {
                        event.preventDefault();
                        // Focus on the use case input
                        const inputs = document.querySelectorAll('textarea[data-testid*="textbox"]');
                        if (inputs.length > 0) {
                            inputs[0].focus();
                        }
                    }
                });
            }
            """,
        )

    return matchmaker_tab


if __name__ == "__main__":
    # Test the component
    demo = create_model_matchmaker_tab()
    demo.launch(debug=True)
