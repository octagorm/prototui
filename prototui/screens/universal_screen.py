"""
UniversalScreen - The unified screen pattern for all TUI interfaces.

UniversalScreen provides a consistent layout and interaction pattern for everything
from simple info dialogs to complex data tables with input fields.
"""

from typing import Any, Optional
from dataclasses import dataclass, field as dataclass_field

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Input, Button
from textual import on

from prototui.components.layered_data_table import LayeredDataTable, TableRow
from prototui.components.explanation_panel import ExplanationPanel


@dataclass
class Field:
    """A field in the UniversalScreen."""

    id: str
    """Unique field identifier"""

    field_type: str
    """Field type: "text", "table", "boolean", "message" """

    label: str = ""
    """Field label"""

    # Text field options
    default_value: str = ""
    """Default value for text fields"""

    placeholder: str = ""
    """Placeholder text for text fields"""

    # Table field options
    columns: Optional[list[str]] = None
    """Column names for table fields"""

    rows: Optional[list[TableRow]] = None
    """Table rows for table fields"""

    select_mode: str = "radio"
    """Selection mode for table fields ("none", "single", "radio", "multi")"""

    show_layers: bool = True
    """Whether to show layers in table fields"""

    show_column_headers: bool = True
    """Whether to show column headers in table fields"""

    auto_height: bool = True
    """Whether to auto-size table height based on row count (default True for forms)"""

    # Boolean field options
    default_bool: bool = False
    """Default value for boolean fields"""

    # Validation
    required: bool = False
    """Whether this field is required (for validation)"""

    # Visibility
    initially_hidden: bool = False
    """Whether this field should be hidden on initial render (for conditional fields)"""


@dataclass
class ScreenResult:
    """Return value from UniversalScreen."""

    confirmed: bool
    """True if user submitted (Enter), False if cancelled (ESC)"""

    values: dict[str, Any]
    """Field ID -> value mapping"""


# Forward declaration - will be defined below
_UniversalScreenBase = None


def _create_screen_class(
    allow_submit: bool,
    custom_bindings: Optional[list[Binding]] = None
) -> type:
    """
    Create a UniversalScreen subclass with the right BINDINGS.

    This is necessary because Textual only reads class-level BINDINGS,
    not instance-level. We dynamically create a subclass with the correct
    bindings based on parameters.
    """
    # Base bindings
    bindings = [
        Binding("escape", "unfocus", "Unfocus", show=False, priority=True),
        Binding("tab", "focus_next", "Next field", show=False),
        Binding("shift+tab", "focus_previous", "Previous field", show=False),
    ]

    # Add Enter if allowed
    if allow_submit:
        bindings.append(
            Binding("enter", "submit", "Submit", show=True, priority=True)
        )

    # Add custom bindings with auto-priority
    if custom_bindings:
        for binding in custom_bindings:
            if isinstance(binding, Binding):
                # Auto-add priority=True if not explicitly set
                if not binding.priority:
                    binding = Binding(
                        binding.key,
                        binding.action,
                        binding.description,
                        show=binding.show,
                        priority=True,
                        key_display=binding.key_display
                    )
                bindings.append(binding)

    # Create the subclass - _UniversalScreenBase will be set after class definition
    class DynamicUniversalScreen(_UniversalScreenBase):
        BINDINGS = bindings

    return DynamicUniversalScreen


class UniversalScreen(Screen[ScreenResult]):
    """
    The universal screen pattern for all TUI interfaces.

    UniversalScreen provides a consistent two-column layout:
    - Left: Main content area with title, message, and fields
    - Right: Explanation panel for help text and hints

    This pattern is used for everything from simple "OK" dialogs to complex
    multi-field forms with data tables.

    Example - Simple message:
        ```python
        screen = UniversalScreen(
            title="Success",
            message="Operation completed successfully",
            explanation_content="You can press Enter to continue"
        )
        result = await app.push_screen_wait(screen)
        ```

    Example - Text input:
        ```python
        screen = UniversalScreen(
            title="Enter Name",
            fields=[
                Field(id="name", field_type="text", label="Name:",
                      placeholder="Enter your name")
            ],
            explanation_content="Please provide your name"
        )
        result = await app.push_screen_wait(screen)
        if result.confirmed:
            name = result.values["name"]
        ```

    Example - Table selection:
        ```python
        screen = UniversalScreen(
            title="Select Service",
            fields=[
                Field(
                    id="service",
                    field_type="table",
                    columns=["Name", "Status"],
                    rows=[
                        TableRow({"Name": "API", "Status": "Running"}),
                        TableRow({"Name": "DB", "Status": "Stopped"}),
                    ],
                    select_mode="radio"
                )
            ],
            explanation_content="Choose a service to configure"
        )
        result = await app.push_screen_wait(screen)
        if result.confirmed:
            selected_rows = result.values["service"]
        ```
    """

    # Default bindings - will be overridden by subclasses
    BINDINGS = [
        Binding("escape", "unfocus", "Unfocus", show=False, priority=True),
        Binding("tab", "focus_next", "Next field", show=False),
        Binding("shift+tab", "focus_previous", "Previous field", show=False),
    ]

    def __new__(
        cls,
        title: str,
        fields: Optional[list[Field]] = None,
        message: str = "",
        explanation_title: str = "",
        explanation_content: str = "",
        explanation_hint: str = "",
        submit_label: str = "Submit",
        cancel_label: str = "Cancel",
        allow_submit: bool = True,
        custom_bindings: Optional[list[Binding]] = None,
        **kwargs,
    ):
        """
        Create an instance of a dynamically generated UniversalScreen subclass.

        This is necessary because Textual only reads class-level BINDINGS.
        """
        # If this is a subclass (like ConfirmationScreen), use normal instantiation
        if cls is not UniversalScreen:
            return super().__new__(cls)

        # For UniversalScreen, create a dynamic subclass with the right bindings
        screen_class = _create_screen_class(allow_submit, custom_bindings)
        return super(UniversalScreen, screen_class).__new__(screen_class)

    def __init__(
        self,
        title: str,
        fields: Optional[list[Field]] = None,
        message: str = "",
        explanation_title: str = "",
        explanation_content: str = "",
        explanation_hint: str = "",
        submit_label: str = "Submit",
        cancel_label: str = "Cancel",
        allow_submit: bool = True,
        custom_bindings: Optional[list[Binding]] = None,
        **kwargs,
    ) -> None:
        """
        Initialize the UniversalScreen.

        Args:
            title: Screen title
            fields: List of fields to display (if any)
            message: Main message (for simple info screens without fields)
            explanation_title: Title for explanation panel
            explanation_content: Content for explanation panel
            explanation_hint: Hint text for explanation panel
            submit_label: Label for submit action (shown in footer)
            cancel_label: Label for cancel action (shown in footer)
            allow_submit: Whether Enter key dismisses the screen (default True)
            custom_bindings: Optional list of custom key bindings for this screen
            **kwargs: Additional screen arguments
        """
        super().__init__(**kwargs)

        self._title = title
        self._fields = fields or []
        self._message = message
        self._explanation_title = explanation_title
        self._explanation_content = explanation_content
        self._explanation_hint = explanation_hint
        self._submit_label = submit_label
        self._cancel_label = cancel_label
        self._allow_submit = allow_submit

        # Track focusable widgets for tab navigation
        self._focusable_ids: list[str] = []

        # Track validation errors
        self._validation_errors: dict[str, str] = {}
        self._original_explanation_content = explanation_content
        self._original_explanation_title = explanation_title

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header()

        with Horizontal(id="universal-screen-content"):
            # Left side: Main content (3fr)
            with Vertical(id="main-content"):
                yield Static(self._title, id="screen-title")

                # Show message if provided
                if self._message:
                    yield Static(self._message, id="screen-message")

                # Render fields
                for field_def in self._fields:
                    yield from self._render_field(field_def)

            # Right side: Explanation panel (2fr)
            yield ExplanationPanel(
                title=self._explanation_title,
                content=self._explanation_content,
                hint=self._explanation_hint,
                id="explanation-panel",
            )

        yield Footer()

    def _render_field(self, field_def: Field) -> ComposeResult:
        """Render a single field based on its type."""
        if field_def.field_type == "text":
            # Text input field
            if field_def.label:
                yield Static(field_def.label, classes="field-label", id=f"label-{field_def.id}")

            input_widget = Input(
                value=field_def.default_value,
                placeholder=field_def.placeholder,
                id=f"field-{field_def.id}",
            )
            self._focusable_ids.append(f"field-{field_def.id}")
            yield input_widget

        elif field_def.field_type == "table":
            # Table selection field
            if field_def.label:
                yield Static(field_def.label, classes="field-label")

            table = LayeredDataTable(
                columns=field_def.columns or [],
                rows=field_def.rows or [],
                show_layers=field_def.show_layers,
                show_column_headers=field_def.show_column_headers,
                select_mode=field_def.select_mode,
                auto_height=field_def.auto_height,
                id=f"field-{field_def.id}",
            )
            self._focusable_ids.append(f"field-{field_def.id}")
            yield table

        elif field_def.field_type == "boolean":
            # Boolean toggle field (simple text for now, can enhance later)
            if field_def.label:
                yield Static(field_def.label, classes="field-label")

            # For now, use a simple static showing current value
            # Can be enhanced with a proper toggle widget later
            value_text = "Yes" if field_def.default_bool else "No"
            yield Static(
                f"[{value_text}] (Press Space to toggle)",
                id=f"field-{field_def.id}",
                classes="boolean-field",
            )
            self._focusable_ids.append(f"field-{field_def.id}")

        elif field_def.field_type == "message":
            # Just a message, no interaction
            yield Static(field_def.label or field_def.default_value, classes="field-message")

    def on_mount(self) -> None:
        """Focus first field when mounted."""
        # Hide initially_hidden fields
        for field_def in self._fields:
            if field_def.initially_hidden:
                self.set_field_visibility(field_def.id, visible=False)

        # Focus the first focusable field
        if self._focusable_ids:
            try:
                first_widget = self.query_one(f"#{self._focusable_ids[0]}")
                first_widget.focus()
            except Exception:
                pass

    @on(LayeredDataTable.RowSelected)
    def on_layered_data_table_row_selected(self, event: LayeredDataTable.RowSelected) -> None:
        """Handle row selection in single-select mode tables (auto-submit)."""
        # Find the table that triggered the event
        table = event.control

        # Only auto-submit for tables in "single" mode
        if table.select_mode == "single":
            # Auto-submit the form when a row is selected in single mode
            self.action_submit()

    def action_submit(self) -> None:
        """Submit the form (Enter key)."""
        if not self._allow_submit:
            # Submit disabled - do nothing
            return

        # Validate fields
        if not self._validate():
            # Validation failed - show errors and don't dismiss
            self._show_validation_errors()
            return

        # Validation passed - clear any error styling
        self._clear_validation_errors()

        values = self._collect_values()
        self.dismiss(ScreenResult(confirmed=True, values=values))

    def action_unfocus(self) -> None:
        """Unfocus the currently focused widget (ESC key)."""
        focused = self.focused
        if focused and focused != self:
            # Focus the screen itself first to prevent automatic refocusing
            self.set_focus(None)
            # Then blur the widget
            focused.blur()

    def action_focus_next(self) -> None:
        """Focus next field (Tab key)."""
        if not self._focusable_ids:
            return

        focused = self.focused
        if focused is None:
            # Nothing focused, focus first
            if self._focusable_ids:
                self.query_one(f"#{self._focusable_ids[0]}").focus()
            return

        # Find current field index
        try:
            # Check if focused widget or any ancestor is in focusable list
            focusable_id = self._find_focusable_ancestor(focused)

            if focusable_id:
                current_index = self._focusable_ids.index(focusable_id)
                next_index = (current_index + 1) % len(self._focusable_ids)
                next_id = self._focusable_ids[next_index]
                self.query_one(f"#{next_id}").focus()
        except Exception:
            pass

    def action_focus_previous(self) -> None:
        """Focus previous field (Shift+Tab key)."""
        if not self._focusable_ids:
            return

        focused = self.focused
        if focused is None:
            # Nothing focused, focus last
            if self._focusable_ids:
                self.query_one(f"#{self._focusable_ids[-1]}").focus()
            return

        # Find current field index
        try:
            # Check if focused widget or any ancestor is in focusable list
            focusable_id = self._find_focusable_ancestor(focused)

            if focusable_id:
                current_index = self._focusable_ids.index(focusable_id)
                prev_index = (current_index - 1) % len(self._focusable_ids)
                prev_id = self._focusable_ids[prev_index]
                self.query_one(f"#{prev_id}").focus()
        except Exception:
            pass

    def _find_focusable_ancestor(self, widget) -> Optional[str]:
        """
        Find the first ancestor (or self) that is in the focusable list.

        Args:
            widget: The widget to check

        Returns:
            The ID of the focusable ancestor, or None
        """
        current = widget
        while current is not None:
            if current.id and current.id in self._focusable_ids:
                return current.id
            current = current.parent
        return None

    def _validate(self) -> bool:
        """
        Validate all fields.

        Returns:
            True if all validations pass, False otherwise
        """
        self._validation_errors.clear()

        for field_def in self._fields:
            if not field_def.required:
                continue

            field_id = f"field-{field_def.id}"

            if field_def.field_type == "text":
                # Validate text field - check if not empty
                try:
                    widget = self.query_one(f"#{field_id}", Input)
                    value = widget.value.strip()
                    if not value:
                        self._validation_errors[field_id] = f"{field_def.label or field_def.id} is required"
                except Exception:
                    pass

            elif field_def.field_type == "table":
                # Validate table field - check if selection made
                try:
                    widget = self.query_one(f"#{field_id}", LayeredDataTable)
                    selected = widget.get_selected_rows()
                    if not selected:
                        self._validation_errors[field_id] = f"{field_def.label or field_def.id} is required"
                except Exception:
                    pass

        return len(self._validation_errors) == 0

    def _show_validation_errors(self) -> None:
        """Show validation errors visually."""
        # Update explanation panel with error message
        try:
            panel = self.query_one("#explanation-panel", ExplanationPanel)
            error_messages = []
            for field_id, error_msg in self._validation_errors.items():
                error_messages.append(f"• {error_msg}")

            error_text = "Please fix the following errors:\n\n" + "\n".join(error_messages)

            panel.update(
                title="Validation Error",
                content=error_text,
                hint="Fix errors and try again"
            )
        except Exception:
            pass

        # Add error class to invalid fields
        for field_id in self._validation_errors.keys():
            try:
                widget = self.query_one(f"#{field_id}")
                widget.add_class("field-error")
            except Exception:
                pass

        # Remove error class from valid fields
        for field_def in self._fields:
            field_id = f"field-{field_def.id}"
            if field_id not in self._validation_errors:
                try:
                    widget = self.query_one(f"#{field_id}")
                    widget.remove_class("field-error")
                except Exception:
                    pass

    def _clear_validation_errors(self) -> None:
        """Clear all validation error styling."""
        # Restore original explanation panel content
        try:
            panel = self.query_one("#explanation-panel", ExplanationPanel)
            panel.update(
                title=self._original_explanation_title,
                content=self._original_explanation_content,
                hint=self._explanation_hint
            )
        except Exception:
            pass

        # Remove error class from all fields
        for field_def in self._fields:
            field_id = f"field-{field_def.id}"
            try:
                widget = self.query_one(f"#{field_id}")
                widget.remove_class("field-error")
            except Exception:
                pass

    def set_field_visibility(self, field_id: str, visible: bool, toggle_required: bool = True) -> bool:
        """
        Show or hide a field and its label.

        This is useful for conditional fields that should only appear based on other field values.
        The field must already be rendered in the screen.

        Args:
            field_id: The field ID (without "field-" prefix)
            visible: True to show, False to hide
            toggle_required: If True, also toggles the field's required property based on visibility

        Returns:
            True if successful, False if field not found

        Example:
            ```python
            # In your app's method
            def _toggle_advanced_field(self):
                if isinstance(self.screen, UniversalScreen):
                    show = self.state.get("show_advanced")
                    self.screen.set_field_visibility("advanced_option", show)
            ```
        """
        try:
            # Find the field widget
            field_widget_id = f"field-{field_id}"
            field_widget = self.query_one(f"#{field_widget_id}")

            # Find the field definition
            field_def = None
            for f in self._fields:
                if f.id == field_id:
                    field_def = f
                    break

            # Find the associated label by ID (labels are rendered with id="label-{field_id}")
            field_label = None
            label_id = f"label-{field_id}"
            try:
                field_label = self.query_one(f"#{label_id}")
            except:
                # Label might not exist for this field
                pass

            # Toggle visibility
            display_value = "block" if visible else "none"
            field_widget.styles.display = display_value
            if field_label:
                field_label.styles.display = display_value

            # Toggle required property if requested
            if toggle_required and field_def:
                field_def.required = visible

            return True

        except Exception:
            return False

    def _collect_values(self) -> dict[str, Any]:
        """Collect values from all fields."""
        values = {}

        for field_def in self._fields:
            field_id = f"field-{field_def.id}"

            try:
                if field_def.field_type == "text":
                    # Get text from Input widget
                    input_widget = self.query_one(f"#{field_id}", Input)
                    values[field_def.id] = input_widget.value

                elif field_def.field_type == "table":
                    # Get selected rows from table
                    table = self.query_one(f"#{field_id}", LayeredDataTable)
                    values[field_def.id] = table.get_selected_rows()

                elif field_def.field_type == "boolean":
                    # For now, just use default value
                    # Can enhance with actual toggle later
                    values[field_def.id] = field_def.default_bool

            except Exception:
                # Field not found or error, skip it
                pass

        return values

    def update_explanation(
        self,
        title: Optional[str] = None,
        content: Optional[str] = None,
        hint: Optional[str] = None,
    ) -> None:
        """Update the explanation panel content."""
        try:
            panel = self.query_one("#explanation-panel", ExplanationPanel)
            panel.update_content(title=title, content=content, hint=hint)
        except Exception:
            pass


# Set the base class for the factory function
_UniversalScreenBase = UniversalScreen


class ConfirmationScreen(UniversalScreen):
    """A confirmation dialog with Y/N hotkeys."""

    BINDINGS = [
        Binding("y", "confirm_yes", "Yes", show=True, priority=True),
        Binding("n", "confirm_no", "No", show=True, priority=True),
        Binding("escape", "unfocus", "Unfocus", show=False, priority=True),
    ]

    def __init__(
        self,
        title: str,
        message: str,
        explanation_title: str = "Confirmation",
        explanation_content: str = "Please confirm your choice.",
        explanation_hint: str = "Press Y for Yes or N for No",
    ):
        """
        Initialize the confirmation dialog.

        Args:
            title: Dialog title
            message: Main message to display
            explanation_title: Title for explanation panel
            explanation_content: Content for explanation panel
            explanation_hint: Hint text for explanation panel
        """
        super().__init__(
            title=title,
            message=message,
            explanation_title=explanation_title,
            explanation_content=explanation_content,
            explanation_hint=explanation_hint,
            allow_submit=False,  # Disable Enter, use Y/N only
        )

    def action_confirm_yes(self) -> None:
        """Handle Y key press - confirm."""
        self.dismiss(ScreenResult(confirmed=True, values={}))

    def action_confirm_no(self) -> None:
        """Handle N key press - cancel."""
        self.dismiss(ScreenResult(confirmed=False, values={}))


def create_confirmation_dialog(
    title: str,
    message: str,
    explanation_title: str = "Confirmation",
    explanation_content: str = "Please confirm your choice.",
    explanation_hint: str = "Press Y for Yes or N for No",
) -> ConfirmationScreen:
    """
    Create a confirmation dialog with Y/N hotkeys.

    Args:
        title: Dialog title
        message: Main message to display
        explanation_title: Title for explanation panel
        explanation_content: Content for explanation panel
        explanation_hint: Hint text for explanation panel

    Returns:
        ConfirmationScreen with Y/N bindings
    """
    return ConfirmationScreen(
        title=title,
        message=message,
        explanation_title=explanation_title,
        explanation_content=explanation_content,
        explanation_hint=explanation_hint,
    )
