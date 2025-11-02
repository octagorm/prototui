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
from textual.widgets import DataTable
from textual.widgets.data_table import RowKey


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

    BINDINGS = [
        Binding("space", "toggle_selection", "Toggle", show=False),
    ]

    columns: reactive[list[str]] = reactive(list, init=False)
    rows: reactive[list[TableRow]] = reactive(list, init=False)
    show_layers: reactive[bool] = reactive(True)
    show_column_headers: reactive[bool] = reactive(True)
    select_mode: reactive[str] = reactive("single")
    auto_height: reactive[bool] = reactive(False)

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
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.columns = columns or []
        self.rows = rows or []
        self.show_layers = show_layers
        self.show_column_headers = show_column_headers
        self.auto_height = auto_height

        # Backward compatibility: multi_select=True maps to select_mode="multi"
        if multi_select is not None:
            self.select_mode = "multi" if multi_select else "single"
        else:
            self.select_mode = select_mode

        self._cursor_type = cursor_type
        self._selected_rows: set[RowKey] = set()  # Track selected rows in multi mode
        self._selected_row: Optional[RowKey] = None  # Track selected row in radio mode
        self._row_map: dict[RowKey, TableRow] = {}  # Map DataTable RowKey to TableRow

    def compose(self) -> ComposeResult:
        """Compose the data table."""
        yield DataTable(
            cursor_type=self._cursor_type,
            show_header=self.show_column_headers,
            id="data-table"
        )

    def on_mount(self) -> None:
        """Initialize the table when mounted."""
        self._rebuild_table()
        # Hide cursor initially until focused
        data_table = self.query_one("#data-table", DataTable)
        data_table.show_cursor = False

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

        # Move cursor to first valid (non-header, non-separator) row
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
            self.post_message(self.RowHighlighted(row, event.row_key))
        else:
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

    def on_key(self, event) -> None:
        """Handle key presses."""
        from textual.events import Key

        if not isinstance(event, Key):
            return

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
        Replace all rows with new rows, preserving selection state.

        This is more efficient than setting self.rows directly when you want
        to preserve which rows are selected across updates.
        """
        # Get currently selected row keys (using row_key field)
        selected_keys = set()
        if self.select_mode == "multi":
            for row_key in self._selected_rows:
                if row_key in self._row_map:
                    table_row = self._row_map[row_key]
                    if table_row.row_key:
                        selected_keys.add(table_row.row_key)
        elif self.select_mode == "radio":
            if self._selected_row and self._selected_row in self._row_map:
                table_row = self._row_map[self._selected_row]
                if table_row.row_key:
                    selected_keys.add(table_row.row_key)

        # Update rows (this will trigger rebuild)
        self.rows = new_rows

        # Restore selection based on row_key
        if selected_keys:
            data_table = self.query_one("#data-table", DataTable)
            for row_key, table_row in self._row_map.items():
                if table_row.row_key in selected_keys:
                    if self.select_mode == "multi":
                        self._selected_rows.add(row_key)
                        self._update_checkbox(row_key)
                    elif self.select_mode == "radio":
                        self._selected_row = row_key
                        self._update_checkbox(row_key)

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
