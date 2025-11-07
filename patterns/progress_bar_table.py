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

from utilities.layered_data_table import LayeredDataTable, TableRow


class ProgressBarTableScreen(Screen):
    """Screen demonstrating progress bar effect in a data table."""

    BINDINGS = [
        Binding("q", "request_quit", "Quit", show=True),
        Binding("r", "randomize_progress", "Randomize", show=True),
        Binding("up", "increment_progress", "Progress +", show=True),
        Binding("down", "decrement_progress", "Progress -", show=True),
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
        self.columns = ["Issue", "Status", "Owner", "Priority"]

        # Sample data with stage-based progress
        # Progress is a list where:
        #   - Integer (1, 2, 3, 4) = fill that column (1-indexed)
        #   - Decimal (1.5, 2.5, 3.5) = fill gap AFTER that column
        # Example: [1, 2.5, 3] = fill col 1, gap between 2-3, and col 3
        self.rows_data = [
            {"Issue": "AUTH-123", "Status": "In Progress", "Owner": "Alice", "Priority": "High",
             "progress": [1, 2]},  # Col 1 and 2, but NOT gap between (no 1.5)!
            {"Issue": "AUTH-124", "Status": "Review", "Owner": "Bob", "Priority": "Medium",
             "progress": [1, 1.5, 2]},  # Col 1 + gap + col 2 (continuous)
            {"Issue": "API-456", "Status": "Done", "Owner": "Charlie", "Priority": "Low",
             "progress": [1, 1.5, 2, 2.5, 3, 3.5, 4]},  # All columns and gaps
            {"Issue": "API-457", "Status": "Todo", "Owner": "Diana", "Priority": "High",
             "progress": []},  # Nothing filled
            {"Issue": "WEB-789", "Status": "In Progress", "Owner": "Eve", "Priority": "Medium",
             "progress": [1, 2.5, 3]},  # Col 1, gap 2-3, col 3 (skips col 2 and gap 1-2!)
            {"Issue": "WEB-790", "Status": "Testing", "Owner": "Frank", "Priority": "High",
             "progress": [1.5, 2, 2.5]},  # Gap 1-2, col 2, gap 2-3 (skips col 1!)
        ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical():
            yield Static("Progress Bar Table Demo", id="title")
            yield Static(
                "Stage-based progress: ↑ adds next stage, ↓ removes last stage, 'r' randomizes, 'q' quits",
                id="info"
            )
            yield LayeredDataTable(
                id="progress-table",
                columns=self.columns,
                rows=[],  # Will be populated in on_mount
                show_layers=False,
                show_column_headers=True,
                select_mode="single",
                cursor_type="row",
                auto_height=False,
            )

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the table with progress bars."""
        self.sub_title = "Continuous Progress Bar Effect"

        # Set cell_padding=0 on the inner DataTable to remove gaps between columns
        table = self.query_one("#progress-table", LayeredDataTable)
        inner_table = table.query_one("#data-table")
        inner_table.cell_padding = 0

        self._rebuild_table()

    def _rebuild_table(self) -> None:
        """Rebuild table with progress bar styling."""
        table = self.query_one("#progress-table", LayeredDataTable)

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

        # Set rows
        table.set_rows(styled_rows)

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
        - progress is a list of stages to fill
        - Integers (1, 2, 3, 4) = fill that column (1-indexed)
        - Decimals (1.5, 2.5, 3.5) = fill gap AFTER that column
        - Non-contiguous segments are supported!

        Args:
            row_data: Row data dictionary
            progress: List of stages to fill (e.g., [1, 1.5, 2, 2.5, 3])
            col_widths: Dictionary of column_name -> width (dynamically calculated)

        Examples:
        - [1] = fill only column 1
        - [1, 1.5, 2] = fill column 1, gap after it, and column 2
        - [1, 2.5, 3] = fill column 1, gap between 2-3, and column 3 (skips col 2!)
        - [1, 1.5, 2, 2.5, 3, 3.5, 4] = fill all columns and all gaps
        """
        values = {}

        # Gap width (space between columns)
        GAP_WIDTH = 2

        for col_index, col in enumerate(self.columns):
            # Use dynamically calculated width
            col_width = col_widths[col]
            col_number = col_index + 1  # 1-indexed
            gap_marker = col_number + 0.5  # e.g., 1.5 for gap after column 1

            # Get the raw value
            raw_value = str(row_data[col])

            # Check if this column should be filled
            fill_column = col_number in progress
            # Check if gap after this column should be filled
            fill_gap = gap_marker in progress
            # Is this the last column?
            is_last_column = col_index == len(self.columns) - 1

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

        return TableRow(values=values, row_key=row_data["Issue"])

    def _update_highlighted_row_progress(self, increment: bool) -> None:
        """
        Update progress of the currently highlighted row.

        increment: True to add next stage, False to remove last stage
        """
        table = self.query_one("#progress-table", LayeredDataTable)
        selected_rows = table.get_selected_rows()

        if not selected_rows:
            return

        selected_row = selected_rows[0]
        row_key = selected_row.row_key

        # All possible stages in order
        num_cols = len(self.columns)
        all_stages = []
        for i in range(1, num_cols + 1):
            all_stages.append(i)        # Column
            if i < num_cols:            # Don't add gap after last column
                all_stages.append(i + 0.5)  # Gap

        # Find the row data
        for row_data in self.rows_data:
            if row_data["Issue"] == row_key:
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

        num_cols = len(self.columns)
        all_stages = []
        for i in range(1, num_cols + 1):
            all_stages.append(i)
            if i < num_cols:
                all_stages.append(i + 0.5)

        for row_data in self.rows_data:
            # Randomly select a subset of stages
            num_stages = random.randint(0, len(all_stages))
            selected_stages = sorted(random.sample(all_stages, num_stages))
            row_data["progress"] = selected_stages

        self._rebuild_table()
        self.notify("Progress values randomized!")

    def action_request_quit(self) -> None:
        """Quit the application."""
        self.app.exit()


class ProgressBarTableApp(App):
    """
    Application demonstrating stage-based progress bar effect in DataTable.

    This pattern shows:
    - Stage-based progress using list notation [1, 1.5, 2, 2.5, 3]
    - Integers (1, 2, 3) = fill columns
    - Decimals (1.5, 2.5) = fill gaps between columns
    - Non-contiguous segments supported (e.g., [1, 2.5, 3] skips column 2)
    - Using cell_padding=0 to remove default gaps
    - Rich Text for selective styling of columns and gaps

    Key insights from Textual docs research:
    1. DataTable cells accept Rich renderables (Text objects)
    2. cell_padding controls horizontal spacing between cells
    3. Setting cell_padding=0 removes gaps between columns
    4. We manually add trailing spaces to create controllable gaps
    5. Gap filling is achieved by styling trailing spaces
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
