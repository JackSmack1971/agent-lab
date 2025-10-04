# Function Specifications for Keyboard Shortcuts Integration

## Overview

This document specifies the functions required for integrating keyboard shortcuts into the main UI. All functions follow Agent Lab's coding standards with type hints, Google-style docstrings, and comprehensive error handling.

## Core Integration Functions

### `create_main_ui() -> gr.Blocks`
**Location**: `src/main.py` (modified)

**Purpose**: Creates the main tabbed interface with keyboard shortcuts integration.

**Parameters**: None

**Returns**:
- `gr.Blocks`: Main Gradio interface with shortcuts integration

**Modifications**:
- Adds imports for keyboard components
- Initializes `KeyboardHandler` and `ContextManager`
- Adds shortcut indicators to header
- Includes settings toggle for shortcuts
- Embeds keyboard shortcuts UI components
- Calls `setup_keyboard_integration()` for event handling

**Error Handling**: Catches initialization errors and logs warnings

---

### `setup_keyboard_integration(main_interface, keyboard_handler, context_manager, main_tabs, shortcuts_toggle, shortcuts_enabled, active_tab_state, shortcut_indicators) -> None`
**Location**: `src/main.py` (new)

**Purpose**: Sets up keyboard event handling and connects shortcut actions to UI components.

**Parameters**:
- `main_interface: gr.Blocks` - Main Gradio interface
- `keyboard_handler: KeyboardHandler` - Keyboard shortcut service
- `context_manager: ContextManager` - UI context manager
- `main_tabs: gr.Tabs` - Main tabbed interface
- `shortcuts_toggle: gr.Checkbox` - Shortcuts enable/disable toggle
- `shortcuts_enabled: gr.State` - Shortcuts enabled state
- `active_tab_state: gr.State` - Current active tab state
- `shortcut_indicators: gr.HTML` - Shortcut indicators component

**Returns**: None

**Functionality**:
- Registers tab-specific shortcuts
- Attaches global keyboard event listener
- Connects tab change events to context updates
- Handles shortcuts toggle changes
- Connects shortcut actions to UI handlers

**Error Handling**: Logs setup failures without crashing interface

---

### `register_tab_shortcuts(keyboard_handler) -> None`
**Location**: `src/main.py` (new)

**Purpose**: Registers keyboard shortcuts for tab navigation and common actions.

**Parameters**:
- `keyboard_handler: KeyboardHandler` - Shortcut registration service

**Returns**: None

**Functionality**:
- Creates `KeyboardShortcut` instances for tab switching
- Registers shortcuts with conflict detection
- Includes platform-specific key combinations

**Error Handling**: Logs registration failures and continues with available shortcuts

---

### `connect_shortcut_actions(keyboard_handler, main_tabs, context_manager, shortcuts_enabled) -> Dict[str, Callable]`
**Location**: `src/main.py` (new)

**Purpose**: Creates mapping of shortcut actions to UI handler functions.

**Parameters**:
- `keyboard_handler: KeyboardHandler` - Shortcut service
- `main_tabs: gr.Tabs` - Main tabs component
- `context_manager: ContextManager` - Context manager
- `shortcuts_enabled: gr.State` - Enabled state

**Returns**:
- `Dict[str, Callable]`: Mapping of action names to handler functions

**Functionality**:
- Defines action handlers for all shortcut types
- Returns handler dictionary for Gradio event connections

**Error Handling**: None (pure mapping function)

---

## Action Handler Functions

### `switch_to_tab(main_tabs, tab_id) -> None`
**Location**: `src/main.py` (new)

**Purpose**: Switches to specified tab and updates context.

**Parameters**:
- `main_tabs: gr.Tabs` - Main tabs component
- `tab_id: str` - Target tab identifier

**Returns**: None

**Functionality**:
- Triggers tab change in Gradio interface
- Updates context manager with new active tab
- Logs successful switches

**Error Handling**: Logs failures and shows user feedback

---

### `update_active_tab_context(current_tab) -> Tuple[str, str]`
**Location**: `src/main.py` (new)

**Purpose**: Updates UI context when active tab changes.

**Parameters**:
- `current_tab: str` - Currently active tab ID

**Returns**:
- `Tuple[str, str]`: (updated_tab_state, updated_indicators_html)

**Functionality**:
- Updates context manager
- Retrieves available shortcuts for new context
- Generates updated indicator bar HTML

**Error Handling**: Returns safe defaults on failure

---

### `toggle_shortcuts_enabled(enabled) -> bool`
**Location**: `src/main.py` (new)

**Purpose**: Toggles keyboard shortcuts enabled/disabled state.

**Parameters**:
- `enabled: bool` - New enabled state

**Returns**:
- `bool`: Confirmed enabled state

**Functionality**:
- Updates keyboard handler enabled state
- Updates context manager
- Saves preference to persistent storage

**Error Handling**: Reverts state on save failure

---

### `focus_search_input() -> None`
**Location**: `src/main.py` (new)

**Purpose**: Focuses on search input in active tab.

**Parameters**: None

**Returns**: None

**Functionality**:
- Determines active tab from context
- Focuses appropriate search input field

**Error Handling**: Logs failures without user disruption

---

### `start_new_conversation() -> None`
**Location**: `src/main.py` (new)

**Purpose**: Starts new conversation in Agent Testing tab.

**Parameters**: None

**Returns**: None

**Functionality**:
- Clears conversation history
- Resets chat interface state

**Error Handling**: Logs failures

---

### `save_current_session() -> None`
**Location**: `src/main.py` (new)

**Purpose**: Saves current session state.

**Parameters**: None

**Returns**: None

**Functionality**:
- Triggers session save operation

**Error Handling**: Logs failures

---

### `cancel_streaming_response() -> None`
**Location**: `src/main.py` (new)

**Purpose**: Cancels active streaming response.

**Parameters**: None

**Returns**: None

**Functionality**:
- Stops streaming operation
- Resets UI state

**Error Handling**: Logs failures

---

### `send_message() -> None`
**Location**: `src/main.py` (new)

**Purpose**: Sends current message in chat interface.

**Parameters**: None

**Returns**: None

**Functionality**:
- Triggers message send action

**Error Handling**: Logs failures

---

### `navigate_message_history(direction) -> None`
**Location**: `src/main.py` (new)

**Purpose**: Navigates message history up or down.

**Parameters**:
- `direction: str` - "up" or "down"

**Returns**: None

**Functionality**:
- Updates message input with history item

**Error Handling**: Logs failures

---

### `toggle_battle_mode() -> None`
**Location**: `src/main.py` (new)

**Purpose**: Toggles battle mode state.

**Parameters**: None

**Returns**: None

**Functionality**:
- Toggles battle mode if available

**Error Handling**: Logs failures

---

### `export_conversation() -> None`
**Location**: `src/main.py` (new)

**Purpose**: Exports current conversation.

**Parameters**: None

**Returns**: None

**Functionality**:
- Triggers export operation

**Error Handling**: Logs failures

---

### `toggle_help_overlay() -> None`
**Location**: `src/main.py` (new)

**Purpose**: Toggles keyboard shortcuts help overlay.

**Parameters**: None

**Returns**: None

**Functionality**:
- Shows/hides help overlay component

**Error Handling**: Logs failures

---

## Utility Functions

### `save_shortcuts_preference(enabled) -> None`
**Location**: `src/main.py` (new)

**Purpose**: Saves shortcuts enabled preference.

**Parameters**:
- `enabled: bool` - Preference value

**Returns**: None

**Functionality**:
- Persists setting to user configuration

**Error Handling**: Logs failures

---

### `load_shortcuts_preference() -> bool`
**Location**: `src/main.py` (new)

**Purpose**: Loads shortcuts enabled preference.

**Parameters**: None

**Returns**:
- `bool`: Preference value (default True)

**Functionality**:
- Retrieves setting from persistent storage

**Error Handling**: Returns default on failure

---

## JavaScript Integration Functions

### `setup_global_keyboard_listener_js(keyboard_handler) -> str`
**Location**: `src/main.py` (new)

**Purpose**: Generates JavaScript for global keyboard event handling.

**Parameters**:
- `keyboard_handler: KeyboardHandler` - Handler instance

**Returns**:
- `str`: JavaScript code as string

**Functionality**:
- Creates event listener for keydown events
- Processes shortcuts through keyboard handler
- Dispatches actions to Gradio

**Error Handling**: JavaScript error handling included

---

## Integration Requirements

### Dependencies
- `src.utils.keyboard_handler.KeyboardHandler`
- `src.utils.keyboard_handler.ContextManager`
- `src.components.keyboard_shortcuts.create_keyboard_shortcuts_ui`
- `src.components.settings.create_settings_tab` (assumed)
- `gradio` components

### State Management
- `shortcuts_enabled: gr.State` - Global shortcuts enabled state
- `active_tab_state: gr.State` - Current active tab
- Context maintained in `ContextManager` instance

### Event Flow
1. User presses key combination
2. JavaScript captures event and prevents default if handled
3. Event processed through `KeyboardHandler.process_event()`
4. Action dispatched to appropriate handler function
5. Handler updates UI components and context
6. Indicators and help overlay update reactively

### Platform Support
- Automatic platform detection (Windows, macOS, Linux)
- Key combination normalization for cross-platform compatibility
- Browser conflict avoidance

### Accessibility
- Visual indicators for available shortcuts
- Help overlay with comprehensive documentation
- Keyboard-only navigation support
- Screen reader compatible elements

### Error Recovery
- Graceful degradation when shortcuts fail
- Logging for debugging and monitoring
- User feedback for failed operations
- State consistency maintenance