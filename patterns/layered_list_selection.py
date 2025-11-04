"""
Pattern: Layered List Selection with Explanation Panel

Use this when selecting ONE item from a grouped/layered list.

Example use cases:
- Services grouped by environment (prod/staging/dev)
- Repositories grouped by team or architecture layer
- Resources organized by category

Features:
- Two-pane layout (list + explanation panel)
- Layered/grouped data with headers
- Cursor automatically skips headers
- Rich help text in side panel

Run: python patterns/layered_list_selection.py
"""

# Add parent directory to path to import utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.binding import Binding

# Import utility for layered table handling
from utilities.layered_data_table import LayeredDataTable, TableRow


class ConfirmQuitScreen(Screen):
    """Confirmation screen for quitting."""

    BINDINGS = [
        Binding("y", "confirm_quit", "Yes", show=True),
        Binding("n", "cancel_quit", "No", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.notify("Are you sure you want to quit? (y/n)", severity="warning")

    def action_confirm_quit(self) -> None:
        self.app.exit()

    def action_cancel_quit(self) -> None:
        self.app.pop_screen()


class ExplanationPanel(Static):
    """Side panel showing help/explanation text."""

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


class LayeredSelectionScreen(Screen):
    """Screen with layered data table and explanation panel."""

    BINDINGS = [
        Binding("enter", "select_item", "Submit", show=True, priority=True),
        Binding("q", "request_quit", "Quit", show=True),
        Binding("escape", "cancel_review", "Back", show=False),
    ]

    def __init__(
        self,
        items: list[dict],
        columns: list[str],
        title: str = "Select Item",
        explanation_title: str = "Help",
        explanation_content: str = ""
    ):
        """
        Initialize layered selection screen.

        Args:
            items: List of TableRow objects with data and optional layer
            columns: Column names for the table
            title: Screen title
            explanation_title: Title for explanation panel
            explanation_content: Content for explanation panel
        """
        super().__init__()
        self.items = items
        self.columns = columns
        self.screen_title = title
        self.explanation_title = explanation_title
        self.explanation_content = explanation_content
        self._review_mode = False
        self._selected_item = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main-container"):
            # Left side: Layered data table
            with Vertical(id="content-pane"):
                yield LayeredDataTable(
                    id="data-table",
                    columns=self.columns,
                    rows=self.items,
                    select_mode="single",  # Single selection, no visual indicator
                    show_layers=True,
                    filterable=True  # Enable filter with / key
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

        # Make explanation pane non-focusable
        explanation_pane = self.query_one("#explanation-pane")
        explanation_pane.can_focus = False

    def on_layered_data_table_row_selected(self, event: LayeredDataTable.RowSelected) -> None:
        """Handle row selection with Enter key."""
        self.action_select_item()

    def action_select_item(self) -> None:
        """Select the current item (triggered by Enter binding)."""
        # If in review mode, second Enter confirms
        if self._review_mode:
            self.dismiss(self._selected_item)
            return

        # Get the selected row
        table = self.query_one(LayeredDataTable)
        selected_rows = table.get_selected_rows()

        if selected_rows:
            self._selected_item = selected_rows[0]
            self._show_review()
            self._review_mode = True

    def _show_review(self) -> None:
        """Show selected item in explanation panel."""
        panel = self.query_one(ExplanationPanel)

        # Get primary identifier (first column)
        first_col = self.columns[0]
        identifier = self._selected_item.values.get(first_col, "Unknown")

        # Build review content
        review_content = f"Selected: {identifier}"
        if self._selected_item.layer:
            review_content += f"\nFrom: {self._selected_item.layer}"

        panel.update_content(
            "Review Your Selection",
            f"{review_content}\n\nPress Enter to confirm, or ESC to go back and change."
        )

        self.sub_title = f"{self.screen_title} - Review"
        self.notify("Review your selection and press Enter to confirm", severity="information")

    def action_cancel_review(self) -> None:
        """Cancel review mode and return to selection."""
        if self._review_mode:
            self._review_mode = False
            self.sub_title = self.screen_title
            panel = self.query_one(ExplanationPanel)
            panel.update_content(self.explanation_title, self.explanation_content)
            self.notify("Returned to selection", severity="information")

    def action_request_quit(self) -> None:
        self.app.push_screen(ConfirmQuitScreen())


class LayeredListSelectionApp(App):
    """
    Application demonstrating layered list selection.

    This pattern shows:
    - Two-pane layout (table + explanation)
    - Layered/grouped data with visual headers
    - Cursor automatically skips headers (handled by LayeredDataTable)
    - Arrow key navigation
    - Enter to select
    """

    CSS = """
    #main-container {
        width: 100%;
        height: 100%;
    }

    #content-pane {
        width: 2fr;
        height: 100%;
    }

    LayeredDataTable {
        height: 100%;
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

    def on_mount(self) -> None:
        # Sample data with layers - now using TableRow
        rows = [
            TableRow(
                {"Repository": "auth-service", "Changes": "Yes", "Status": "Modified"},
                layer="Core Services"
            ),
            TableRow(
                {"Repository": "config-service", "Changes": "No", "Status": "Clean"},
                layer="Core Services"
            ),
            TableRow(
                {"Repository": "api-gateway", "Changes": "Yes", "Status": "Modified"},
                layer="API Layer"
            ),
            TableRow(
                {"Repository": "user-service", "Changes": "Yes", "Status": "Modified"},
                layer="API Layer"
            ),
            TableRow(
                {"Repository": "notification-service", "Changes": "No", "Status": "Clean"},
                layer="API Layer"
            ),
            TableRow(
                {"Repository": "web-app", "Changes": "Yes", "Status": "Modified"},
                layer="Frontend"
            ),
            TableRow(
                {"Repository": "admin-dashboard", "Changes": "No", "Status": "Clean"},
                layer="Frontend"
            ),
        ]

        screen = LayeredSelectionScreen(
            items=rows,
            columns=["Repository", "Changes", "Status"],
            title="Repository Management",
            explanation_title="Select Repository",
            explanation_content=(
                "Choose a repository to work with from the list on the left.\n\n"
                "Repositories are organized by architectural layer (Core Services, API Layer, Frontend). "
                "Use the arrow keys to navigate between repositories. "
                "The cursor automatically skips group headers.\n\n"
                "Press '/' to filter repositories by name, changes, or status. "
                "Use Tab or arrow keys to move to the results, ESC to clear.\n\n"
                "Press Enter to select a repository. You'll be able to review your selection "
                "before confirming.\n\n"
                "Press 'q' to quit."
            )
        )

        self.push_screen(screen, self.handle_selection)

    def handle_selection(self, selected_row: TableRow | None) -> None:
        if selected_row:
            self.notify(
                f"Selected: {selected_row.values.get('Repository')} "
                f"from {selected_row.layer}",
                severity="information"
            )
        self.exit()


if __name__ == "__main__":
    app = LayeredListSelectionApp()
    app.run()
