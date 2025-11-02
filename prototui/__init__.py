"""
TUI Library - Reusable Textual components and patterns for building terminal UIs.

This library provides:
- Core components: LayeredDataTable, ExplanationPanel
- UniversalScreen: Unified screen pattern for all interfaces
- Utilities: async_helpers, state_manager
- Consistent theming and styling
"""

__version__ = "0.1.0"

# Core components will be importable from top level
from prototui.components.layered_data_table import LayeredDataTable, TableRow
from prototui.components.explanation_panel import ExplanationPanel

# The universal screen pattern
from prototui.screens.universal_screen import (
    UniversalScreen,
    Field,
    ScreenResult,
    ConfirmationScreen,
    create_confirmation_dialog,
)

__all__ = [
    "LayeredDataTable",
    "TableRow",
    "ExplanationPanel",
    "UniversalScreen",
    "Field",
    "ScreenResult",
    "ConfirmationScreen",
    "create_confirmation_dialog",
]
