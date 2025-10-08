"""Visual loading states and progress indicators component for Agent Lab.

This module provides loading overlays, skeleton screens, and progress bars
for various asynchronous operations throughout the application.
"""

import asyncio
from typing import Dict, Any, Optional, List
import gradio as gr
from datetime import datetime


class LoadingStateManager:
    """Manages loading states across the application with thread-safe operations."""

    def __init__(self):
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def start_loading(self, operation_id: str, operation_type: str, message: str) -> Dict[str, Any]:
        """Start a loading state for an operation.

        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation (e.g., "message_send", "model_refresh")
            message: Loading message to display

        Returns:
            Dict with UI state updates
        """
        async with self._lock:
            self.active_operations[operation_id] = {
                "type": operation_type,
                "message": message,
                "start_time": datetime.now(),
                "progress": 0
            }

            # Return UI state updates
            return {
                "loading_visible": True,
                "loading_message": message,
                "progress_visible": self._should_show_progress(operation_type),
                "progress_value": 0,
                "buttons_disabled": self._get_buttons_to_disable(operation_type)
            }

    async def update_progress(self, operation_id: str, progress: float, message: str) -> Dict[str, Any]:
        """Update progress for an ongoing operation.

        Args:
            operation_id: Operation identifier
            progress: Progress percentage (0-100)
            message: Updated status message

        Returns:
            Dict with progress updates
        """
        async with self._lock:
            if operation_id in self.active_operations:
                self.active_operations[operation_id]["progress"] = progress
                self.active_operations[operation_id]["message"] = message

                return {
                    "loading_message": message,
                    "progress_value": progress
                }

        return {}

    async def complete_loading(self, operation_id: str, success: bool = True) -> Dict[str, Any]:
        """Complete a loading operation.

        Args:
            operation_id: Operation identifier
            success: Whether the operation succeeded

        Returns:
            Dict with completion updates
        """
        async with self._lock:
            if operation_id in self.active_operations:
                operation = self.active_operations[operation_id]
                duration = datetime.now() - operation["start_time"]

                # Log completion
                print(f"Operation {operation_id} completed in {duration.total_seconds():.2f}s")

                del self.active_operations[operation_id]

                return {
                    "loading_visible": False,
                    "progress_visible": False,
                    "buttons_disabled": [],
                    "success_message": "Operation completed successfully" if success else None,
                    "error_message": None if success else "Operation failed"
                }

            # For nonexistent operations, still return loading_visible: False to ensure UI consistency
            return {
                "loading_visible": False,
                "progress_visible": False,
                "buttons_disabled": [],
                "success_message": None,
                "error_message": None
            }

    def _should_show_progress(self, operation_type: str) -> bool:
        """Determine if progress bar should be shown for operation type."""
        progress_operations = ["session_load", "model_refresh", "data_export", "message_send"]
        return operation_type in progress_operations

    def _get_buttons_to_disable(self, operation_type: str) -> List[str]:
        """Return list of button IDs to disable during operation."""
        disable_map = {
            "message_send": ["send-btn", "stop-btn"],
            "session_save": ["save-btn", "load-btn"],
            "model_refresh": ["refresh-models", "build-agent"],
            "session_load": ["load-session", "save-session", "new-session"]
        }
        return disable_map.get(operation_type, [])


def render_loading_overlay(operation_type: str, message: str, progress: float) -> str:
    """Render a loading overlay with appropriate visual elements.

    Args:
        operation_type: Type of operation being performed
        message: Current status message
        progress: Progress percentage (0-100)

    Returns:
        HTML string for the loading overlay
    """
    # Choose appropriate loading animation
    animation_type = get_animation_for_operation(operation_type)

    html = """
    <div class="loading-overlay" role="status" aria-live="polite">
        <div class="loading-content">
    """

    # Add loading animation
    if animation_type == "spinner":
        html += '<div class="loading-spinner" aria-hidden="true"></div>'
    elif animation_type == "skeleton":
        html += render_skeleton_loader(operation_type)
    elif animation_type == "progress":
        html += f'<div class="progress-bar"><div class="progress-fill" style="width: {progress}%"></div></div>'

    # Add message
    html += f'<div class="loading-message">{message}</div>'

    # Add cancel button for cancellable operations
    if is_cancellable(operation_type):
        html += '<button class="cancel-btn" onclick="cancelOperation()">Cancel</button>'

    html += """
        </div>
    </div>
    """

    return html


def render_skeleton_loader(operation_type: str) -> str:
    """Render skeleton loading placeholders matching the content structure with enhanced animations.

    Args:
        operation_type: Type of operation for skeleton type

    Returns:
        HTML string with skeleton placeholders
    """
    if operation_type == "message_send":
        return """
        <div class="skeleton-chat">
            <div class="skeleton-avatar"></div>
            <div class="skeleton-content">
                <div class="skeleton-line short"></div>
                <div class="skeleton-line medium"></div>
                <div class="skeleton-line long"></div>
            </div>
        </div>
        """
    elif operation_type == "session_load":
        return """
        <div class="skeleton-session">
            <div class="skeleton-header">
                <div class="skeleton-line wide"></div>
                <div class="skeleton-line medium"></div>
            </div>
            <div class="skeleton-body">
                <div class="skeleton-line wide"></div>
                <div class="skeleton-line wide"></div>
                <div class="skeleton-line medium"></div>
            </div>
        </div>
        """
    elif operation_type == "model_refresh":
        return """
        <div class="skeleton-models">
            <div class="skeleton-model-card" data-count="3">
                <div class="skeleton-line wide"></div>
                <div class="skeleton-line medium"></div>
                <div class="skeleton-line short"></div>
            </div>
        </div>
        """
    else:
        return '<div class="skeleton-line medium"></div>'


def get_animation_for_operation(operation_type: str) -> str:
    """Get the appropriate animation type for an operation.

    Args:
        operation_type: Type of operation

    Returns:
        Animation type ("spinner", "skeleton", "progress")
    """
    animation_map = {
        "message_send": "skeleton",
        "model_refresh": "progress",
        "session_load": "progress",
        "session_save": "spinner",
        "data_export": "progress"
    }
    return animation_map.get(operation_type, "spinner")


def is_cancellable(operation_type: str) -> bool:
    """Check if an operation type can be cancelled.

    Args:
        operation_type: Type of operation

    Returns:
        True if operation can be cancelled
    """
    cancellable_ops = ["message_send", "model_refresh", "data_export"]
    return operation_type in cancellable_ops


def render_success_feedback(message: str = "Operation completed successfully", duration_ms: int = 1000) -> str:
    """Render success feedback with checkmark animation.

    Args:
        message: Success message to display
        duration_ms: Duration to show feedback (1000ms default)

    Returns:
        HTML string for success feedback
    """
    return f"""
    <div class="success-feedback" id="success-feedback-{hash(message)}">
        <svg class="success-checkmark checkmark-animation" viewBox="0 0 24 24">
            <path d="M5 13l4 4L19 7" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>{message}</span>
    </div>
    <script>
    (function() {{
        // Display duration: {duration_ms}ms
        const feedback = document.querySelector('#success-feedback-{hash(message)}');

        if (feedback) {{
            // Check for reduced motion preference
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

            if (prefersReducedMotion) {{
                feedback.classList.add('show');
                setTimeout(() => {{
                    feedback.remove();
                }}, {duration_ms});
                return;
            }}

            // Show with animation
            feedback.classList.add('show');

            setTimeout(() => {{
                feedback.classList.add('hide');
                setTimeout(() => {{
                    feedback.remove();
                }}, 300);
            }}, {duration_ms});
        }}
    }})();
    </script>
    """


def render_enhanced_progress_bar(progress: float, show_percentage: bool = True) -> str:
    """Render an enhanced progress bar with smooth animations.

    Args:
        progress: Progress percentage (0-100)
        show_percentage: Whether to show percentage text

    Returns:
        HTML string for enhanced progress bar
    """
    percentage_text = f"{progress:.1f}%" if show_percentage else ""

    return f"""
    <div class="progress-bar-enhanced">
        <div class="progress-fill-enhanced" style="width: {progress}%"></div>
    </div>
    {f'<div class="progress-text">{percentage_text}</div>' if show_percentage else ''}
    """


def create_success_feedback_component() -> gr.HTML:
    """Create a success feedback component.

    Returns:
        Gradio HTML component for success feedback
    """
    return gr.HTML(
        value="",
        elem_id="success-feedback",
        visible=False,
        elem_classes=["success-feedback-component"]
    )


def create_enhanced_progress_component() -> gr.HTML:
    """Create an enhanced progress bar component.

    Returns:
        Gradio HTML component for enhanced progress
    """
    return gr.HTML(
        value="",
        elem_id="enhanced-progress",
        visible=False,
        elem_classes=["enhanced-progress-component"]
    )


def create_loading_overlay_component(operation_type: str = "general") -> gr.HTML:
    """Create a Gradio HTML component for loading overlay.

    Args:
        operation_type: Type of operation for initial setup

    Returns:
        Gradio HTML component for loading overlay
    """
    return gr.HTML(
        value="",
        elem_id=f"loading-{operation_type}",
        visible=False,
        elem_classes=["loading-overlay-component"]
    )


def create_progress_bar_component() -> gr.HTML:
    """Create a progress bar component.

    Returns:
        Gradio HTML component for progress bar
    """
    return gr.HTML(
        value="",
        elem_id="progress-bar",
        visible=False,
        elem_classes=["progress-bar-component"]
    )


# Global loading state manager instance
loading_manager = LoadingStateManager()


# CSS for loading states
LOADING_STATES_CSS = """
.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(255, 255, 255, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    backdrop-filter: blur(2px);
}

.loading-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 24px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    min-width: 200px;
}

.loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.loading-message {
    color: #333;
    font-size: 14px;
    text-align: center;
    max-width: 300px;
}

.progress-bar {
    width: 200px;
    height: 8px;
    background: #f0f0f0;
    border-radius: 4px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: #3498db;
    transition: width 0.3s ease;
}

.cancel-btn {
    background: #dc3545;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 12px;
    cursor: pointer;
    transition: background-color 0.2s;
}

.cancel-btn:hover {
    background: #c82333;
}

/* Enhanced skeleton loading styles */
.skeleton-chat {
    display: flex;
    gap: 12px;
    width: 100%;
    max-width: 500px;
    padding: 16px;
}

.skeleton-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    flex-shrink: 0;
}

.skeleton-content {
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
}

.skeleton-session {
    display: flex;
    flex-direction: column;
    gap: 16px;
    width: 100%;
    max-width: 400px;
    padding: 20px;
}

.skeleton-header {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.skeleton-body {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.skeleton-models {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 16px;
    width: 100%;
}

.skeleton-model-card {
    padding: 16px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: white;
}

.skeleton-model-card .skeleton-line {
    margin-bottom: 8px;
}

.skeleton-model-card .skeleton-line:last-child {
    margin-bottom: 0;
}

.skeleton-line {
    height: 16px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 4px;
}

.skeleton-line.short {
    width: 60%;
}

.skeleton-line.medium {
    width: 80%;
}

.skeleton-line.long {
    width: 100%;
}

.skeleton-line.wide {
    width: 100%;
    height: 20px;
}

@keyframes skeleton-loading {
    0% {
        background-position: 200% 0;
    }
    100% {
        background-position: -200% 0;
    }
}

/* Success feedback styles */
.success-feedback {
    position: fixed;
    top: 20px;
    right: 20px;
    background: #4CAF50;
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
    display: flex;
    align-items: center;
    gap: 8px;
    z-index: 1000;
    transform: translateX(100%);
    opacity: 0;
    transition: transform 300ms ease-out, opacity 300ms ease-out;
}

.success-feedback.show {
    transform: translateX(0);
    opacity: 1;
}

.success-feedback.hide {
    transform: translateX(100%);
    opacity: 0;
}

.success-checkmark {
    width: 20px;
    height: 20px;
    stroke: white;
    stroke-width: 3;
    fill: none;
    animation: checkmark-draw 1000ms ease-out forwards;
}

@keyframes checkmark-draw {
    0% {
        stroke-dasharray: 0, 100;
    }
    100% {
        stroke-dasharray: 100, 100;
    }
}

/* Enhanced progress bar with smooth animations */
.progress-bar-enhanced {
    width: 100%;
    height: 8px;
    background: #f0f0f0;
    border-radius: 4px;
    overflow: hidden;
    position: relative;
}

.progress-fill-enhanced {
    height: 100%;
    background: linear-gradient(90deg, #3498db, #2980b9);
    border-radius: 4px;
    transition: width 300ms cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
}

.progress-fill-enhanced::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.3),
        transparent
    );
    animation: progress-shine 2s infinite;
}

@keyframes progress-shine {
    0% {
        transform: translateX(-100%);
    }
    100% {
        transform: translateX(100%);
    }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
    .skeleton-line,
    .skeleton-avatar,
    .progress-fill-enhanced::after,
    .success-checkmark {
        animation: none !important;
    }

    .progress-fill-enhanced {
        transition: width 0.1s linear;
    }

    .success-feedback {
        transition: none;
    }
}

/* Component visibility classes */
.loading-overlay-component {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
}

.progress-bar-component {
    width: 100%;
    margin: 8px 0;
}

.success-feedback-component {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
}

.enhanced-progress-component {
    width: 100%;
    margin: 8px 0;
}

.progress-text {
    text-align: center;
    font-size: 12px;
    color: #666;
    margin-top: 4px;
}
"""