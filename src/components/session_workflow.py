"""Session workflow integration component for Agent Lab.

This module provides session management workflows including auto-save prompts,
session status indicators, and session switching functionality.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from uuid import uuid4
import gradio as gr

from agents.models import Session
from services.persist import save_session, load_session, list_sessions


class SessionWorkflowManager:
    """Manages session-related workflows and user prompts."""

    def __init__(self):
        self.session_state: Dict[str, Dict[str, Any]] = {}
        self.save_prompts_shown: set = set()

    async def check_save_prompt_needed(self, session_id: str, message_count: int) -> bool:
        """Determine if a save prompt should be shown.

        Args:
            session_id: Current session ID
            message_count: Number of messages in session

        Returns:
            True if save prompt should be shown
        """
        if message_count >= 5 and session_id not in self.save_prompts_shown:
            # Check if session has unsaved changes
            session_state = await self._get_session_state(session_id)
            return session_state.get("has_unsaved_changes", False)

        return False

    async def show_save_prompt(self, session_id: str) -> Dict[str, Any]:
        """Show a save prompt for the current session.

        Args:
            session_id: Current session ID

        Returns:
            Dict with prompt data
        """
        session_info = await self._get_session_info(session_id)

        prompt_data = {
            "session_name": session_info.get("name", "Untitled Session"),
            "message_count": session_info.get("message_count", 0),
            "last_activity": session_info.get("last_modified", datetime.now(timezone.utc))
        }

        # Mark prompt as shown
        self.save_prompts_shown.add(session_id)

        return {
            "show_prompt": True,
            "prompt_type": "save_session",
            "data": prompt_data
        }

    async def handle_save_action(self, session_id: str, action: str, custom_name: str = "") -> Dict[str, Any]:
        """Handle save prompt actions.

        Args:
            session_id: Current session ID
            action: Action taken ("save_draft", "save_custom", "dismiss")
            custom_name: Custom name for session (if action is "save_custom")

        Returns:
            Dict with action result
        """
        if action == "save_draft":
            name = f"Draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            await self._save_session(session_id, name)
            return {"action": "saved", "name": name}

        elif action == "save_custom":
            if custom_name:
                await self._save_session(session_id, custom_name)
                return {"action": "saved", "name": custom_name}
            else:
                return {"action": "error", "message": "Custom name is required"}

        elif action == "dismiss":
            # Mark as dismissed for this session
            self.save_prompts_shown.add(session_id)
            return {"action": "dismissed"}

        return {"action": "error", "message": "Unknown action"}

    async def _get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get session state information."""
        # In a real implementation, this would query the session service
        return self.session_state.get(session_id, {"has_unsaved_changes": True})

    async def _get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session information."""
        # In a real implementation, this would query the session service
        return self.session_state.get(session_id, {
            "name": f"Session {session_id[:8]}",
            "message_count": 0,
            "last_modified": datetime.now(timezone.utc)
        })

    async def _save_session(self, session_id: str, name: str) -> None:
        """Save session with given name."""
        # In a real implementation, this would call the session service
        # For now, just update our local state
        if session_id in self.session_state:
            self.session_state[session_id]["has_unsaved_changes"] = False
            self.session_state[session_id]["name"] = name
            self.session_state[session_id]["last_modified"] = datetime.now(timezone.utc)


def render_session_status_indicator(session_id: str, status: Dict[str, Any]) -> str:
    """Render visual indicators for session state.

    Args:
        session_id: Session identifier
        status: Status dictionary with state, last_modified, etc.

    Returns:
        HTML string for status indicator
    """
    status_icon = ""
    status_class = ""
    status_text = ""

    state = status.get("state", "unsaved")

    if state == "saved":
        status_icon = "✅"
        status_class = "status-saved"
        status_text = "Saved"
    elif state == "unsaved":
        status_icon = "🟠"
        status_class = "status-unsaved"
        status_text = "Unsaved changes"
    elif state == "saving":
        status_icon = "⏳"
        status_class = "status-saving"
        status_text = "Saving..."
    elif state == "error":
        status_icon = "❌"
        status_class = "status-error"
        status_text = "Save failed"
    else:
        status_icon = "❓"
        status_class = "status-unknown"
        status_text = "Unknown"

    last_modified = status.get("last_modified")
    if last_modified:
        if isinstance(last_modified, datetime):
            time_display = format_relative_time(last_modified)
            status_text += f" {time_display}"

    return f"""
    <div class="session-status {status_class}" id="status-{session_id}">
        <span class="status-icon">{status_icon}</span>
        <span class="status-text">{status_text}</span>
    </div>
    """


def render_session_switcher(current_session_id: str, recent_sessions: List[Dict[str, Any]]) -> str:
    """Render the session switcher dropdown.

    Args:
        current_session_id: Currently active session ID
        recent_sessions: List of recent session dictionaries

    Returns:
        HTML string for session switcher
    """
    current_session = next(
        (s for s in recent_sessions if s.get("id") == current_session_id),
        {"name": "Current Session", "last_modified": datetime.now(timezone.utc)}
    )

    html = f"""
    <div class="session-switcher">
        <div class="current-session">
            <span class="label">Current Session:</span>
            <span class="name">{current_session['name']}</span>
            {render_session_status_indicator(current_session_id, current_session.get('status', {}))}
        </div>

        <div class="session-dropdown">
            <select onchange="switchSession(this.value)">
                <option value="">Switch Session...</option>
    """

    for session in recent_sessions:
        selected = "selected" if session.get('id') == current_session_id else ""
        modified_time = format_relative_time(session.get('last_modified', datetime.now(timezone.utc)))
        html += f"""
        <option value="{session['id']}" {selected}>
            {session['name']} ({modified_time})
        </option>
        """

    html += """
            </select>
        </div>

        <div class="session-actions">
            <button onclick="saveCurrentSession()">Save Current</button>
        </div>
    </div>
    """

    return html


def format_relative_time(dt: datetime) -> str:
    """Format a datetime as relative time (e.g., '2 hours ago').

    Args:
        dt: Datetime to format

    Returns:
        Relative time string
    """
    if not isinstance(dt, datetime):
        return "recently"

    now = datetime.now(timezone.utc)
    diff = now - dt

    if diff.days > 0:
        if diff.days == 1:
            return "1 day ago"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return dt.strftime("%b %d")
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "just now"


def render_save_prompt_toast(prompt_data: Dict[str, Any]) -> str:
    """Render a save prompt as a toast notification.

    Args:
        prompt_data: Prompt data from show_save_prompt

    Returns:
        HTML string for toast notification
    """
    session_name = prompt_data.get("session_name", "Untitled Session")
    message_count = prompt_data.get("message_count", 0)

    return f"""
    <div class="save-prompt-toast" role="dialog" aria-labelledby="save-prompt-title">
        <div class="toast-header">
            <h4 id="save-prompt-title">💾 Save Session?</h4>
            <button class="toast-close" onclick="dismissSavePrompt()" aria-label="Dismiss">×</button>
        </div>
        <div class="toast-body">
            <p>Your conversation with <strong>{session_name}</strong> has grown to {message_count} messages.</p>
            <p>Save your progress to avoid losing it?</p>
        </div>
        <div class="toast-actions">
            <button class="btn-secondary" onclick="saveAsDraft()">Save as Draft</button>
            <button class="btn-primary" onclick="saveWithCustomName()">Save with Name</button>
            <button class="btn-link" onclick="dismissSavePrompt()">Dismiss</button>
        </div>
    </div>
    """


def create_session_status_component(session_id: str = "current") -> gr.HTML:
    """Create a session status indicator component.

    Args:
        session_id: Session identifier

    Returns:
        Gradio HTML component for status display
    """
    return gr.HTML(
        value=render_session_status_indicator(session_id, {"state": "unsaved"}),
        elem_id=f"session-status-{session_id}",
        elem_classes=["session-status-component"]
    )


def create_session_switcher_component() -> gr.HTML:
    """Create a session switcher component.

    Returns:
        Gradio HTML component for session switching
    """
    return gr.HTML(
        value=render_session_switcher("", []),
        elem_id="session-switcher",
        elem_classes=["session-switcher-component"]
    )


def create_save_prompt_component() -> gr.HTML:
    """Create a save prompt toast component.

    Returns:
        Gradio HTML component for save prompts
    """
    return gr.HTML(
        value="",
        elem_id="save-prompt-toast",
        visible=False,
        elem_classes=["save-prompt-component"]
    )


# Global session workflow manager instance
session_workflow_manager = SessionWorkflowManager()


# CSS for session workflow components
SESSION_WORKFLOW_CSS = """
.session-status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
}

.status-saved {
    background: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.status-unsaved {
    background: #fff3cd;
    color: #856404;
    border: 1px solid #ffeaa7;
}

.status-saving {
    background: #cce7ff;
    color: #004085;
    border: 1px solid #99d6ff;
}

.status-error {
    background: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.status-icon {
    font-size: 14px;
}

.status-text {
    white-space: nowrap;
}

.session-switcher {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    background: #f8f9fa;
    border-radius: 6px;
    border: 1px solid #e9ecef;
}

.current-session {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.current-session .label {
    font-weight: 500;
    color: #495057;
}

.current-session .name {
    font-weight: 600;
    color: #212529;
}

.session-dropdown select {
    min-width: 200px;
    padding: 6px 8px;
    border: 1px solid #ced4da;
    border-radius: 4px;
    background: white;
}

.session-actions {
    display: flex;
    gap: 8px;
}

.session-actions button {
    padding: 6px 12px;
    border: 1px solid #007bff;
    background: #007bff;
    color: white;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: background-color 0.2s;
}

.session-actions button:hover {
    background: #0056b3;
}

.save-prompt-toast {
    position: fixed;
    top: 20px;
    right: 20px;
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    min-width: 300px;
    max-width: 400px;
    z-index: 10000;
}

.toast-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #e9ecef;
}

.toast-header h4 {
    margin: 0;
    font-size: 16px;
    color: #495057;
}

.toast-close {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    color: #6c757d;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.toast-body {
    padding: 16px;
}

.toast-body p {
    margin: 8px 0;
    color: #495057;
    line-height: 1.5;
}

.toast-actions {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid #e9ecef;
    justify-content: flex-end;
}

.btn-primary {
    background: #007bff;
    color: white;
    border: 1px solid #007bff;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
}

.btn-secondary {
    background: #6c757d;
    color: white;
    border: 1px solid #6c757d;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
}

.btn-link {
    background: none;
    color: #007bff;
    border: none;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 12px;
    text-decoration: underline;
}

.btn-primary:hover {
    background: #0056b3;
}

.btn-secondary:hover {
    background: #545b62;
}

.btn-link:hover {
    color: #0056b3;
}
"""