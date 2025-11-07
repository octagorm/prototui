"""
FormScreen Utility: Reusable form screen with text inputs and table selections.

Provides a standardized two-pane form layout with:
- Text input fields with validation
- Multiple table selection fields (using LayeredDataTable)
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

    table_fields = [
        TableSelectionField(
            id="category",
            label="Category",
            columns=["Name", "Description"],
            rows=[...],  # List of TableRow objects
            required=True
        ),
        TableSelectionField(
            id="priority",
            label="Priority",
            columns=["Level", "SLA"],
            rows=[...],
            required=False
        ),
    ]

    screen = FormScreen(
        text_fields=text_fields,
        table_fields=table_fields,
        title="My Form",
        explanation_title="Help",
        explanation_content="Instructions here..."
    )
"""

from dataclasses import dataclass
from typing import Callable

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Label
from textual.containers import Horizontal, VerticalScroll
from textual.binding import Binding

from .layered_data_table import LayeredDataTable, TableRow
from .explanation_panel import ExplanationPanel


@dataclass
class TextField:
    """Definition for a text input field."""
    id: str
    label: str
    placeholder: str = ""
    required: bool = False
    validator: Callable[[str], str | None] | None = None  # Returns error message or None
    visible_when: Callable[[dict], bool] | None = None  # Function to determine visibility based on current values


@dataclass
class TableSelectionField:
    """Definition for a table selection field."""
    id: str
    label: str
    columns: list[str]
    rows: list[TableRow]
    required: bool = False
    visible_when: Callable[[dict], bool] | None = None  # Function to determine visibility based on current values


class FormScreen(Screen):
    """
    Reusable form screen with text inputs and table selections.

    Features:
    - Two-pane layout (form 2/3, explanation 1/3)
    - Text input fields with validation
    - Multiple table selection fields (radio mode with visual indicator)
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
    }
    """

    def __init__(
        self,
        text_fields: list[TextField] | None = None,
        table_fields: list[TableSelectionField] | None = None,
        fields: list[TextField | TableSelectionField] | None = None,
        title: str = "Form",
        explanation_title: str = "Help",
        explanation_content: str = "",
        on_quit: Callable | None = None
    ):
        """
        Initialize form screen.

        Args:
            text_fields: List of TextField definitions (optional, legacy parameter)
            table_fields: List of TableSelectionField definitions (optional, legacy parameter)
            fields: List of mixed TextField and TableSelectionField in desired order (optional)
                   If provided, text_fields and table_fields are ignored.
            title: Screen title
            explanation_title: Title for explanation panel
            explanation_content: Content for explanation panel
            on_quit: Optional callback when user quits without submitting
        """
        super().__init__()
        
        # Support both old API (separate text_fields/table_fields) and new API (mixed fields)
        if fields:
            self.fields = fields
            self.text_fields = [f for f in fields if isinstance(f, TextField)]
            self.table_fields = [f for f in fields if isinstance(f, TableSelectionField)]
        else:
            self.text_fields = text_fields or []
            self.table_fields = table_fields or []
            # Preserve old behavior: text fields first, then table fields
            self.fields = self.text_fields + self.table_fields
        
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
                # Render fields in order
                for field in self.fields:
                    if isinstance(field, TextField):
                        # Text input field
                        label_text = field.label
                        if not field.required:
                            label_text += " (optional)"
                        
                        label = Label(label_text)
                        label.add_class(f"field-label-{field.id}")
                        yield label
                        
                        input_widget = Input(
                            placeholder=field.placeholder,
                            id=field.id
                        )
                        if field.visible_when:
                            label.display = False
                            input_widget.display = False
                        yield input_widget
                    
                    elif isinstance(field, TableSelectionField):
                        # Table selection field
                        table_label = field.label
                        if not field.required:
                            table_label += " (optional)"
                        
                        label = Label(table_label)
                        label.add_class(f"field-label-{field.id}")
                        yield label
                        
                        table = LayeredDataTable(
                            id=field.id,
                            columns=field.columns,
                            rows=field.rows,
                            select_mode="radio",
                            show_layers=False,
                            show_column_headers=True,
                            auto_height=True
                        )
                        if field.visible_when:
                            label.display = False
                            table.display = False
                        yield table

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

        # Hide table cursors initially (shown only when focused)
        def hide_table_cursors():
            for table_field in self.table_fields:
                table = self.query_one(f"#{table_field.id}", LayeredDataTable)
                inner_table = table.query_one("#data-table")
                inner_table.show_cursor = False

        # Delay hiding cursors until after LayeredDataTable's on_mount
        if self.table_fields:
            self.call_after_refresh(hide_table_cursors)

        # Focus on first field after screen is fully mounted
        def focus_first_field():
            # Focus on first text field if available
            if self.text_fields:
                first_field = self.text_fields[0]
                first_input = self.query_one(f"#{first_field.id}", Input)
                first_input.focus()
            # Otherwise focus on first table field if available
            elif self.table_fields:
                first_table_field = self.table_fields[0]
                table = self.query_one(f"#{first_table_field.id}", LayeredDataTable)
                inner_table = table.query_one("#data-table")
                inner_table.focus()

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
                # Focus on first text field if available
                if self.text_fields:
                    first_field = self.text_fields[0]
                    first_input = self.query_one(f"#{first_field.id}", Input)
                    first_input.focus()
                # Otherwise focus on first table field if available
                elif self.table_fields:
                    first_table_field = self.table_fields[0]
                    table = self.query_one(f"#{first_table_field.id}", LayeredDataTable)
                    inner_table = table.query_one("#data-table")
                    inner_table.focus()
            elif event.key == "shift+tab":
                event.prevent_default()
                event.stop()
                # Focus on last field (table fields come after text fields)
                if self.table_fields:
                    last_table_field = self.table_fields[-1]
                    table = self.query_one(f"#{last_table_field.id}", LayeredDataTable)
                    inner_table = table.query_one("#data-table")
                    inner_table.focus()
                elif self.text_fields:
                    last_text_field = self.text_fields[-1]
                    last_input = self.query_one(f"#{last_text_field.id}", Input)
                    last_input.focus()

    def get_current_values(self) -> dict:
        """
        Get current form values (used for visibility conditions and dynamic updates).
        
        Returns:
            Dictionary with current values from all fields.
        """
        values = {}
        
        # Get text field values
        for field in self.text_fields:
            try:
                input_widget = self.query_one(f"#{field.id}", Input)
                values[field.id] = input_widget.value.strip()
            except:
                pass
        
        # Get table selections
        for table_field in self.table_fields:
            try:
                table = self.query_one(f"#{table_field.id}", LayeredDataTable)
                selected_rows = table.get_selected_rows()
                if selected_rows:
                    values[table_field.id] = selected_rows[0]
            except:
                pass
        
        return values
    
    def _update_field_visibility(self) -> None:
        """Update visibility of conditional fields based on current values."""
        current_values = self.get_current_values()
        
        # Update text field visibility
        for field in self.text_fields:
            if field.visible_when:
                should_show = field.visible_when(current_values)
                try:
                    input_widget = self.query_one(f"#{field.id}", Input)
                    label = self.query_one(f".field-label-{field.id}", Label)
                    
                    input_widget.display = should_show
                    label.display = should_show
                except:
                    pass
        
        # Update table field visibility
        for table_field in self.table_fields:
            if table_field.visible_when:
                should_show = table_field.visible_when(current_values)
                try:
                    table = self.query_one(f"#{table_field.id}", LayeredDataTable)
                    label = self.query_one(f".field-label-{table_field.id}", Label)
                    
                    table.display = should_show
                    label.display = should_show
                except:
                    pass

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
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes to update conditional field visibility."""
        self._update_field_visibility()
    
    def on_layered_data_table_row_selected(self, event) -> None:
        """Handle table selection changes."""
        # Update conditional field visibility
        self._update_field_visibility()
        
        # Call external callback if provided (for dynamic row updates)
        if hasattr(self, '_table_selection_callback') and self._table_selection_callback:
            self._table_selection_callback(event)

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
            
            # Skip validation for hidden fields
            if not input_widget.display:
                continue
            
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

        # Validate table selections
        for table_field in self.table_fields:
            table = self.query_one(f"#{table_field.id}", LayeredDataTable)
            
            # Skip validation for hidden fields
            if not table.display:
                continue
            
            selected_rows = table.get_selected_rows()

            if table_field.required and not selected_rows:
                errors.append(f"{table_field.label} is required")
                table.add_class("error")
            else:
                table.remove_class("error")
                if selected_rows:
                    # Get selected row (radio mode = only one)
                    values[table_field.id] = selected_rows[0]

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

        # Add table selection values
        for table_field in self.table_fields:
            table_value = self._submitted_values.get(table_field.id)
            if table_value:
                label = table_field.label.rstrip(":")
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
