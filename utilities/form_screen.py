"""
FormScreen Utility: Reusable form screen with text inputs and table selection.

Provides a standardized two-pane form layout with:
- Text input fields with validation
- Table selection fields (using LayeredDataTable)
- Explanation panel on the right (1/3 of space)
- Automatic focus management
- Enter to submit with priority
- Visual validation feedback

Usage:
    from utilities.form_screen import FormScreen, TextField, TableSelectionField

    text_fields = [
        TextField(id="name", label="Name", required=True),
        TextField(id="email", label="Email", placeholder="user@example.com", required=True),
        TextField(id="notes", label="Notes", required=False),
    ]

    table_field = TableSelectionField(
        id="category",
        label="Category",
        columns=["Name", "Description"],
        rows=[...],  # List of TableRow objects
        required=True
    )

    screen = FormScreen(
        text_fields=text_fields,
        table_field=table_field,
        title="My Form",
        explanation_title="Help",
        explanation_content="Instructions here..."
    )
"""

from dataclasses import dataclass
from typing import Callable

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Input, Label
from textual.containers import Horizontal, VerticalScroll
from textual.binding import Binding

from .layered_data_table import LayeredDataTable, TableRow


@dataclass
class TextField:
    """Definition for a text input field."""
    id: str
    label: str
    placeholder: str = ""
    required: bool = False
    validator: Callable[[str], str | None] | None = None  # Returns error message or None


@dataclass
class TableSelectionField:
    """Definition for a table selection field."""
    id: str
    label: str
    columns: list[str]
    rows: list[TableRow]
    required: bool = False


class ExplanationPanel(Static):
    """Side panel showing help/explanation text."""

    # Prevent this panel from being focusable
    can_focus = False

    def __init__(self, title: str, content: str):
        super().__init__()
        self.panel_title = title
        self.panel_content = content

    def render(self) -> str:
        return f"[bold]{self.panel_title}[/bold]\n\n{self.panel_content}"

    def update_content(self, title: str, content: str) -> None:
        """Update panel content dynamically."""
        self.panel_title = title
        self.panel_content = content
        self.refresh()


class FormScreen(Screen):
    """
    Reusable form screen with text inputs and table selection.

    Features:
    - Two-pane layout (form 2/3, explanation 1/3)
    - Text input fields with validation
    - Table selection field (radio mode with visual indicator)
    - Required field validation
    - Automatic focus management
    - Enter to submit (priority binding)
    - Visual error feedback (red borders)
    - Console output on submission
    """

    BINDINGS = [
        Binding("enter", "submit", "Submit", show=True, priority=True),
        Binding("q", "request_quit", "Quit", show=True),
        Binding("escape", "blur_focus", "Blur", show=False),
    ]

    CSS = """
    #main-container {
        width: 100%;
        height: 100%;
    }

    #form-pane {
        width: 2fr;
        height: 100%;
        padding: 1 2;
    }

    Label {
        margin: 1 0 0 0;
    }

    Input {
        margin: 0 0 1 0;
    }

    Input.error {
        border: tall red;
    }

    LayeredDataTable {
        height: auto;
        max-height: 10;
        margin: 0 0 1 0;
    }

    LayeredDataTable.error {
        border: tall red;
    }

    #explanation-pane {
        width: 1fr;
        height: 100%;
        background: $panel;
        border-left: solid $primary;
        padding: 1 2;
    }

    ExplanationPanel {
        width: 100%;
        height: auto;
    }
    """

    def __init__(
        self,
        text_fields: list[TextField],
        table_field: TableSelectionField,
        title: str = "Form",
        explanation_title: str = "Help",
        explanation_content: str = "",
        on_quit: Callable | None = None
    ):
        """
        Initialize form screen.

        Args:
            text_fields: List of TextField definitions
            table_field: TableSelectionField definition
            title: Screen title
            explanation_title: Title for explanation panel
            explanation_content: Content for explanation panel
            on_quit: Optional callback when user quits without submitting
        """
        super().__init__()
        self.text_fields = text_fields
        self.table_field = table_field
        self.screen_title = title
        self.explanation_title = explanation_title
        self.explanation_content = explanation_content
        self.on_quit_callback = on_quit
        self._review_mode = False
        self._submitted_values = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main-container"):
            # Left side: Form
            with VerticalScroll(id="form-pane"):
                # Text input fields
                for field in self.text_fields:
                    # Add "(optional)" to label if not required
                    label_text = field.label
                    if not field.required:
                        label_text += " (optional)"
                    yield Label(label_text)
                    yield Input(
                        placeholder=field.placeholder,
                        id=field.id
                    )

                # Table selection field
                table_label = self.table_field.label
                if not self.table_field.required:
                    table_label += " (optional)"
                yield Label(table_label)
                yield LayeredDataTable(
                    id=self.table_field.id,
                    columns=self.table_field.columns,
                    rows=self.table_field.rows,
                    select_mode="radio",  # Radio mode shows ● indicator
                    show_layers=False,
                    show_column_headers=True,
                    auto_height=True
                )

            # Right side: Explanation panel
            with VerticalScroll(id="explanation-pane"):
                yield ExplanationPanel(
                    self.explanation_title,
                    self.explanation_content
                )

        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.screen_title

        # Make scroll containers non-focusable (explanation pane should never be in tab order)
        form_pane = self.query_one("#form-pane", VerticalScroll)
        explanation_pane = self.query_one("#explanation-pane", VerticalScroll)
        form_pane.can_focus = False
        explanation_pane.can_focus = False

        # Hide table cursor initially (shown only when focused)
        def hide_table_cursor():
            table = self.query_one(f"#{self.table_field.id}", LayeredDataTable)
            inner_table = table.query_one("#data-table")
            inner_table.show_cursor = False

        # Delay hiding cursor until after LayeredDataTable's on_mount
        self.call_after_refresh(hide_table_cursor)

        # Focus on first input field after screen is fully mounted
        def focus_first_field():
            if self.text_fields:
                first_field = self.text_fields[0]
                first_input = self.query_one(f"#{first_field.id}", Input)
                first_input.focus()

        self.call_after_refresh(focus_first_field)

    def on_key(self, event) -> None:
        """
        Handle Tab/Shift+Tab when no widget is focused.

        IMPORTANT: We intercept key events here rather than overriding action_focus_next/
        action_focus_previous because when nothing is focused, Tab/Shift+Tab dispatch to
        the App level, not the Screen level. Using on_key with event.prevent_default()
        and event.stop() ensures we catch it at the Screen level.
        """
        # Only intercept when nothing is focused
        if not self.focused:
            if event.key == "tab":
                event.prevent_default()
                event.stop()
                if self.text_fields:
                    first_field = self.text_fields[0]
                    first_input = self.query_one(f"#{first_field.id}", Input)
                    first_input.focus()
            elif event.key == "shift+tab":
                event.prevent_default()
                event.stop()
                table = self.query_one(f"#{self.table_field.id}", LayeredDataTable)
                inner_table = table.query_one("#data-table")
                inner_table.focus()

    def action_blur_focus(self) -> None:
        """Blur focus from current widget (ESC key), or exit review mode."""
        # If in review mode, ESC goes back to editing
        if self._review_mode:
            self._review_mode = False
            self.sub_title = self.screen_title
            # Restore original explanation content
            panel = self.query_one(ExplanationPanel)
            panel.update_content(self.explanation_title, self.explanation_content)
            self.notify("Returned to edit mode", severity="information")
            return

        # Blur focus from current widget
        if self.focused:
            self.set_focus(None)

    def on_descendant_focus(self, event) -> None:
        """Show table cursor when table receives focus."""
        # Show cursor only when table is focused (prevents looking pre-selected)
        if event.widget.id == "data-table":
            event.widget.show_cursor = True

    def on_descendant_blur(self, event) -> None:
        """Hide table cursor when table loses focus."""
        # Hide cursor when table loses focus
        if event.widget.id == "data-table":
            event.widget.show_cursor = False

    def action_submit(self) -> None:
        """Validate and submit the form."""
        # If in review mode, second Enter press confirms
        if self._review_mode:
            self.dismiss(self._submitted_values)
            return

        values = {}
        errors = []

        # Validate text fields
        for field in self.text_fields:
            input_widget = self.query_one(f"#{field.id}", Input)
            value = input_widget.value.strip()

            if field.required and not value:
                errors.append(f"{field.label} is required")
                input_widget.add_class("error")
            else:
                input_widget.remove_class("error")

                # Run custom validator if provided
                if value and field.validator:
                    error = field.validator(value)
                    if error:
                        errors.append(error)
                        input_widget.add_class("error")
                        continue

                values[field.id] = value

        # Validate table selection
        table = self.query_one(f"#{self.table_field.id}", LayeredDataTable)
        selected_rows = table.get_selected_rows()

        if self.table_field.required and not selected_rows:
            errors.append(f"{self.table_field.label} is required")
            table.add_class("error")
        else:
            table.remove_class("error")
            if selected_rows:
                # Get selected row (radio mode = only one)
                values[self.table_field.id] = selected_rows[0]

        if errors:
            error_msg = "\n".join(errors)
            print(f"\n⚠️  VALIDATION ERRORS:\n{error_msg}\n")
            self.notify(error_msg, severity="error", timeout=5)
            return

        # Store values and show review in explanation pane
        self._submitted_values = values
        self._show_review()
        self._review_mode = True

    def _show_review(self) -> None:
        """Show submitted values in the explanation pane."""
        panel = self.query_one(ExplanationPanel)

        # Build review content
        review_lines = []

        # Add text field values
        for field in self.text_fields:
            value = self._submitted_values.get(field.id, "")
            if value or field.required:
                label = field.label.rstrip(":")
                review_lines.append(f"{label}: {value or 'N/A'}")

        # Add table selection value
        table_value = self._submitted_values.get(self.table_field.id)
        if table_value:
            label = self.table_field.label.rstrip(":")
            # Format table row values
            if isinstance(table_value, TableRow):
                formatted = ", ".join(f"{v}" for v in table_value.values.values())
                review_lines.append(f"{label}: {formatted}")

        review_content = "\n".join(review_lines)

        panel.update_content(
            "Review Your Submission",
            f"{review_content}\n\nPress Enter to confirm, or ESC to go back and edit."
        )

        self.sub_title = f"{self.screen_title} - Review"
        self.notify("Review your submission and press Enter to confirm", severity="information")

    def action_request_quit(self) -> None:
        """Handle quit request."""
        if self.on_quit_callback:
            self.on_quit_callback()
        else:
            # Default behavior: dismiss with None
            self.dismiss(None)
