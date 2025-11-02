"""
ExplanationPanel - A widget for displaying contextual help and explanations.
"""

from typing import Optional

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class ExplanationPanel(Widget):
    """
    A panel for displaying contextual help, explanations, and hints.

    This widget is designed to sit alongside main content (like a list or form)
    and provide context-sensitive information to guide the user.

    Example:
        ```python
        panel = ExplanationPanel(
            title="Select a Service",
            content="Choose the service you want to configure.",
            hint="Use arrow keys to navigate, Enter to select."
        )

        # Update dynamically
        panel.update_content("You selected: Service A", "Press Enter to continue.")
        ```

    Attributes:
        title: Panel title (reactive)
        content: Main explanatory content (reactive)
        hint: Optional hint text (reactive)
    """

    COMPONENT_CLASSES = {
        "explanation--title",
        "explanation--content",
        "explanation--hint",
    }

    title: reactive[str] = reactive("")
    content: reactive[str] = reactive("")
    hint: reactive[str] = reactive("")

    def __init__(
        self,
        title: str = "",
        content: str = "",
        hint: str = "",
        **kwargs,
    ) -> None:
        """
        Initialize the ExplanationPanel.

        Args:
            title: Panel title
            content: Main explanatory content
            hint: Optional hint text (e.g., keyboard shortcuts)
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.title = title
        self.content = content
        self.hint = hint

    def compose(self) -> ComposeResult:
        """Compose the panel."""
        with VerticalScroll():
            yield Static(self.title, id="explanation-title", classes="explanation--title")
            yield Static(self.content, id="explanation-content", classes="explanation--content")
            yield Static(self.hint, id="explanation-hint", classes="explanation--hint")

    def watch_title(self, new_title: str) -> None:
        """React to title changes."""
        if self.is_mounted:
            title_widget = self.query_one("#explanation-title", Static)
            title_widget.update(new_title)

    def watch_content(self, new_content: str) -> None:
        """React to content changes."""
        if self.is_mounted:
            content_widget = self.query_one("#explanation-content", Static)
            content_widget.update(new_content)

    def watch_hint(self, new_hint: str) -> None:
        """React to hint changes."""
        if self.is_mounted:
            hint_widget = self.query_one("#explanation-hint", Static)
            hint_widget.update(new_hint)

    def update_content(
        self,
        content: Optional[str] = None,
        hint: Optional[str] = None,
        title: Optional[str] = None,
    ) -> None:
        """
        Update panel content.

        Args:
            content: New content text (if provided)
            hint: New hint text (if provided)
            title: New title (if provided)
        """
        if title is not None:
            self.title = title
        if content is not None:
            self.content = content
        if hint is not None:
            self.hint = hint

    def clear(self) -> None:
        """Clear all panel content."""
        self.title = ""
        self.content = ""
        self.hint = ""

    def set_success(self, message: str, hint: str = "") -> None:
        """
        Display a success message.

        Args:
            message: Success message
            hint: Optional hint text
        """
        self.title = "✓ Success"
        self.content = message
        self.hint = hint

    def set_error(self, message: str, hint: str = "") -> None:
        """
        Display an error message.

        Args:
            message: Error message
            hint: Optional hint text
        """
        self.title = "✗ Error"
        self.content = message
        self.hint = hint

    def set_warning(self, message: str, hint: str = "") -> None:
        """
        Display a warning message.

        Args:
            message: Warning message
            hint: Optional hint text
        """
        self.title = "⚠ Warning"
        self.content = message
        self.hint = hint

    def set_info(self, message: str, hint: str = "") -> None:
        """
        Display an info message.

        Args:
            message: Info message
            hint: Optional hint text
        """
        self.title = "ℹ Info"
        self.content = message
        self.hint = hint
