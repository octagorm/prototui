"""
LayeredDataTable - A data table with layer grouping and sorting.
"""

from typing import Any, Optional, Iterable
from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DataTable, Input, Static
from textual.widgets.data_table import RowKey
from textual.containers import Vertical


@dataclass
class TableRow:
    """Represents a row in the LayeredDataTable."""

    values: dict[str, Any]
    """Column name -> value mapping."""

    layer: Optional[str] = None
    """Optional layer grouping."""

    row_key: Optional[str] = None
    """Optional unique key for this row."""


class LayeredDataTable(Widget):
    """
    A data table that groups rows by layers with alphabetical sorting.

    Built on Textual's DataTable but adds layer grouping similar to LayeredListView.
    Rows are grouped by their 'layer' attribute and sorted alphabetically within each layer.

    Example:
        ```python
        # Define columns
        columns = ["Name", "Type", "Status"]

        # Define rows with layers
        rows = [
            TableRow({"Name": "auth-service", "Type": "Core", "Status": "Running"}, layer="Production"),
            TableRow({"Name": "api-gateway", "Type": "API", "Status": "Running"}, layer="Production"),
            TableRow({"Name": "test-service", "Type": "Test", "Status": "Stopped"}, layer="Development"),
        ]

        table = LayeredDataTable(columns=columns, rows=rows, show_layers=True)
        ```

    Attributes:
        columns: List of column names
        rows: List of table rows
        show_layers: Whether to display layer separators
        select_mode: Selection mode ("none", "single", "radio", "multi")
            - "none": No selection, just cursor movement
            - "single": Enter to select, no visual indicator
            - "radio": Single select with ● showing current selection
            - "multi": Space to toggle, Enter to confirm, shows ○/● for each row
        cursor_type: Type of cursor ("row", "cell", or "none")
    """

    COMPONENT_CLASSES = {
        "layered-data-table--layer-header",
    }

    DEFAULT_CSS = """
    LayeredDataTable {
        height: auto;
    }

    LayeredDataTable #filter-info {
        height: auto;
        padding: 0 1;
        color: $text-muted;
        text-style: italic;
    }

    LayeredDataTable #filter-info.filter-hidden {
        display: none;
    }

    LayeredDataTable #filter-input {
        margin: 0 1 1 1;
    }

    LayeredDataTable #filter-input.filter-hidden {
        display: none;
    }

    LayeredDataTable #data-table {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_selection", "Toggle", show=False),
        # Disable Page Up/Down/Home/End (not available on Macs)
        Binding("pageup", "do_nothing", "", show=False),
        Binding("pagedown", "do_nothing", "", show=False),
        Binding("home", "do_nothing", "", show=False),
        Binding("end", "do_nothing", "", show=False),
    ]

    columns: reactive[list[str]] = reactive(list, init=False)
    rows: reactive[list[TableRow]] = reactive(list, init=False)
    show_layers: reactive[bool] = reactive(True)
    show_column_headers: reactive[bool] = reactive(True)
    select_mode: reactive[str] = reactive("single")
    auto_height: reactive[bool] = reactive(False)
    _filter_visible: reactive[bool] = reactive(False)

    class RowSelected(Message):
        """Posted when a row is selected (Enter key in single-select mode)."""

        def __init__(self, row: TableRow, row_key: RowKey) -> None:
            super().__init__()
            self.row = row
            self.row_key = row_key

    class RowHighlighted(Message):
        """Posted when a row is highlighted (cursor movement)."""

        def __init__(self, row: Optional[TableRow], row_key: Optional[RowKey]) -> None:
            super().__init__()
            self.row = row
            self.row_key = row_key

    class RowToggled(Message):
        """Posted when a row is toggled (Space key in multi-select mode)."""

        def __init__(self, row: TableRow, row_key: RowKey, selected: bool) -> None:
            super().__init__()
            self.row = row
            self.row_key = row_key
            self.selected = selected

    class SelectionConfirmed(Message):
        """Posted when selection is confirmed (Enter key in multi-select mode)."""

        def __init__(self, rows: list[TableRow]) -> None:
            super().__init__()
            self.rows = rows

    def __init__(
        self,
        columns: Optional[list[str]] = None,
        rows: Optional[list[TableRow]] = None,
        show_layers: bool = True,
        show_column_headers: bool = True,
        select_mode: str = "single",
        multi_select: Optional[bool] = None,  # Deprecated, for backward compatibility
        cursor_type: str = "row",
        auto_height: bool = False,
        filterable: bool = False,
        **kwargs,
    ) -> None:
        """
        Initialize the LayeredDataTable.

        Args:
            columns: List of column names
            rows: Initial rows to display
            show_layers: Whether to show layer separators
            show_column_headers: Whether to show column headers
            select_mode: Selection mode ("none", "single", "radio", "multi")
            multi_select: (Deprecated) Use select_mode="multi" instead
            cursor_type: Cursor type ("row", "cell", or "none")
            auto_height: Whether to auto-size height based on row count (default False)
            filterable: Whether to show filter input (press / to filter)
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.columns = columns or []
        self.show_layers = show_layers
        self.show_column_headers = show_column_headers
        self.auto_height = auto_height
        self.filterable = filterable

        # Backward compatibility: multi_select=True maps to select_mode="multi"
        if multi_select is not None:
            self.select_mode = "multi" if multi_select else "single"
        else:
            self.select_mode = select_mode

        self._cursor_type = cursor_type
        self._selected_rows: set[RowKey] = set()  # Track selected rows in multi mode
        self._filter_text: str = ""  # Current filter text
        self._all_rows: list[TableRow] = rows or []  # All rows (before filtering)
        self._filtered_count: int = 0  # Number of visible rows after filtering
        self._selected_row: Optional[RowKey] = None  # Track selected row in radio mode
        self._row_map: dict[RowKey, TableRow] = {}  # Map DataTable RowKey to TableRow
        self._cursor_row_key: Optional[str] = None  # Track cursor position by row_key

        # Set rows (this will be the initially displayed rows)
        self.rows = rows or []

    def compose(self) -> ComposeResult:
        """Compose the data table with optional filter."""
        if self.filterable:
            with Vertical():
                yield Static("", id="filter-info", classes="filter-hidden")
                yield Input(
                    placeholder="Type to filter... (Tab/arrows to select from results)",
                    id="filter-input",
                    classes="filter-hidden",
                    disabled=True  # Disabled when hidden to prevent focusing
                )
                yield DataTable(
                    cursor_type=self._cursor_type,
                    show_header=self.show_column_headers,
                    id="data-table"
                )
        else:
            yield DataTable(
                cursor_type=self._cursor_type,
                show_header=self.show_column_headers,
                id="data-table"
            )

    def on_mount(self) -> None:
        """Initialize the table when mounted."""
        # Add Filter binding if filterable is True
        if self.filterable:
            # Add the filter binding dynamically
            self._bindings.bind("/", "focus_filter", "Filter", show=True, priority=False)

            # Ensure filter input is disabled and hidden on mount
            filter_input = self.query_one("#filter-input", Input)
            filter_input.disabled = True
            filter_input.display = False

        self._rebuild_table()
        # Show cursor if cursor_type is not "none"
        if self._cursor_type != "none":
            data_table = self.query_one("#data-table", DataTable)
            data_table.show_cursor = True
            # Focus the table so it can receive input
            self.call_after_refresh(data_table.focus)

    def focus(self, scroll_visible: bool = True) -> None:
        """Focus the table (delegates to inner DataTable)."""
        data_table = self.query_one("#data-table", DataTable)
        data_table.show_cursor = True
        data_table.focus(scroll_visible)

    def on_focus(self) -> None:
        """Show cursor when table gains focus."""
        data_table = self.query_one("#data-table", DataTable)
        data_table.show_cursor = True

    def on_blur(self) -> None:
        """Hide cursor when table loses focus."""
        data_table = self.query_one("#data-table", DataTable)
        data_table.show_cursor = False

    def watch_rows(self, new_rows: list[TableRow]) -> None:
        """React to rows changing."""
        # Update all_rows only if not actively filtering
        # (to avoid losing original data when filter updates self.rows)
        if not self._filter_text:
            self._all_rows = list(new_rows)

        if self.is_mounted:
            self._rebuild_table()

    def watch_columns(self, new_columns: list[str]) -> None:
        """React to columns changing."""
        if self.is_mounted:
            self._rebuild_table()

    def watch_show_layers(self, show: bool) -> None:
        """React to show_layers changing."""
        if self.is_mounted:
            self._rebuild_table()

    def watch_show_column_headers(self, show: bool) -> None:
        """React to show_column_headers changing."""
        if self.is_mounted:
            # Update the DataTable's show_header attribute
            data_table = self.query_one("#data-table", DataTable)
            data_table.show_header = show
            self._rebuild_table()

    def watch__filter_visible(self, visible: bool) -> None:
        """React to filter visibility changing."""
        if not self.is_mounted or not self.filterable:
            return

        filter_input = self.query_one("#filter-input", Input)
        filter_info = self.query_one("#filter-info", Static)

        if visible:
            # Show and enable
            filter_input.remove_class("filter-hidden")
            filter_info.remove_class("filter-hidden")
            filter_input.disabled = False
            filter_input.display = True
        else:
            # Hide and disable
            filter_input.add_class("filter-hidden")
            filter_info.add_class("filter-hidden")
            filter_input.disabled = True
            filter_input.display = False

    def _rebuild_table(self) -> None:
        """Rebuild the data table from current rows and columns."""
        data_table = self.query_one("#data-table", DataTable)
        data_table.clear(columns=True)
        self._row_map.clear()

        if not self.columns:
            return

        # Add checkbox column in radio and multi modes
        if self.select_mode in ("radio", "multi"):
            data_table.add_column("", key="checkbox", width=1)

        # Add columns
        for col in self.columns:
            # Show column label only if show_column_headers is True
            label = col if self.show_column_headers else ""
            data_table.add_column(label, key=col)

        if not self.rows:
            return

        # Group rows by layer
        layered_rows: dict[Optional[str], list[TableRow]] = {}
        for row in self.rows:
            layer = row.layer if self.show_layers else None
            if layer not in layered_rows:
                layered_rows[layer] = []
            layered_rows[layer].append(row)

        # Sort layers alphabetically (None goes last)
        sorted_layers = sorted(
            layered_rows.keys(),
            key=lambda x: (x is None, x if x is not None else "")
        )

        # Build table with layer separators
        for layer_index, layer in enumerate(sorted_layers):
            layer_rows = layered_rows[layer]

            # Add layer header row if showing layers and layer exists
            if self.show_layers and layer is not None:
                has_checkbox = self.select_mode in ("radio", "multi")
                header_values = [""] * (len(self.columns) + (1 if has_checkbox else 0))
                # Put layer name in first data column (not checkbox column)
                if has_checkbox:
                    header_values[1] = f"[bold]{layer}[/bold]"
                else:
                    header_values[0] = f"[bold]{layer}[/bold]"
                data_table.add_row(*header_values, key=f"layer-header-{layer_index}")

            # Sort rows within layer alphabetically by first column value
            sorted_rows = sorted(
                layer_rows,
                key=lambda r: str(r.values.get(self.columns[0], "")).lower() if self.columns else ""
            )

            # Add rows
            for row in sorted_rows:
                row_values = []

                # Add checkbox in radio/multi modes
                if self.select_mode in ("radio", "multi"):
                    # Will be updated when row is added
                    row_values.append("")

                # Add column values
                for col in self.columns:
                    row_values.append(row.values.get(col, ""))

                # Generate or use provided row key
                row_key_str = row.row_key or f"row-{id(row)}"
                row_key = data_table.add_row(*row_values, key=row_key_str)
                self._row_map[row_key] = row

                # Update checkbox if in radio/multi modes
                if self.select_mode in ("radio", "multi"):
                    self._update_checkbox(row_key)

            # Add empty separator row between layers (except after last layer)
            if self.show_layers and layer_index < len(sorted_layers) - 1:
                has_checkbox = self.select_mode in ("radio", "multi")
                separator_values = [""] * (len(self.columns) + (1 if has_checkbox else 0))
                data_table.add_row(*separator_values, key=f"separator-{layer_index}")

        # Restore cursor position if we have a tracked position
        if self._cursor_row_key:
            cursor_restored = False
            for dt_row_key, table_row in self._row_map.items():
                if table_row.row_key == self._cursor_row_key:
                    try:
                        row_index = data_table.get_row_index(dt_row_key)
                        data_table.move_cursor(row=row_index)
                        cursor_restored = True
                    except Exception:
                        pass
                    break

            # If we couldn't restore, move to first valid row
            if not cursor_restored:
                self._move_cursor_to_first_valid_row()
        else:
            # No tracked position, move to first valid row
            self._move_cursor_to_first_valid_row()

        # Set dynamic height based on number of rows (if auto_height is enabled)
        if self.auto_height:
            self._update_table_height()

    def _update_checkbox(self, row_key: RowKey) -> None:
        """Update the checkbox for a row."""
        if self.select_mode not in ("radio", "multi"):
            return

        data_table = self.query_one("#data-table", DataTable)

        if self.select_mode == "radio":
            # Radio mode: show ● only for selected row, empty for others
            checkbox = "●" if row_key == self._selected_row else ""
        else:  # multi mode
            # Multi mode: show ○/● for all rows
            checkbox = "●" if row_key in self._selected_rows else "○"

        data_table.update_cell(row_key, "checkbox", checkbox)
        data_table.refresh()

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key)."""
        event.stop()

        # Skip layer headers and separators
        if str(event.row_key.value).startswith(("layer-header-", "separator-")):
            return

        if event.row_key in self._row_map:
            row = self._row_map[event.row_key]

            if self.select_mode == "multi":
                # In multi mode, Enter confirms all selections
                selected = [self._row_map[key] for key in self._selected_rows if key in self._row_map]
                self.post_message(self.SelectionConfirmed(selected))
            elif self.select_mode == "radio":
                # In radio mode, Enter selects this row (moves the ●)
                old_selection = self._selected_row
                self._selected_row = event.row_key

                # Update checkboxes (clear old, set new)
                if old_selection and old_selection in self._row_map:
                    self._update_checkbox(old_selection)
                self._update_checkbox(event.row_key)

                # Post selection message
                self.post_message(self.RowSelected(row, event.row_key))
            else:  # single or none mode
                # In single/none mode, Enter selects the row (no visual change)
                self.post_message(self.RowSelected(row, event.row_key))

    @on(DataTable.RowHighlighted)
    def on_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlighting (cursor movement)."""
        event.stop()

        if event.row_key and event.row_key in self._row_map:
            row = self._row_map[event.row_key]
            # Track cursor position for automatic restoration
            self._cursor_row_key = row.row_key
            self.post_message(self.RowHighlighted(row, event.row_key))
        else:
            self._cursor_row_key = None
            self.post_message(self.RowHighlighted(None, None))

    def action_toggle_selection(self) -> None:
        """Toggle selection for current row (Space key)."""
        if self.select_mode not in ("multi", "radio"):
            return

        data_table = self.query_one("#data-table", DataTable)
        if data_table.cursor_row is None:
            return

        row_keys = list(data_table.rows.keys())
        if data_table.cursor_row >= len(row_keys):
            return

        row_key = row_keys[data_table.cursor_row]

        # Skip layer headers and separators
        if str(row_key.value).startswith(("layer-header-", "separator-")):
            return

        if row_key not in self._row_map:
            return

        if self.select_mode == "multi":
            # Multi mode: toggle checkbox
            self._toggle_row_selection(row_key)
        else:  # radio mode
            # Radio mode: move ● to this row
            old_selection = self._selected_row
            self._selected_row = row_key

            # Update checkboxes (clear old, set new)
            if old_selection and old_selection in self._row_map:
                self._update_checkbox(old_selection)
            self._update_checkbox(row_key)

            # Post selection message
            row = self._row_map[row_key]
            self.post_message(self.RowSelected(row, row_key))

    def action_focus_filter(self) -> None:
        """Focus the filter input (/ key)."""
        if not self.filterable:
            return

        # Show the filter and focus it
        self._filter_visible = True
        filter_input = self.query_one("#filter-input", Input)
        self.call_after_refresh(filter_input.focus)

    def action_do_nothing(self) -> None:
        """Dummy action to disable default bindings."""
        pass

    @on(Input.Changed, "#filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        """Handle filter text changes."""
        self._filter_text = event.value.lower()
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Apply current filter to rows."""
        if not self._filter_text:
            # No filter - show all rows
            self.rows = self._all_rows
        else:
            # Filter rows - search across all column values
            filtered = []
            for row in self._all_rows:
                # Check if filter text matches any column value
                match = any(
                    self._filter_text in str(value).lower()
                    for value in row.values.values()
                )
                if match:
                    filtered.append(row)
            self.rows = filtered

        # Update filter info
        if self.filterable:
            self._filtered_count = len(self.rows)
            total = len(self._all_rows)
            if self._filter_text:
                info_text = f"Filter: {self._filter_text} ({self._filtered_count} of {total} matches)"
            else:
                info_text = ""
            filter_info = self.query_one("#filter-info", Static)
            filter_info.update(info_text)

    def on_key(self, event) -> None:
        """Handle key presses."""
        from textual.events import Key

        if not isinstance(event, Key):
            return

        # Handle / key to open/focus filter
        if event.key == "slash" and self.filterable:
            filter_input = self.query_one("#filter-input", Input)
            # Only focus if filter is not already focused
            if not filter_input.has_focus:
                self.action_focus_filter()
                event.prevent_default()
                event.stop()
                return

        # Handle keys when filter input is focused
        if self.filterable:
            filter_input = self.query_one("#filter-input", Input)
            if filter_input.has_focus:
                # ESC - clear filter, hide it, return to table
                if event.key == "escape":
                    filter_input.value = ""
                    self._filter_text = ""
                    self._apply_filter()
                    self._filter_visible = False
                    data_table = self.query_one("#data-table", DataTable)
                    data_table.focus()
                    event.prevent_default()
                    event.stop()
                    return

                # Tab or arrow keys - shift focus to table, hide filter if no text
                if event.key in ("tab", "up", "down"):
                    if not filter_input.value.strip():
                        # No text, hide the filter
                        self._filter_visible = False
                    data_table = self.query_one("#data-table", DataTable)
                    data_table.focus()
                    event.prevent_default()
                    event.stop()
                    return

                # Left/right arrows - allow normal text editing behavior
                # (don't prevent default for these)

        # Allow tab/shift+tab to bubble up for screen-level focus navigation
        if event.key in ("tab", "shift+tab"):
            # Don't prevent default, don't stop - let it bubble
            return

        # Handle arrow keys to skip headers/separators
        # We need to prevent the default DataTable behavior
        if event.key in ("up", "down"):
            self._navigate_skip_headers(event.key == "down")
            event.prevent_default()
            event.stop()

    def _navigate_skip_headers(self, move_down: bool) -> None:
        """Navigate up or down, skipping header and separator rows with wrapping."""
        data_table = self.query_one("#data-table", DataTable)
        if data_table.cursor_row is None:
            return

        row_keys = list(data_table.rows.keys())
        if not row_keys:
            return

        # Build list of valid (non-header, non-separator) row indices
        valid_indices = []
        for index, row_key in enumerate(row_keys):
            if not str(row_key.value).startswith(("layer-header-", "separator-")):
                valid_indices.append(index)

        if not valid_indices:
            return

        # Find current position in valid indices
        current_row = data_table.cursor_row
        try:
            current_valid_index = valid_indices.index(current_row)
        except ValueError:
            # Current row is not valid (shouldn't happen), move to first valid
            data_table.move_cursor(row=valid_indices[0])
            return

        # Move to next/previous valid index with wrapping
        if move_down:
            next_valid_index = (current_valid_index + 1) % len(valid_indices)
        else:
            next_valid_index = (current_valid_index - 1) % len(valid_indices)

        # Move cursor to the target row
        target_row_index = valid_indices[next_valid_index]
        data_table.move_cursor(row=target_row_index)

    def _move_cursor_to_first_valid_row(self) -> None:
        """Move cursor to the first valid (non-header, non-separator) row."""
        data_table = self.query_one("#data-table", DataTable)
        row_keys = list(data_table.rows.keys())

        if not row_keys:
            return

        # Find first valid row
        for index, row_key in enumerate(row_keys):
            if not str(row_key.value).startswith(("layer-header-", "separator-")):
                # Move cursor to this row
                data_table.move_cursor(row=index)
                return

    def _update_table_height(self) -> None:
        """Update table height based on number of rows."""
        data_table = self.query_one("#data-table", DataTable)
        row_count = len(data_table.rows)

        if row_count == 0:
            # No rows, minimal height
            self.styles.height = 3
            return

        # Calculate height needed
        # Each row is approximately 1 line, plus header if shown
        header_height = 2 if self.show_column_headers else 0

        # Maximum rows to show before scrolling (configurable)
        max_visible_rows = 10

        # Calculate total height: header + min(rows, max) + border/padding
        visible_rows = min(row_count, max_visible_rows)
        total_height = header_height + visible_rows + 2  # +2 for borders

        self.styles.height = total_height

    def _toggle_row_selection(self, row_key: RowKey) -> None:
        """Toggle selection state of a row."""
        if row_key in self._selected_rows:
            self._selected_rows.remove(row_key)
            selected = False
        else:
            self._selected_rows.add(row_key)
            selected = True

        # Update checkbox
        self._update_checkbox(row_key)

        # Post toggle message
        if row_key in self._row_map:
            row = self._row_map[row_key]
            self.post_message(self.RowToggled(row, row_key, selected))

    def get_selected_rows(self) -> list[TableRow]:
        """
        Get currently selected rows.

        Returns:
            - "multi" mode: All toggled rows
            - "radio" mode: The row with the ● indicator
            - "single"/"none" mode: The currently highlighted row
        """
        if self.select_mode == "multi":
            return [self._row_map[key] for key in self._selected_rows if key in self._row_map]
        elif self.select_mode == "radio":
            # Radio mode: return the selected row (the one with ●)
            if self._selected_row and self._selected_row in self._row_map:
                return [self._row_map[self._selected_row]]
            return []
        else:  # single or none mode
            # Return highlighted row
            data_table = self.query_one("#data-table", DataTable)
            if data_table.cursor_row is not None:
                row_keys = list(data_table.rows.keys())
                if data_table.cursor_row < len(row_keys):
                    row_key = row_keys[data_table.cursor_row]
                    if row_key in self._row_map:
                        return [self._row_map[row_key]]
            return []

    def add_row(self, row: TableRow) -> None:
        """Add a new row to the table."""
        self.rows = self.rows + [row]

    def add_column(self, column_name: str) -> None:
        """Add a new column to the table."""
        self.columns = self.columns + [column_name]

    def update_cell(self, row: TableRow, column: str, value: Any) -> None:
        """Update a cell value."""
        # Update the row data
        row.values[column] = value

        # Update the table display
        data_table = self.query_one("#data-table", DataTable)
        for row_key, mapped_row in self._row_map.items():
            if mapped_row is row:
                data_table.update_cell(row_key, column, value)
                break

    def set_rows(self, new_rows: list[TableRow]) -> None:
        """
        Replace all rows with new rows, preserving selection state and cursor position.

        Cursor position is automatically restored by tracking in _cursor_row_key.
        This method focuses on restoring selection state.
        """
        # Get currently selected row keys (using row_key field)
        selected_keys = set()
        if self.select_mode == "multi":
            for row_key in self._selected_rows:
                if row_key in self._row_map:
                    table_row = self._row_map[row_key]
                    if table_row.row_key and isinstance(table_row.row_key, str):
                        selected_keys.add(table_row.row_key)
        elif self.select_mode == "radio":
            if self._selected_row and self._selected_row in self._row_map:
                table_row = self._row_map[self._selected_row]
                if table_row.row_key and isinstance(table_row.row_key, str):
                    selected_keys.add(table_row.row_key)

        # Update rows (this will trigger rebuild via watch_rows)
        # Cursor position will be automatically restored by _rebuild_table()
        self.rows = new_rows

        # Restore selection after rebuild completes
        def restore_selection():
            if selected_keys:
                for dt_row_key, table_row in self._row_map.items():
                    if table_row.row_key and table_row.row_key in selected_keys:
                        if self.select_mode == "multi":
                            self._selected_rows.add(dt_row_key)
                            self._update_checkbox(dt_row_key)
                        elif self.select_mode == "radio":
                            self._selected_row = dt_row_key
                            self._update_checkbox(dt_row_key)

        self.call_after_refresh(restore_selection)

    @property
    def _rows(self) -> list[TableRow]:
        """Access to internal rows for layer selection logic."""
        return self.rows

    def select_rows_by_layer(self, layer: str) -> None:
        """
        Select all rows in a specific layer and deselect all others.
        Only works in multi or radio select modes.
        """
        if self.select_mode not in ("multi", "radio"):
            return

        # Clear existing selections
        if self.select_mode == "multi":
            old_selected = list(self._selected_rows)
            self._selected_rows.clear()
        else:
            old_selected = [self._selected_row] if self._selected_row else []
            self._selected_row = None

        # Select rows in the specified layer
        first_in_layer = None
        for row_key, table_row in self._row_map.items():
            if table_row.layer == layer:
                if self.select_mode == "multi":
                    self._selected_rows.add(row_key)
                elif self.select_mode == "radio" and first_in_layer is None:
                    # Radio mode: select only the first row in layer
                    first_in_layer = row_key
                    self._selected_row = row_key

        # Update checkboxes for all affected rows
        affected_keys = set(old_selected)
        if self.select_mode == "multi":
            affected_keys.update(self._selected_rows)
        elif first_in_layer:
            affected_keys.add(first_in_layer)

        for row_key in affected_keys:
            if row_key in self._row_map:
                self._update_checkbox(row_key)

    def toggle_rows_by_layer(self, layer: str) -> None:
        """
        Toggle selection of all rows in a specific layer without affecting other layers.
        If all rows in the layer are selected, deselect them.
        If any row in the layer is unselected, select all rows in the layer.
        Only works in multi select mode.
        """
        if self.select_mode != "multi":
            return

        # Find all rows in this layer
        layer_rows = [row_key for row_key, table_row in self._row_map.items()
                     if table_row.layer == layer]

        if not layer_rows:
            return

        # Check if all rows in layer are selected
        all_selected = all(row_key in self._selected_rows for row_key in layer_rows)

        # Toggle: if all selected, deselect; otherwise select all
        if all_selected:
            # Deselect all in layer
            for row_key in layer_rows:
                self._selected_rows.discard(row_key)
        else:
            # Select all in layer
            for row_key in layer_rows:
                self._selected_rows.add(row_key)

        # Update checkboxes for all affected rows
        for row_key in layer_rows:
            self._update_checkbox(row_key)

    def toggle_all_rows(self) -> None:
        """
        Toggle selection of all rows.
        If all rows are selected, deselect all.
        If any row is unselected, select all.
        Only works in multi select mode.
        """
        if self.select_mode != "multi":
            return

        # Get all non-header row keys
        all_rows = [row_key for row_key in self._row_map.keys()]

        if not all_rows:
            return

        # Check if all rows are selected
        all_selected = all(row_key in self._selected_rows for row_key in all_rows)

        # Toggle: if all selected, deselect; otherwise select all
        if all_selected:
            self._selected_rows.clear()
        else:
            self._selected_rows.update(all_rows)

        # Update checkboxes for all rows
        for row_key in all_rows:
            self._update_checkbox(row_key)

    def get_cursor_layer(self) -> Optional[str]:
        """Get the layer of the currently highlighted row."""
        data_table = self.query_one("#data-table", DataTable)
        if data_table.cursor_row is None:
            return None

        row_keys = list(data_table.rows.keys())
        if data_table.cursor_row >= len(row_keys):
            return None

        row_key = row_keys[data_table.cursor_row]
        if row_key in self._row_map:
            return self._row_map[row_key].layer

        return None
