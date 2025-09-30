"""Phase 0 UI shell for Agent Lab."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from os import getenv
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import gradio as gr
from dotenv import load_dotenv

from agents.models import AgentConfig, RunRecord
from agents.runtime import build_agent, run_agent
from services.persist import append_run, init_csv

load_dotenv()

# Security: never print the API key; warn the operator so they can add it securely.
if not getenv("OPENROUTER_API_KEY"):
    print(
        "Warning: OPENROUTER_API_KEY is not set. The UI will run in limited mode until a key is provided."
    )

DEFAULT_AGENT_CONFIG = AgentConfig(
    name="Test Agent",
    model="openai/gpt-4-turbo",
    system_prompt="You are a helpful assistant.",
)


def _web_badge_html(enabled: bool) -> str:
    """Render the HTML badge describing the web tool state."""

    badge_color = "#0066cc" if enabled else "#666666"
    badge_state = "ON" if enabled else "OFF"
    return (
        "<span style=\"background:{color};color:white;padding:4px 8px;border-radius:4px;\">"
        "Web Tool: {state}</span>"
    ).format(color=badge_color, state=badge_state)


def build_agent_handler(
    name: str,
    model: str,
    sys_prompt: str,
    temp: float,
    top_p: float,
    web_enabled: bool,
    config_state: AgentConfig,
) -> tuple[AgentConfig, str, str, Any]:
    """Build an agent using the runtime and update UI state."""

    updated_config = AgentConfig(
        name=name,
        model=model,
        system_prompt=sys_prompt,
        temperature=temp,
        top_p=top_p,
        tools=["web_fetch"] if web_enabled else [],
    )

    badge_html = _web_badge_html(web_enabled)

    try:
        agent = build_agent(updated_config, include_web=web_enabled)
    except Exception as exc:  # pragma: no cover - runtime guard
        error_badge = _web_badge_html("web_fetch" in config_state.tools)
        return config_state, f"❌ Error: {exc}", error_badge, None

    return updated_config, "✅ Agent built successfully", badge_html, agent


async def send_message_handler(
    message: str,
    history: list[list[str]] | None,
    config_state: AgentConfig,
    agent_state: Any,
) -> tuple[list[list[str]], list[list[str]], str]:
    """Send a chat message to the agent and persist telemetry."""

    chat_history = history[:] if history else []
    trimmed_message = message.strip()

    if not trimmed_message:
        return chat_history, chat_history, "⚠️ Enter a message to send."

    if agent_state is None:
        error_response = "⚠️ Build the agent before starting a chat."
        chat_history.append([trimmed_message, error_response])
        return chat_history, chat_history, error_response

    start_time = time.time()

    try:
        agent_response, _usage = await run_agent(agent_state, trimmed_message)
    except Exception as exc:  # pragma: no cover - runtime guard
        error_text = f"❌ Agent error: {exc}"
        chat_history.append([trimmed_message, error_text])
        return chat_history, chat_history, error_text

    latency_ms = int((time.time() - start_time) * 1000)
    chat_history.append([trimmed_message, agent_response])

    timestamp = datetime.utcnow().replace(microsecond=0)
    web_tool_enabled = "web_fetch" in config_state.tools

    record = RunRecord(
        ts=timestamp,
        agent_name=config_state.name,
        model=config_state.model,
        latency_ms=latency_ms,
        streaming=False,
        tool_web_enabled=web_tool_enabled,
        web_status="ok" if web_tool_enabled else "off",
    )

    await asyncio.to_thread(append_run, record)

    run_info = (
        f"🕒 {latency_ms}ms | 🧠 {config_state.model} | "
        f"📅 {timestamp.isoformat()}"
    )

    return chat_history, chat_history, run_info


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
                chatbot = gr.Chatbot(label="Conversation", height=600)
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
            fn=build_agent_handler,
            inputs=[
                agent_name,
                model_selector,
                system_prompt,
                temperature,
                top_p,
                web_tool_enabled,
                config_state,
            ],
            outputs=[
                config_state,
                run_info_display,
                web_badge,
                agent_state,
            ],
        )

        send_btn.click(
            fn=send_message_handler,
            inputs=[user_input, history_state, config_state, agent_state],
            outputs=[chatbot, history_state, run_info_display],
        )

    return demo


if __name__ == "__main__":
    init_csv()
    print("Telemetry CSV initialized.")
    app = create_ui()
    app.launch(server_name="0.0.0.0", server_port=7860)
