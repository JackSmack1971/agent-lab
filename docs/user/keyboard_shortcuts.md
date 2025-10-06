# Keyboard Shortcuts Documentation

## Overview

Agent Lab provides comprehensive keyboard shortcut support to enhance productivity and streamline workflow. All shortcuts are context-aware, cross-platform compatible, and include accessibility features.

### Key Features

- **Cross-Platform Support**: Automatic platform detection with optimized key combinations for Windows, macOS, and Linux
- **Context Awareness**: Shortcuts adapt based on current UI state (input fields, modals, streaming responses)
- **Accessibility**: Screen reader support, high contrast indicators, and customizable bindings
- **Safety**: Rate limiting and conflict detection to prevent accidental actions
- **Visual Feedback**: Toast notifications and indicator bars show shortcut usage

## Getting Started

### Basic Usage

1. **Help Panel**: Press `Ctrl + /` (or `Cmd + /` on Mac) to open the interactive shortcuts help
2. **Search**: Use the search box in the help panel to find specific shortcuts
3. **Visual Indicators**: Look for the shortcut indicator bar at the bottom of the interface
4. **Categories**: Browse shortcuts by Navigation, Actions, or Configuration categories

### Platform-Specific Notes

| Platform | Modifier Key | Notes |
|----------|-------------|--------|
| **Windows** | `Ctrl` | Standard Windows shortcuts, avoids browser conflicts |
| **macOS** | `Cmd` (⌘) | Follows macOS conventions, uses Command key |
| **Linux** | `Ctrl` | Compatible with most desktop environments |

## Complete Shortcut Reference

### Navigation Shortcuts

These shortcuts help you move around the application efficiently.

#### Open Model Matchmaker
- **Shortcut**: `Ctrl + M` (Windows/Linux) / `Cmd + M` (macOS)
- **Description**: Navigate to the Model Matchmaker tab
- **Context**: Available globally when no modal is open
- **Use Case**: Quickly switch to model selection and comparison tools

#### Focus Search
- **Shortcut**: `Ctrl + K` (Windows/Linux) / `Cmd + K` (macOS)
- **Description**: Focus on the search/command palette
- **Context**: Available globally
- **Use Case**: Quickly access search functionality for models, settings, or commands

### Action Shortcuts

Core operational shortcuts for managing conversations and responses.

#### New Conversation
- **Shortcut**: `Ctrl + N` (Windows/Linux) / `Cmd + N` (macOS)
- **Description**: Start a new conversation
- **Context**: Available globally when no modal is open
- **Use Case**: Begin fresh conversations without using the mouse

#### Save Session
- **Shortcut**: `Ctrl + S` (Windows/Linux) / `Cmd + S` (macOS)
- **Description**: Save the current session
- **Context**: Available globally
- **Use Case**: Preserve conversation history and settings

#### Export Conversation
- **Shortcut**: `Ctrl + E` (Windows/Linux) / `Cmd + E` (macOS)
- **Description**: Export the current conversation
- **Context**: Available globally when conversation data exists
- **Use Case**: Save conversations to external files or share them

#### Send Message
- **Shortcut**: `Ctrl + Enter` (Windows/Linux) / `Cmd + Enter` (macOS)
- **Description**: Send the current message
- **Context**: Available when input field is active and has content
- **Use Case**: Submit messages without clicking the send button

#### Cancel Streaming Response
- **Shortcut**: `Escape`
- **Description**: Cancel an active streaming response
- **Context**: Available during streaming responses
- **Use Case**: Stop long-running responses quickly

#### Navigate Message History Up
- **Shortcut**: `Ctrl + ↑` (Windows/Linux) / `Cmd + ↑` (macOS)
- **Description**: Navigate to previous message in history
- **Context**: Available in input fields with message history
- **Use Case**: Quickly recall and edit previous messages

#### Navigate Message History Down
- **Shortcut**: `Ctrl + ↓` (Windows/Linux) / `Cmd + ↓` (macOS)
- **Description**: Navigate to next message in history
- **Context**: Available in input fields with message history
- **Use Case**: Cycle through message history forward

### Configuration Shortcuts

Shortcuts for accessing settings and toggling application features.

#### Open Settings
- **Shortcut**: `Ctrl + ,` (Windows/Linux) / `Cmd + ,` (macOS)
- **Description**: Open application settings panel
- **Context**: Available globally when no modal is open
- **Use Case**: Quickly access configuration options

#### Show Keyboard Shortcuts Help
- **Shortcut**: `Ctrl + /` (Windows/Linux) / `Cmd + /` (macOS)
- **Description**: Display the keyboard shortcuts help panel
- **Context**: Available globally
- **Use Case**: Learn shortcuts or search for specific functionality

#### Toggle Battle Mode
- **Shortcut**: `Ctrl + B` (Windows/Linux) / `Cmd + B` (macOS)
- **Description**: Enable or disable battle mode for model comparison
- **Context**: Available globally
- **Use Case**: Switch between single model and comparison modes

## Platform-Specific Notes

### Windows
- Uses `Ctrl` as the primary modifier key
- Avoids common browser shortcuts (`Ctrl+T`, `Ctrl+W`, `Ctrl+R`)
- Compatible with Windows accessibility features

### macOS
- Uses `Cmd` (⌘) instead of `Ctrl` for consistency with macOS conventions
- Supports standard macOS keyboard navigation
- Compatible with VoiceOver and other accessibility tools

### Linux
- Uses `Ctrl` as the primary modifier key
- Compatible with most desktop environments (GNOME, KDE, etc.)
- Supports Orca screen reader and other accessibility tools

## Troubleshooting and Tips

### Common Issues

#### Shortcuts Not Working
- **Check Context**: Some shortcuts only work in specific UI contexts (e.g., input fields)
- **Modal Conflicts**: Shortcuts are disabled when modals or dialogs are open
- **Browser Focus**: Ensure the application window has focus
- **Platform Detection**: Verify the correct platform is detected in settings

#### Rate Limiting
- The system prevents rapid-fire keyboard events to avoid accidental actions
- If shortcuts feel unresponsive, wait a moment and try again
- Rate limit is set to 10 events per second maximum

#### Conflict Resolution
- Custom shortcuts are checked for conflicts with browser and system shortcuts
- Conflicts are logged but don't prevent shortcut registration
- Use the help panel to see which shortcuts are currently active

### Tips for Efficiency

1. **Learn Gradually**: Start with basic shortcuts like `Ctrl+K` (search) and `Ctrl+/` (help)
2. **Context Awareness**: Pay attention to the shortcut indicator bar showing available shortcuts
3. **Search Function**: Use the search in the help panel to quickly find shortcuts
4. **Visual Feedback**: Watch for toast notifications confirming shortcut actions
5. **Practice**: Use shortcuts consistently to build muscle memory

### Customization

While Agent Lab doesn't currently support user-defined shortcuts, the system is designed for future extensibility. The help panel and indicator bar will automatically reflect any new shortcuts added through configuration.

## Accessibility Information

### Screen Reader Support
- All shortcuts are announced through ARIA labels and live regions
- The help panel includes semantic markup for screen readers
- Keyboard navigation follows WCAG 2.1 guidelines

### Visual Indicators
- High contrast shortcut badges with clear typography
- Visual keyboard diagram in the help panel
- Toast notifications provide clear feedback for actions

### Alternative Input Methods
- Compatible with keyboard-only navigation
- Supports assistive technologies like switch control
- Rate limiting prevents accidental activations

## Technical Details for Developers

### Architecture Overview

The keyboard shortcut system consists of three main components:

1. **KeyboardHandler**: Core service managing shortcut registration and event processing
2. **ContextManager**: Tracks UI state to determine shortcut availability
3. **UI Components**: Visual indicators, help panels, and feedback systems

### Shortcut Registration

Shortcuts are defined as `KeyboardShortcut` objects with the following properties:

```python
KeyboardShortcut(
    id="unique_identifier",
    name="Human Readable Name",
    description="What the shortcut does",
    key_combination=["ctrl", "m"],
    action="action_to_perform",
    context=["global"],
    platform_overrides={"mac": ["meta", "m"]}
)
```

### Context System

Shortcuts use context tags to determine availability:

- `global`: Available when no modal is open
- `input_safe`: Safe to use in input fields
- `streaming_safe`: Safe during streaming responses
- Tab-specific contexts (e.g., `matchmaker`, `chat`)

### Platform Detection

The system automatically detects the platform and normalizes key combinations:

- **Windows**: `ctrl` → `ctrl`, `meta` → `ctrl`
- **macOS**: `ctrl` → `meta`, `meta` → `meta`
- **Linux**: `ctrl` → `ctrl`, `meta` → `ctrl`

### Event Processing

Keyboard events are processed through a pipeline:

1. **Rate Limiting**: Check event frequency (max 10/sec)
2. **Platform Normalization**: Convert to platform-specific combinations
3. **Context Validation**: Verify shortcut availability
4. **Action Dispatch**: Return action string for execution

### Security Considerations

- Rate limiting prevents keyboard-based attacks
- Context validation prevents unsafe operations
- Browser-reserved shortcuts are avoided
- All shortcuts are validated before registration

### Future Extensibility

The system is designed to support:

- User-defined custom shortcuts
- Plugin-based shortcut extensions
- Advanced context rules
- Shortcut profiles and themes
- Integration with external accessibility tools

---

For questions or issues with keyboard shortcuts, refer to the main [Agent Lab documentation](../README.md) or open an issue in the project repository.