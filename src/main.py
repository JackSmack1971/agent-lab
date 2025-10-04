"""Main entry point for Agent Lab with Model Matchmaker integration."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import gradio as gr

# Import existing app functionality
from app import create_ui as create_agent_lab_ui

# Import model matchmaker component
from src.components.model_matchmaker import create_model_matchmaker_tab
from src.models.recommendation import ModelRecommendation


def apply_config_to_agent(recommendation: ModelRecommendation) -> None:
    """Apply a model recommendation to the agent configuration.

    Args:
        recommendation: ModelRecommendation object to apply
    """
    # This would be called when "Apply Config" button is clicked
    # In a real implementation, this would update the agent config form
    # For now, just print the recommendation
    print(f"Applying config for model: {recommendation.model_id}")
    print(f"Suggested temperature: {recommendation.suggested_config.temperature}")
    print(f"Estimated cost: ${recommendation.estimated_cost_per_1k:.4f}/1K tokens")


def create_main_ui() -> gr.Blocks:
    """Create the main tabbed interface for Agent Lab with Model Matchmaker."""

    with gr.Blocks(title="Agent Lab - AI Model Matchmaker") as main_interface:
        gr.Markdown("# 🤖 Agent Lab")
        gr.Markdown("Test AI agents across multiple models and get personalized recommendations.")

        with gr.Tabs():
            with gr.TabItem("🧪 Agent Testing"):
                # Embed the existing Agent Lab interface
                agent_lab_ui = create_agent_lab_ui()
                # Note: In Gradio, we can't directly embed Blocks, so we'd need to refactor
                # For now, we'll recreate the core functionality here
                gr.Markdown("### Agent Configuration & Testing")
                gr.Markdown("*Agent testing interface would be embedded here*")
                gr.Markdown("*(Note: Full integration requires refactoring app.py to use components)*")

            with gr.TabItem("🎯 Model Matchmaker"):
                # Create the model matchmaker tab
                matchmaker_tab = create_model_matchmaker_tab(
                    apply_config_callback=apply_config_to_agent
                )

    return main_interface


if __name__ == "__main__":
    # Launch the main interface
    demo = create_main_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_api=False,
        debug=True,
    )