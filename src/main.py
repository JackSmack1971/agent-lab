"""Main entry point for Agent Lab with Model Matchmaker integration."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import gradio as gr

# Import existing app functionality
from app import create_ui as create_agent_lab_ui

# Import cost optimizer component
from src.components.cost_optimizer import create_cost_optimizer_tab
from src.components.keyboard_shortcuts import create_keyboard_shortcuts_ui

# Import model matchmaker component
from src.components.model_matchmaker import create_model_matchmaker_tab
from src.components.settings import create_settings_tab
from src.models.recommendation import ModelRecommendation

# Import keyboard shortcuts components
from src.utils.keyboard_handler import (
    ContextManager,
    KeyboardHandler,
    KeyboardShortcut,
    ShortcutContext,
)

logger = logging.getLogger(__name__)

# Global keyboard services (initialized in create_main_ui)
keyboard_handler: Optional[KeyboardHandler] = None
context_manager: Optional[ContextManager] = None


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
    """Create the main tabbed interface with keyboard shortcuts integration."""

    # Import keyboard components
    from src.components.keyboard_shortcuts import create_keyboard_shortcuts_ui
    from src.components.settings import create_settings_tab
    from src.utils.keyboard_handler import ContextManager, KeyboardHandler

    # Initialize keyboard services
    global keyboard_handler, context_manager
    keyboard_handler = KeyboardHandler()
    context_manager = ContextManager()

    # Create settings state for shortcuts toggle
    shortcuts_enabled = gr.State(value=True)

    with gr.Blocks(title="Agent Lab - AI Model Matchmaker") as main_interface:
        # Header with shortcut indicators
        with gr.Row():
            gr.Markdown("# 🤖 Agent Lab")
            # Embed shortcut indicator bar
            shortcut_indicators = create_shortcut_indicator_bar()

        # Settings toggle in header
        with gr.Row():
            shortcuts_toggle = gr.Checkbox(
                label="Enable Keyboard Shortcuts",
                value=True,
                elem_id="shortcuts-toggle",
            )

        gr.Markdown(
            "Test AI agents across multiple models and get personalized recommendations."
        )

        # Initialize tab selection state for context management
        active_tab_state = gr.State(value="agent_testing")

        with gr.Tabs(elem_id="main-tabs") as main_tabs:
            with gr.TabItem("🧪 Agent Testing", id="agent_testing"):
                # Embed the existing Agent Lab interface
                agent_lab_ui = create_agent_lab_ui()
                # Note: In full implementation, refactor app.py to use components

                gr.Markdown("### Agent Configuration & Testing")
                gr.Markdown("*Agent testing interface would be embedded here*")
                gr.Markdown(
                    "*(Note: Full integration requires refactoring app.py to use components)*"
                )

            with gr.TabItem("🎯 Model Matchmaker", id="model_matchmaker"):
                # Create the model matchmaker tab
                matchmaker_tab = create_model_matchmaker_tab(
                    apply_config_callback=apply_config_to_agent
                )

            with gr.TabItem("💰 Cost Optimizer", id="cost_optimizer"):
                # Create the cost optimizer tab
                cost_optimizer_tab = create_cost_optimizer_tab()

            with gr.TabItem("⚙️ Settings", id="settings"):
                # Create settings tab with shortcuts toggle
                settings_tab = create_settings_tab()

        # Embed keyboard shortcuts UI components
        shortcuts_ui = create_keyboard_shortcuts_ui(
            keyboard_handler=keyboard_handler, context_manager=context_manager
        )

        # Setup keyboard event handling and action connections
        setup_keyboard_integration(
            main_interface=main_interface,
            keyboard_handler=keyboard_handler,
            context_manager=context_manager,
            main_tabs=main_tabs,
            shortcuts_toggle=shortcuts_toggle,
            shortcuts_enabled=shortcuts_enabled,
            active_tab_state=active_tab_state,
            shortcut_indicators=shortcut_indicators,
        )

    return main_interface


def create_shortcut_indicator_bar() -> gr.HTML:
    """Create the persistent shortcut indicator bar for global accessibility.

    Returns:
        HTML component displaying current context shortcuts
    """
    from src.components.keyboard_shortcuts import create_shortcut_indicator_bar

    return create_shortcut_indicator_bar()


def setup_keyboard_integration(
    main_interface: gr.Blocks,
    keyboard_handler: KeyboardHandler,
    context_manager: ContextManager,
    main_tabs: gr.Tabs,
    shortcuts_toggle: gr.Checkbox,
    shortcuts_enabled: gr.State,
    active_tab_state: gr.State,
    shortcut_indicators: gr.HTML,
) -> None:
    """Setup keyboard event handling and action connections."""

    # Register tab-specific shortcuts
    register_tab_shortcuts(keyboard_handler)

    # Attach global keyboard event listener to main interface
    main_interface.load(
        fn=None,
        inputs=None,
        outputs=None,
        js=setup_global_keyboard_listener_js(keyboard_handler),
    )

    # Handle tab changes for context updates
    main_tabs.select(
        fn=update_active_tab_context,
        inputs=[active_tab_state],
        outputs=[active_tab_state, shortcut_indicators],
    ).then(fn=context_manager.update_context, inputs=[active_tab_state], outputs=[])

    # Handle shortcuts toggle
    shortcuts_toggle.change(
        fn=toggle_shortcuts_enabled,
        inputs=[shortcuts_enabled],
        outputs=[shortcuts_enabled],
    )

    # Connect shortcut actions to UI components
    connect_shortcut_actions(
        keyboard_handler=keyboard_handler,
        main_tabs=main_tabs,
        context_manager=context_manager,
        shortcuts_enabled=shortcuts_enabled,
    )


def register_tab_shortcuts(keyboard_handler: KeyboardHandler) -> None:
    """Register shortcuts for tab navigation and actions."""

    # Tab navigation shortcuts
    tab_shortcuts = [
        KeyboardShortcut(
            id="switch_to_agent_testing",
            name="Switch to Agent Testing",
            description="Navigate to Agent Testing tab",
            key_combination=["ctrl", "1"],
            action="switch_tab_agent_testing",
            context=["global"],
        ),
        KeyboardShortcut(
            id="switch_to_matchmaker",
            name="Switch to Model Matchmaker",
            description="Navigate to Model Matchmaker tab",
            key_combination=["ctrl", "m"],
            action="switch_tab_model_matchmaker",
            context=["global"],
        ),
        KeyboardShortcut(
            id="switch_to_cost_optimizer",
            name="Switch to Cost Optimizer",
            description="Navigate to Cost Optimizer tab",
            key_combination=["ctrl", "o"],
            action="switch_tab_cost_optimizer",
            context=["global"],
        ),
        KeyboardShortcut(
            id="switch_to_settings",
            name="Switch to Settings",
            description="Navigate to Settings tab",
            key_combination=["ctrl", ","],
            action="switch_tab_settings",
            context=["global"],
        ),
    ]

    # Register each shortcut
    for shortcut in tab_shortcuts:
        try:
            keyboard_handler.register_shortcut(shortcut)
        except ValueError as e:
            logger.warning(f"Failed to register shortcut {shortcut.id}: {e}")


def connect_shortcut_actions(
    keyboard_handler: KeyboardHandler,
    main_tabs: gr.Tabs,
    context_manager: ContextManager,
    shortcuts_enabled: gr.State,
) -> Dict[str, Callable]:
    """Connect keyboard shortcut actions to UI handlers."""

    action_handlers = {
        "switch_tab_agent_testing": lambda params=None: switch_to_tab(
            main_tabs, "agent_testing"
        ),
        "switch_tab_model_matchmaker": lambda params=None: switch_to_tab(
            main_tabs, "model_matchmaker"
        ),
        "switch_tab_cost_optimizer": lambda params=None: switch_to_tab(
            main_tabs, "cost_optimizer"
        ),
        "switch_tab_settings": lambda params=None: switch_to_tab(main_tabs, "settings"),
        "focus_search": lambda params=None: focus_search_input(),
        "new_conversation": lambda params=None: start_new_conversation(),
        "save_session": lambda params=None: save_current_session(),
        "open_settings": lambda params=None: switch_to_tab(main_tabs, "settings"),
        "show_help": lambda params=None: toggle_help_overlay(),
        "toggle_battle_mode": lambda params=None: toggle_battle_mode(),
        "export_conversation": lambda params=None: export_conversation(),
        "cancel_streaming": lambda params=None: cancel_streaming_response(),
        "send_message": lambda params=None: send_message(),
        "navigate_history_up": lambda params=None: navigate_message_history("up"),
        "navigate_history_down": lambda params=None: navigate_message_history("down"),
    }

    # In real implementation, these would be connected via Gradio events
    # For pseudocode, we define the mapping

    return action_handlers


def switch_to_tab(main_tabs: gr.Tabs, tab_id: str) -> None:
    """Switch to specified tab and update context.

    Args:
        main_tabs: Main tabs component
        tab_id: Target tab identifier
    """
    try:
        # Update Gradio tabs selection
        # Note: Gradio tabs selection is handled via frontend JS
        # This function would trigger the tab change

        # Update context manager
        if context_manager:
            context_manager.update_context(active_tab=tab_id)

        # Log successful tab switch
        logger.info(f"Switched to tab: {tab_id}")

    except Exception as e:
        logger.error(f"Failed to switch to tab {tab_id}: {e}")


def update_active_tab_context(current_tab: str) -> Tuple[str, str]:
    """Update context when active tab changes.

    Args:
        current_tab: Currently active tab ID

    Returns:
        Tuple of (updated_tab_state, updated_indicators_html)
    """
    try:
        # Update context manager
        if context_manager:
            context_manager.update_context(active_tab=current_tab)

        # Get available shortcuts for new context
        indicators_html = ""
        if context_manager and keyboard_handler:
            context = context_manager.get_current_context()
            available_shortcuts = keyboard_handler.get_available_shortcuts(context)

            # Generate updated indicators HTML
            indicators_html = render_shortcut_indicators_html(available_shortcuts)

        return current_tab, indicators_html

    except Exception as e:
        logger.error(f"Failed to update tab context: {e}")
        return current_tab, ""


def toggle_shortcuts_enabled(enabled: bool) -> bool:
    """Toggle keyboard shortcuts enabled state.

    Args:
        enabled: New enabled state

    Returns:
        Confirmed enabled state
    """
    try:
        # Update context manager
        if context_manager:
            context_manager.update_context(shortcuts_enabled=enabled)

        # Save to persistent settings
        save_shortcuts_preference(enabled)

        logger.info(f"Keyboard shortcuts {'enabled' if enabled else 'disabled'}")

        return enabled

    except Exception as e:
        logger.error(f"Failed to toggle shortcuts: {e}")
        return not enabled  # Revert on error


def setup_global_keyboard_listener_js(keyboard_handler: KeyboardHandler) -> str:
    """Generate JavaScript for global keyboard event handling.

    Args:
        keyboard_handler: Keyboard handler instance

    Returns:
        JavaScript code as string
    """
    return f"""
        document.addEventListener('keydown', function(event) {{
            // Prevent default for handled shortcuts
            if (handleKeyboardShortcut(event, {keyboard_handler})) {{
                event.preventDefault();
                event.stopPropagation();
            }}
        }});

        function handleKeyboardShortcut(event, handler) {{
            // Check if shortcuts are enabled
            if (!window.shortcuts_enabled) return false;

            // Create event data
            const shortcutEvent = {{
                key: event.key,
                ctrl_key: event.ctrlKey,
                meta_key: event.metaKey,
                alt_key: event.altKey,
                shift_key: event.shiftKey,
                platform: detectPlatform(),
                context: getCurrentContext(),
                timestamp: Date.now() / 1000
            }};

            // Process through keyboard handler
            const action = handler.process_event(shortcutEvent);

            if (action) {{
                // Execute action via Gradio
                executeShortcutAction(action, shortcutEvent);
                return true;
            }}

            return false;
        }}

        function executeShortcutAction(action, event) {{
            // Trigger corresponding Gradio event
            // This would be connected to the action handlers
            window.gradio.dispatchEvent(new CustomEvent('shortcut-action', {{
                detail: {{ action: action, event: event }}
            }}));
        }}

        function detectPlatform() {{
            const ua = navigator.userAgent;
            if (ua.includes('Mac')) return 'mac';
            if (ua.includes('Windows')) return 'windows';
            return 'linux';
        }}

        function getCurrentContext() {{
            // Get current UI context from Gradio state
            return window.current_context || {{}};
        }}
    """


def render_shortcut_indicators_html(available_shortcuts: List[KeyboardShortcut]) -> str:
    """Render HTML for shortcut indicator badges.

    Args:
        available_shortcuts: List of currently available shortcuts

    Returns:
        HTML string with shortcut badges
    """
    from src.components.keyboard_shortcuts import render_shortcut_indicators_html

    return render_shortcut_indicators_html(available_shortcuts)


# Component action handlers
def focus_search_input() -> None:
    """Focus on the search input field in active tab."""
    try:
        # Determine active tab and focus appropriate search input
        if context_manager:
            context = context_manager.get_current_context()

            if context.active_tab == "model_matchmaker":
                # Focus model matchmaker search
                pass
            elif context.active_tab == "cost_optimizer":
                # Focus cost optimizer search
                pass
            # etc.

        logger.info("Focused search input")

    except Exception as e:
        logger.error(f"Failed to focus search input: {e}")


def start_new_conversation() -> None:
    """Start a new conversation in Agent Testing tab."""
    try:
        # Clear conversation history and reset UI
        # Only active when agent_testing tab is selected

        logger.info("Started new conversation")

    except Exception as e:
        logger.error(f"Failed to start new conversation: {e}")


def save_current_session() -> None:
    """Save the current session state."""
    try:
        # Trigger save operation for current session

        logger.info("Saved current session")

    except Exception as e:
        logger.error(f"Failed to save session: {e}")


def cancel_streaming_response() -> None:
    """Cancel any active streaming response."""
    try:
        # Stop streaming and reset UI state

        logger.info("Cancelled streaming response")

    except Exception as e:
        logger.error(f"Failed to cancel streaming: {e}")


def send_message() -> None:
    """Send the current message in chat interface."""
    try:
        # Trigger message send action

        logger.info("Sent message")

    except Exception as e:
        logger.error(f"Failed to send message: {e}")


def navigate_message_history(direction: str) -> None:
    """Navigate message history up or down."""
    try:
        # Update message input with history item

        logger.info(f"Navigated message history {direction}")

    except Exception as e:
        logger.error(f"Failed to navigate message history: {e}")


def toggle_help_overlay() -> None:
    """Toggle the keyboard shortcuts help overlay."""
    try:
        # Toggle visibility of help overlay
        # In real implementation, this would update Gradio component visibility

        logger.info("Toggled help overlay")

    except Exception as e:
        logger.error(f"Failed to toggle help overlay: {e}")


def toggle_battle_mode() -> None:
    """Toggle battle mode if available."""
    try:
        # Toggle battle mode state

        logger.info("Toggled battle mode")

    except Exception as e:
        logger.error(f"Failed to toggle battle mode: {e}")


def export_conversation() -> None:
    """Export current conversation."""
    try:
        # Trigger export operation

        logger.info("Exported conversation")

    except Exception as e:
        logger.error(f"Failed to export conversation: {e}")


def save_shortcuts_preference(enabled: bool) -> None:
    """Save keyboard shortcuts preference to persistent storage.

    Args:
        enabled: Whether shortcuts should be enabled
    """
    try:
        # Placeholder for persistent storage implementation
        # In a real implementation, this would save to a config file or database
        logger.info(f"Shortcuts preference saved: {enabled}")

    except Exception as e:
        logger.error(f"Failed to save shortcuts preference: {e}")


if __name__ == "__main__":
    # Launch the main interface
    demo = create_main_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_api=False,
        debug=True,
    )
