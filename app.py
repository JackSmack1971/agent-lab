"""Phase 0 UI shell for Agent Lab."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from os import getenv
from pathlib import Path
from threading import Event
from typing import Any, AsyncGenerator, Literal, cast
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import gradio as gr
from dotenv import load_dotenv
from fastapi import Response
from loguru import logger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from agents.models import AgentConfig, RunRecord, Session
from agents.runtime import build_agent, run_agent_stream
from services.persist import append_run, init_csv, list_sessions, save_session, load_session
from services.catalog import get_model_choices, get_models
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path

ComponentUpdate = dict[str, Any]

# Prometheus metrics
REQUEST_COUNT = Counter('agent_lab_requests_total', 'Total number of requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('agent_lab_request_duration_seconds', 'Request duration in seconds', ['method', 'endpoint'])
HEALTH_CHECK_COUNT = Counter('agent_lab_health_checks_total', 'Total health checks', ['status'])
AGENT_BUILD_COUNT = Counter('agent_lab_agent_builds_total', 'Total agent builds', ['success'])
AGENT_RUN_COUNT = Counter('agent_lab_agent_runs_total', 'Total agent runs', ['aborted'])


def health_check() -> dict[str, Any]:
    """Perform health checks and return status information."""
    import httpx
    from agents.tools import fetch_url

    timestamp = datetime.now(timezone.utc).isoformat()

    # Check API key presence
    api_key_present = bool(getenv("OPENROUTER_API_KEY"))

    # Check database connectivity (data directory and CSV file)
    data_dir = Path("data")
    csv_file = data_dir / "runs.csv"
    database_ok = data_dir.exists() and csv_file.exists()

    # Check OpenRouter API connectivity
    api_connectivity_ok = False
    if api_key_present:
        try:
            # Simple connectivity check to OpenRouter models endpoint
            response = httpx.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {getenv('OPENROUTER_API_KEY')}"}, timeout=5.0)
            api_connectivity_ok = response.status_code == 200
        except Exception:
            api_connectivity_ok = False

    # Check web tool availability
    web_tool_ok = fetch_url is not None

    # Determine overall status
    critical_deps = [api_key_present, database_ok, api_connectivity_ok]
    optional_deps = [web_tool_ok]

    healthy_count = sum(critical_deps) + sum(optional_deps)
    total_deps = len(critical_deps) + len(optional_deps)

    if healthy_count == total_deps:
        status = "healthy"
    elif healthy_count >= len(critical_deps):
        status = "degraded"
    else:
        status = "unhealthy"

    HEALTH_CHECK_COUNT.labels(status=status).inc()

    return {
        "status": status,
        "version": "1.0.0",  # TODO: Read from package metadata
        "timestamp": timestamp,
        "dependencies": {
            "api_key": api_key_present,
            "database": database_ok,
            "api_connectivity": api_connectivity_ok,
            "web_tool": web_tool_ok,
        },
    }


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
        logger.warning("Failed to load models, using fallback catalog.")
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

    logger.info(
        "Model catalog loaded",
        extra={
            "model_count": len(display_choices),
            "source": source_enum,
            "source_label": source_label,
        }
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

# Configure loguru for structured logging
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    level="INFO",
    serialize=True,  # JSON format for production
)

# Security: never print the API key; warn the operator so they can add it securely.
if not getenv("OPENROUTER_API_KEY"):
    logger.warning(
        "OPENROUTER_API_KEY is not set. The UI will run in limited mode until a key is provided."
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
    """Validate agent name field with security checks."""
    from agents.tools import validate_agent_name_comprehensive

    security_result = validate_agent_name_comprehensive(name)
    if not security_result["is_valid"]:
        return {"status": "error", "message": f"❌ Agent Name: {security_result['message']}", "is_valid": False}

    # Additional UI-specific checks
    if not name or not name.strip():
        return {"status": "error", "message": "❌ Agent Name: This field is required", "is_valid": False}
    if len(name) > 100:
        return {"status": "error", "message": "❌ Agent Name: Maximum 100 characters allowed", "is_valid": False}
    return {"status": "success", "message": "✅ Agent Name is valid", "is_valid": True}

def validate_system_prompt(prompt: str) -> dict:
    """Validate system prompt field with security checks."""
    from agents.tools import validate_system_prompt_comprehensive

    security_result = validate_system_prompt_comprehensive(prompt)
    if not security_result["is_valid"]:
        return {"status": "error", "message": f"❌ System Prompt: {security_result['message']}", "is_valid": False}

    # Additional UI-specific checks
    if not prompt or not prompt.strip():
        return {"status": "error", "message": "❌ System Prompt: This field is required", "is_valid": False}
    if len(prompt) > 10000:
        return {"status": "error", "message": "❌ System Prompt: Maximum 10,000 characters allowed", "is_valid": False}
    return {"status": "success", "message": "✅ System Prompt is valid", "is_valid": True}

def validate_temperature(temp: str | float) -> dict:
    """Validate temperature field with robust validation."""
    from agents.tools import validate_temperature_robust

    security_result = validate_temperature_robust(temp)
    if not security_result["is_valid"]:
        return {"status": "error", "message": f"❌ Temperature: {security_result['message']}", "is_valid": False}

    return {"status": "success", "message": "✅ Temperature is valid", "is_valid": True}

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
class ThreadSafeLoadingStateManager:
    """
    Thread-safe loading state manager with proper concurrency handling.
    """

    def __init__(self):
        self._states: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def start_loading(self, operation_id: str, component: str) -> dict:
        """
        Start loading state for an operation with thread safety.
        """
        async with self._lock:
            if operation_id in self._states:
                # Operation already in progress
                return self._get_current_state(component)

            self._states[operation_id] = {
                "start_time": asyncio.get_event_loop().time(),
                "component": component
            }

            return self._get_loading_state(component)

    async def complete_loading(self, operation_id: str) -> dict:
        """
        Complete loading state for an operation.
        """
        async with self._lock:
            if operation_id not in self._states:
                return self._get_default_state()

            state = self._states.pop(operation_id)
            component = state["component"]

            return self._get_completed_state(component)

    async def cancel_loading(self, operation_id: str) -> dict:
        """
        Cancel loading state for an operation.
        """
        async with self._lock:
            state = self._states.pop(operation_id, None)
            if not state:
                return self._get_default_state()

            component = state["component"]
            return self._get_cancelled_state(component)

    def _get_loading_state(self, component: str) -> dict:
        """Get loading state for component."""
        if component == "button":
            return {"interactive": False, "value": "Loading..."}
        elif component == "panel":
            return {"visible": True, "value": "Loading..."}
        return {}

    def _get_completed_state(self, component: str) -> dict:
        """Get completed state for component."""
        if component == "button":
            return {"interactive": True, "value": "Send Message"}
        elif component == "panel":
            return {"visible": False, "value": ""}
        return {}

    def _get_cancelled_state(self, component: str) -> dict:
        """Get cancelled state for component."""
        if component == "button":
            return {"interactive": True, "value": "Cancelled"}
        elif component == "panel":
            return {"visible": False, "value": "Cancelled"}
        return {}

    def _get_default_state(self) -> dict:
        """Get default state."""
        return {}

    def _get_current_state(self, component: str) -> dict:
        """Get current state for component."""
        return self._get_loading_state(component)

# Global loading state manager
loading_manager = ThreadSafeLoadingStateManager()


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
        AGENT_BUILD_COUNT.labels(success='true').inc()
    except Exception as exc:  # pragma: no cover - runtime guard
        AGENT_BUILD_COUNT.labels(success='false').inc()
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
        logger.warning("Model refresh failed; falling back to cached list.")
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


async def send_message_streaming_fixed(
    message: str,
    history: list[list[str]] | None,
    config_state: AgentConfig,
    model_source_enum: str,
    agent_state: Any,
    cancel_event_state: Event | None,
    is_generating_state: bool,
    experiment_id: str,
    task_label: str,
    run_notes: str,
    id_mapping: dict
) -> AsyncGenerator[tuple, None]:
    """
    Fixed streaming message handler with proper state management.

    Key improvements:
    - Immediate cancellation check before processing
    - Proper cleanup on cancellation
    - State validation before yielding
    - Error recovery with meaningful messages
    """
    correlation_id = f"stream_{asyncio.get_event_loop().time()}"

    try:
        # Input validation and sanitization
        if not message or not message.strip():
            yield (
                None,  # chat_history
                None,  # agent_display
                "Enter a message to send to the agent.",  # status_message
                gr.update(interactive=True),  # send_button
                gr.update(visible=False),  # cancel_button
                None,  # model_display
                None,  # agent_state
                cancel_event_state,  # cancel_event
                False,  # is_generating
                None,  # experiment_id_display
                None,  # task_label_display
                None,  # run_notes_display
                None,  # metadata_display
            )
            return

        sanitized_message = message.strip()
        if len(sanitized_message) > 10000:  # Reasonable message limit
            yield (
                None,
                None,
                "Message too long. Please limit to 10,000 characters.",
                gr.update(interactive=True),
                gr.update(visible=False),
                None, None, None, False, None, None, None, None
            )
            return

        # Check for immediate cancellation
        if cancel_event_state and cancel_event_state.is_set():
            yield (
                history,
                None,
                "Generation cancelled before starting.",
                gr.update(interactive=True),
                gr.update(visible=False),
                None, None, None, False, None, None, None, None
            )
            return

        # Build agent with error handling
        try:
            include_web = "web_fetch" in getattr(config_state, 'tools', [])
            agent = build_agent(config_state, include_web=include_web)
        except Exception as e:
            logger.error("Failed to build agent", extra={"error": str(e)})
            yield (
                history,
                None,
                f"Failed to initialize agent: {str(e)}",
                gr.update(interactive=True),
                gr.update(visible=False),
                None, None, None, False, None, None, None, None
            )
            return

        # Initialize streaming state
        collected_deltas = []
        start_time = asyncio.get_event_loop().time()

        def on_delta(delta: str) -> None:
            """Accumulate streaming deltas."""
            if delta and not (cancel_event_state and cancel_event_state.is_set()):
                collected_deltas.append(delta)

        # Create new cancel event if none provided
        active_cancel_event = cancel_event_state or Event()

        # Yield initial streaming state
        yield (
            history,
            None,
            "Generating response...",
            gr.update(interactive=False),
            gr.update(visible=True),
            None,
            agent,
            active_cancel_event,
            True,
            experiment_id or "",
            task_label or "",
            run_notes or "",
            None
        )

        # Perform streaming with comprehensive error handling
        try:
            stream_result = await run_agent_stream(
                agent, sanitized_message, on_delta, active_cancel_event,
                correlation_id=correlation_id
            )

            # Check if cancelled during streaming
            if active_cancel_event.is_set() or stream_result.aborted:
                final_text = "".join(collected_deltas)
                status_msg = f"Generation cancelled. Partial response: {len(final_text)} characters."
            else:
                final_text = stream_result.text
                status_msg = "Response generated"

            # Prepare final history
            new_history = history or []
            new_history.append([sanitized_message, final_text])

            # Persist run data
            try:
                run_record = RunRecord(
                    ts=datetime.now(timezone.utc),
                    agent_name=config_state.name,
                    model=config_state.model,
                    prompt_tokens=stream_result.usage.get("prompt_tokens", 0) if stream_result.usage else 0,
                    completion_tokens=stream_result.usage.get("completion_tokens", 0) if stream_result.usage else 0,
                    total_tokens=stream_result.usage.get("total_tokens", 0) if stream_result.usage else 0,
                    latency_ms=stream_result.latency_ms,
                    cost_usd=0.0,  # TODO: Implement calculate_cost function
                    experiment_id=experiment_id or "",
                    task_label=task_label or "",
                    run_notes=run_notes or "",
                    streaming=True,
                    model_list_source=cast(Literal["dynamic", "fallback"], model_source_enum if model_source_enum in ["dynamic", "fallback"] else "fallback"),
                    tool_web_enabled=include_web,
                    web_status="ok" if include_web else "off",
                    aborted=stream_result.aborted
                )
                await asyncio.to_thread(append_run, run_record, correlation_id)
            except Exception as e:
                logger.warning("Failed to persist run data", extra={"error": str(e)})
                # Don't fail the UI for persistence errors

            # Final yield with complete state
            yield (
                new_history,
                None,
                status_msg,
                gr.update(interactive=True),
                gr.update(visible=False),
                None,
                None,
                None,
                False,
                experiment_id or "",
                task_label or "",
                run_notes or "",
                {
                    "latency_ms": stream_result.latency_ms,
                    "usage": stream_result.usage,
                    "aborted": stream_result.aborted
                }
            )

        except Exception as e:
            logger.error("Streaming failed", extra={"error": str(e), "correlation_id": correlation_id})
            error_msg = f"Generation failed: {str(e)}"

            # Yield error state
            yield (
                history,
                None,
                error_msg,
                gr.update(interactive=True),
                gr.update(visible=False),
                None, None, None, False, None, None, None, None
            )

    except Exception as e:
        logger.error("Unexpected error in send_message_streaming", extra={"error": str(e)})
        yield (
            history,
            None,
            f"Unexpected error: {str(e)}",
            gr.update(interactive=True),
            gr.update(visible=False),
            None, None, None, False, None, None, None, None
        )


def stop_generation(
    cancel_event: Event | None,
    is_generating: bool,
) -> tuple[str, Event | None, bool, ComponentUpdate | None, ComponentUpdate | None]:
    """Signal the active stream to stop safely when requested by the user."""

    if cancel_event and hasattr(cancel_event, 'set'):
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
) -> tuple[Session | None, str, list, AgentConfig, str, str, str, float, float, bool, list, dict]:
    """Load session from disk and restore all state."""
    if not session_name:
        return None, "?? Select a session to load", [], DEFAULT_AGENT_CONFIG, "", "", "", 0.7, 1.0, False, [], {}

    try:
        sessions = {s[0]: s[1] for s in list_sessions()}
        if session_name not in sessions:
            return None, f"? Session not found: {session_name}", [], DEFAULT_AGENT_CONFIG, "", "", "", 0.7, 1.0, False, [], {}

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

        # Prepare metadata for display
        metadata = {
            "id": session.id,
            "created_at": session.created_at.isoformat(),
            "agent_config": cfg.model_dump(),
            "model_id": session.model_id,
            "notes": session.notes
        }

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
            "web_fetch" in cfg.tools,
            history,  # transcript_preview
            metadata  # session_metadata
        )
    except Exception as exc:
        return None, f"? Load failed: {exc}", [], DEFAULT_AGENT_CONFIG, "", "", "", 0.7, 1.0, False, [], {}


def new_session_handler() -> tuple[None, str, list, str, list, dict]:
    """Clear current session and start fresh."""
    return None, "?? New session started", [], "", [], {}


def create_ui() -> gr.Blocks:
    """Construct the tabbed Gradio Blocks layout for Agent Lab optimized for 16:9 displays."""

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

        with gr.Tabs(elem_id="main-tabs"):
            with gr.TabItem("Chat", elem_id="chat-tab"):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=2):
                        chatbot = gr.Chatbot(label="Conversation", height=700)
                    with gr.Column(scale=1):
                        with gr.Accordion("Message Input", open=True):
                            user_input = gr.Textbox(
                                label="Your Message",
                                lines=3,
                                placeholder="Type your message here...",
                                elem_id="chat-input"
                            )
                            with gr.Row():
                                send_btn = gr.Button("Send", variant="primary", elem_id="send-btn")
                                stop_btn = gr.Button("Stop", variant="stop", visible=False, interactive=False, elem_id="stop-btn")
                        with gr.Accordion("Experiment Tagging (optional)", open=False):
                            experiment_id_input = gr.Textbox(
                                label="Experiment ID",
                                placeholder="prompt-optimization-v3",
                                info="Group related runs together (e.g., 'temperature-test', 'model-comparison')"
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

            with gr.TabItem("Configuration", elem_id="config-tab"):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=1):
                        gr.Markdown("## Agent Configuration")
                        agent_name = gr.Textbox(
                            label="Agent Name",
                            value="Test Agent",
                            elem_id="agent-name"
                        )
                        model_selector = gr.Dropdown(
                            label="Model",
                            choices=INITIAL_DROPDOWN_VALUES or [DEFAULT_MODEL_ID],
                            value=INITIAL_DROPDOWN_VALUES[0] if INITIAL_DROPDOWN_VALUES else DEFAULT_MODEL_ID,
                            filterable=True,
                            info="Start typing to search models by name or provider",
                            elem_id="model-selector"
                        )
                        model_source_indicator = gr.Markdown(
                            value=_format_source_display(INITIAL_MODEL_SOURCE_LABEL),
                            elem_id="model-source"
                        )
                        refresh_models_button = gr.Button(
                            "Refresh Models",
                            variant="secondary",
                            elem_id="refresh-models"
                        )
                        system_prompt = gr.Textbox(
                            label="System Prompt",
                            lines=8,
                            value="You are a helpful assistant.",
                            elem_id="system-prompt"
                        )
                        temperature = gr.Slider(
                            label="Temperature",
                            minimum=0.0,
                            maximum=2.0,
                            value=0.7,
                            step=0.1,
                            elem_id="temperature"
                        )
                        top_p = gr.Slider(
                            label="Top-p",
                            minimum=0.0,
                            maximum=1.0,
                            value=1.0,
                            step=0.05,
                            elem_id="top-p"
                        )
                        web_tool_enabled = gr.Checkbox(
                            label="Enable Web Fetch Tool",
                            value=False,
                            elem_id="web-tool"
                        )
                        with gr.Row():
                            build_agent = gr.Button("Build Agent", variant="primary", elem_id="build-agent")
                            reset_agent = gr.Button("Reset", variant="secondary", elem_id="reset-agent")

                    with gr.Column(scale=1):
                        gr.Markdown("## Model Information & Validation")
                        web_badge = gr.HTML(
                            value="<span style=\"background:#666;color:white;padding:4px 8px;border-radius:4px;\">Web Tool: OFF</span>",
                            elem_id="web-badge"
                        )
                        validation_status = gr.Markdown(
                            value="Ready to build agent",
                            elem_id="validation-status"
                        )

            with gr.TabItem("Sessions", elem_id="sessions-tab"):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=1):
                        gr.Markdown("## Session Management")
                        session_name_input = gr.Textbox(
                            label="Session Name",
                            placeholder="experiment-gpt4-vs-claude",
                            info="Give this session a memorable name",
                            elem_id="session-name"
                        )
                        with gr.Row():
                            save_session_btn = gr.Button("Save", variant="secondary", scale=1, elem_id="save-session")
                            load_session_btn = gr.Button("Load", variant="secondary", scale=1, elem_id="load-session")
                            new_session_btn = gr.Button("New", variant="secondary", scale=1, elem_id="new-session")
                        session_list = gr.Dropdown(
                            label="Saved Sessions",
                            choices=[],
                            value=None,
                            interactive=True,
                            info="Select a session to load",
                            elem_id="session-list"
                        )
                        session_status = gr.Markdown(
                            value="_No active session_",
                            elem_id="session-status"
                        )

                    with gr.Column(scale=1):
                        gr.Markdown("## Session Details")
                        transcript_preview = gr.Chatbot(
                            label="Transcript Preview",
                            height=400,
                            elem_id="transcript-preview"
                        )
                        session_metadata = gr.JSON(
                            label="Session Metadata",
                            elem_id="session-metadata"
                        )

            with gr.TabItem("Analytics", elem_id="analytics-tab"):
                with gr.Row(equal_height=True):
                    with gr.Column(scale=1):
                        gr.Markdown("## Run Statistics")
                        run_info_display = gr.Markdown(
                            value="No runs yet",
                            elem_id="run-info"
                        )
                        download_csv = gr.Button(
                            "Download runs.csv",
                            elem_id="download-csv"
                        )

                    with gr.Column(scale=1):
                        gr.Markdown("## Visualizations")
                        # Placeholder for future chart implementations
                        analytics_placeholder = gr.Markdown(
                            value="Charts and visualizations will be implemented here",
                            elem_id="analytics-charts"
                        )

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
            fn=send_message_streaming_fixed,
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
                temperature, top_p, web_tool_enabled, transcript_preview, session_metadata
            ]
        )

        new_session_btn.click(
            fn=new_session_handler,
            outputs=[current_session_state, session_status, history_state, session_name_input, transcript_preview, session_metadata]
        )

        # Populate session list on app load
        demo.load(
            fn=lambda: [(s[0], s[0]) for s in list_sessions()],
            outputs=[session_list]
        )

    return demo


if __name__ == "__main__":
    init_csv()

    # Add health check endpoint
    app = create_ui()
    app.app.add_api_route("/health", health_check, methods=["GET"])

    # Add Prometheus metrics endpoint
    def metrics():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.app.add_api_route("/metrics", metrics, methods=["GET"])

    # Security: Configurable server host binding with secure default
    server_host = getenv("GRADIO_SERVER_HOST", "127.0.0.1")
    app.launch(server_name=server_host, server_port=7860)
    print("Telemetry CSV initialized.")
