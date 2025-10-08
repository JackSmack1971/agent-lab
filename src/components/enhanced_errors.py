"""Enhanced error messages and contextual help component for Agent Lab.

This module provides comprehensive validation with helpful error messages,
contextual guidance, and expandable help content for form fields.
"""

from typing import Dict, Any, Optional
import gradio as gr


class EnhancedErrorManager:
    """Manages enhanced error messages with contextual help."""

    def __init__(self):
        self.field_configs = self._get_field_configs()

    def _get_field_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get validation configurations for all form fields."""
        return {
            "agent_name": {
                "required": True,
                "min_length": 1,
                "max_length": 100,
                "pattern": r"^[a-zA-Z0-9_-]+$",
                "help_title": "Agent Name Requirements",
                "help_description": "Choose a descriptive name for your AI agent",
                "rules": [
                    "2-100 characters long",
                    "Use letters, numbers, hyphens, and underscores only",
                    "Avoid special characters"
                ],
                "examples": ["ResearchAssistant", "CodeReviewer", "DataAnalyst-v2"]
            },
            "system_prompt": {
                "required": True,
                "min_length": 1,
                "max_length": 10000,
                "help_title": "System Prompt Guidelines",
                "help_description": "Define your AI agent's role and behavior",
                "rules": [
                    "1-10,000 characters long",
                    "Be specific about the agent's role",
                    "Include behavioral guidelines",
                    "Avoid contradictory instructions"
                ],
                "examples": [
                    "You are a helpful coding assistant.",
                    "You are a research analyst specializing in data science."
                ]
            },
            "temperature": {
                "required": True,
                "min_value": 0.0,
                "max_value": 2.0,
                "help_title": "Temperature Parameter",
                "help_description": "Controls creativity vs consistency in responses",
                "guidance": {
                    "low": "0.1-0.3: More focused and consistent",
                    "medium": "0.4-0.7: Balanced creativity and consistency",
                    "high": "0.8-2.0: More creative and varied"
                },
                "examples": ["0.1", "0.7", "1.0"]
            },
            "top_p": {
                "required": True,
                "min_value": 0.0,
                "max_value": 1.0,
                "help_title": "Top-p Parameter",
                "help_description": "Controls response diversity by limiting token selection",
                "guidance": {
                    "low": "0.1-0.5: More focused responses",
                    "medium": "0.6-0.8: Balanced diversity",
                    "high": "0.9-1.0: Maximum diversity"
                },
                "examples": ["0.1", "0.7", "1.0"]
            }
        }

    def validate_field_with_enhanced_errors(self, field_name: str, value: Any) -> Dict[str, Any]:
        """Validate a form field and return enhanced error information.

        Args:
            field_name: Name of the field being validated
            value: The current field value

        Returns:
            Dict with validation results and help content
        """
        config = self.field_configs.get(field_name, {})

        try:
            # Basic validation based on field type
            if field_name == "agent_name":
                return self._validate_agent_name(value, config)
            elif field_name == "system_prompt":
                return self._validate_system_prompt(value, config)
            elif field_name == "temperature":
                return self._validate_temperature(value, config)
            elif field_name == "top_p":
                return self._validate_top_p(value, config)
            else:
                return {
                    "is_valid": True,
                    "error_message": "",
                    "help_content": None,
                    "suggestions": [],
                    "examples": []
                }

        except Exception as e:
            return {
                "is_valid": False,
                "error_message": f"Validation failed due to an unexpected error: {str(e)}",
                "help_content": None,
                "suggestions": ["Please try again or refresh the page"],
                "examples": []
            }

    def _validate_agent_name(self, value: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate agent name field."""
        if not value or not value.strip():
            return {
                "is_valid": False,
                "error_message": "Agent Name: This field is required",
                "help_content": {
                    "title": config["help_title"],
                    "description": config["help_description"],
                    "rules": config["rules"],
                    "examples": config["examples"]
                },
                "suggestions": ["Try: 'Research Assistant' or 'Code Reviewer'"],
                "examples": config["examples"]
            }

        value = value.strip()
        if len(value) < 2 or len(value) > config["max_length"]:
            return {
                "is_valid": False,
                "error_message": f"Agent Name: Must be 2-{config['max_length']} characters long",
                "help_content": {
                    "title": config["help_title"],
                    "description": config["help_description"],
                    "rules": config["rules"],
                    "examples": config["examples"]
                },
                "suggestions": [f"Current length: {len(value)} characters"],
                "examples": config["examples"]
            }

        import re
        if not re.match(config["pattern"], value):
            return {
                "is_valid": False,
                "error_message": "Agent Name: Invalid characters detected",
                "help_content": {
                    "title": config["help_title"],
                    "description": config["help_description"],
                    "rules": config["rules"],
                    "examples": config["examples"]
                },
                "suggestions": ["Use only letters, numbers, hyphens, and underscores"],
                "examples": config["examples"]
            }

        return {
            "is_valid": True,
            "error_message": "",
            "help_content": None,
            "suggestions": [],
            "examples": []
        }

    def _validate_system_prompt(self, value: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate system prompt field."""
        if not value or not value.strip():
            return {
                "is_valid": False,
                "error_message": "System Prompt: This field is required",
                "help_content": {
                    "title": config["help_title"],
                    "description": config["help_description"],
                    "rules": config["rules"],
                    "examples": config["examples"]
                },
                "suggestions": ["Define your agent's role and behavior"],
                "examples": config["examples"]
            }

        value = value.strip()
        if len(value) > config["max_length"]:
            return {
                "is_valid": False,
                "error_message": f"System Prompt: Maximum {config['max_length']} characters allowed",
                "help_content": {
                    "title": config["help_title"],
                    "description": config["help_description"],
                    "rules": config["rules"],
                    "examples": config["examples"]
                },
                "suggestions": [f"Current length: {len(value)} characters. Try shortening your prompt."],
                "examples": config["examples"]
            }

        return {
            "is_valid": True,
            "error_message": "",
            "help_content": None,
            "suggestions": [],
            "examples": []
        }

    def _validate_temperature(self, value: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate temperature field."""
        try:
            temp_val = float(value)
        except (ValueError, TypeError):
            return {
                "is_valid": False,
                "error_message": "Temperature: Must be a number between 0.0 and 2.0",
                "help_content": {
                    "title": config["help_title"],
                    "description": config["help_description"],
                    "guidance": config["guidance"],
                    "examples": config["examples"]
                },
                "suggestions": ["Enter a number like 0.7 or 1.0"],
                "examples": config["examples"]
            }

        if temp_val < config["min_value"] or temp_val > config["max_value"]:
            return {
                "is_valid": False,
                "error_message": f"Temperature: Must be between {config['min_value']} and {config['max_value']}",
                "help_content": {
                    "title": config["help_title"],
                    "description": config["help_description"],
                    "guidance": config["guidance"],
                    "examples": config["examples"]
                },
                "suggestions": ["Use 0.1-0.3 for focused tasks, 0.7-1.0 for creative tasks"],
                "examples": config["examples"]
            }

        return {
            "is_valid": True,
            "error_message": "",
            "help_content": None,
            "suggestions": [],
            "examples": []
        }

    def _validate_top_p(self, value: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate top_p field."""
        try:
            top_p_val = float(value)
        except (ValueError, TypeError):
            return {
                "is_valid": False,
                "error_message": "Top-p: Must be a number between 0.0 and 1.0",
                "help_content": {
                    "title": config["help_title"],
                    "description": config["help_description"],
                    "guidance": config["guidance"],
                    "examples": config["examples"]
                },
                "suggestions": ["Enter a number like 0.9 or 0.1"],
                "examples": config["examples"]
            }

        if top_p_val < config["min_value"] or top_p_val > config["max_value"]:
            return {
                "is_valid": False,
                "error_message": f"Top-p: Must be between {config['min_value']} and {config['max_value']}",
                "help_content": {
                    "title": config["help_title"],
                    "description": config["help_description"],
                    "guidance": config["guidance"],
                    "examples": config["examples"]
                },
                "suggestions": ["Use 0.1-0.5 for focused responses, 0.9-1.0 for diverse responses"],
                "examples": config["examples"]
            }

        return {
            "is_valid": True,
            "error_message": "",
            "help_content": None,
            "suggestions": [],
            "examples": []
        }


def render_error_message(error_data: Dict[str, Any], show_help_button: bool = True) -> str:
    """Render an enhanced error message with contextual help.

    Args:
        error_data: Result from validate_field_with_enhanced_errors
        show_help_button: Whether to show expandable help content

    Returns:
        HTML string for the error display
    """
    if error_data.get("is_valid", True):
        return ""

    html = """
    <div class="enhanced-error" role="alert" aria-live="assertive">
        <div class="error-header">
            <span class="error-icon">❌</span>
            <span class="error-text">{error_message}</span>
        </div>
    """.format(error_message=error_data["error_message"])

    if error_data.get("suggestions"):
        html += '<div class="error-suggestions">'
        for suggestion in error_data["suggestions"]:
            html += '<div class="suggestion">💡 {suggestion}</div>'.format(suggestion=suggestion)
        html += '</div>'

    if show_help_button and error_data.get("help_content"):
        help_content = error_data["help_content"]
        html += """
        <button class="learn-more-btn" onclick="toggleHelp('{field_name}')">
            Learn More ▼
        </button>
        <div id="help-{field_name}" class="help-content" style="display: none;">
            <h4>{title}</h4>
            <p>{description}</p>
        """.format(
            field_name="field",  # This will be replaced with actual field name
            title=help_content["title"],
            description=help_content["description"]
        )

        # Add rules if present
        if "rules" in help_content:
            html += "<div class='help-rules'><ul>"
            for rule in help_content["rules"]:
                html += f"<li>{rule}</li>"
            html += "</ul></div>"

        # Add guidance if present
        if "guidance" in help_content:
            html += "<div class='help-guidance'>"
            for range_key, description in help_content["guidance"].items():
                html += f"<div class='guidance-item'>{description}</div>"
            html += "</div>"

        # Add examples if present
        if "examples" in help_content:
            html += "<div class='help-examples'><strong>Examples:</strong><ul>"
            for example in help_content["examples"]:
                html += f"<li><code>{example}</code></li>"
            html += "</ul></div>"

        html += """
        </div>
        """

    html += "</div>"
    return html


def create_enhanced_error_display(field_name: str) -> gr.HTML:
    """Create an HTML component for displaying enhanced error messages.

    Args:
        field_name: Name of the field this error display is for

    Returns:
        Gradio HTML component for error display
    """
    return gr.HTML(
        value="",
        elem_id=f"error-{field_name}",
        visible=False,
        elem_classes=["enhanced-error-display"]
    )


# Global error manager instance
error_manager = EnhancedErrorManager()


# CSS for enhanced error messages
ENHANCED_ERROR_CSS = """
.enhanced-error {
    background: #fff5f5;
    border: 1px solid #feb2b2;
    border-radius: 6px;
    padding: 12px;
    margin-top: 8px;
    font-size: 14px;
}

.error-header {
    display: flex;
    align-items: flex-start;
    gap: 8px;
}

.error-icon {
    font-size: 16px;
    flex-shrink: 0;
}

.error-text {
    color: #c53030;
    font-weight: 500;
    line-height: 1.4;
}

.error-suggestions {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #fed7d7;
}

.suggestion {
    color: #744210;
    font-size: 13px;
    margin-bottom: 4px;
    padding: 4px 8px;
    background: #fef5e7;
    border-radius: 4px;
    border-left: 3px solid #f6ad55;
}

.learn-more-btn {
    background: #3182ce;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 12px;
    cursor: pointer;
    margin-top: 8px;
    transition: background-color 0.2s;
}

.learn-more-btn:hover {
    background: #2c5282;
}

.help-content {
    margin-top: 12px;
    padding: 12px;
    background: #f7fafc;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
}

.help-content h4 {
    margin: 0 0 8px 0;
    color: #2d3748;
    font-size: 16px;
}

.help-content p {
    margin: 0 0 12px 0;
    color: #4a5568;
    line-height: 1.5;
}

.help-rules ul {
    margin: 8px 0;
    padding-left: 20px;
}

.help-rules li {
    margin-bottom: 4px;
    color: #4a5568;
}

.help-guidance {
    margin: 12px 0;
}

.guidance-item {
    padding: 8px;
    margin-bottom: 6px;
    background: white;
    border-radius: 4px;
    border-left: 3px solid #3182ce;
    font-size: 13px;
}

.help-examples {
    margin-top: 12px;
}

.help-examples ul {
    margin: 8px 0;
    padding-left: 20px;
}

.help-examples code {
    background: #f7fafc;
    padding: 2px 4px;
    border-radius: 3px;
    font-family: monospace;
    font-size: 12px;
}

.enhanced-error-display {
    min-height: 20px;
}
"""