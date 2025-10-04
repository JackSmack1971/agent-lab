"""Settings component for Agent Lab.

This module provides the settings tab with configuration options
including keyboard shortcuts toggle and other application preferences.
"""

from typing import Optional, Dict, Any
import gradio as gr
import logging

logger = logging.getLogger(__name__)


def create_settings_tab() -> gr.Blocks:
    """Create the settings tab with configuration options.

    Returns:
        Gradio Blocks component for the settings tab
    """
    with gr.Blocks() as settings_tab:
        gr.Markdown("## ⚙️ Settings")

        # Keyboard Shortcuts Section
        with gr.Group():
            gr.Markdown("### ⌨️ Keyboard Shortcuts")
            shortcuts_enabled = gr.Checkbox(
                label="Enable Keyboard Shortcuts",
                value=True,
                info="Toggle global keyboard shortcuts on/off"
            )

            gr.Markdown("*Keyboard shortcuts help you navigate and perform actions quickly.*")

        # Other Settings Sections (placeholders for future expansion)
        with gr.Group():
            gr.Markdown("### 🎨 Appearance")
            gr.Markdown("*Theme and display preferences will be added here.*")

        with gr.Group():
            gr.Markdown("### 🔧 Advanced")
            gr.Markdown("*Advanced configuration options will be added here.*")

        # Settings state management
        settings_state = gr.State(value={"shortcuts_enabled": True})

        # Event handlers
        shortcuts_enabled.change(
            fn=update_shortcuts_setting,
            inputs=[shortcuts_enabled, settings_state],
            outputs=[settings_state]
        )

    return settings_tab


def update_shortcuts_setting(enabled: bool, current_settings: Dict[str, Any]) -> Dict[str, Any]:
    """Update the keyboard shortcuts setting.

    Args:
        enabled: New enabled state
        current_settings: Current settings dictionary

    Returns:
        Updated settings dictionary
    """
    try:
        updated_settings = current_settings.copy()
        updated_settings["shortcuts_enabled"] = enabled

        # Persist settings (placeholder for future implementation)
        # save_settings_to_file(updated_settings)

        logger.info(f"Keyboard shortcuts {'enabled' if enabled else 'disabled'}")

        return updated_settings

    except Exception as e:
        logger.error(f"Failed to update shortcuts setting: {e}")
        return current_settings


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