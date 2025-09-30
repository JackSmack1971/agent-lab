"""Phase 0 UI shell for Agent Lab."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from os import getenv
from pathlib import Path
from threading import Event
from typing import Any, AsyncGenerator, Literal

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import gradio as gr
from dotenv import load_dotenv

from agents.models import AgentConfig, RunRecord
from agents.runtime import build_agent, run_agent_stream
from services.persist import append_run, init_csv
from services.catalog import get_model_choices, get_models

ComponentUpdate = dict[str, Any]


def load_initial_models() -> tuple[
    list[tuple[str, str]],
    str,
    list[Any],
    Literal["dynamic", "fallback"],
]:
    """Load the starting model catalog for the UI with secure fallbacks."""

    try:
        models, source_enum, timestamp = get_models()
    except Exception:  # pragma: no cover - defensive guard
        # Security: avoid leaking internal errors to the UI or console logs.
        print("Warning: failed to load models, using fallback catalog.")
        models, source_enum, timestamp = get_models()

    choices = get_model_choices()

    if source_enum == "dynamic":
        fetch_time = timestamp.astimezone(timezone.utc).strftime("%H:%M")
        source_label = f"Dynamic (fetched {fetch_time})"
    else:
        source_label = "Fallback"

    print(
        "Model catalog loaded: "
        f"{len(choices)} options from {source_enum} ({source_label})."
    )

    return choices, source_label, models, source_enum


INITIAL_MODEL_CHOICES, INITIAL_MODEL_SOURCE_LABEL, _INITIAL_MODELS, INITIAL_MODEL_SOURCE_ENUM = (
    load_initial_models()
)

DEFAULT_MODEL_ID = (
    INITIAL_MODEL_CHOICES[0][1]
    if INITIAL_MODEL_CHOICES
    else "openai/gpt-4-turbo"
)

INITIAL_DROPDOWN_VALUES = [choice[1] for choice in INITIAL_MODEL_CHOICES]

load_dotenv()

# Security: never print the API key; warn the operator so they can add it securely.
if not getenv("OPENROUTER_API_KEY"):
    print(
        "Warning: OPENROUTER_API_KEY is not set. The UI will run in limited mode until a key is provided."
    )

DEFAULT_AGENT_CONFIG = AgentConfig(
    name="Test Agent",
    model=DEFAULT_MODEL_ID,
    system_prompt="You are a helpful assistant.",
)


def _format_source_display(label: str) -> str:
    """Render the model source label for display."""

    return f"**Model catalog:** {label}"


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


def refresh_models_handler(
    current_model: str,
    config_state: AgentConfig,
    existing_choices: list[tuple[str, str]] | None,
) -> tuple[
    list[tuple[str, str]],
    str,
    Literal["dynamic", "fallback"],
    ComponentUpdate,
    str,
    AgentConfig,
    str,
]:
    """Refresh the model catalog and propagate secure UI updates."""

    try:
        models, source_enum, timestamp = get_models(force_refresh=True)
        choices = [(model.display_name, model.id) for model in models]
        if source_enum == "dynamic":
            fetch_time = timestamp.astimezone(timezone.utc).strftime("%H:%M")
            source_label = f"Dynamic (fetched {fetch_time})"
        else:
            source_label = "Fallback"
        message = f"✅ Model catalog refreshed: {len(choices)} options from {source_enum}."
    except Exception:  # pragma: no cover - defensive guard
        # Security: revert to fallback data without exposing sensitive error details.
        print("Warning: model refresh failed; falling back to cached list.")
        choices = list(existing_choices or INITIAL_MODEL_CHOICES)
        if not choices:
            choices = [(DEFAULT_MODEL_ID, DEFAULT_MODEL_ID)]
        source_label = "Fallback"
        source_enum = "fallback"
        message = "⚠️ Model refresh failed. Using fallback model list."
    values = [choice[1] for choice in choices]
    if current_model in values:
        selected_value = current_model
    elif values:
        selected_value = values[0]
    else:
        selected_value = config_state.model

    dropdown_update = gr.update(choices=values or [selected_value], value=selected_value)

    updated_config = config_state.model_copy(update={"model": selected_value})

    return (
        choices,
        source_label,
        source_enum,
        dropdown_update,
        _format_source_display(source_label),
        updated_config,
        message,
    )


async def send_message_streaming(
    message: str,
    history: list[list[str]] | None,
    config_state: AgentConfig,
    model_source_enum: Literal["dynamic", "fallback"],
    agent_state: Any,
    cancel_event_state: Event | None,
    is_generating_state: bool,
) -> AsyncGenerator[
    tuple[
        list[list[str]],
        list[list[str]],
        str,
        Event | None,
        bool,
        ComponentUpdate | None,
        ComponentUpdate | None,
    ],
    None,
]:
    """Stream a chat message to the agent and persist telemetry securely."""

    chat_history = history[:] if history else []
    trimmed_message = message.strip()

    send_idle: ComponentUpdate = gr.update(interactive=True)
    stop_hidden: ComponentUpdate = gr.update(visible=False, interactive=False)

    if not trimmed_message:
        # Security: do not trigger agent execution on empty input.
        yield (
            chat_history,
            chat_history,
            "⚠️ Enter a message to send.",
            cancel_event_state,
            is_generating_state,
            send_idle,
            stop_hidden,
        )
        return

    if agent_state is None:
        error_response = "⚠️ Build the agent before starting a chat."
        chat_history.append([trimmed_message, error_response])
        yield (
            chat_history,
            chat_history,
            error_response,
            cancel_event_state,
            is_generating_state,
            send_idle,
            stop_hidden,
        )
        return

    cancel_token = Event()
    chat_history.append([trimmed_message, ""])

    delta_event = asyncio.Event()

    def handle_delta(delta: str) -> None:
        """Capture each streamed fragment and flag UI updates."""

        if not delta:
            return
        chat_history[-1][1] += delta
        delta_event.set()

    stream_task = asyncio.create_task(
        run_agent_stream(agent_state, trimmed_message, handle_delta, cancel_token)
    )

    streaming_info = "🔄 Streaming response..."
    send_disabled: ComponentUpdate = gr.update(interactive=False)
    stop_visible: ComponentUpdate = gr.update(visible=True, interactive=True)

    # Surface initial state to toggle buttons and store cancellation token.
    yield (
        chat_history,
        chat_history,
        streaming_info,
        cancel_token,
        True,
        send_disabled,
        stop_visible,
    )

    try:
        while not stream_task.done():
            try:
                await asyncio.wait_for(delta_event.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                continue
            delta_event.clear()
            yield (
                chat_history,
                chat_history,
                streaming_info,
                cancel_token,
                True,
                send_disabled,
                stop_visible,
            )

        stream_result = await stream_task
    except Exception as exc:  # pragma: no cover - runtime guard
        error_text = f"❌ Agent error: {exc}"
        chat_history[-1][1] = error_text
        yield (
            chat_history,
            chat_history,
            error_text,
            None,
            False,
            send_idle,
            stop_hidden,
        )
        return

    if delta_event.is_set():
        delta_event.clear()
        yield (
            chat_history,
            chat_history,
            streaming_info,
            cancel_token,
            True,
            send_disabled,
            stop_visible,
        )

    # Normalise streamed text to the final consolidated response.
    chat_history[-1][1] = stream_result.text

    raw_usage = stream_result.usage
    usage: dict[str, Any]
    if isinstance(raw_usage, dict):
        usage = raw_usage
    else:
        # Defensive: cope with providers that omit usage or return non-mapping data.
        try:
            usage = dict(raw_usage or {})
        except TypeError:
            usage = {}

    def _extract_int(keys: list[str]) -> int:
        for key in keys:
            value = usage.get(key)
            if isinstance(value, dict):
                # Handle nested usage structures such as {"prompt": 12}.
                nested_value = value.get("total") or value.get("value")
                if nested_value is not None:
                    value = nested_value
            try:
                return int(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
        return 0

    def _extract_float(keys: list[str]) -> float:
        for key in keys:
            value = usage.get(key)
            if isinstance(value, dict):
                candidate = value.get("usd") or value.get("amount")
                if candidate is not None:
                    value = candidate
            try:
                return float(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
        return 0.0

    prompt_tokens = _extract_int([
        "prompt_tokens",
        "promptTokens",
        "input_tokens",
        "inputTokens",
        "prompt",
    ])
    completion_tokens = _extract_int([
        "completion_tokens",
        "completionTokens",
        "output_tokens",
        "outputTokens",
        "completion",
    ])
    total_tokens = _extract_int([
        "total_tokens",
        "totalTokens",
        "tokens",
    ])

    if total_tokens == 0 and (prompt_tokens or completion_tokens):
        total_tokens = prompt_tokens + completion_tokens

    cost_usd = _extract_float([
        "cost_usd",
        "total_cost",
        "cost",
        "usd_cost",
    ])

    usage_available = bool(usage)

    timestamp = datetime.utcnow().replace(microsecond=0)
    web_tool_enabled = "web_fetch" in config_state.tools

    model_source = model_source_enum if model_source_enum == "dynamic" else "fallback"

    record = RunRecord(
        ts=timestamp,
        agent_name=config_state.name,
        model=config_state.model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=stream_result.latency_ms,
        cost_usd=cost_usd,
        streaming=True,
        model_list_source=model_source,
        tool_web_enabled=web_tool_enabled,
        web_status="ok" if web_tool_enabled else "off",
        aborted=stream_result.aborted,
    )

    try:
        await asyncio.to_thread(append_run, record)
    except Exception as exc:  # pragma: no cover - filesystem/runtime guard
        run_info = f"⚠️ Response logged with warning: {exc}"
    else:
        status_prefix = "⏹️ Generation stopped" if stream_result.aborted else "✅ Response ready"
        if usage_available:
            token_fragment = (
                " | 🔢 "
                f"{prompt_tokens}?{completion_tokens} ({total_tokens} total)"
            )
        else:
            token_fragment = " | 🔢 tokens unavailable"
        cost_fragment = f" | 💰 ${cost_usd:.4f}" if cost_usd > 0 else ""
        aborted_fragment = " | 🛑 Aborted" if stream_result.aborted else ""
        run_info = (
            f"{status_prefix} | 🕒 {stream_result.latency_ms}ms | "
            f"🧠 {config_state.model} | 📅 {timestamp.isoformat()}"
            f"{token_fragment}{cost_fragment}{aborted_fragment}"
        )

    yield (
        chat_history,
        chat_history,
        run_info,
        None,
        False,
        send_idle,
        stop_hidden,
    )


def stop_generation(
    cancel_event: Event | None,
    is_generating: bool,
) -> tuple[str, Event | None, bool, ComponentUpdate | None, ComponentUpdate | None]:
    """Signal the active stream to stop safely when requested by the user."""

    if isinstance(cancel_event, Event):
        cancel_event.set()

    status_text = "⏹️ Stopping..." if is_generating else "⚠️ No generation in progress."
    # Security: disable buttons to avoid duplicate stop requests while the stream halts.
    send_update: ComponentUpdate | None = (
        gr.update(interactive=False) if is_generating else None
    )
    stop_update: ComponentUpdate = gr.update(interactive=False)

    return status_text, cancel_event, is_generating, send_update, stop_update


def create_ui() -> gr.Blocks:
    """Construct the initial Gradio Blocks layout for Agent Lab."""

    with gr.Blocks(title="Agent Lab") as demo:
        config_state = gr.State(DEFAULT_AGENT_CONFIG)
        agent_state = gr.State(None)
        history_state = gr.State([])
        cancel_event_state = gr.State(None)
        is_generating_state = gr.State(False)
        model_choices_state = gr.State(INITIAL_MODEL_CHOICES)
        model_source_label_state = gr.State(INITIAL_MODEL_SOURCE_LABEL)
        model_source_enum_state = gr.State(INITIAL_MODEL_SOURCE_ENUM)

        with gr.Row(equal_height=True):
            with gr.Column(scale=1):
                gr.Markdown("## Agent Configuration")
                agent_name = gr.Textbox(label="Agent Name", value="Test Agent")
                model_selector = gr.Dropdown(
                    label="Model",
                    choices=INITIAL_DROPDOWN_VALUES or [DEFAULT_MODEL_ID],
                    value=DEFAULT_AGENT_CONFIG.model,
                )
                model_source_indicator = gr.Markdown(
                    value=_format_source_display(INITIAL_MODEL_SOURCE_LABEL)
                )
                refresh_models_button = gr.Button("Refresh Models", variant="secondary")
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
                stop_btn = gr.Button("Stop", variant="stop", visible=False, interactive=False)

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

        refresh_models_button.click(
            fn=refresh_models_handler,
            inputs=[model_selector, config_state, model_choices_state],
            outputs=[
                model_choices_state,
                model_source_label_state,
                model_source_enum_state,
                model_selector,
                model_source_indicator,
                config_state,
                run_info_display,
            ],
        )

        send_btn.click(
            fn=send_message_streaming,
            inputs=[
                user_input,
                history_state,
                config_state,
                model_source_enum_state,
                agent_state,
                cancel_event_state,
                is_generating_state,
            ],
            outputs=[
                chatbot,
                history_state,
                run_info_display,
                cancel_event_state,
                is_generating_state,
                send_btn,
                stop_btn,
            ],
        )

        stop_btn.click(
            fn=stop_generation,
            inputs=[cancel_event_state, is_generating_state],
            outputs=[run_info_display, cancel_event_state, is_generating_state, send_btn, stop_btn],
        )

    return demo


if __name__ == "__main__":
    init_csv()
    print("Telemetry CSV initialized.")
    app = create_ui()
    app.launch(server_name="0.0.0.0", server_port=7860)
