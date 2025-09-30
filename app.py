"""Phase 0 UI shell for Agent Lab."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import gradio as gr
from dotenv import load_dotenv

from agents.models import AgentConfig

load_dotenv()

# Security: never print the API key; warn the operator so they can add it securely.
if not os.getenv("OPENROUTER_API_KEY"):
    print(
        "Warning: OPENROUTER_API_KEY is not set. The UI will run in limited mode until a key is provided."
    )

DEFAULT_AGENT_CONFIG = AgentConfig(
    name="Test Agent",
    model="openai/gpt-4-turbo",
    system_prompt="You are a helpful assistant.",
)


def handle_build_agent(
    agent_name: str,
    model_id: str,
    system_prompt: str,
    temperature: float,
    top_p: float,
    web_tool_enabled: bool,
    _config_state: AgentConfig,
    _agent_state: Any,
) -> tuple[AgentConfig, str, str, Any]:
    """Placeholder build handler that updates config state and telemetry banner."""

    updated_config = AgentConfig(
        name=agent_name,
        model=model_id,
        system_prompt=system_prompt,
        temperature=temperature,
        top_p=top_p,
        tools=["web_fetch"] if web_tool_enabled else [],
    )

    badge_color = "#0066cc" if web_tool_enabled else "#666"
    badge_state = "ON" if web_tool_enabled else "OFF"
    badge_html = (
        "<span style=\"background:{color};color:white;padding:4px 8px;border-radius:4px;\">"
        "Web Tool: {state}</span>"
    ).format(color=badge_color, state=badge_state)

    return (
        updated_config,
        "Agent building not implemented",
        badge_html,
        None,
    )


def handle_send_message(
    user_message: str,
    history: list[dict[str, str]] | None,
    _agent_state: Any,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Placeholder chat handler that echoes a not implemented response."""

    existing_history: list[dict[str, str]] = history or []

    if not user_message.strip():
        return existing_history, existing_history

    updated_history = existing_history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": "Chat not implemented"},
    ]
    return updated_history, updated_history


def create_ui() -> gr.Blocks:
    """Construct the initial Gradio Blocks layout for Agent Lab."""

    with gr.Blocks(title="Agent Lab") as demo:
        config_state = gr.State(DEFAULT_AGENT_CONFIG)
        agent_state = gr.State(None)
        history_state = gr.State([])

        with gr.Row(equal_height=True):
            with gr.Column(scale=1):
                gr.Markdown("## Agent Configuration")
                agent_name = gr.Textbox(label="Agent Name", value="Test Agent")
                model_selector = gr.Dropdown(
                    label="Model",
                    choices=[
                        "openai/gpt-4-turbo",
                        "anthropic/claude-3-opus",
                    ],
                    value="openai/gpt-4-turbo",
                )
                system_prompt = gr.Textbox(
                    label="System Prompt",
                    lines=8,
                    value="You are a helpful assistant.",
                )
                temperature = gr.Slider(
                    label="Temperature",
                    minimum=0.0,
                    maximum=2.0,
                    value=0.7,
                    step=0.1,
                )
                top_p = gr.Slider(
                    label="Top-p",
                    minimum=0.0,
                    maximum=1.0,
                    value=1.0,
                    step=0.05,
                )
                web_tool_enabled = gr.Checkbox(
                    label="Enable Web Fetch Tool",
                    value=False,
                )
                build_agent = gr.Button("Build Agent", variant="primary")
                reset_agent = gr.Button("Reset", variant="secondary")

            with gr.Column(scale=2):
                chatbot = gr.Chatbot(label="Conversation", height=600, type="messages")
                with gr.Row():
                    user_input = gr.Textbox(label="Message", scale=4, lines=2)
                    send_btn = gr.Button("Send", scale=1)
                stop_btn = gr.Button("Stop", variant="stop", visible=False)

            with gr.Column(scale=1):
                gr.Markdown("## Run Info")
                run_info_display = gr.Markdown(value="No runs yet")
                web_badge = gr.HTML(
                    value="<span style=\"background:#666;color:white;padding:4px 8px;border-radius:4px;\">Web Tool: OFF</span>"
                )
                download_csv = gr.Button("Download runs.csv")

        build_agent.click(
            fn=handle_build_agent,
            inputs=[
                agent_name,
                model_selector,
                system_prompt,
                temperature,
                top_p,
                web_tool_enabled,
                config_state,
                agent_state,
            ],
            outputs=[
                config_state,
                run_info_display,
                web_badge,
                agent_state,
            ],
        )

        send_btn.click(
            fn=handle_send_message,
            inputs=[user_input, history_state, agent_state],
            outputs=[chatbot, history_state],
        )

    return demo


if __name__ == "__main__":
    app = create_ui()
    app.launch(server_name="0.0.0.0", server_port=7860)
