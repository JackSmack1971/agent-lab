# tests/src/utils/test_keyboard_handler.py

"""Unit tests for keyboard_handler.py module.

Tests cover all classes, methods, and error paths to achieve >=90% coverage.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import logging

from src.utils.keyboard_handler import (
    KeyboardShortcut,
    ShortcutContext,
    ShortcutEvent,
    PlatformDetector,
    ContextManager,
    KeyboardHandler,
    DEFAULT_SHORTCUTS,
    PLATFORM_MAPPINGS,
    BROWSER_RESERVED,
)


class TestKeyboardShortcut:
    """Test KeyboardShortcut class."""

    def test_valid_creation(self):
        """Test creating a valid KeyboardShortcut."""
        shortcut = KeyboardShortcut(
            id="test_shortcut",
            name="Test Shortcut",
            description="A test shortcut",
            key_combination=["ctrl", "s"],
            action="save",
        )
        assert shortcut.id == "test_shortcut"
        assert shortcut.name == "Test Shortcut"
        assert shortcut.description == "A test shortcut"
        assert shortcut.key_combination == ["ctrl", "s"]
        assert shortcut.action == "save"
        assert shortcut.context == []
        assert shortcut.platform_overrides == {}
        assert shortcut.enabled is True

    def test_invalid_creation_empty_id(self):
        """Test creation with empty id raises error."""
        with pytest.raises(Exception):
            KeyboardShortcut(
                id="",
                name="Test",
                description="Test",
                key_combination=["ctrl", "s"],
                action="save",
            )

    @patch('src.utils.keyboard_handler.logger')
    def test_creation_logging_on_error(self, mock_logger):
        """Test that validation errors are logged."""
        with pytest.raises(Exception):
            KeyboardShortcut(
                id="",
                name="Test",
                description="Test",
                key_combination=["ctrl", "s"],
                action="save",
            )
        mock_logger.error.assert_called_once()

    def test_get_normalized_combination_with_override(self):
        """Test get_normalized_combination with platform override."""
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
            platform_overrides={"mac": ["meta", "s"]},
        )
        assert shortcut.get_normalized_combination("mac") == ["meta", "s"]
        assert shortcut.get_normalized_combination("windows") == ["ctrl", "s"]

    def test_get_normalized_combination_without_override(self):
        """Test get_normalized_combination without override uses PlatformDetector."""
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )
        with patch.object(PlatformDetector, 'normalize_combination', return_value=["ctrl", "s"]):
            assert shortcut.get_normalized_combination("windows") == ["ctrl", "s"]


class TestShortcutContext:
    """Test ShortcutContext class."""

    def test_creation(self):
        """Test creating ShortcutContext."""
        context = ShortcutContext(
            active_tab="chat",
            focused_element="input",
            modal_open=True,
            input_active=True,
            streaming_active=False,
            available_actions=["save", "load"],
        )
        assert context.active_tab == "chat"
        assert context.focused_element == "input"
        assert context.modal_open is True
        assert context.input_active is True
        assert context.streaming_active is False
        assert context.available_actions == ["save", "load"]

    def test_default_creation(self):
        """Test default ShortcutContext."""
        context = ShortcutContext()
        assert context.active_tab == ""
        assert context.focused_element == ""
        assert context.modal_open is False
        assert context.input_active is False
        assert context.streaming_active is False
        assert context.available_actions is None


class TestShortcutEvent:
    """Test ShortcutEvent class."""

    def test_valid_creation(self):
        """Test creating a valid ShortcutEvent."""
        event = ShortcutEvent(
            key="s",
            ctrl_key=True,
            meta_key=False,
            alt_key=False,
            shift_key=False,
            platform="windows",
            context=ShortcutContext(),
        )
        assert event.key == "s"
        assert event.ctrl_key is True
        assert event.meta_key is False
        assert event.alt_key is False
        assert event.shift_key is False
        assert event.platform == "windows"
        assert isinstance(event.context, ShortcutContext)

    def test_invalid_creation_empty_key(self):
        """Test creation with empty key raises error."""
        with pytest.raises(Exception):
            ShortcutEvent(key="")

    @patch('src.utils.keyboard_handler.logger')
    def test_creation_logging_on_error(self, mock_logger):
        """Test that validation errors are logged."""
        with pytest.raises(Exception):
            ShortcutEvent(key="")
        mock_logger.error.assert_called_once()

    def test_to_combination_ctrl_only(self):
        """Test to_combination with ctrl key."""
        event = ShortcutEvent(key="s", ctrl_key=True)
        assert event.to_combination() == ["ctrl", "s"]

    def test_to_combination_all_modifiers(self):
        """Test to_combination with all modifiers."""
        event = ShortcutEvent(
            key="S",
            ctrl_key=True,
            meta_key=True,
            alt_key=True,
            shift_key=True,
        )
        # Sorted: ctrl, meta, alt, shift, then key lower
        assert event.to_combination() == ["ctrl", "meta", "alt", "shift", "s"]

    def test_to_combination_meta_key(self):
        """Test to_combination with meta key to cover line 112."""
        event = ShortcutEvent(key="t", meta_key=True)
        assert "meta" in event.to_combination()


class TestPlatformDetector:
    """Test PlatformDetector class."""

    @patch('src.utils.keyboard_handler._platform_mod.system')
    def test_get_platform_windows(self, mock_system):
        """Test platform detection for Windows."""
        mock_system.return_value = "Windows"
        assert PlatformDetector.get_platform() == "windows"

    @patch('src.utils.keyboard_handler._platform_mod.system')
    def test_get_platform_mac(self, mock_system):
        """Test platform detection for Mac."""
        mock_system.return_value = "Darwin"
        assert PlatformDetector.get_platform() == "mac"

    @patch('src.utils.keyboard_handler._platform_mod.system')
    def test_get_platform_linux(self, mock_system):
        """Test platform detection for Linux."""
        mock_system.return_value = "Linux"
        assert PlatformDetector.get_platform() == "linux"

    @patch('src.utils.keyboard_handler._platform_mod.system')
    @patch('src.utils.keyboard_handler.logger')
    def test_get_platform_unsupported(self, mock_logger, mock_system):
        """Test platform detection for unsupported platform."""
        mock_system.return_value = "Unknown"
        with pytest.raises(ValueError, match="Unsupported platform"):
            PlatformDetector.get_platform()
        mock_logger.error.assert_called_once()

    @patch('src.utils.keyboard_handler._platform_mod.system')
    @patch('src.utils.keyboard_handler.logger')
    def test_get_platform_exception(self, mock_logger, mock_system):
        """Test platform detection with exception."""
        mock_system.side_effect = Exception("System error")
        with pytest.raises(ValueError, match="Unable to detect platform"):
            PlatformDetector.get_platform()
        mock_logger.error.assert_called_once()

    def test_normalize_combination_empty(self):
        """Test normalize_combination with empty combination."""
        with pytest.raises(ValueError, match="Empty key combination"):
            PlatformDetector.normalize_combination([], "windows")

    def test_normalize_combination_normal(self):
        """Test normalize_combination normal case."""
        combo = PlatformDetector.normalize_combination(["CTRL", "S"], "windows")
        assert combo == ["ctrl", "s"]

    def test_normalize_combination_with_mapping(self):
        """Test normalize_combination with platform mapping."""
        combo = PlatformDetector.normalize_combination(["meta", "t"], "windows")
        assert combo == ["ctrl", "t"]

    def test_normalize_combination_non_string(self):
        """Test normalize_combination with non-string key to cover line 152."""
        combo = PlatformDetector.normalize_combination([123, "s"], "windows")  # type: ignore
        assert combo == ["123", "s"]


class TestContextManager:
    """Test ContextManager class."""

    def test_init(self):
        """Test ContextManager initialization."""
        manager = ContextManager()
        assert isinstance(manager._current_context, ShortcutContext)
        assert manager._cache_timeout == 0.1

    def test_get_current_context(self):
        """Test get_current_context."""
        manager = ContextManager()
        context = manager.get_current_context()
        assert isinstance(context, ShortcutContext)

    def test_update_context_valid(self):
        """Test update_context with valid attributes."""
        manager = ContextManager()
        manager.update_context(active_tab="chat", modal_open=True)
        context = manager.get_current_context()
        assert context.active_tab == "chat"
        assert context.modal_open is True

    @patch('src.utils.keyboard_handler.logger')
    def test_update_context_invalid_attribute(self, mock_logger):
        """Test update_context with invalid attribute."""
        manager = ContextManager()
        manager.update_context(invalid_attr="value")
        mock_logger.warning.assert_called_once_with("Unknown context attribute: invalid_attr")

    @patch('src.utils.keyboard_handler.logger')
    def test_update_context_setattr_exception(self, mock_logger):
        """Test update_context with setattr exception."""
        manager = ContextManager()
        # Mock setattr to raise
        with patch.object(manager._current_context, '__setattr__', side_effect=Exception("Set error")):
            manager.update_context(active_tab="chat")
        mock_logger.error.assert_called_once()

    def test_is_shortcut_available_modal_open(self):
        """Test is_shortcut_available when modal is open."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )
        context = ShortcutContext(modal_open=True)
        assert not manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_input_active_no_flag(self):
        """Test is_shortcut_available when input active and no input_safe."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )
        context = ShortcutContext(input_active=True)
        assert not manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_input_active_with_flag(self):
        """Test is_shortcut_available when input active with input_safe."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
            context=["input_safe"],
        )
        context = ShortcutContext(input_active=True)
        assert manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_streaming_active_no_flag(self):
        """Test is_shortcut_available when streaming active and no streaming_safe."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )
        context = ShortcutContext(streaming_active=True)
        assert not manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_streaming_active_with_flag(self):
        """Test is_shortcut_available when streaming active with streaming_safe."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
            context=["streaming_safe"],
        )
        context = ShortcutContext(streaming_active=True)
        assert manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_available_actions_none(self):
        """Test is_shortcut_available with available_actions None."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )
        context = ShortcutContext(available_actions=None)
        assert manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_available_actions_contains(self):
        """Test is_shortcut_available with available_actions containing action."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )
        context = ShortcutContext(available_actions=["save", "load"])
        assert manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_available_actions_not_contains(self):
        """Test is_shortcut_available with available_actions not containing action."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )
        context = ShortcutContext(available_actions=["load"])
        assert not manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_global_context(self):
        """Test is_shortcut_available with global context."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
            context=["global"],
        )
        context = ShortcutContext()
        assert manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_active_tab_match(self):
        """Test is_shortcut_available with active_tab matching context."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
            context=["chat"],
        )
        context = ShortcutContext(active_tab="chat")
        assert manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_empty_context(self):
        """Test is_shortcut_available with empty context."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
            context=[],
        )
        context = ShortcutContext()
        assert manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_flag_in_context(self):
        """Test is_shortcut_available with flag in context."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
            context=["input_safe"],
        )
        context = ShortcutContext()
        assert manager.is_shortcut_available(shortcut, context)

    def test_is_shortcut_available_no_match(self):
        """Test is_shortcut_available with no match."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
            context=["specific_tab"],
        )
        context = ShortcutContext(active_tab="other_tab")
        assert not manager.is_shortcut_available(shortcut, context)

    @patch('src.utils.keyboard_handler.logger')
    def test_is_shortcut_available_exception(self, mock_logger):
        """Test is_shortcut_available with exception."""
        manager = ContextManager()
        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )
        context = ShortcutContext()
        # Mock to raise exception
        with patch.object(shortcut, 'context', new_callable=Mock) as mock_context:
            mock_context.__contains__.side_effect = Exception("Contains error")
            assert not manager.is_shortcut_available(shortcut, context)
        mock_logger.error.assert_called_once()


class TestKeyboardHandler:
    """Test KeyboardHandler class."""

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    def test_init(self, mock_context_manager, mock_platform_detector):
        """Test KeyboardHandler initialization."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        mock_platform_detector.assert_called_once()
        mock_context_manager.assert_called_once()
        assert handler._platform_detector == mock_pd_instance
        assert handler._context_manager == mock_cm_instance
        assert handler._shortcuts == {}
        assert handler._event_history == []
        assert handler._platform == "windows"

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    def test_init_with_custom_detectors(self, mock_context_manager, mock_platform_detector):
        """Test KeyboardHandler with custom detectors."""
        mock_pd = Mock()
        mock_cm = Mock()
        handler = KeyboardHandler(platform_detector=mock_pd, context_manager=mock_cm)
        assert handler._platform_detector == mock_pd
        assert handler._context_manager == mock_cm

    @patch('src.utils.keyboard_handler.logger')
    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    def test_init_default_shortcuts_registration_error(self, mock_context_manager, mock_platform_detector, mock_logger):
        """Test init with default shortcuts registration error to cover lines 219-226."""
        # Make DEFAULT_SHORTCUTS have invalid data
        with patch('src.utils.keyboard_handler.DEFAULT_SHORTCUTS', [{"invalid": "data"}]):
            mock_pd_instance = Mock()
            mock_pd_instance.get_platform.return_value = "windows"
            mock_platform_detector.return_value = mock_pd_instance
            mock_cm_instance = Mock()
            mock_context_manager.return_value = mock_cm_instance

            handler = KeyboardHandler()
            mock_logger.error.assert_called_once_with("Invalid default shortcut: Invalid shortcut data")

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    def test_register_shortcut_success(self, mock_context_manager, mock_platform_detector):
        """Test register_shortcut success."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )

        with patch.object(handler, 'check_conflicts', return_value=[]), \
              patch.object(KeyboardShortcut, 'get_normalized_combination', return_value=["ctrl", "s"]), \
              patch('src.utils.keyboard_handler.logger') as mock_logger:
            handler.register_shortcut(shortcut)
            assert "test" in handler._shortcuts
            mock_logger.info.assert_called()

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    def test_register_shortcut_duplicate_id(self, mock_context_manager, mock_platform_detector):
        """Test register_shortcut with duplicate id."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut1 = KeyboardShortcut(
            id="test",
            name="Test1",
            description="Test1",
            key_combination=["ctrl", "s"],
            action="save",
        )
        shortcut2 = KeyboardShortcut(
            id="test",
            name="Test2",
            description="Test2",
            key_combination=["ctrl", "t"],
            action="new",
        )

        with patch.object(handler, 'check_conflicts', return_value=[]):
            handler.register_shortcut(shortcut1)
            with pytest.raises(ValueError, match="Shortcut ID already exists"):
                handler.register_shortcut(shortcut2)

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler.logger')
    def test_register_shortcut_conflicts(self, mock_logger, mock_context_manager, mock_platform_detector):
        """Test register_shortcut with conflicts."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )

        with patch.object(handler, 'check_conflicts', return_value=["conflict"]), \
              patch.object(KeyboardShortcut, 'get_normalized_combination', return_value=["ctrl", "s"]):
            handler.register_shortcut(shortcut)
            mock_logger.warning.assert_called_once()

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler.logger')
    def test_register_shortcut_revalidation_error(self, mock_logger, mock_context_manager, mock_platform_detector):
        """Test register_shortcut revalidation error."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )

        with patch.object(handler, 'check_conflicts', return_value=[]), \
              patch.object(KeyboardShortcut, 'get_normalized_combination', return_value=["ctrl", "s"]), \
              patch('src.utils.keyboard_handler.KeyboardShortcut.model_validate', side_effect=Exception("Validation error")):
            with pytest.raises(ValueError, match="Invalid shortcut data"):
                handler.register_shortcut(shortcut)
            mock_logger.error.assert_called()

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler.logger')
    def test_register_shortcut_other_exception(self, mock_logger, mock_context_manager, mock_platform_detector):
        """Test register_shortcut with other exception."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )

        with patch.object(handler, 'check_conflicts', side_effect=Exception("Check error")):
            with pytest.raises(Exception):
                handler.register_shortcut(shortcut)
            mock_logger.error.assert_called()

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    def test_unregister_shortcut_success(self, mock_context_manager, mock_platform_detector):
        """Test unregister_shortcut success."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )

        with patch.object(handler, 'check_conflicts', return_value=[]), \
              patch.object(KeyboardShortcut, 'get_normalized_combination', return_value=["ctrl", "s"]), \
              patch('src.utils.keyboard_handler.logger'):
            handler.register_shortcut(shortcut)
            handler.unregister_shortcut("test")
            assert "test" not in handler._shortcuts

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    def test_unregister_shortcut_not_found(self, mock_context_manager, mock_platform_detector):
        """Test unregister_shortcut not found."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        with pytest.raises(ValueError, match="Shortcut not found"):
            handler.unregister_shortcut("nonexistent")

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler.logger')
    def test_unregister_shortcut_exception(self, mock_logger, mock_context_manager, mock_platform_detector):
        """Test unregister_shortcut with exception."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        with patch.object(handler, '_shortcuts', {'test': None}), \
             patch('src.utils.keyboard_handler.logger'):
            # Mock del to raise
            with patch('builtins.del') as mock_del:
                mock_del.side_effect = Exception("Del error")
                with pytest.raises(Exception):
                    handler.unregister_shortcut("test")
                mock_logger.error.assert_called()

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler._monotonic')
    def test_process_event_success(self, mock_monotonic, mock_context_manager, mock_platform_detector):
        """Test process_event success."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_pd_instance.normalize_combination.return_value = ["ctrl", "s"]
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_cm_instance.is_shortcut_available.return_value = True
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )

        with patch.object(handler, 'check_conflicts', return_value=[]), \
              patch.object(KeyboardShortcut, 'get_normalized_combination', return_value=["ctrl", "s"]), \
              patch('src.utils.keyboard_handler.logger'):
            handler.register_shortcut(shortcut)

        event = ShortcutEvent(key="s", ctrl_key=True)
        mock_monotonic.return_value = 1.0

        with patch('src.utils.keyboard_handler.logger') as mock_logger:
            result = handler.process_event(event)
            assert result == "save"
            mock_logger.info.assert_called()

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler.logger')
    def test_process_event_validation_error(self, mock_logger, mock_context_manager, mock_platform_detector):
        """Test process_event with validation error."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        event = ShortcutEvent(key="s", ctrl_key=True)

        # Mock validation to fail
        with patch('src.utils.keyboard_handler.ShortcutEvent.model_validate', side_effect=Exception("Validation error")):
            with pytest.raises(ValueError, match="Invalid keyboard event"):
                handler.process_event(event)
            mock_logger.error.assert_called()

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler.logger')
    def test_process_event_rate_limit_exceeded(self, mock_logger, mock_context_manager, mock_platform_detector):
        """Test process_event with rate limit exceeded."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        event = ShortcutEvent(key="s", ctrl_key=True)

        # Mock rate limit to return False
        with patch.object(handler, '_check_rate_limit', return_value=False):
            result = handler.process_event(event)
            assert result is None
            mock_logger.warning.assert_called_with("Rate limit exceeded for keyboard events")

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler.logger')
    def test_process_event_no_match(self, mock_logger, mock_context_manager, mock_platform_detector):
        """Test process_event with no matching shortcut."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_pd_instance.normalize_combination.return_value = ["ctrl", "t"]
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        event = ShortcutEvent(key="t", ctrl_key=True)

        result = handler.process_event(event)
        assert result is None
        mock_logger.warning.assert_called()

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler.logger')
    def test_process_event_exception(self, mock_logger, mock_context_manager, mock_platform_detector):
        """Test process_event with exception."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        event = ShortcutEvent(key="s", ctrl_key=True)

        # Mock normalize_combination to raise
        mock_pd_instance.normalize_combination.side_effect = Exception("Normalize error")

        result = handler.process_event(event)
        assert result is None
        mock_logger.error.assert_called()

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    def test_get_available_shortcuts_success(self, mock_context_manager, mock_platform_detector):
        """Test get_available_shortcuts success."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_cm_instance.is_shortcut_available.return_value = True
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )

        with patch.object(handler, 'check_conflicts', return_value=[]), \
              patch.object(KeyboardShortcut, 'get_normalized_combination', return_value=["ctrl", "s"]), \
              patch('src.utils.keyboard_handler.logger'):
            handler.register_shortcut(shortcut)

        context = ShortcutContext()
        result = handler.get_available_shortcuts(context)
        assert len(result) == 1
        assert result[0].id == "test"

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler.logger')
    def test_get_available_shortcuts_exception(self, mock_logger, mock_context_manager, mock_platform_detector):
        """Test get_available_shortcuts with exception to cover lines 327-329."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_cm_instance.is_shortcut_available.side_effect = Exception("Available error")
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )

        with patch.object(handler, 'check_conflicts', return_value=[]), \
             patch.object(shortcut, 'get_normalized_combination', return_value=["ctrl", "s"]):
            handler.register_shortcut(shortcut)

        context = ShortcutContext()
        result = handler.get_available_shortcuts(context)
        assert result == []
        mock_logger.error.assert_called()

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    def test_check_conflicts_browser_reserved(self, mock_context_manager, mock_platform_detector):
        """Test check_conflicts with browser reserved."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "t"],
            action="new_tab",
        )

        conflicts = handler.check_conflicts(shortcut)
        assert "Browser reserved" in conflicts[0]

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    def test_check_conflicts_application_conflict(self, mock_context_manager, mock_platform_detector):
        """Test check_conflicts with application conflict to cover line 343."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut1 = KeyboardShortcut(
            id="test1",
            name="Test1",
            description="Test1",
            key_combination=["ctrl", "s"],
            action="save",
        )
        shortcut2 = KeyboardShortcut(
            id="test2",
            name="Test2",
            description="Test2",
            key_combination=["ctrl", "s"],
            action="save",
        )

        with patch.object(handler, 'check_conflicts', return_value=[]), \
              patch.object(KeyboardShortcut, 'get_normalized_combination', return_value=["ctrl", "s"]), \
              patch('src.utils.keyboard_handler.logger'):
            handler.register_shortcut(shortcut1)

        conflicts = handler.check_conflicts(shortcut2)
        assert "Application conflict" in conflicts[0]

    @patch('src.utils.keyboard_handler.PlatformDetector')
    @patch('src.utils.keyboard_handler.ContextManager')
    @patch('src.utils.keyboard_handler.logger')
    def test_check_conflicts_exception(self, mock_logger, mock_context_manager, mock_platform_detector):
        """Test check_conflicts with exception to cover lines 347-349."""
        mock_pd_instance = Mock()
        mock_pd_instance.get_platform.return_value = "windows"
        mock_platform_detector.return_value = mock_pd_instance
        mock_cm_instance = Mock()
        mock_context_manager.return_value = mock_cm_instance

        handler = KeyboardHandler()

        shortcut = KeyboardShortcut(
            id="test",
            name="Test",
            description="Test",
            key_combination=["ctrl", "s"],
            action="save",
        )

        # Mock get_normalized_combination to raise
        with patch.object(KeyboardShortcut, 'get_normalized_combination', side_effect=Exception("Normalize error")):
            conflicts = handler.check_conflicts(shortcut)
            assert "Error during conflict check" in conflicts[0]
            mock_logger.error.assert_called()

    @patch('src.utils.keyboard_handler._monotonic')
    def test_check_rate_limit_under_limit(self, mock_monotonic):
        """Test _check_rate_limit under limit."""
        mock_monotonic.return_value = 1.0
        handler = KeyboardHandler()
        assert handler._check_rate_limit(0.5, 1.0) is True
        assert len(handler._event_history) == 1

    @patch('src.utils.keyboard_handler._monotonic')
    def test_check_rate_limit_over_limit(self, mock_monotonic):
        """Test _check_rate_limit over limit."""
        mock_monotonic.return_value = 1.0
        handler = KeyboardHandler()
        # Add max events
        handler._event_history = [0.1] * 10
        assert handler._check_rate_limit(0.5, 1.0) is False

    @patch('src.utils.keyboard_handler._monotonic')
    def test_check_rate_limit_eviction(self, mock_monotonic):
        """Test _check_rate_limit with old event eviction."""
        mock_monotonic.return_value = 2.0  # After 1 second
        handler = KeyboardHandler()
        handler._event_history = [0.1, 0.2]  # Old events
        assert handler._check_rate_limit(1.5, 2.0) is True
        # Old events should be evicted
        assert len(handler._event_history) == 1