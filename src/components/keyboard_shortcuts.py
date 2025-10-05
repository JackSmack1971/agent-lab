"""Keyboard shortcuts UI component for Agent Lab.

This module provides Gradio UI components for displaying keyboard shortcuts,
help panels, visual indicators, and accessibility features.
"""

from typing import Any, Dict, List, Optional

import gradio as gr

from src.utils.keyboard_handler import (
    ContextManager,
    KeyboardHandler,
    KeyboardShortcut,
    ShortcutContext,
)


def create_keyboard_shortcuts_ui(
    keyboard_handler: KeyboardHandler, context_manager: ContextManager
) -> gr.Blocks:
    """Create the keyboard shortcuts UI component with help overlay and indicators.

    Args:
        keyboard_handler: Initialized KeyboardHandler service instance
        context_manager: ContextManager for UI state tracking

    Returns:
        Gradio Blocks component containing shortcut UI elements
    """
    # Initialize component state
    shortcut_help_visible = gr.State(value=False)
    search_query = gr.State(value="")
    active_toast = gr.State(value=None)
    context_state = gr.State(value=ShortcutContext())
    available_shortcuts_state = gr.State(value=[])

    with gr.Blocks() as shortcuts_ui:
        # Global shortcut indicators container (always visible)
        with gr.Row(visible=True) as global_indicators:
            shortcut_indicator_bar = create_shortcut_indicator_bar()
            toast_notification_area = create_toast_area()

        # Hidden trigger button for help toggle
        help_toggle_btn = gr.Button(visible=False)

        # Floating help overlay (conditionally visible)
        with gr.Row(visible=False) as help_overlay:
            help_panel, search_input, category_contents = create_help_overlay_panel()

        # Event handlers for dynamic updates
        setup_event_handlers(
            shortcuts_ui,
            keyboard_handler,
            context_manager,
            shortcut_help_visible,
            search_query,
            active_toast,
            context_state,
            available_shortcuts_state,
            shortcut_indicator_bar,
            help_overlay,
            help_toggle_btn,
            search_input,
            category_contents,
            toast_notification_area,
        )

    return shortcuts_ui


def create_shortcut_indicator_bar() -> gr.HTML:
    """Create the persistent shortcut indicator bar for global accessibility.

    Returns:
        HTML component displaying current context shortcuts
    """
    return gr.HTML(
        value=render_shortcut_indicators_html([]),
        elem_id="shortcut-indicators",
        elem_classes=["shortcut-indicators"],
    )


def create_shortcut_indicator(shortcut: KeyboardShortcut) -> str:
    """Create HTML for a single shortcut indicator badge.

    Args:
        shortcut: Shortcut to display

    Returns:
        HTML string for the badge
    """
    return f"""
    <span class="shortcut-badge"
          data-shortcut-id="{shortcut.id}"
          title="{shortcut.description}">
        <kbd>{format_key_combination(shortcut.key_combination)}</kbd>
        {shortcut.name}
    </span>
    """


def render_shortcut_indicators_html(available_shortcuts: List[KeyboardShortcut]) -> str:
    """Render HTML for shortcut indicator badges.

    Args:
        available_shortcuts: List of currently available shortcuts

    Returns:
        HTML string with shortcut badges
    """
    if not available_shortcuts:
        return ""

    badges_html = []
    for shortcut in available_shortcuts[:5]:  # Limit to 5 most relevant
        badge_html = f"""
        <span class="shortcut-badge"
              data-shortcut-id="{shortcut.id}"
              title="{shortcut.description}">
            <kbd>{format_key_combination(shortcut.key_combination)}</kbd>
            {shortcut.name}
        </span>
        """
        badges_html.append(badge_html)

    return f"""
    <div class="shortcut-indicator-bar">
        {"".join(badges_html)}
        <button class="help-toggle-btn"
                onclick="toggleHelpPanel()"
                aria-label="Show keyboard shortcuts help">
            ?
        </button>
    </div>
    """


def create_help_overlay_panel() -> tuple:
    """Create the comprehensive help overlay with search and categories.

    Returns:
        Tuple of (help_panel, search_input, category_contents)
    """
    with gr.Blocks() as help_panel:
        # Header with search and close button
        with gr.Row():
            gr.Markdown("## ⌨️ Keyboard Shortcuts Help")
            close_button = gr.Button("✕", size="sm", elem_classes=["close-btn"])

        # Search functionality
        search_input = gr.Textbox(
            placeholder="Search shortcuts...",
            label="Search",
            elem_classes=["shortcut-search"],
        )

        # Category tabs
        category_contents = {}
        with gr.Tabs() as category_tabs:
            categories = ["All", "Navigation", "Actions", "Configuration"]

            for category in categories:
                with gr.TabItem(category):
                    category_content = create_category_content(category)
                    category_contents[category] = category_content

        # Keyboard diagram section
        keyboard_diagram = create_visual_keyboard_diagram()

    return help_panel, search_input, category_contents


def create_category_content(category: str) -> gr.HTML:
    """Create content for a specific shortcut category.

    Args:
        category: Category name ("All", "Navigation", etc.)

    Returns:
        HTML component with categorized shortcuts
    """
    return gr.HTML(
        value=render_category_shortcuts_html(category, []),
        elem_id=f"category-{category.lower()}",
    )


def render_category_shortcuts_html(
    category: str, shortcuts: List[KeyboardShortcut], search_filter: str = ""
) -> str:
    """Render HTML for shortcuts in a specific category with optional filtering.

    Args:
        category: Category to display
        shortcuts: All available shortcuts
        search_filter: Search query to filter shortcuts

    Returns:
        HTML string with categorized shortcut list
    """
    filtered_shortcuts = filter_shortcuts_by_category_and_search(
        shortcuts, category, search_filter
    )

    if not filtered_shortcuts:
        return "<p>No shortcuts found in this category.</p>"

    shortcut_items = []
    for shortcut in filtered_shortcuts:
        item_html = f"""
        <div class="shortcut-item">
            <div class="shortcut-keys">
                <kbd>{format_key_combination(shortcut.key_combination)}</kbd>
            </div>
            <div class="shortcut-info">
                <div class="shortcut-name">{shortcut.name}</div>
                <div class="shortcut-description">{shortcut.description}</div>
                <div class="shortcut-context">Context: {", ".join(shortcut.context)}</div>
            </div>
        </div>
        """
        shortcut_items.append(item_html)

    return f"""
    <div class="shortcut-list">
        {"".join(shortcut_items)}
    </div>
    """


def create_visual_keyboard_diagram() -> gr.HTML:
    """Create visual keyboard diagram showing key locations.

    Returns:
        HTML component with interactive keyboard diagram
    """
    return gr.HTML(
        value=render_keyboard_diagram_html(),
        elem_id="keyboard-diagram",
        elem_classes=["keyboard-diagram"],
    )


def render_keyboard_diagram_html() -> str:
    """Render HTML for interactive keyboard diagram.

    Returns:
        HTML string with keyboard layout
    """
    # Simplified QWERTY layout with common shortcut keys highlighted
    return """
    <div class="keyboard-container">
        <div class="keyboard-row">
            <div class="key modifier" data-key="ctrl">Ctrl</div>
            <div class="key modifier" data-key="alt">Alt</div>
            <div class="key modifier" data-key="shift">Shift</div>
            <div class="key">`</div>
            <div class="key active" data-key="1">1</div>
            <!-- ... more keys ... -->
        </div>
        <!-- Additional rows for full keyboard layout -->
        <div class="keyboard-legend">
            <div class="legend-item">
                <div class="key-sample modifier"></div>
                <span>Modifier Keys</span>
            </div>
            <div class="legend-item">
                <div class="key-sample active"></div>
                <span>Shortcut Keys</span>
            </div>
        </div>
    </div>
    """


def create_toast_area() -> gr.HTML:
    """Create toast notification area for shortcut usage feedback.

    Returns:
        HTML component for displaying toast messages
    """
    return gr.HTML(value="", elem_id="toast-area", elem_classes=["toast-area"])


def show_shortcut_toast(shortcut: KeyboardShortcut, action_result: str) -> str:
    """Generate HTML for shortcut usage toast notification.

    Args:
        shortcut: Shortcut that was triggered
        action_result: Result of the shortcut action

    Returns:
        HTML string for toast notification
    """
    status_icon = "✅" if action_result == "success" else "❌"
    status_class = "success" if action_result == "success" else "error"

    return f"""
    <div class="toast-notification {status_class}" role="alert">
        <div class="toast-icon">{status_icon}</div>
        <div class="toast-content">
            <div class="toast-title">{shortcut.name}</div>
            <div class="toast-message">{action_result}</div>
        </div>
        <button class="toast-close" onclick="hideToast()" aria-label="Close notification">
            ✕
        </button>
    </div>
    """


def setup_event_handlers(
    shortcuts_ui: gr.Blocks,
    keyboard_handler: KeyboardHandler,
    context_manager: ContextManager,
    shortcut_help_visible: gr.State,
    search_query: gr.State,
    active_toast: gr.State,
    context_state: gr.State,
    available_shortcuts_state: gr.State,
    shortcut_indicator_bar: gr.HTML,
    help_overlay: gr.Row,
    help_toggle_btn: gr.Button,
    search_input: gr.Textbox,
    category_contents: Dict[str, gr.HTML],
    toast_notification_area: gr.HTML,
) -> None:
    """Set up all event handlers for dynamic UI updates.

    Args:
        shortcuts_ui: Main shortcuts UI component
        keyboard_handler: Keyboard handler service
        context_manager: Context manager service
        shortcut_help_visible: State for help panel visibility
        search_query: State for search input
        active_toast: State for active toast notifications
        context_state: State for current UI context
        available_shortcuts_state: State for available shortcuts
        shortcut_indicator_bar: Shortcut indicator bar component
        help_overlay: Help overlay row component
        help_toggle_btn: Help toggle button
        search_input: Search input textbox
        category_contents: Dictionary of category HTML components
        toast_notification_area: Toast notification area
    """
    # Global keyboard event listener (attached to document)
    shortcuts_ui.load(
        fn=None, inputs=None, outputs=None, js=setup_global_keyboard_listener()
    )

    # Context update triggers
    context_state.change(
        fn=update_shortcut_indicators,
        inputs=[context_state, available_shortcuts_state],
        outputs=[shortcut_indicator_bar],
    )

    # Help panel toggle
    help_toggle_btn.click(
        fn=toggle_help_panel,
        inputs=[shortcut_help_visible],
        outputs=[help_overlay, shortcut_help_visible],
    )

    # Search functionality
    search_input.change(
        fn=filter_shortcuts_display,
        inputs=[search_query, available_shortcuts_state],
        outputs=list(category_contents.values()),
    )

    # Toast auto-hide timer
    active_toast.change(
        fn=schedule_toast_hide, inputs=[active_toast], outputs=[toast_notification_area]
    )


def update_shortcut_indicators(
    context: ShortcutContext, available_shortcuts: List[KeyboardShortcut]
) -> str:
    """Update shortcut indicator bar based on current context.

    Args:
        context: Current UI context
        available_shortcuts: All registered shortcuts

    Returns:
        HTML string for updated indicator bar
    """
    context_shortcuts = [
        shortcut
        for shortcut in available_shortcuts
        if is_shortcut_available_in_context(shortcut, context)
    ]

    return render_shortcut_indicators_html(context_shortcuts)


def update_shortcut_help(
    context: ShortcutContext,
    available_shortcuts: List[KeyboardShortcut],
    search_query: str = "",
) -> Dict[str, str]:
    """Update shortcut help panel content based on context and search.

    Args:
        context: Current UI context
        available_shortcuts: All registered shortcuts
        search_query: Current search query

    Returns:
        Dictionary mapping category names to HTML content
    """
    return update_help_panel_content(context, available_shortcuts, search_query)


def update_help_panel_content(
    context: ShortcutContext,
    available_shortcuts: List[KeyboardShortcut],
    search_query: str,
) -> Dict[str, str]:
    """Update all help panel content based on context and search.

    Args:
        context: Current UI context
        available_shortcuts: All registered shortcuts
        search_query: Current search query

    Returns:
        Dictionary mapping category names to HTML content
    """
    context_shortcuts = [
        shortcut
        for shortcut in available_shortcuts
        if is_shortcut_available_in_context(shortcut, context)
    ]

    categories = ["All", "Navigation", "Actions", "Configuration"]
    updates = {}

    for category in categories:
        updates[category] = render_category_shortcuts_html(
            category, context_shortcuts, search_query
        )

    return updates


def filter_shortcuts_by_category_and_search(
    shortcuts: List[KeyboardShortcut], category: str, search_query: str
) -> List[KeyboardShortcut]:
    """Filter shortcuts by category and search query.

    Args:
        shortcuts: List of shortcuts to filter
        category: Category filter ("All", "Navigation", etc.)
        search_query: Search query string

    Returns:
        Filtered list of shortcuts
    """
    filtered = shortcuts

    # Apply category filter
    if category != "All":
        category_map = {
            "Navigation": ["global", "navigation"],
            "Actions": ["global", "actions"],
            "Configuration": ["global", "config"],
        }
        allowed_contexts = category_map.get(category, [])
        filtered = [
            s for s in filtered if any(ctx in s.context for ctx in allowed_contexts)
        ]

    # Apply search filter
    if search_query:
        query_lower = search_query.lower()
        filtered = [
            s
            for s in filtered
            if (
                query_lower in s.name.lower()
                or query_lower in s.description.lower()
                or any(query_lower in key.lower() for key in s.key_combination)
            )
        ]

    return filtered


def format_key_combination(combination: List[str]) -> str:
    """Format key combination for display.

    Args:
        combination: List of key strings

    Returns:
        Formatted string for display (e.g., "Ctrl+M")
    """
    key_display_map = {
        "ctrl": "Ctrl",
        "meta": "Cmd",
        "alt": "Alt",
        "shift": "Shift",
        "enter": "Enter",
        "escape": "Esc",
        "arrowup": "↑",
        "arrowdown": "↓",
        "arrowleft": "←",
        "arrowright": "→",
    }

    formatted_keys = []
    for key in combination:
        formatted_keys.append(key_display_map.get(key.lower(), key.upper()))

    return "+".join(formatted_keys)


def is_shortcut_available_in_context(
    shortcut: KeyboardShortcut, context: ShortcutContext
) -> bool:
    """Check if shortcut is available in the given context.

    Args:
        shortcut: Shortcut to check
        context: Current UI context

    Returns:
        True if available, False otherwise
    """
    # Global shortcuts available unless in modal
    if "global" in shortcut.context and not context.modal_open:
        return True

    # Tab-specific shortcuts
    if context.active_tab and context.active_tab in shortcut.context:
        return True

    # Input field restrictions
    if context.input_active and "input_safe" not in shortcut.context:
        return False

    # Streaming restrictions
    if context.streaming_active and "streaming_safe" not in shortcut.context:
        return False

    # Action availability
    if shortcut.action not in context.available_actions:
        return False

    return False


def toggle_help_panel(visible: bool) -> tuple:
    """Toggle help panel visibility.

    Args:
        visible: Current visibility state

    Returns:
        Tuple of (new_visibility, updated_state)
    """
    return not visible, not visible


def filter_shortcuts_display(
    search_query: str, shortcuts: List[KeyboardShortcut]
) -> Dict[str, str]:
    """Filter shortcuts display based on search.

    Args:
        search_query: Search query
        shortcuts: Available shortcuts

    Returns:
        Dictionary of category HTML content
    """
    # Placeholder - implement based on context
    return {}


def schedule_toast_hide(toast_content: str) -> str:
    """Schedule toast notification to hide.

    Args:
        toast_content: Current toast HTML

    Returns:
        Updated toast HTML (empty after timeout)
    """
    return ""  # In real implementation, use JS for timing


def setup_global_keyboard_listener() -> str:
    """Set up global keyboard event listener JavaScript.

    Returns:
        JavaScript code for event listener
    """
    return """
    // JavaScript for global keyboard listener
    document.addEventListener('keydown', function(event) {
        // Handle keyboard events
    });
    """


# CSS styling for the component
SHORTCUT_UI_CSS = """
.shortcut-indicators {
    position: fixed;
    bottom: 10px;
    right: 10px;
    z-index: 1000;
}

.shortcut-indicator-bar {
    display: flex;
    gap: 8px;
    align-items: center;
}

.shortcut-badge {
    background: #f0f0f0;
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 4px;
}

.help-toggle-btn {
    background: #007bff;
    color: white;
    border: none;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    cursor: pointer;
}

.toast-area {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1001;
}

.toast-notification {
    background: white;
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    gap: 8px;
    max-width: 300px;
}

.toast-notification.success {
    border-color: #28a745;
}

.toast-notification.error {
    border-color: #dc3545;
}

.toast-close {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 16px;
}

.keyboard-diagram {
    margin-top: 20px;
}

.keyboard-container {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 16px;
    background: #f8f9fa;
}

.keyboard-row {
    display: flex;
    gap: 2px;
    margin-bottom: 2px;
}

.key {
    width: 40px;
    height: 40px;
    border: 1px solid #ccc;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    background: white;
}

.key.modifier {
    background: #e9ecef;
    font-weight: bold;
}

.key.active {
    background: #007bff;
    color: white;
}

.keyboard-legend {
    margin-top: 16px;
    display: flex;
    gap: 16px;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
}

.key-sample {
    width: 20px;
    height: 20px;
    border: 1px solid #ccc;
    border-radius: 2px;
}

.key-sample.modifier {
    background: #e9ecef;
}

.key-sample.active {
    background: #007bff;
}

.shortcut-list {
    max-height: 400px;
    overflow-y: auto;
}

.shortcut-item {
    display: flex;
    gap: 12px;
    padding: 8px;
    border-bottom: 1px solid #eee;
    align-items: center;
}

.shortcut-keys kbd {
    background: #f8f9fa;
    border: 1px solid #ccc;
    border-radius: 3px;
    padding: 2px 4px;
    font-size: 11px;
    font-family: monospace;
}

.shortcut-name {
    font-weight: bold;
}

.shortcut-description {
    color: #666;
    font-size: 14px;
}

.shortcut-context {
    color: #999;
    font-size: 12px;
}

.close-btn {
    background: #dc3545;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.shortcut-search {
    width: 100%;
}
"""

# Note: CSS is included in the HTML components above
