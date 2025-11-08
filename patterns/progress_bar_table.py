"""
Pattern: Progress Bar Table

Demonstrates how to create a visual "progress bar" effect that stretches
continuously over multiple columns in a DataTable.

Use this when:
- Showing task/issue progress across a table
- Visualizing completion status with a continuous bar
- Need a progress indicator that spans multiple columns

Solution:
- Uses cell_padding=0 to remove gaps between columns
- Applies Rich Text reverse styling for progress effect
- Calculates which columns should be highlighted based on progress value

Run: python patterns/progress_bar_table.py
"""

# Add parent directory to path to import utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static
from textual.containers import Vertical
from textual.binding import Binding
from rich.text import Text
from textual.widgets.data_table import RowKey

from utilities.layered_data_table import LayeredDataTable, TableRow


class ProgressBarDataTable(LayeredDataTable):
    """
    Extended LayeredDataTable with padded checkboxes for progress bar pattern.

    This subclass overrides checkbox update behavior to add padding (2 spaces on each side)
    without modifying the base LayeredDataTable class.
    """

    def _update_checkbox(self, row_key: RowKey) -> None:
        """Override to add padding to checkboxes."""
        if self.select_mode not in ("radio", "multi"):
            return

        data_table = self.query_one("#data-table")

        if self.select_mode == "radio":
            # Radio mode: show ● only for selected row, empty for others
            checkbox = "●" if row_key == self._selected_row else ""
        else:  # multi mode
            # Multi mode: show ○/● for all rows
            checkbox = "●" if row_key in self._selected_rows else "○"

        # Add padding: 2 spaces before and after
        padded_checkbox = f"  {checkbox}  " if checkbox else "    "

        data_table.update_cell(row_key, "checkbox", padded_checkbox)
        data_table.refresh()


class ProgressBarTableScreen(Screen):
    """Screen demonstrating progress bar effect in a data table."""

    BINDINGS = [
        Binding("q", "request_quit", "Quit", show=True),
        Binding("r", "randomize_progress", "Randomize", show=True),
        Binding("up", "increment_progress", "Progress +", show=True),
        Binding("down", "decrement_progress", "Progress -", show=True),
        Binding("space", "toggle_selection", "Toggle", show=True),
    ]

    DEFAULT_CSS = """
    ProgressBarTableScreen {
        align: center middle;
    }

    #title {
        width: 100%;
        height: auto;
        padding: 1 2;
        text-align: center;
        text-style: bold;
        background: $panel;
    }

    #info {
        width: 100%;
        height: auto;
        padding: 1 2;
        text-align: center;
        color: $text-muted;
    }

    #progress-table {
        width: 100%;
        height: 1fr;
        margin: 1 2;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress_data = {}  # row_key -> progress value (0.0 to 1.0)

        # Define columns: pre-progress + progress columns
        # Pre-progress columns are regular columns (not part of stage-based progress)
        self.pre_progress_columns = ["ID", "Type"]
        self.progress_columns = ["Issue", "Status", "Owner", "Priority"]
        self.columns = self.pre_progress_columns + self.progress_columns

        # Sample data with stage-based progress
        # Progress is a list where:
        #   - Integer (1, 2, 3, 4) = fill that PROGRESS column (1-indexed within progress_columns)
        #   - Decimal (1.5, 2.5, 3.5) = fill gap AFTER that progress column
        # Example: [1, 2.5, 3] = fill col 1, gap between 2-3, and col 3
        self.rows_data = [
            {"ID": "1", "Type": "Bug", "Issue": "AUTH-123", "Status": "In Progress",
             "Owner": "Alice", "Priority": "High",
             "progress": [1, 2], "row_key": "row-1"},  # Col 1 and 2, but NOT gap between (no 1.5)!
            {"ID": "2", "Type": "Feature", "Issue": "AUTH-124", "Status": "Review",
             "Owner": "Bob", "Priority": "Medium",
             "progress": [1, 1.5, 2], "row_key": "row-2"},  # Col 1 + gap + col 2 (continuous)
            {"ID": "3", "Type": "Bug", "Issue": "API-456", "Status": "Done",
             "Owner": "Charlie", "Priority": "Low",
             "progress": [1, 1.5, 2, 2.5, 3, 3.5, 4], "row_key": "row-3"},  # All columns and gaps
            {"ID": "4", "Type": "Task", "Issue": "API-457", "Status": "Todo",
             "Owner": "Diana", "Priority": "High",
             "progress": [], "row_key": "row-4"},  # Nothing filled
            {"ID": "5", "Type": "Feature", "Issue": "WEB-789", "Status": "In Progress",
             "Owner": "Eve", "Priority": "Medium",
             "progress": [1, 2.5, 3], "row_key": "row-5"},  # Col 1, gap 2-3, col 3 (skips col 2 and gap 1-2!)
            {"ID": "6", "Type": "Bug", "Issue": "WEB-790", "Status": "Testing",
             "Owner": "Frank", "Priority": "High",
             "progress": [1.5, 2, 2.5], "row_key": "row-6"},  # Gap 1-2, col 2, gap 2-3 (skips col 1!)
        ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical():
            yield Static("Progress Bar Table Demo", id="title")
            yield Static(
                "Multi-select table: Space to toggle, ↑/↓ adjust progress, 'r' randomizes, 'q' quits",
                id="info"
            )
            yield ProgressBarDataTable(
                id="progress-table",
                columns=self.columns,
                rows=[],  # Will be populated in on_mount
                show_layers=False,
                show_column_headers=True,
                select_mode="multi",  # Multi-select mode
                cursor_type="row",
                auto_height=False,
            )

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the table with progress bars."""
        self.sub_title = "Continuous Progress Bar Effect"

        # Set cell_padding=0 on the inner DataTable to remove gaps between columns
        table = self.query_one("#progress-table", ProgressBarDataTable)
        inner_table = table.query_one("#data-table")
        inner_table.cell_padding = 0

        self._rebuild_table()

        # After table is built, set checkbox column width
        def adjust_checkbox_column():
            try:
                # Set checkbox column width to 5 (for "  ○  " spacing)
                for column in inner_table.columns.values():
                    if column.key == "checkbox":
                        column.width = 5
                        break
                inner_table.refresh()
            except Exception:
                pass

        self.call_after_refresh(adjust_checkbox_column)

    def _rebuild_table(self) -> None:
        """Rebuild table with progress bar styling."""
        table = self.query_one("#progress-table", ProgressBarDataTable)

        # Calculate dynamic column widths based on content
        col_widths = self._calculate_dynamic_widths()

        # Create styled rows
        styled_rows = []
        for row_data in self.rows_data:
            progress = row_data["progress"]
            row_key = row_data["Issue"]

            # Store progress value
            self.progress_data[row_key] = progress

            # Create styled row based on progress (pass calculated widths)
            styled_row = self._create_progress_row(row_data, progress, col_widths)
            styled_rows.append(styled_row)

        # Set rows (checkboxes will be padded automatically by ProgressBarDataTable._update_checkbox)
        table.set_rows(styled_rows)

        # Ensure checkbox column has proper width after rebuild
        def adjust_checkbox_width():
            try:
                inner_table = table.query_one("#data-table")
                for column in inner_table.columns.values():
                    if column.key == "checkbox":
                        column.width = 5
                        inner_table.refresh()
                        break
            except Exception:
                pass

        self.call_after_refresh(adjust_checkbox_width)

    def _calculate_dynamic_widths(self) -> dict[str, int]:
        """
        Calculate column widths dynamically based on actual content.

        Returns dictionary of column_name -> width (in characters).
        """
        widths = {}

        for col in self.columns:
            # Start with header width
            max_width = len(col)

            # Check all row values for this column
            for row_data in self.rows_data:
                value = str(row_data.get(col, ""))
                max_width = max(max_width, len(value))

            # No extra padding - tight fit to content
            widths[col] = max_width

        return widths

    def _create_progress_row(self, row_data: dict, progress: list, col_widths: dict[str, int]) -> TableRow:
        """
        Create a TableRow with stage-based progress bar styling.

        STAGE-BASED approach using list notation:
        - progress is a list of stages to fill (applies ONLY to progress_columns)
        - Integers (1, 2, 3, 4) = fill that PROGRESS column (1-indexed within progress_columns)
        - Decimals (1.5, 2.5, 3.5) = fill gap AFTER that PROGRESS column
        - Pre-progress columns (ID, Type) always have normal gaps
        - Non-contiguous segments are supported!

        Args:
            row_data: Row data dictionary
            progress: List of stages to fill (e.g., [1, 1.5, 2, 2.5, 3])
            col_widths: Dictionary of column_name -> width (dynamically calculated)

        Examples:
        - [1] = fill only first progress column (Issue)
        - [1, 1.5, 2] = fill Issue, gap after it, and Status
        - [1, 2.5, 3] = fill Issue, gap between Status-Owner, and Owner (skips Status!)
        - [1, 1.5, 2, 2.5, 3, 3.5, 4] = fill all progress columns and all gaps
        """
        values = {}

        # Gap width (space between columns)
        GAP_WIDTH = 2

        for col_index, col in enumerate(self.columns):
            # Use dynamically calculated width
            col_width = col_widths[col]
            is_last_column = col_index == len(self.columns) - 1

            # Get the raw value
            raw_value = str(row_data.get(col, ""))

            # Check if this is a pre-progress column or progress column
            if col in self.pre_progress_columns:
                # Pre-progress columns: always normal styling with normal gap
                text = Text()
                padded_value = raw_value.ljust(col_width)
                text.append(padded_value)
                if not is_last_column:
                    text.append(" " * GAP_WIDTH)
                values[col] = text

            elif col in self.progress_columns:
                # Progress columns: apply stage-based styling
                # Find position within progress_columns (1-indexed)
                progress_col_index = self.progress_columns.index(col)
                col_number = progress_col_index + 1  # 1-indexed
                gap_marker = col_number + 0.5  # e.g., 1.5 for gap after column 1

                # Check if this column should be filled
                fill_column = col_number in progress
                # Check if gap after this column should be filled
                fill_gap = gap_marker in progress

                # Build the text with proper styling
                text = Text()
                padded_value = raw_value.ljust(col_width)

                if fill_column and fill_gap:
                    # Fill column + gap
                    text.append(padded_value, style="reverse")
                    if not is_last_column:
                        text.append(" " * GAP_WIDTH, style="reverse")
                    values[col] = text

                elif fill_column and not fill_gap:
                    # Fill column only, gap is NOT styled
                    text.append(padded_value, style="reverse")
                    if not is_last_column:
                        text.append(" " * GAP_WIDTH)  # Normal style (no reverse)
                    values[col] = text

                elif not fill_column and fill_gap:
                    # Column is NOT filled, but gap IS styled
                    text.append(padded_value)  # Normal style
                    if not is_last_column:
                        text.append(" " * GAP_WIDTH, style="reverse")
                    values[col] = text

                else:
                    # Neither column nor gap is filled
                    text.append(padded_value)
                    if not is_last_column:
                        text.append(" " * GAP_WIDTH)
                    values[col] = text

        return TableRow(values=values, row_key=row_data.get("row_key", row_data.get("Issue", f"row-{id(row_data)}")))

    def _update_highlighted_row_progress(self, increment: bool) -> None:
        """
        Update progress of the currently highlighted row.

        increment: True to add next stage, False to remove last stage
        """
        table = self.query_one("#progress-table", ProgressBarDataTable)
        selected_rows = table.get_selected_rows()

        if not selected_rows:
            return

        selected_row = selected_rows[0]
        row_key = selected_row.row_key

        # All possible stages in order (based on progress_columns, not all columns)
        num_progress_cols = len(self.progress_columns)
        all_stages = []
        for i in range(1, num_progress_cols + 1):
            all_stages.append(i)        # Column
            if i < num_progress_cols:   # Don't add gap after last column
                all_stages.append(i + 0.5)  # Gap

        # Find the row data
        for row_data in self.rows_data:
            if row_data.get("row_key") == row_key:
                current_progress = row_data["progress"]

                if increment:
                    # Add next stage that's not already in progress
                    for stage in all_stages:
                        if stage not in current_progress:
                            current_progress.append(stage)
                            self.notify(f"{row_key}: Added stage {stage}")
                            break
                    else:
                        self.notify(f"{row_key}: Already at max progress")
                else:
                    # Remove last stage in chronological order
                    if current_progress:
                        # Find the last stage in chronological order
                        last_stage = max(current_progress)
                        current_progress.remove(last_stage)
                        self.notify(f"{row_key}: Removed stage {last_stage}")
                    else:
                        self.notify(f"{row_key}: Already at zero progress")

                # Rebuild table
                self._rebuild_table()
                break

    def action_increment_progress(self) -> None:
        """Add next stage to progress."""
        self._update_highlighted_row_progress(increment=True)

    def action_decrement_progress(self) -> None:
        """Remove last stage from progress."""
        self._update_highlighted_row_progress(increment=False)

    def action_randomize_progress(self) -> None:
        """Randomize all progress values."""
        import random

        num_progress_cols = len(self.progress_columns)
        all_stages = []
        for i in range(1, num_progress_cols + 1):
            all_stages.append(i)
            if i < num_progress_cols:
                all_stages.append(i + 0.5)

        for row_data in self.rows_data:
            # Randomly select a subset of stages
            num_stages = random.randint(0, len(all_stages))
            selected_stages = sorted(random.sample(all_stages, num_stages))
            row_data["progress"] = selected_stages

        self._rebuild_table()
        self.notify("Progress values randomized!")

    def action_toggle_selection(self) -> None:
        """Toggle selection of current row (Space key)."""
        table = self.query_one("#progress-table", ProgressBarDataTable)
        table.action_toggle_selection()

    def action_request_quit(self) -> None:
        """Quit the application."""
        self.app.exit()


class ProgressBarTableApp(App):
    """
    Application demonstrating stage-based progress bar effect in multi-select DataTable.

    This pattern shows:
    - Multi-select table with checkbox column
    - Pre-progress columns (ID, Type) with normal gaps
    - Progress columns (Issue, Status, Owner, Priority) with stage-based styling
    - Stage-based progress using list notation [1, 1.5, 2, 2.5, 3]
      - Integers (1, 2, 3, 4) = fill PROGRESS columns (not all columns!)
      - Decimals (1.5, 2.5, 3.5) = fill gaps between PROGRESS columns
    - Non-contiguous segments supported (e.g., [1, 2.5, 3] skips column 2)
    - Using cell_padding=0 to remove default gaps
    - Rich Text for selective styling of columns and gaps
    - GAP_WIDTH = 2 for visible gaps

    Key insights from Textual docs research:
    1. DataTable cells accept Rich renderables (Text objects)
    2. cell_padding controls horizontal spacing between cells
    3. Setting cell_padding=0 removes gaps between columns
    4. We manually add trailing spaces to create controllable gaps
    5. Gap filling is achieved by styling trailing spaces
    6. Multi-select adds a checkbox column automatically
    7. Progress numbering applies only to progress_columns, not all columns
    """

    CSS = """
    Screen {
        background: $surface;
    }
    """

    def on_mount(self) -> None:
        """Push the main screen."""
        self.push_screen(ProgressBarTableScreen())


if __name__ == "__main__":
    from utilities.terminal_compat import run_app

    app = ProgressBarTableApp()
    run_app(app)  # Handles colors + IntelliJ mouse issues
