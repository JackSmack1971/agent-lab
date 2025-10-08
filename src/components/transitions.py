"""Tab transition animations and micro-interactions component for Agent Lab.

This module provides smooth transitions for tab switching, button feedback,
and success animations with accessibility support and performance optimization.
"""

import gradio as gr
from typing import Dict, Any, Optional
import json


class TransitionManager:
    """Manages UI transitions and micro-interactions with accessibility support."""

    def __init__(self):
        self.active_transitions: Dict[str, Dict[str, Any]] = {}

    def create_tab_transition(self, from_tab: str, to_tab: str, duration_ms: int = 400) -> Dict[str, Any]:
        """Create a tab transition animation.

        Args:
            from_tab: Source tab element ID
            to_tab: Target tab element ID
            duration_ms: Animation duration (300-500ms range)

        Returns:
            Dict with transition configuration
        """
        # Clamp duration to acceptable range
        duration_ms = max(300, min(500, duration_ms))

        return {
            "type": "tab_transition",
            "from_tab": from_tab,
            "to_tab": to_tab,
            "duration_ms": duration_ms,
            "animation": "fade",
            "respect_reduced_motion": True
        }

    def create_button_feedback(self, button_id: str, feedback_type: str = "press") -> Dict[str, Any]:
        """Create button interaction feedback animation.

        Args:
            button_id: Button element ID
            feedback_type: Type of feedback ("press", "hover", "success")

        Returns:
            Dict with feedback configuration
        """
        duration_ms = 150 if feedback_type == "press" else 200

        return {
            "type": "button_feedback",
            "button_id": button_id,
            "feedback_type": feedback_type,
            "duration_ms": duration_ms,
            "animation": "scale" if feedback_type == "press" else "glow",
            "respect_reduced_motion": True
        }

    def create_success_feedback(self, target_id: str, message: str = "Success!") -> Dict[str, Any]:
        """Create success feedback animation with checkmark.

        Args:
            target_id: Target element ID for feedback
            message: Success message to display

        Returns:
            Dict with success feedback configuration
        """
        return {
            "type": "success_feedback",
            "target_id": target_id,
            "message": message,
            "duration_ms": 1000,
            "animation": "checkmark",
            "respect_reduced_motion": True
        }


def render_tab_transition_html(transition_config: Dict[str, Any]) -> str:
    """Render HTML for tab transition animation.

    Args:
        transition_config: Transition configuration from TransitionManager

    Returns:
        HTML string for the transition
    """
    from_tab = transition_config["from_tab"]
    to_tab = transition_config["to_tab"]
    duration = transition_config["duration_ms"]

    html = f"""
    <script>
    (function() {{
        const fromTab = document.querySelector('#{from_tab}');
        const toTab = document.querySelector('#{to_tab}');

        if (fromTab && toTab) {{
            // Check for reduced motion preference
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

            if (prefersReducedMotion) {{
                // Skip animation for reduced motion
                fromTab.style.display = 'none';
                toTab.style.display = 'block';
                return;
            }}

            // Fade out current tab
            fromTab.style.transition = 'opacity {duration}ms ease-out';
            fromTab.style.opacity = '0';

            setTimeout(() => {{
                fromTab.style.display = 'none';

                // Fade in new tab
                toTab.style.display = 'block';
                toTab.style.opacity = '0';
                toTab.style.transition = 'opacity {duration}ms ease-in';

                requestAnimationFrame(() => {{
                    toTab.style.opacity = '1';
                }});
            }}, {duration});
        }}
    }})();
    </script>
    """

    return html


def render_button_feedback_html(feedback_config: Dict[str, Any]) -> str:
    """Render HTML for button feedback animation.

    Args:
        feedback_config: Feedback configuration from TransitionManager

    Returns:
        HTML string for the feedback
    """
    button_id = feedback_config["button_id"]
    feedback_type = feedback_config["feedback_type"]
    duration = feedback_config["duration_ms"]
    animation = feedback_config["animation"]

    if animation == "scale":
        transform = "scale(0.95)"
        reset_transform = "scale(1)"
    else:  # glow
        transform = "filter: brightness(1.1)"
        reset_transform = "filter: brightness(1)"

    html = f"""
    <script>
    (function() {{
        const button = document.querySelector('#{button_id}');

        if (button) {{
            // Check for reduced motion preference
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

            if (prefersReducedMotion) {{
                // Skip animation for reduced motion
                return;
            }}

            // Apply feedback animation
            button.style.transition = 'transform {duration}ms ease-out, filter {duration}ms ease-out';
            button.style.transform = '{transform}';
            button.style.filter = '{transform}' if '{animation}' === 'glow' else '';

            setTimeout(() => {{
                button.style.transform = '{reset_transform}';
                button.style.filter = '{reset_transform}' if '{animation}' === 'glow' else '';
            }}, {duration});
        }}
    }})();
    </script>
    """

    return html


def render_success_feedback_html(feedback_config: Dict[str, Any]) -> str:
    """Render HTML for success feedback animation.

    Args:
        feedback_config: Success feedback configuration from TransitionManager

    Returns:
        HTML string for the success feedback
    """
    target_id = feedback_config["target_id"]
    message = feedback_config["message"]
    duration = feedback_config["duration_ms"]

    html = f"""
    <div class="success-feedback-overlay" id="success-{target_id}" style="display: none;">
        <div class="success-content">
            <div class="checkmark-animation">
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                    <circle cx="24" cy="24" r="20" stroke="#4CAF50" stroke-width="3" fill="none"/>
                    <path d="M16 24l6 6 10-10" stroke="#4CAF50" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none">
                        <animate attributeName="stroke-dasharray" values="0,100;100,100" dur="{duration}ms" fill="freeze"/>
                    </path>
                </svg>
            </div>
            <div class="success-message">{message}</div>
        </div>
    </div>
    <script>
    (function() {{
        const overlay = document.querySelector('#success-{target_id}');

        if (overlay) {{
            // Check for reduced motion preference
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

            if (prefersReducedMotion) {{
                // Show without animation
                overlay.style.display = 'flex';
                setTimeout(() => {{
                    overlay.style.display = 'none';
                }}, {duration});
                return;
            }}

            // Show with animation
            overlay.style.display = 'flex';
            overlay.style.opacity = '0';
            overlay.style.transform = 'scale(0.8)';

            requestAnimationFrame(() => {{
                overlay.style.transition = 'opacity {duration}ms ease-out, transform {duration}ms ease-out';
                overlay.style.opacity = '1';
                overlay.style.transform = 'scale(1)';
            }});

            setTimeout(() => {{
                overlay.style.transition = 'opacity 200ms ease-in, transform 200ms ease-in';
                overlay.style.opacity = '0';
                overlay.style.transform = 'scale(0.9)';
                setTimeout(() => {{
                    overlay.style.display = 'none';
                }}, 200);
            }}, {duration});
        }}
    }})();
    </script>
    """

    return html


def create_transition_component(transition_type: str = "tab") -> gr.HTML:
    """Create a Gradio HTML component for transitions.

    Args:
        transition_type: Type of transition ("tab", "button", "success")

    Returns:
        Gradio HTML component for transitions
    """
    return gr.HTML(
        value="",
        elem_id=f"transition-{transition_type}",
        visible=False,
        elem_classes=["transition-component"]
    )


# CSS for transitions and micro-interactions
TRANSITIONS_CSS = """
/* Tab transition styles */
.tab-transition {
    transition: opacity 400ms ease-in-out;
}

.tab-transition.fade-out {
    opacity: 0;
}

.tab-transition.fade-in {
    opacity: 1;
}

/* Button feedback animations */
.button-feedback {
    transition: transform 150ms ease-out, filter 200ms ease-out, box-shadow 150ms ease-out;
    position: relative;
    overflow: hidden;
}

.button-feedback::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.3);
    transform: translate(-50%, -50%);
    transition: width 200ms ease-out, height 200ms ease-out;
}

.button-feedback:active {
    transform: scale(0.95);
}

.button-feedback:active::before {
    width: 300px;
    height: 300px;
}

.button-feedback:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.button-feedback.success {
    animation: button-success 200ms ease-out;
}

.button-feedback.loading {
    position: relative;
    color: transparent;
}

.button-feedback.loading::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 16px;
    height: 16px;
    margin: -8px 0 0 -8px;
    border: 2px solid transparent;
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: button-loading 1s linear infinite;
}

@keyframes button-success {
    0% { transform: scale(1); filter: brightness(1); }
    50% { transform: scale(1.05); filter: brightness(1.1); }
    100% { transform: scale(1); filter: brightness(1); }
}

@keyframes button-loading {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Success feedback overlay */
.success-feedback-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(76, 175, 80, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    backdrop-filter: blur(4px);
}

.success-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 32px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    border: 2px solid #4CAF50;
}

.checkmark-animation {
    animation: checkmark-bounce 1000ms ease-out;
}

@keyframes checkmark-bounce {
    0% { transform: scale(0); }
    50% { transform: scale(1.2); }
    70% { transform: scale(0.9); }
    100% { transform: scale(1); }
}

.success-message {
    color: #2E7D32;
    font-size: 18px;
    font-weight: 600;
    text-align: center;
}

/* Reduced motion overrides */
@media (prefers-reduced-motion: reduce) {
    .tab-transition,
    .button-feedback,
    .success-feedback-overlay,
    .checkmark-animation {
        animation: none !important;
        transition: none !important;
    }

    .tab-transition.fade-out,
    .tab-transition.fade-in {
        opacity: 1 !important;
    }

    .button-feedback:active {
        transform: none !important;
    }
}

/* Component visibility classes */
.transition-component {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
}
"""


# Global transition manager instance
transition_manager = TransitionManager()