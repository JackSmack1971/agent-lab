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

from agents.models import AgentConfig, RunRecord, Session
from agents.runtime import build_agent, run_agent_stream
from services.persist import append_run, init_csv, list_sessions, save_session, load_session
from services.catalog import get_model_choices, get_models
from uuid import uuid4
from datetime import datetime, timezone

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

    # Create display labels: "Display Name (provider)" -> model_id
    display_choices = []
    for model in models:
        display_label = f"{model.display_name} ({model.provider})"
        display_choices.append((display_label, model.id))

    if source_enum == "dynamic":
        fetch_time = timestamp.astimezone(timezone.utc).strftime("%H:%M")
        source_label = f"Dynamic (fetched {fetch_time})"
    else:
        source_label = "Fallback"

    print(
        "Model catalog loaded: "
        f"{len(display_choices)} options from {source_enum} ({source_label})."
    )

    return display_choices, source_label, models, source_enum


INITIAL_MODEL_CHOICES, INITIAL_MODEL_SOURCE_LABEL, _INITIAL_MODELS, INITIAL_MODEL_SOURCE_ENUM = (
    load_initial_models()
)

DEFAULT_MODEL_ID = (
    INITIAL_MODEL_CHOICES[0][1]
    if INITIAL_MODEL_CHOICES
    else "openai/gpt-4-turbo"
)

INITIAL_DROPDOWN_VALUES = [choice[0] for choice in INITIAL_MODEL_CHOICES]

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


# UX Improvements - Inline Validation, Keyboard Shortcuts, Loading States

def validate_agent_name(name: str) -> dict:
    """Validate agent name field."""
    if not name or not name.strip():
        return {"status": "error", "message": "❌ Agent Name: This field is required", "is_valid": False}
    if len(name) > 100:
        return {"status": "error", "message": "❌ Agent Name: Maximum 100 characters allowed", "is_valid": False}
    return {"status": "success", "message": "✅ Agent Name is valid", "is_valid": True}

def validate_system_prompt(prompt: str) -> dict:
    """Validate system prompt field."""
    if not prompt or not prompt.strip():
        return {"status": "error", "message": "❌ System Prompt: This field is required", "is_valid": False}
    if len(prompt) > 10000:
        return {"status": "error", "message": "❌ System Prompt: Maximum 10,000 characters allowed", "is_valid": False}
    return {"status": "success", "message": "✅ System Prompt is valid", "is_valid": True}

def validate_temperature(temp: str | float) -> dict:
    """Validate temperature field."""
    try:
        temp_val = float(temp)
        if temp_val < 0.0:
            return {"status": "error", "message": "❌ Temperature: Minimum value is 0.0", "is_valid": False}
        if temp_val > 2.0:
            return {"status": "error", "message": "❌ Temperature: Maximum value is 2.0", "is_valid": False}
        return {"status": "success", "message": "✅ Temperature is valid", "is_valid": True}
    except (ValueError, TypeError):
        return {"status": "error", "message": "❌ Temperature: Must be a number between 0.0 and 2.0", "is_valid": False}

def validate_top_p(top_p: str | float) -> dict:
    """Validate top_p field."""
    try:
        top_p_val = float(top_p)
        if top_p_val < 0.0:
            return {"status": "error", "message": "❌ Top P: Minimum value is 0.0", "is_valid": False}
        if top_p_val > 1.0:
            return {"status": "error", "message": "❌ Top P: Maximum value is 1.0", "is_valid": False}
        return {"status": "success", "message": "✅ Top P is valid", "is_valid": True}
    except (ValueError, TypeError):
        return {"status": "error", "message": "❌ Top P: Must be a number between 0.0 and 1.0", "is_valid": False}

def validate_model_selection(model_id: str, available_models: list | None) -> dict:
    """Validate model selection."""
    if not available_models:
        return {"status": "error", "message": "❌ Model: No models available", "is_valid": False}
    model_ids = [m.id for m in available_models]
    if model_id not in model_ids:
        return {"status": "error", "message": "❌ Model: Please select a valid model", "is_valid": False}
    return {"status": "success", "message": "✅ Model is valid", "is_valid": True}

def validate_form_field(field_name: str, value: Any, available_models: list | None = None) -> dict:
    """Central validation dispatcher."""
    if field_name == "agent_name":
        return validate_agent_name(value)
    elif field_name == "system_prompt":
        return validate_system_prompt(value)
    elif field_name == "temperature":
        return validate_temperature(value)
    elif field_name == "top_p":
        return validate_top_p(value)
    elif field_name == "model":
        return validate_model_selection(value, available_models)
    return {"status": "unknown", "message": "", "is_valid": True}

# Keyboard Shortcuts Implementation
def handle_keyboard_shortcut(keyboard_event: gr.EventData) -> str:
    """Handle keyboard shortcuts from JavaScript."""
    try:
        event_data = keyboard_event._data if hasattr(keyboard_event, '_data') else {}
        key = event_data.get('key', '').lower()
        ctrl_key = event_data.get('ctrlKey', False)
        meta_key = event_data.get('metaKey', False)
        shift_key = event_data.get('shiftKey', False)

        # Normalize Ctrl/Cmd
        modifier = ctrl_key or meta_key

        # Define shortcuts
        if modifier and key == 'enter':
            return 'send_message'
        elif modifier and key == 'k':
            return 'focus_input'
        elif modifier and key == 'r':
            return 'refresh_models'
        elif key == 'escape':
            return 'stop_generation'

        return 'none'
    except Exception:
        return 'none'

# Loading States Implementation
class LoadingStateManager:
    """Manages loading states for UI elements."""

    def __init__(self):
        self.active_operations = {}

    def start_loading(self, operation_id: str, operation_type: str) -> dict:
        """Start loading state for an operation."""
        self.active_operations[operation_id] = {
            'type': operation_type,
            'start_time': datetime.now(timezone.utc)
        }

        if operation_type == 'button':
            return {'interactive': False, 'value': self._get_loading_text(operation_type)}
        elif operation_type == 'panel':
            return {'visible': True, '__type__': 'update'}
        return {}

    def complete_loading(self, operation_id: str, success: bool = True) -> dict:
        """Complete loading state for an operation."""
        if operation_id in self.active_operations:
            operation_type = self.active_operations[operation_id]['type']
            del self.active_operations[operation_id]

            if operation_type == 'button':
                return {'interactive': True, 'value': self._get_default_text(operation_type)}
            elif operation_type == 'panel':
                return {'visible': False, '__type__': 'update'}
        return {}

    def _get_loading_text(self, operation_type: str) -> str:
        """Get loading text for operation type."""
        texts = {
            'button': {
                'agent_build': 'Building...',
                'model_refresh': 'Refreshing...',
                'session_save': 'Saving...',
                'session_load': 'Loading...'
            }
        }
        return texts.get('button', {}).get(operation_type, 'Loading...')

    def _get_default_text(self, operation_type: str) -> str:
        """Get default text for operation type."""
        texts = {
            'button': {
                'agent_build': 'Build Agent',
                'model_refresh': 'Refresh Models',
                'session_save': 'Save Session',
                'session_load': 'Load Session'
            }
        }
        return texts.get('button', {}).get(operation_type, '')

# Global loading state manager
loading_manager = LoadingStateManager()


def build_agent_handler(
    name: str,
    model_display_label: str,
    sys_prompt: str,
    temp: float,
    top_p: float,
    web_enabled: bool,
    config_state: AgentConfig,
    id_mapping: dict[str, str],
) -> tuple[AgentConfig, str, str, Any]:
    """Build an agent using the runtime and update UI state."""

    # Resolve display label to actual model ID
    model_id = id_mapping.get(model_display_label, model_display_label)

    updated_config = AgentConfig(
        name=name,
        model=model_id,
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
    current_display_label: str,
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
    dict[str, str],
]:
    """Refresh the model catalog and propagate secure UI updates."""

    try:
        models, source_enum, timestamp = get_models(force_refresh=True)
        choices = [
            (f"{model.display_name} ({model.provider})", model.id)
            for model in models
        ]
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

    # Create mapping: display_label -> model_id
    id_mapping = {choice[0]: choice[1] for choice in choices}

    # Find current selection
    current_model_id = id_mapping.get(current_display_label, config_state.model)
    # Find display label for current model ID
    display_labels = [choice[0] for choice in choices]
    selected_label = current_display_label if current_display_label in display_labels else (
        display_labels[0] if display_labels else DEFAULT_MODEL_ID
    )

    dropdown_update = gr.update(choices=display_labels, value=selected_label)
    updated_config = config_state.model_copy(update={"model": current_model_id})

    return (
        choices,
        source_label,
        source_enum,
        dropdown_update,
        _format_source_display(source_label),
        updated_config,
        message,
        id_mapping,
    )


async def send_message_streaming(
    message: str,
    history: list[list[str]] | None,
    config_state: AgentConfig,
    model_source_enum: Literal["dynamic", "fallback"],
    agent_state: Any,
    cancel_event_state: Event | None,
    is_generating_state: bool,
    experiment_id: str,
    task_label: str,
    run_notes: str,
    id_mapping: dict[str, str],  # NEW: for resolving display labels
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
        experiment_id=experiment_id.strip(),
        task_label=task_label.strip(),
        run_notes=run_notes.strip(),
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

        tag_info = ""
        if experiment_id.strip():
            tag_info += f" | ?? Exp: {experiment_id.strip()}"
        if task_label.strip() and task_label != "other":
            tag_info += f" | ??? Task: {task_label}"
        if run_notes.strip():
            tag_info += f" | ?? Notes: {run_notes.strip()[:30]}..." if len(run_notes.strip()) > 30 else f" | ?? {run_notes.strip()}"

        # Resolve model ID to display label for UI
        reverse_mapping = {v: k for k, v in id_mapping.items()}
        model_display = reverse_mapping.get(config_state.model, config_state.model)

        run_info = (
            f"{status_prefix} | 🕒 {stream_result.latency_ms}ms | "
            f"🧠 {model_display} | 📅 {timestamp.isoformat()}"
            f"{token_fragment}{cost_fragment}{aborted_fragment}{tag_info}"
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


def save_session_handler(
    session_name: str,
    config_state: AgentConfig,
    history_state: list,
    current_session: Session | None,
) -> tuple[Session | None, str, list[tuple[str, str]], ComponentUpdate]:
    """Save current session to disk with user-provided name."""
    if not session_name.strip():
        return current_session, "?? Please enter a session name", [], gr.update()

    # Create new session or update existing
    session = Session(
        id=current_session.id if current_session else str(uuid4()),
        created_at=current_session.created_at if current_session else datetime.now(timezone.utc),
        agent_config=config_state,
        transcript=[{"role": msg[0], "content": msg[1], "ts": datetime.now(timezone.utc).isoformat()}
                   for pair in history_state for msg in [("user", pair[0]), ("assistant", pair[1])]],
        model_id=config_state.model,
        notes=session_name
    )

    try:
        path = save_session(session)
        sessions_list = [(s[0], s[0]) for s in list_sessions()]
        return session, f"? Saved: {path.name}", sessions_list, gr.update(choices=sessions_list)
    except Exception as exc:
        return current_session, f"? Save failed: {exc}", [], gr.update()


def load_session_handler(
    session_name: str | None,
    id_mapping: dict[str, str],
) -> tuple[Session | None, str, list, AgentConfig, str, str, str, float, float, bool]:
    """Load session from disk and restore all state."""
    if not session_name:
        return None, "?? Select a session to load", [], DEFAULT_AGENT_CONFIG, "", "", "", 0.7, 1.0, False

    try:
        sessions = {s[0]: s[1] for s in list_sessions()}
        if session_name not in sessions:
            return None, f"? Session not found: {session_name}", [], DEFAULT_AGENT_CONFIG, "", "", "", 0.7, 1.0, False

        session = load_session(sessions[session_name])

        # Reconstruct chat history
        history = []
        transcript = session.transcript
        for i in range(0, len(transcript), 2):
            if i + 1 < len(transcript):
                user_msg = transcript[i]["content"]
                asst_msg = transcript[i + 1]["content"]
                history.append([user_msg, asst_msg])

        cfg = session.agent_config

        # Find display label for loaded model ID
        reverse_mapping = {v: k for k, v in id_mapping.items()}
        model_display_label = reverse_mapping.get(cfg.model, cfg.model)

        return (
            session,
            f"? Loaded: {session_name}",
            history,
            cfg,
            cfg.name,
            model_display_label,  # Return display label for dropdown
            cfg.system_prompt,
            cfg.temperature,
            cfg.top_p,
            "web_fetch" in cfg.tools
        )
    except Exception as exc:
        return None, f"? Load failed: {exc}", [], DEFAULT_AGENT_CONFIG, "", "", "", 0.7, 1.0, False


def new_session_handler() -> tuple[None, str, list, str]:
    """Clear current session and start fresh."""
    return None, "?? New session started", [], ""


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
        model_id_mapping_state = gr.State({
            choice[0]: choice[1] for choice in INITIAL_MODEL_CHOICES
        })
        current_session_state = gr.State(None)

        with gr.Row(equal_height=True):
            with gr.Column(scale=1):
                gr.Markdown("## Agent Configuration")
                agent_name = gr.Textbox(label="Agent Name", value="Test Agent")
                model_selector = gr.Dropdown(
                    label="Model",
                    choices=INITIAL_DROPDOWN_VALUES or [DEFAULT_MODEL_ID],
                    value=INITIAL_DROPDOWN_VALUES[0] if INITIAL_DROPDOWN_VALUES else DEFAULT_MODEL_ID,
                    filterable=True,
                    info="Start typing to search models by name or provider"
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

                with gr.Accordion("?? Session Management", open=False):
                    gr.Markdown("Save your configuration and chat history for later.")
                    session_name_input = gr.Textbox(
                        label="Session Name",
                        placeholder="experiment-gpt4-vs-claude",
                        info="Give this session a memorable name"
                    )
                    with gr.Row():
                        save_session_btn = gr.Button("?? Save", variant="secondary", scale=1)
                        load_session_btn = gr.Button("?? Load", variant="secondary", scale=1)
                        new_session_btn = gr.Button("?? New", variant="secondary", scale=1)

                    session_list = gr.Dropdown(
                        label="Saved Sessions",
                        choices=[],
                        value=None,
                        interactive=True,
                        info="Select a session to load"
                    )
                    session_status = gr.Markdown(value="_No active session_")

                with gr.Accordion("??? Run Tagging (optional)", open=False):
                    gr.Markdown("Tag your runs for easier analysis and comparison.")
                    experiment_id_input = gr.Textbox(
                        label="Experiment ID",
                        placeholder="prompt-optimization-v3",
                        info="?? Group related runs together (e.g., 'temperature-test', 'model-comparison')"
                    )
                    task_label_input = gr.Dropdown(
                        label="Task Type",
                        choices=["reasoning", "creative", "coding", "summarization", "analysis", "debugging", "other"],
                        value="other",
                        allow_custom_value=True,
                        info="Categorize what kind of task this run performs"
                    )
                    run_notes_input = gr.Textbox(
                        label="Run Notes",
                        placeholder="Testing impact of higher temperature on creative tasks...",
                        lines=2,
                        info="Free-form notes about this specific run"
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
                model_id_mapping_state,
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
                model_id_mapping_state,
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
                experiment_id_input,
                task_label_input,
                run_notes_input,
                model_id_mapping_state,  # NEW: for resolving display labels
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

        # Session management event handlers
        save_session_btn.click(
            fn=save_session_handler,
            inputs=[session_name_input, config_state, history_state, current_session_state],
            outputs=[current_session_state, session_status, session_list, session_list]
        )

        load_session_btn.click(
            fn=load_session_handler,
            inputs=[session_list, model_id_mapping_state],
            outputs=[
                current_session_state, session_status, history_state,
                config_state, agent_name, model_selector, system_prompt,
                temperature, top_p, web_tool_enabled
            ]
        )

        new_session_btn.click(
            fn=new_session_handler,
            outputs=[current_session_state, session_status, history_state, session_name_input]
        )

        # Populate session list on app load
        demo.load(
            fn=lambda: [(s[0], s[0]) for s in list_sessions()],
            outputs=[session_list]
        )

    return demo


if __name__ == "__main__":
    init_csv()
    print("Telemetry CSV initialized.")
    app = create_ui()
    # Security: Configurable server host binding with secure default
    server_host = getenv("GRADIO_SERVER_HOST", "127.0.0.1")
    app.launch(server_name=server_host, server_port=7860)
