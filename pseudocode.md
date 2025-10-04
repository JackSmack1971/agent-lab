# Keyboard Shortcuts Integration Pseudocode

## Overview

This pseudocode details the integration of keyboard shortcuts into the main UI (`src/main.py`). The integration follows Agent Lab's architecture with global keyboard event handling, context-aware shortcuts, and UI components for help overlays and indicators.

## Key Integration Points

1. **Global Keyboard Handler**: Attached to main Gradio Blocks
2. **Context Management**: Tracks active tab and UI state
3. **Shortcut Actions**: Connected to tab navigation and component actions
4. **Settings Toggle**: Enable/disable keyboard shortcuts
5. **Help Overlay**: Accessible from all tabs with shortcut indicators

## Modified create_main_ui() Function

```python
def create_main_ui() -> gr.Blocks:
    """Create the main tabbed interface with keyboard shortcuts integration."""

    # Import keyboard components
    from src.utils.keyboard_handler import KeyboardHandler, ContextManager
    from src.components.keyboard_shortcuts import create_keyboard_shortcuts_ui
    from src.components.settings import create_settings_tab  # Assume exists or create

    # Initialize keyboard services
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
                elem_id="shortcuts-toggle"
            )

        gr.Markdown("Test AI agents across multiple models and get personalized recommendations.")

        # Initialize tab selection state for context management
        active_tab_state = gr.State(value="agent_testing")

        with gr.Tabs(elem_id="main-tabs") as main_tabs:
            with gr.TabItem("🧪 Agent Testing", id="agent_testing"):
                # Embed the existing Agent Lab interface
                agent_lab_ui = create_agent_lab_ui()
                # Note: In full implementation, refactor app.py to use components

                gr.Markdown("### Agent Configuration & Testing")
                gr.Markdown("*Agent testing interface would be embedded here*")
                gr.Markdown("*(Note: Full integration requires refactoring app.py to use components)*")

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
            keyboard_handler=keyboard_handler,
            context_manager=context_manager
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
            shortcut_indicators=shortcut_indicators
        )

    return main_interface
```

## Keyboard Integration Setup Function

```python
def setup_keyboard_integration(
    main_interface: gr.Blocks,
    keyboard_handler: KeyboardHandler,
    context_manager: ContextManager,
    main_tabs: gr.Tabs,
    shortcuts_toggle: gr.Checkbox,
    shortcuts_enabled: gr.State,
    active_tab_state: gr.State,
    shortcut_indicators: gr.HTML
) -> None:
    """Setup keyboard event handling and action connections."""

    # Register tab-specific shortcuts
    register_tab_shortcuts(keyboard_handler)

    # Attach global keyboard event listener to main interface
    main_interface.load(
        fn=None,
        inputs=None,
        outputs=None,
        js=setup_global_keyboard_listener_js(keyboard_handler)
    )

    # Handle tab changes for context updates
    main_tabs.select(
        fn=update_active_tab_context,
        inputs=[active_tab_state],
        outputs=[active_tab_state, shortcut_indicators]
    ).then(
        fn=context_manager.update_context,
        inputs=[active_tab_state],
        outputs=[]
    )

    # Handle shortcuts toggle
    shortcuts_toggle.change(
        fn=toggle_shortcuts_enabled,
        inputs=[shortcuts_enabled],
        outputs=[shortcuts_enabled]
    )

    # Connect shortcut actions to UI components
    connect_shortcut_actions(
        keyboard_handler=keyboard_handler,
        main_tabs=main_tabs,
        context_manager=context_manager,
        shortcuts_enabled=shortcuts_enabled
    )
```

## Tab Shortcuts Registration

```python
def register_tab_shortcuts(keyboard_handler: KeyboardHandler) -> None:
    """Register shortcuts for tab navigation and actions."""

    # Tab navigation shortcuts
    tab_shortcuts = [
        KeyboardShortcut(
            id="switch_to_agent_testing",
            name="Switch to Agent Testing",
            description="Navigate to Agent Testing tab",
            key_combination=["ctrl", "1"],
            action="switch_tab",
            context=["global"],
            action_params={"tab": "agent_testing"}
        ),
        KeyboardShortcut(
            id="switch_to_matchmaker",
            name="Switch to Model Matchmaker",
            description="Navigate to Model Matchmaker tab",
            key_combination=["ctrl", "m"],
            action="switch_tab",
            context=["global"],
            action_params={"tab": "model_matchmaker"}
        ),
        KeyboardShortcut(
            id="switch_to_cost_optimizer",
            name="Switch to Cost Optimizer",
            description="Navigate to Cost Optimizer tab",
            key_combination=["ctrl", "o"],
            action="switch_tab",
            context=["global"],
            action_params={"tab": "cost_optimizer"}
        ),
        KeyboardShortcut(
            id="switch_to_settings",
            name="Switch to Settings",
            description="Navigate to Settings tab",
            key_combination=["ctrl", ","],
            action="switch_tab",
            context=["global"],
            action_params={"tab": "settings"}
        )
    ]

    # Register each shortcut
    for shortcut in tab_shortcuts:
        try:
            keyboard_handler.register_shortcut(shortcut)
        except ValueError as e:
            logger.warning(f"Failed to register shortcut {shortcut.id}: {e}")
```

## Shortcut Action Connection

```python
def connect_shortcut_actions(
    keyboard_handler: KeyboardHandler,
    main_tabs: gr.Tabs,
    context_manager: ContextManager,
    shortcuts_enabled: gr.State
) -> Dict[str, Callable]:
    """Connect keyboard shortcut actions to UI handlers."""

    action_handlers = {
        "switch_tab": lambda params: switch_to_tab(main_tabs, params.get("tab")),
        "focus_search": lambda params: focus_search_input(),
        "new_conversation": lambda params: start_new_conversation(),
        "save_session": lambda params: save_current_session(),
        "open_settings": lambda params: switch_to_tab(main_tabs, "settings"),
        "show_help": lambda params: toggle_help_overlay(),
        "toggle_battle_mode": lambda params: toggle_battle_mode(),
        "export_conversation": lambda params: export_conversation(),
        "cancel_streaming": lambda params: cancel_streaming_response(),
        "send_message": lambda params: send_message(),
        "navigate_history_up": lambda params: navigate_message_history("up"),
        "navigate_history_down": lambda params: navigate_message_history("down")
    }

    # In real implementation, these would be connected via Gradio events
    # For pseudocode, we define the mapping

    return action_handlers
```

## Tab Switching Handler

```python
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
        context_manager.update_context(active_tab=tab_id)

        # Log successful tab switch
        logger.info(f"Switched to tab: {tab_id}")

    except Exception as e:
        logger.error(f"Failed to switch to tab {tab_id}: {e}")
        # Show error toast or notification
```

## Context Update Handler

```python
def update_active_tab_context(current_tab: str) -> Tuple[str, str]:
    """Update context when active tab changes.

    Args:
        current_tab: Currently active tab ID

    Returns:
        Tuple of (updated_tab_state, updated_indicators_html)
    """
    try:
        # Update context manager
        context_manager.update_context(active_tab=current_tab)

        # Get available shortcuts for new context
        context = context_manager.get_current_context()
        available_shortcuts = keyboard_handler.get_available_shortcuts(context)

        # Generate updated indicators HTML
        indicators_html = render_shortcut_indicators_html(available_shortcuts)

        return current_tab, indicators_html

    except Exception as e:
        logger.error(f"Failed to update tab context: {e}")
        return current_tab, ""
```

## Settings Toggle Handler

```python
def toggle_shortcuts_enabled(enabled: bool) -> bool:
    """Toggle keyboard shortcuts enabled state.

    Args:
        enabled: New enabled state

    Returns:
        Confirmed enabled state
    """
    try:
        # Update keyboard handler enabled state
        keyboard_handler.set_enabled(enabled)

        # Update context manager
        context_manager.update_context(shortcuts_enabled=enabled)

        # Save to persistent settings
        save_shortcuts_preference(enabled)

        logger.info(f"Keyboard shortcuts {'enabled' if enabled else 'disabled'}")

        return enabled

    except Exception as e:
        logger.error(f"Failed to toggle shortcuts: {e}")
        return not enabled  # Revert on error
```

## Global Keyboard Listener JavaScript

```javascript
function setup_global_keyboard_listener_js(keyboard_handler) {
    return `
        document.addEventListener('keydown', function(event) {
            // Prevent default for handled shortcuts
            if (handleKeyboardShortcut(event, keyboard_handler)) {
                event.preventDefault();
                event.stopPropagation();
            }
        });

        function handleKeyboardShortcut(event, handler) {
            // Check if shortcuts are enabled
            if (!window.shortcuts_enabled) return false;

            // Create event data
            const shortcutEvent = {
                key: event.key,
                ctrl_key: event.ctrlKey,
                meta_key: event.metaKey,
                alt_key: event.altKey,
                shift_key: event.shiftKey,
                platform: detectPlatform(),
                context: getCurrentContext(),
                timestamp: Date.now() / 1000
            };

            // Process through keyboard handler
            const action = handler.process_event(shortcutEvent);

            if (action) {
                // Execute action via Gradio
                executeShortcutAction(action, shortcutEvent);
                return true;
            }

            return false;
        }

        function executeShortcutAction(action, event) {
            // Trigger corresponding Gradio event
            // This would be connected to the action handlers
            window.gradio.dispatchEvent(new CustomEvent('shortcut-action', {
                detail: { action: action, event: event }
            }));
        }

        function detectPlatform() {
            const ua = navigator.userAgent;
            if (ua.includes('Mac')) return 'mac';
            if (ua.includes('Windows')) return 'windows';
            return 'linux';
        }

        function getCurrentContext() {
            // Get current UI context from Gradio state
            return window.current_context || {};
        }
    `;
}
```

## Help Overlay Toggle

```python
def toggle_help_overlay() -> None:
    """Toggle the keyboard shortcuts help overlay."""
    try:
        # Toggle visibility of help overlay
        # In real implementation, this would update Gradio component visibility

        logger.info("Toggled help overlay")

    except Exception as e:
        logger.error(f"Failed to toggle help overlay: {e}")
```

## Component Action Handlers

```python
def focus_search_input() -> None:
    """Focus on the search input field in active tab."""
    try:
        # Determine active tab and focus appropriate search input
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
```

## Error Handling and Logging

All functions include comprehensive error handling with logging:

```python
import logging

logger = logging.getLogger(__name__)

# Error handling pattern used throughout:
try:
    # Function logic
    pass
except Exception as e:
    logger.error(f"Operation failed: {e}")
    # Handle error appropriately
```

## Platform-Specific Handling

Keyboard combinations are normalized for different platforms:

- **Windows/Linux**: Ctrl key
- **macOS**: Cmd (Meta) key
- Automatic detection and normalization in `KeyboardHandler`

## Context-Aware Availability

Shortcuts are only available when appropriate:

- Tab-specific shortcuts only in relevant tabs
- Input-safe shortcuts avoid interfering with text input
- Streaming-safe shortcuts work during response generation
- Modal state prevents conflicting shortcuts

## Settings Persistence

```python
def save_shortcuts_preference(enabled: bool) -> None:
    """Save shortcuts enabled preference to persistent storage."""
    try:
        # Save to user settings file or database
        pass
    except Exception as e:
        logger.error(f"Failed to save shortcuts preference: {e}")

def load_shortcuts_preference() -> bool:
    """Load shortcuts enabled preference."""
    try:
        # Load from settings
        return True  # Default
    except Exception as e:
        logger.error(f"Failed to load shortcuts preference: {e}")
        return True
```

This pseudocode provides a complete integration plan following Agent Lab's architecture and coding standards.