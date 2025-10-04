# Keyboard Shortcut System Architecture

## Overview
The Keyboard Shortcut System provides comprehensive keyboard navigation and workflow acceleration for Agent Lab. This system enables power-user efficiency through context-aware shortcuts, cross-platform compatibility, and seamless integration across all application tabs (Agent Testing, Model Matchmaker, Cost Optimizer).

## 1. System Design

### Component Architecture

#### Core Components
The Keyboard Shortcut System follows Agent Lab's established 3-layer architecture pattern with specialized components:

**UI Layer (`src/components/`)**:
- `KeyboardShortcutsUI` Gradio component for displaying shortcut help and indicators
- Integrated into main application header/footer for global accessibility
- Visual feedback components for active shortcuts and context states

**Runtime Layer (`src/services/`)**:
- `KeyboardHandler` service for shortcut registration, conflict resolution, and execution
- `PlatformDetector` utility for cross-platform shortcut adaptation
- `ContextManager` for dynamic shortcut enabling/disabling based on UI state

**API Layer (Integration)**:
- Extends existing Gradio event handling in `app.py`
- Integrates with tab navigation system in `src/main.py`
- Hooks into component-specific actions across all tabs

#### Component Boundaries and Interfaces

**Data Models (`src/models/keyboard.py`)**:
```python
class KeyboardShortcut(BaseModel):
    """Represents a keyboard shortcut definition."""
    id: str
    name: str
    description: str
    key_combination: List[str]  # e.g., ['ctrl', 'm']
    action: str  # Action identifier
    context: List[str]  # Contexts where shortcut is active
    platform_overrides: Dict[str, List[str]]  # Platform-specific keys
    enabled: bool = True

class ShortcutContext(BaseModel):
    """Represents UI context for shortcut availability."""
    active_tab: str
    focused_element: str
    modal_open: bool
    input_active: bool
    streaming_active: bool
    available_actions: List[str]

class ShortcutEvent(BaseModel):
    """Represents a keyboard event for processing."""
    key: str
    ctrl_key: bool
    meta_key: bool
    alt_key: bool
    shift_key: bool
    platform: str
    context: ShortcutContext
```

**Service Interface (`src/services/keyboard_handler.py`)**:
```python
class KeyboardHandler:
    """Central service for keyboard shortcut management."""

    def register_shortcut(self, shortcut: KeyboardShortcut) -> None:
        """Register a new keyboard shortcut."""

    def unregister_shortcut(self, shortcut_id: str) -> None:
        """Remove a keyboard shortcut."""

    def process_event(self, event: ShortcutEvent) -> Optional[str]:
        """Process keyboard event and return action if matched."""

    def get_available_shortcuts(self, context: ShortcutContext) -> List[KeyboardShortcut]:
        """Get shortcuts available in current context."""

    def check_conflicts(self, shortcut: KeyboardShortcut) -> List[str]:
        """Check for conflicts with existing shortcuts."""

class PlatformDetector:
    """Utility for detecting and adapting to different platforms."""

    @staticmethod
    def get_platform() -> str:
        """Detect current platform (windows, mac, linux)."""

    @staticmethod
    def normalize_combination(combination: List[str], platform: str) -> List[str]:
        """Normalize key combination for platform."""

class ContextManager:
    """Manages UI context for shortcut availability."""

    def get_current_context(self) -> ShortcutContext:
        """Get current UI context."""

    def is_shortcut_available(self, shortcut: KeyboardShortcut, context: ShortcutContext) -> bool:
        """Check if shortcut is available in context."""
```

**UI Interface (`src/components/keyboard_shortcuts.py`)**:
```python
def create_keyboard_shortcuts_ui() -> gr.Blocks:
    """Create keyboard shortcuts help UI component."""

def create_shortcut_indicator(active_shortcuts: List[str]) -> gr.HTML:
    """Create visual indicator for active shortcuts."""

def update_shortcut_help(context: ShortcutContext) -> str:
    """Update help display based on current context."""
```

### Data Flows

#### Shortcut Registration Flow
```
Component Initialization → Shortcut Definition → Conflict Check
    ↓
Registration → Platform Adaptation → Context Mapping
    ↓
Active Shortcut Pool → UI Integration
```

1. **Registration Process**:
   - Components define shortcuts during initialization
   - Platform detector adapts key combinations
   - Conflict resolver validates no browser/system conflicts
   - Context manager maps shortcuts to UI states

#### Event Processing Flow
```
User Keypress → Browser Event → Gradio Handler
    ↓
Event Normalization → Context Evaluation → Shortcut Matching
    ↓
Action Execution → UI Update → Feedback Display
```

1. **Real-Time Processing**:
   - Keyboard events captured via Gradio's event system
   - Platform normalization handles Ctrl/Cmd differences
   - Context checking prevents inappropriate actions
   - Action routing to appropriate component handlers

#### Context Awareness Flow
```
UI State Change → Context Update → Shortcut Filtering
    ↓
Available Actions → Indicator Update → Help Refresh
    ↓
User Feedback → Visual Cues
```

1. **Dynamic Adaptation**:
   - Tab switches update active context
   - Input focus changes disable text-entry shortcuts
   - Modal dialogs restrict shortcuts appropriately
   - Streaming states modify available actions

### Integration Patterns

#### Main Application Integration (`src/main.py`)
- Global keyboard event handler attached to main Blocks
- Context manager integrated with tab navigation
- Shortcut indicators in application header
- Help overlay accessible from all tabs

#### Tab-Specific Integration
- **Agent Testing Tab**: Chat input, model switching, session management
- **Model Matchmaker Tab**: Recommendation application, filter toggles
- **Cost Optimizer Tab**: Alert management, trend navigation

#### Component Integration (`src/components/`)
- Each component registers its shortcuts on creation
- Action handlers provided as callbacks
- Context updates triggered by component state changes

## 2. Platform-Specific Considerations

### Cross-Platform Compatibility

#### Key Combination Normalization
```python
PLATFORM_MAPPINGS = {
    'mac': {'ctrl': 'meta', 'alt': 'option'},
    'windows': {'meta': 'ctrl'},
    'linux': {'meta': 'ctrl'}
}
```

#### Browser Conflict Resolution
- **Reserved Combinations**: Avoid browser shortcuts (Ctrl+T, Ctrl+W, etc.)
- **Graceful Degradation**: Fall back to alternative combinations
- **User Override**: Allow custom shortcut configuration

### Platform Detection Strategy
- **Client-Side Detection**: JavaScript platform detection
- **Server-Side Adaptation**: Python-based combination mapping
- **Runtime Switching**: Handle platform changes during session

## 3. Conflict Resolution Strategy

### Conflict Detection
- **Browser Conflicts**: Check against known browser shortcuts
- **System Conflicts**: Platform-specific reserved combinations
- **Application Conflicts**: Duplicate key combinations within app

### Resolution Mechanisms
- **Priority System**: Component-specific priority levels
- **Context Restrictions**: Limit shortcuts to specific UI contexts
- **Alternative Combinations**: Provide fallback key combinations
- **User Configuration**: Allow users to resolve conflicts manually

### Validation Pipeline
```
New Shortcut → Browser Conflict Check → System Conflict Check
    ↓
Application Conflict Check → Context Validation → Registration
    ↓
User Notification (if conflicts found)
```

## 4. Context Awareness Logic

### Context Types
- **Global Context**: Always available shortcuts
- **Tab Context**: Tab-specific shortcuts
- **Component Context**: Component-specific actions
- **Modal Context**: Dialog and overlay restrictions

### Context Evaluation
```python
def evaluate_context_availability(shortcut: KeyboardShortcut, context: ShortcutContext) -> bool:
    """Determine if shortcut is available in current context."""

    # Global shortcuts always available unless in modal
    if shortcut.context == ['global'] and not context.modal_open:
        return True

    # Tab-specific shortcuts
    if context.active_tab in shortcut.context:
        return True

    # Input field restrictions
    if context.input_active and 'input_safe' not in shortcut.context:
        return False

    # Streaming restrictions
    if context.streaming_active and 'streaming_safe' not in shortcut.context:
        return False

    return False
```

### Dynamic Context Updates
- **Event-Driven**: UI state changes trigger context updates
- **Polling Fallback**: Periodic context checks for reliability
- **Debounced Updates**: Prevent excessive context recalculations

## 5. UI Indicator Patterns

### Visual Feedback Components
- **Shortcut Hints**: Tooltips showing available shortcuts
- **Active Indicators**: Highlight currently available shortcuts
- **Context Badges**: Show current context restrictions
- **Help Overlay**: Comprehensive shortcut reference

### Accessibility Considerations
- **Screen Reader Support**: ARIA labels for shortcut indicators
- **High Contrast**: Visible indicators in all themes
- **Keyboard Navigation**: Full keyboard accessibility for help system
- **Focus Management**: Proper focus handling around shortcuts

## 6. Testing Strategy

### Unit Testing (`tests/unit/test_keyboard_handler.py`)
- **Shortcut Registration**: Test adding/removing shortcuts
- **Event Processing**: Test keyboard event handling
- **Platform Detection**: Test cross-platform key mapping
- **Conflict Resolution**: Test conflict detection and resolution

### Integration Testing (`tests/integration/test_keyboard_integration.py`)
- **End-to-End Shortcuts**: Test complete shortcut workflows
- **Context Switching**: Test shortcut availability across tabs
- **Platform Compatibility**: Test on different platforms
- **Browser Compatibility**: Test in different browsers

### Component Testing
- **UI Component Tests**: Test shortcut help display
- **Service Integration**: Test with actual Gradio components
- **Performance Tests**: Test event processing latency

### Test Coverage Requirements
- **Unit Tests**: 90%+ coverage for all keyboard logic
- **Integration Tests**: Full workflow coverage
- **Cross-Platform Tests**: Windows, Mac, Linux validation
- **Accessibility Tests**: Screen reader and keyboard navigation

## 7. Security Considerations

### Input Validation
- **Event Sanitization**: Validate all keyboard event data
- **Action Authorization**: Ensure shortcuts only trigger allowed actions
- **Context Isolation**: Prevent shortcuts from accessing unauthorized contexts

### Rate Limiting
- **Event Throttling**: Prevent keyboard event spam
- **Action Limiting**: Rate limit expensive shortcut actions
- **Logging**: Audit all shortcut usage for security monitoring

## 8. Performance Optimization

### Event Processing Optimization
- **Debounced Events**: Prevent excessive event processing
- **Lazy Loading**: Load shortcuts only when needed
- **Caching**: Cache context evaluations and shortcut lookups

### Memory Management
- **Shortcut Pool Limits**: Maximum number of registered shortcuts
- **Context Cache**: Cache recent context evaluations
- **Event Cleanup**: Proper cleanup of event listeners

## 9. Observability

### Metrics Collection
```python
shortcut_usage = Counter(
    "shortcut_usage_total",
    "Number of times each shortcut is used",
    ["shortcut_id", "context", "platform"]
)

shortcut_conflicts = Gauge(
    "shortcut_conflicts_detected",
    "Number of detected shortcut conflicts"
)

context_evaluation_time = Histogram(
    "context_evaluation_duration_seconds",
    "Time spent evaluating shortcut context",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1]
)
```

### Logging Strategy
- **Usage Logging**: Track shortcut usage patterns
- **Error Logging**: Log shortcut processing errors
- **Conflict Logging**: Log detected conflicts and resolutions
- **Performance Logging**: Monitor processing latency

### Monitoring Dashboards
- **Usage Analytics**: Most/least used shortcuts
- **Conflict Monitoring**: Active conflicts and resolutions
- **Performance Metrics**: Processing latency and error rates
- **Platform Distribution**: Usage across different platforms

## Component Maintainability and Testability

### Module Structure
- **Max Lines per Module**: 500 lines to maintain readability
- **Single Responsibility**: Each module handles one concern
- **Dependency Injection**: Services accept dependencies for testability
- **Interface Segregation**: Clean interfaces between components

### Code Quality Standards
- **Type Hints**: All functions use proper type annotations
- **Docstrings**: Google-style documentation for all public APIs
- **Linting**: Black formatting and pylint compliance
- **Security**: Bandit security linting with zero vulnerabilities

### Extensibility
- **Plugin Architecture**: Allow third-party shortcuts
- **Configuration Files**: External shortcut configuration
- **Custom Actions**: Support for user-defined actions
- **Theme Integration**: Shortcut indicators adapt to UI themes

This architecture ensures the Keyboard Shortcut System provides powerful, accessible navigation while maintaining security, performance, and cross-platform compatibility throughout Agent Lab.