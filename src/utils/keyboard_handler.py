"""Keyboard shortcut handler for Agent Lab.

This module provides cross-platform keyboard shortcut management with context awareness,
conflict detection, and rate limiting for security.
"""

from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field, ValidationError
import platform
import time
from collections import defaultdict
import logging

# Constants for platform mappings
PLATFORM_MAPPINGS = {
    'mac': {'ctrl': 'meta', 'alt': 'option'},
    'windows': {'meta': 'ctrl'},
    'linux': {'meta': 'ctrl'}
}

# Browser reserved shortcuts to avoid
BROWSER_RESERVED = {
    'windows': {'ctrl+t', 'ctrl+w', 'ctrl+r', 'ctrl+n', 'f5'},
    'mac': {'meta+t', 'meta+w', 'meta+r', 'meta+n', 'meta+q'},
    'linux': {'ctrl+t', 'ctrl+w', 'ctrl+r', 'ctrl+n', 'f5'}
}

# Default shortcut mappings
DEFAULT_SHORTCUTS = [
    {
        'id': 'open_matchmaker',
        'name': 'Open Model Matchmaker',
        'description': 'Navigate to Model Matchmaker tab',
        'key_combination': ['ctrl', 'm'],
        'action': 'open_matchmaker',
        'context': ['global'],
        'platform_overrides': {'mac': ['meta', 'm']}
    },
    {
        'id': 'focus_search',
        'name': 'Focus Search',
        'description': 'Focus on search/command palette',
        'key_combination': ['ctrl', 'k'],
        'action': 'focus_search',
        'context': ['global'],
        'platform_overrides': {'mac': ['meta', 'k']}
    },
    {
        'id': 'new_conversation',
        'name': 'New Conversation',
        'description': 'Start a new conversation',
        'key_combination': ['ctrl', 'n'],
        'action': 'new_conversation',
        'context': ['global'],
        'platform_overrides': {'mac': ['meta', 'n']}
    },
    {
        'id': 'save_session',
        'name': 'Save Session',
        'description': 'Save current session',
        'key_combination': ['ctrl', 's'],
        'action': 'save_session',
        'context': ['global'],
        'platform_overrides': {'mac': ['meta', 's']}
    },
    {
        'id': 'open_settings',
        'name': 'Open Settings',
        'description': 'Open application settings',
        'key_combination': ['ctrl', ','],
        'action': 'open_settings',
        'context': ['global'],
        'platform_overrides': {'mac': ['meta', ',']}
    },
    {
        'id': 'show_help',
        'name': 'Show Keyboard Shortcuts Help',
        'description': 'Display keyboard shortcuts help',
        'key_combination': ['ctrl', '/'],
        'action': 'show_help',
        'context': ['global'],
        'platform_overrides': {'mac': ['meta', '/']}
    },
    {
        'id': 'toggle_battle_mode',
        'name': 'Toggle Battle Mode',
        'description': 'Enable or disable battle mode',
        'key_combination': ['ctrl', 'b'],
        'action': 'toggle_battle_mode',
        'context': ['global'],
        'platform_overrides': {'mac': ['meta', 'b']}
    },
    {
        'id': 'export_conversation',
        'name': 'Export Conversation',
        'description': 'Export current conversation',
        'key_combination': ['ctrl', 'e'],
        'action': 'export_conversation',
        'context': ['global'],
        'platform_overrides': {'mac': ['meta', 'e']}
    },
    {
        'id': 'cancel_streaming',
        'name': 'Cancel Streaming Response',
        'description': 'Cancel active streaming response',
        'key_combination': ['escape'],
        'action': 'cancel_streaming',
        'context': ['global', 'streaming_safe']
    },
    {
        'id': 'send_message',
        'name': 'Send Message',
        'description': 'Send the current message',
        'key_combination': ['ctrl', 'enter'],
        'action': 'send_message',
        'context': ['input_safe'],
        'platform_overrides': {'mac': ['meta', 'enter']}
    },
    {
        'id': 'navigate_history_up',
        'name': 'Navigate Message History Up',
        'description': 'Navigate to previous message in history',
        'key_combination': ['ctrl', 'arrowup'],
        'action': 'navigate_history_up',
        'context': ['input_safe'],
        'platform_overrides': {'mac': ['meta', 'arrowup']}
    },
    {
        'id': 'navigate_history_down',
        'name': 'Navigate Message History Down',
        'description': 'Navigate to next message in history',
        'key_combination': ['ctrl', 'arrowdown'],
        'action': 'navigate_history_down',
        'context': ['input_safe'],
        'platform_overrides': {'mac': ['meta', 'arrowdown']}
    }
]

# Rate limiting constants
MAX_EVENTS_PER_SECOND = 10
RATE_LIMIT_WINDOW = 1.0  # seconds

logger = logging.getLogger(__name__)


class KeyboardShortcut(BaseModel):
    """Represents a keyboard shortcut definition.

    Attributes:
        id: Unique identifier for the shortcut.
        name: Human-readable name.
        description: Description of what the shortcut does.
        key_combination: List of keys (e.g., ['ctrl', 'm']).
        action: Action identifier to execute.
        context: List of contexts where shortcut is active.
        platform_overrides: Platform-specific key combinations.
        enabled: Whether the shortcut is currently enabled.
    """
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    key_combination: List[str] = Field(min_length=1)
    action: str = Field(..., min_length=1)
    context: List[str] = Field(default_factory=list)
    platform_overrides: Dict[str, List[str]] = Field(default_factory=dict)
    enabled: bool = True

    def get_normalized_combination(self, platform: str) -> List[str]:
        """Get platform-normalized key combination.

        Args:
            platform: Current platform ('windows', 'mac', 'linux').

        Returns:
            Normalized key combination list.
        """
        if platform in self.platform_overrides:
            return self.platform_overrides[platform]
        return PlatformDetector.normalize_combination(self.key_combination, platform)


class ShortcutContext(BaseModel):
    """Represents UI context for shortcut availability.

    Attributes:
        active_tab: Currently active tab name.
        focused_element: Currently focused element ID.
        modal_open: Whether a modal dialog is open.
        input_active: Whether an input field is active.
        streaming_active: Whether streaming response is active.
        available_actions: List of currently available actions.
    """
    active_tab: str = ""
    focused_element: str = ""
    modal_open: bool = False
    input_active: bool = False
    streaming_active: bool = False
    available_actions: List[str] = Field(default_factory=list)


class ShortcutEvent(BaseModel):
    """Represents a keyboard event for processing.

    Attributes:
        key: The pressed key.
        ctrl_key: Whether Ctrl key is pressed.
        meta_key: Whether Meta/Cmd key is pressed.
        alt_key: Whether Alt key is pressed.
        shift_key: Whether Shift key is pressed.
        platform: Detected platform.
        context: Current UI context.
        timestamp: Event timestamp for rate limiting.
    """
    key: str = Field(..., min_length=1)
    ctrl_key: bool = False
    meta_key: bool = False
    alt_key: bool = False
    shift_key: bool = False
    platform: str = Field(default="")
    context: ShortcutContext = Field(default_factory=ShortcutContext)
    timestamp: float = Field(default_factory=time.time)

    def to_combination(self) -> List[str]:
        """Convert event to key combination with SORTED modifiers."""
        combination = []
        
        # Add modifiers in SORTED order: ctrl, meta, alt, shift
        if self.ctrl_key:
            combination.append('ctrl')
        if self.meta_key:
            combination.append('meta')
        if self.alt_key:
            combination.append('alt')
        if self.shift_key:
            combination.append('shift')
        
        # Add main key (lowercase)
        combination.append(self.key.lower())
        
        return combination


class PlatformDetector:
    """Utility for detecting and adapting to different platforms."""

    @staticmethod
    def get_platform() -> str:
        """Detect current platform.

        Returns:
            Platform string: 'windows', 'mac', or 'linux'.

        Raises:
            ValueError: If platform detection fails.
        """
        try:
            system = platform.system().lower()
            if system == 'darwin':
                return 'mac'
            elif system == 'windows':
                return 'windows'
            elif system == 'linux':
                return 'linux'
            else:
                raise ValueError(f"Unsupported platform: {system}")
        except ValidationError as e:
            logger.error(f"Shortcut validation failed: {e}")
            raise ValueError("Invalid shortcut data") from e
        except Exception as e:
            logger.error(f"Platform detection failed: {e}")
            raise ValueError("Unable to detect platform") from e

    @staticmethod
    def normalize_combination(combination: List[str], platform: str) -> List[str]:
        """Normalize key combination for platform.

        Args:
            combination: Original key combination.
            platform: Target platform.

        Returns:
            Normalized combination.

        Raises:
            ValueError: If combination is invalid.
        """
        if not combination:
            raise ValueError("Empty key combination")

        normalized = []
        mapping = PLATFORM_MAPPINGS.get(platform, {})

        for key in combination:
            key_lower = key.lower()
            if key_lower in mapping:
                normalized.append(mapping[key_lower])
            else:
                normalized.append(key_lower)

        return normalized


class ContextManager:
    """Manages UI context for shortcut availability."""

    def __init__(self):
        """Initialize context manager."""
        self._current_context = ShortcutContext()
        self._context_cache: Dict[str, ShortcutContext] = {}
        self._cache_timeout = 0.1  # seconds

    def get_current_context(self) -> ShortcutContext:
        """Get current UI context.

        Returns:
            Current ShortcutContext instance.
        """
        # In real implementation, this would query the UI state
        # For pseudocode, return cached or default context
        return self._current_context

    def update_context(self, **kwargs) -> None:
        """Update current context with new values.

        Args:
            **kwargs: Context attributes to update.
        """
        for key, value in kwargs.items():
            if hasattr(self._current_context, key):
                try:
                    setattr(self._current_context, key, value)
                except Exception as e:
                    logger.error(f"Failed to set context attribute {key}: {e}")
            else:
                logger.warning(f"Unknown context attribute: {key}")

    def is_shortcut_available(self, shortcut: KeyboardShortcut, context: ShortcutContext) -> bool:
        """Check if shortcut is available in context.

        Args:
            shortcut: Shortcut to check.
            context: Current context.

        Returns:
            True if shortcut is available, False otherwise.
        """
        # Modal blocks ALL shortcuts (no exceptions)
        if context.modal_open:
            return False

        # Input restrictions check for 'input_safe' flag
        if context.input_active and 'input_safe' not in shortcut.context:
            return False

        # Streaming restrictions check for 'streaming_safe' flag
        if context.streaming_active and 'streaming_safe' not in shortcut.context:
            return False

        # Available actions check: if list is non-empty, action must be in it
        if context.available_actions is not None and shortcut.action not in context.available_actions:
            return False

        # Global shortcuts
        if 'global' in shortcut.context:
            return True

        # Tab-specific shortcuts
        if context.active_tab and context.active_tab in shortcut.context:
            return True

        # Context flags (input_safe, streaming_safe, etc.)
        context_flags = {'input_safe', 'streaming_safe'}
        if shortcut.context and any(flag in context_flags for flag in shortcut.context):
            return True

        # Empty context = not available by default
        return False


class KeyboardHandler:
    """Central service for keyboard shortcut management."""

    def __init__(self, platform_detector: Optional[PlatformDetector] = None,
                 context_manager: Optional[ContextManager] = None):
        """Initialize keyboard handler.

        Args:
            platform_detector: Platform detection utility.
            context_manager: Context management utility.
        """
        self._platform_detector = platform_detector or PlatformDetector()
        self._context_manager = context_manager or ContextManager()
        self._shortcuts: Dict[str, KeyboardShortcut] = {}
        self._event_history: List[float] = []
        self._platform = self._platform_detector.get_platform()

        # Register default shortcuts
        for shortcut_data in DEFAULT_SHORTCUTS:
            try:
                shortcut = KeyboardShortcut(**shortcut_data)
                self.register_shortcut(shortcut)
            except ValidationError as e:
                logger.error(f"Invalid default shortcut: {e}")

    def register_shortcut(self, shortcut: KeyboardShortcut) -> None:
        """Register a new keyboard shortcut.

        Args:
            shortcut: Shortcut to register.

        Raises:
            ValueError: If shortcut is invalid or conflicts exist.
        """
        try:
            # Validate shortcut
            if shortcut.id in self._shortcuts:
                raise ValueError(f"Shortcut ID already exists: {shortcut.id}")

            # Check for conflicts
            conflicts = self.check_conflicts(shortcut)
            if conflicts:
                logger.warning(f"Conflicts detected for shortcut {shortcut.id}: {conflicts}")
                # Allow registration but log conflicts

            # Normalize combination for current platform
            normalized = shortcut.get_normalized_combination(self._platform)
            shortcut.key_combination = normalized

            # Re-validate shortcut after normalization
            try:
                KeyboardShortcut.model_validate(shortcut.model_dump())
            except ValidationError as e:
                logger.error(f"Shortcut re-validation failed: {e}")
                raise ValueError("Invalid shortcut after normalization") from e

            self._shortcuts[shortcut.id] = shortcut
            logger.info(f"Registered shortcut: {shortcut.id}")

        except ValidationError as e:
            logger.error(f"Shortcut validation failed: {e}")
            raise ValueError("Invalid shortcut data") from e
        except Exception as e:
            logger.error(f"Shortcut registration failed: {e}")
            raise

    def unregister_shortcut(self, shortcut_id: str) -> None:
        """Remove a keyboard shortcut.

        Args:
            shortcut_id: ID of shortcut to remove.

        Raises:
            ValueError: If shortcut doesn't exist.
        """
        try:
            if shortcut_id not in self._shortcuts:
                raise ValueError(f"Shortcut not found: {shortcut_id}")

            del self._shortcuts[shortcut_id]
            logger.info(f"Unregistered shortcut: {shortcut_id}")

        except ValidationError as e:
            logger.error(f"Shortcut validation failed: {e}")
            raise ValueError("Invalid shortcut data") from e
        except Exception as e:
            logger.error(f"Shortcut unregistration failed: {e}")
            raise

    def process_event(self, event: ShortcutEvent) -> Optional[str]:
        """Process keyboard event and return action if matched.

        Args:
            event: Keyboard event to process.

        Returns:
            Action string if shortcut matched, None otherwise.

        Raises:
            ValueError: If event is invalid.
        """
        try:
            # Validate event
            try:
                ShortcutEvent.model_validate(event.model_dump())
            except ValidationError as e:
                logger.error(f"Event validation failed: {e}")
                raise ValueError("Invalid keyboard event") from e

            # Rate limiting check
            if not self._check_rate_limit(event.timestamp):
                logger.warning("Rate limit exceeded for keyboard events")
                return None

            event.platform = event.platform or self._platform

            # Get current context
            context = event.context

            # Find matching shortcut
            combination = event.to_combination()
            normalized_combination = self._platform_detector.normalize_combination(
                combination, event.platform)

            for shortcut in self._shortcuts.values():
                if not shortcut.enabled:
                    continue

                shortcut_combo = shortcut.get_normalized_combination(event.platform)
                if shortcut_combo == normalized_combination:
                    if self._context_manager.is_shortcut_available(shortcut, context):
                        logger.info(f"Shortcut triggered: {shortcut.id}")
                        return shortcut.action

            return None

        except ValidationError as e:
            logger.error(f"Event validation failed: {e}")
            raise ValueError("Invalid keyboard event") from e
        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            return None

    def get_available_shortcuts(self, context: ShortcutContext) -> List[KeyboardShortcut]:
        """Get shortcuts available in current context.

        Args:
            context: Current UI context.

        Returns:
            List of available KeyboardShortcut instances.
        """
        try:
            available = []
            for shortcut in self._shortcuts.values():
                if shortcut.enabled and self._context_manager.is_shortcut_available(shortcut, context):
                    available.append(shortcut)
            return available
        except ValidationError as e:
            logger.error(f"Shortcut validation failed: {e}")
            raise ValueError("Invalid shortcut data") from e
        except Exception as e:
            logger.error(f"Available shortcuts retrieval failed: {e}")
            return []

    def check_conflicts(self, shortcut: KeyboardShortcut) -> List[str]:
        """Check for conflicts with existing shortcuts.

        Args:
            shortcut: Shortcut to check.

        Returns:
            List of conflict descriptions.
        """
        conflicts = []
        try:
            combo = shortcut.get_normalized_combination(self._platform)

            # Check browser conflicts
            combo_str = '+'.join(sorted(combo))
            if combo_str in BROWSER_RESERVED.get(self._platform, set()):
                conflicts.append(f"Browser reserved: {combo_str}")

            # Check application conflicts
            for existing in self._shortcuts.values():
                existing_combo = existing.get_normalized_combination(self._platform)
                if existing_combo == combo and existing.id != shortcut.id:
                    conflicts.append(f"Application conflict with {existing.id}: {combo_str}")

            return conflicts

        except ValidationError as e:
            logger.error(f"Shortcut validation failed: {e}")
            raise ValueError("Invalid shortcut data") from e
        except Exception as e:
            logger.error(f"Conflict check failed: {e}")
            return [f"Error during conflict check: {str(e)}"]

    def _check_rate_limit(self, timestamp: float) -> bool:
        """Check if event is within rate limits.

        Args:
            timestamp: Event timestamp.

        Returns:
            True if within limits, False if rate limited.
        """
        current_time = time.time()

        # Clean old events
        self._event_history = [
            t for t in self._event_history
            if current_time - t <= RATE_LIMIT_WINDOW
        ]

        # Check rate
        if len(self._event_history) >= MAX_EVENTS_PER_SECOND:
            return False

        self._event_history.append(timestamp)
        return True