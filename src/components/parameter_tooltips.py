"""Parameter guidance tooltips component for Agent Lab.

This module provides contextual tooltips and guidance for AI model parameters,
helping users understand temperature, top-p, and other configuration options.
"""

from typing import Dict, Any, Optional, List
import gradio as gr


class TooltipManager:
    """Manages parameter guidance tooltips."""

    def __init__(self):
        self.tooltips: Dict[str, Dict[str, Any]] = {}
        self.active_tooltips: set = set()
        self._initialize_tooltips()

    def _initialize_tooltips(self):
        """Initialize tooltip data for all parameters."""
        self.tooltips = {
            "temperature": {
                "title": "Temperature",
                "description": "Controls creativity vs consistency in responses",
                "guidance": {
                    "low": "0.1-0.3: More focused and consistent responses",
                    "medium": "0.4-0.7: Balanced creativity and consistency",
                    "high": "0.8-2.0: More creative and varied responses"
                },
                "use_cases": [
                    "Code generation: Use 0.1-0.3",
                    "Creative writing: Use 0.7-1.0",
                    "Factual Q&A: Use 0.1-0.3"
                ],
                "examples": ["0.1", "0.7", "1.0"]
            },
            "top_p": {
                "title": "Top-p (Nucleus Sampling)",
                "description": "Controls response diversity by limiting token selection to top probability mass",
                "guidance": {
                    "low": "0.1-0.5: More focused responses, lower diversity",
                    "medium": "0.6-0.8: Balanced diversity and focus",
                    "high": "0.9-1.0: Maximum diversity, more varied responses"
                },
                "use_cases": [
                    "Technical writing: Use 0.1-0.5",
                    "Conversational: Use 0.7-0.9",
                    "Brainstorming: Use 0.9-1.0"
                ],
                "examples": ["0.1", "0.7", "1.0"]
            },
            "max_tokens": {
                "title": "Max Tokens",
                "description": "Maximum length of the generated response",
                "guidance": {
                    "short": "50-200: Brief responses, quick answers",
                    "medium": "200-500: Balanced length, detailed answers",
                    "long": "500-1000: Comprehensive responses, in-depth analysis"
                },
                "use_cases": [
                    "Quick answers: Use 50-200 tokens",
                    "Explanations: Use 200-500 tokens",
                    "Detailed analysis: Use 500-1000 tokens"
                ],
                "examples": ["100", "500", "1000"]
            },
            "system_prompt": {
                "title": "System Prompt",
                "description": "Instructions that define the AI's role and behavior",
                "guidance": {
                    "minimal": "Keep it concise and focused on the core role",
                    "detailed": "Include specific behavioral guidelines and constraints",
                    "contextual": "Provide relevant background information and context"
                },
                "use_cases": [
                    "General assistant: Simple role definition",
                    "Specialized tasks: Include domain-specific instructions",
                    "Safety-critical: Add explicit safety and ethical guidelines"
                ],
                "examples": [
                    "You are a helpful assistant.",
                    "You are a Python programming expert. Provide clear, well-commented code examples.",
                    "You are a medical information assistant. Always recommend consulting healthcare professionals for medical advice."
                ]
            }
        }

    def register_tooltip(self, parameter_name: str, tooltip_data: Dict[str, Any]):
        """Register a tooltip for a parameter.

        Args:
            parameter_name: Name of the parameter
            tooltip_data: Tooltip configuration data
        """
        self.tooltips[parameter_name] = tooltip_data

    def get_tooltip_html(self, parameter_name: str, current_value: Any = None) -> str:
        """Generate HTML for a parameter tooltip.

        Args:
            parameter_name: Name of the parameter
            current_value: Current parameter value for highlighting

        Returns:
            HTML string for the tooltip
        """
        if parameter_name not in self.tooltips:
            return ""

        tooltip = self.tooltips[parameter_name]

        html = f"""
        <div class="parameter-tooltip" role="tooltip">
            <h4>{tooltip['title']}</h4>
            <p>{tooltip['description']}</p>
        """

        # Add guidance section if present
        if "guidance" in tooltip:
            html += '<div class="guidance-section">'
            for range_key, description in tooltip["guidance"].items():
                highlight_class = self._get_highlight_class_for_value(current_value, range_key, parameter_name)
                html += f'<div class="guidance-item {highlight_class}">{description}</div>'
            html += "</div>"

        # Add use cases if present
        if "use_cases" in tooltip:
            html += '<div class="use-cases-section"><h5>Use Cases:</h5><ul>'
            for use_case in tooltip["use_cases"]:
                html += f"<li>{use_case}</li>"
            html += "</ul></div>"

        # Add examples if present
        if "examples" in tooltip:
            html += '<div class="examples-section"><h5>Examples:</h5><ul>'
            for example in tooltip["examples"]:
                html += f"<li><code>{example}</code></li>"
            html += "</ul></div>"

        html += "</div>"
        return html

    def get_model_comparison_tooltip(self, model_options: List[Dict[str, Any]]) -> str:
        """Generate tooltip for model selection comparison.

        Args:
            model_options: List of model option dictionaries

        Returns:
            HTML string for model comparison tooltip
        """
        html = """
        <div class="model-comparison-tooltip" role="tooltip">
            <h4>🤖 Model Comparison</h4>
            <div class="model-grid">
        """

        for model in model_options:
            html += f"""
            <div class="model-option">
                <h5>{model.get('name', 'Unknown')}</h5>
                <div class="model-strengths">💡 {model.get('strengths', 'General purpose')}</div>
                <div class="model-cost">${model.get('cost', '0.00')}/1K tokens</div>
                <div class="model-speed">⚡ {model.get('speed', 'Medium')}</div>
            </div>
            """

        html += """
            </div>
        </div>
        """

        return html

    def _get_highlight_class_for_value(self, current_value: Any, range_key: str, parameter_name: str) -> str:
        """Determine highlight class based on current value and range.

        Args:
            current_value: Current parameter value
            range_key: Range identifier (low, medium, high, etc.)
            parameter_name: Name of the parameter

        Returns:
            CSS class for highlighting
        """
        if current_value is None:
            return ""

        try:
            if parameter_name == "temperature":
                return self._get_temperature_highlight(current_value, range_key)
            elif parameter_name == "top_p":
                return self._get_top_p_highlight(current_value, range_key)
            elif parameter_name == "max_tokens":
                return self._get_max_tokens_highlight(current_value, range_key)
        except (ValueError, TypeError):
            pass

        return ""

    def _get_temperature_highlight(self, value: float, range_key: str) -> str:
        """Get highlight class for temperature value."""
        if range_key == "low" and 0.0 <= value <= 0.3:
            return "current-range"
        elif range_key == "medium" and 0.4 <= value <= 0.7:
            return "current-range"
        elif range_key == "high" and 0.8 <= value <= 2.0:
            return "current-range"
        return ""

    def _get_top_p_highlight(self, value: float, range_key: str) -> str:
        """Get highlight class for top_p value."""
        if range_key == "low" and 0.0 <= value <= 0.5:
            return "current-range"
        elif range_key == "medium" and 0.6 <= value <= 0.8:
            return "current-range"
        elif range_key == "high" and 0.9 <= value <= 1.0:
            return "current-range"
        return ""

    def _get_max_tokens_highlight(self, value: int, range_key: str) -> str:
        """Get highlight class for max_tokens value."""
        if range_key == "short" and 1 <= value <= 200:
            return "current-range"
        elif range_key == "medium" and 201 <= value <= 500:
            return "current-range"
        elif range_key == "long" and 501 <= value <= 1000:
            return "current-range"
        return ""


def create_parameter_tooltip_component(parameter_name: str) -> gr.HTML:
    """Create a tooltip component for a parameter.

    Args:
        parameter_name: Name of the parameter

    Returns:
        Gradio HTML component for the tooltip
    """
    tooltip_manager = TooltipManager()
    return gr.HTML(
        value="",
        elem_id=f"tooltip-{parameter_name}",
        visible=False,
        elem_classes=["parameter-tooltip-component"]
    )


def create_model_comparison_component() -> gr.HTML:
    """Create a model comparison tooltip component.

    Returns:
        Gradio HTML component for model comparison
    """
    return gr.HTML(
        value="",
        elem_id="model-comparison-tooltip",
        visible=False,
        elem_classes=["model-comparison-component"]
    )


# Global tooltip manager instance
tooltip_manager = TooltipManager()


# Sample model data for comparison tooltip
SAMPLE_MODEL_DATA = [
    {
        "name": "GPT-4 Turbo",
        "strengths": "Best for complex reasoning",
        "cost": "0.03",
        "speed": "Medium"
    },
    {
        "name": "Claude 3.5 Sonnet",
        "strengths": "Excellent for analysis",
        "cost": "0.015",
        "speed": "Fast"
    },
    {
        "name": "Gemini 1.5 Pro",
        "strengths": "Fast, good for casual use",
        "cost": "0.00125",
        "speed": "Very Fast"
    }
]


# CSS for parameter tooltips
PARAMETER_TOOLTIPS_CSS = """
.parameter-tooltip {
    position: absolute;
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    padding: 16px;
    max-width: 350px;
    z-index: 1000;
    font-size: 14px;
    line-height: 1.5;
}

.parameter-tooltip h4 {
    margin: 0 0 8px 0;
    color: #495057;
    font-size: 16px;
    font-weight: 600;
}

.parameter-tooltip p {
    margin: 0 0 12px 0;
    color: #6c757d;
}

.guidance-section {
    margin: 12px 0;
}

.guidance-item {
    padding: 8px 12px;
    margin-bottom: 6px;
    border-radius: 4px;
    background: #f8f9fa;
    border-left: 3px solid #dee2e6;
    font-size: 13px;
    transition: all 0.2s ease;
}

.guidance-item.current-range {
    background: #d1ecf1;
    border-left-color: #17a2b8;
    font-weight: 500;
}

.use-cases-section h5,
.examples-section h5 {
    margin: 12px 0 6px 0;
    color: #495057;
    font-size: 14px;
    font-weight: 600;
}

.use-cases-section ul,
.examples-section ul {
    margin: 6px 0;
    padding-left: 20px;
}

.use-cases-section li,
.examples-section li {
    margin-bottom: 4px;
    color: #6c757d;
}

.examples-section code {
    background: #f1f3f4;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 12px;
    color: #d73a49;
}

.model-comparison-tooltip {
    position: absolute;
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    padding: 16px;
    max-width: 400px;
    z-index: 1000;
}

.model-comparison-tooltip h4 {
    margin: 0 0 12px 0;
    color: #495057;
    font-size: 16px;
    text-align: center;
}

.model-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
}

.model-option {
    padding: 12px;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    background: #f8f9fa;
}

.model-option h5 {
    margin: 0 0 8px 0;
    color: #495057;
    font-size: 14px;
    font-weight: 600;
}

.model-strengths,
.model-cost,
.model-speed {
    font-size: 12px;
    color: #6c757d;
    margin-bottom: 4px;
}

.model-cost {
    color: #28a745;
    font-weight: 500;
}

.model-speed {
    color: #007bff;
}

/* Tooltip positioning utilities */
.tooltip-position-top {
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    margin-bottom: 8px;
}

.tooltip-position-bottom {
    top: 100%;
    left: 50%;
    transform: translateX(-50%);
    margin-top: 8px;
}

.tooltip-position-left {
    right: 100%;
    top: 50%;
    transform: translateY(-50%);
    margin-right: 8px;
}

.tooltip-position-right {
    left: 100%;
    top: 50%;
    transform: translateY(-50%);
    margin-left: 8px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .parameter-tooltip,
    .model-comparison-tooltip {
        max-width: 280px;
        font-size: 13px;
    }

    .model-grid {
        gap: 8px;
    }

    .model-option {
        padding: 8px;
    }
}
"""