"""
Pattern: Layered Multi-Select with Explanation Panel

Use this when selecting MULTIPLE items from grouped/layered lists.

Example use cases:
- Select multiple services across environments
- Choose files from different directories
- Pick resources from multiple categories

Features:
- Two-pane layout (list + explanation panel)
- Multi-select with Space key
- Layered data with group headers
- Layer selection hotkey (l) - selects all in layer
- Selection count tracking

Run: python patterns/layered_multi_select.py
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


class LayeredMultiSelectScreen(Screen):
    """Screen with layered multi-select table and explanation panel."""

    BINDINGS = [
        Binding("enter", "confirm_selection", "Submit", show=True, priority=True),
        Binding("l", "toggle_layer", "Toggle Layer", show=True),
        Binding("a", "toggle_all", "Toggle All", show=True),
        Binding("q", "request_quit", "Quit", show=True),
        Binding("escape", "cancel_review", "Back", show=False),
    ]

    def __init__(
        self,
        items: list[TableRow],
        columns: list[str],
        title: str = "Select Items",
        explanation_title: str = "Help",
        explanation_content: str = ""
    ):
        """
        Initialize layered multi-select screen.

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
        self._selected_items = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main-container"):
            # Left side: Layered data table with multi-select
            with Vertical(id="content-pane"):
                yield LayeredDataTable(
                    id="data-table",
                    columns=self.columns,
                    rows=self.items,
                    select_mode="multi",  # Multi-select with checkboxes
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
        self._update_subtitle()

        # Make explanation pane non-focusable
        explanation_pane = self.query_one("#explanation-pane")
        explanation_pane.can_focus = False

    def on_layered_data_table_row_toggled(self, event: LayeredDataTable.RowToggled) -> None:
        """Handle row selection changes to update subtitle."""
        self._update_subtitle()

    def _update_subtitle(self) -> None:
        """Update subtitle with selection count."""
        table = self.query_one(LayeredDataTable)
        selected = table.get_selected_rows()
        count = len(selected)
        self.sub_title = f"{self.screen_title} ({count} selected)"

    def action_toggle_layer(self) -> None:
        """Toggle selection of all items in the current layer."""
        table = self.query_one(LayeredDataTable)
        current_layer = table.get_cursor_layer()

        if current_layer:
            table.toggle_rows_by_layer(current_layer)
            self._update_subtitle()

    def action_toggle_all(self) -> None:
        """Toggle selection of all items."""
        table = self.query_one(LayeredDataTable)
        table.toggle_all_rows()
        self._update_subtitle()

    def action_confirm_selection(self) -> None:
        """Confirm selection and return selected items."""
        # If in review mode, second Enter confirms
        if self._review_mode:
            self.dismiss(self._selected_items)
            return

        # Get selected items
        table = self.query_one(LayeredDataTable)
        selected_items = table.get_selected_rows()

        if selected_items:
            self._selected_items = selected_items
            self._show_review()
            self._review_mode = True
        else:
            self.notify("No items selected", severity="warning")

    def _show_review(self) -> None:
        """Show selected items in explanation panel."""
        panel = self.query_one(ExplanationPanel)

        # Build review content
        review_lines = []
        for item in self._selected_items:
            # Get first column value as primary identifier
            first_col = self.columns[0]
            identifier = item.values.get(first_col, "Unknown")
            if item.layer:
                review_lines.append(f"• {identifier} ({item.layer})")
            else:
                review_lines.append(f"• {identifier}")

        review_content = "\n".join(review_lines)

        panel.update_content(
            "Review Your Selections",
            f"Selected {len(self._selected_items)} items:\n\n{review_content}\n\n"
            f"Press Enter to confirm, or ESC to go back and change."
        )

        self.sub_title = f"{self.screen_title} - Review ({len(self._selected_items)} selected)"
        self.notify("Review your selections and press Enter to confirm", severity="information")

    def action_cancel_review(self) -> None:
        """Cancel review mode and return to selection."""
        if self._review_mode:
            self._review_mode = False
            self._update_subtitle()
            panel = self.query_one(ExplanationPanel)
            panel.update_content(self.explanation_title, self.explanation_content)
            self.notify("Returned to selection", severity="information")

    def action_request_quit(self) -> None:
        self.app.push_screen(ConfirmQuitScreen())


class LayeredMultiSelectApp(App):
    """
    Application demonstrating layered multi-select.

    This pattern shows:
    - Two-pane layout (table + explanation)
    - Multi-select with Space key
    - Visual selection indicators (checkboxes)
    - Layered data with headers
    - Layer selection with (l) hotkey
    - Selection count in subtitle
    - Dynamic explanation updates
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
        # Sample data with layers - using TableRow
        rows = [
            TableRow(
                {"Service": "auth-service", "Status": "Running", "Port": "3000"},
                layer="Production"
            ),
            TableRow(
                {"Service": "api-gateway", "Status": "Running", "Port": "8080"},
                layer="Production"
            ),
            TableRow(
                {"Service": "user-service", "Status": "Running", "Port": "3001"},
                layer="Production"
            ),
            TableRow(
                {"Service": "auth-service", "Status": "Running", "Port": "3000"},
                layer="Staging"
            ),
            TableRow(
                {"Service": "api-gateway", "Status": "Stopped", "Port": "8080"},
                layer="Staging"
            ),
            TableRow(
                {"Service": "test-service", "Status": "Running", "Port": "4000"},
                layer="Development"
            ),
            TableRow(
                {"Service": "mock-service", "Status": "Stopped", "Port": "4001"},
                layer="Development"
            ),
        ]

        screen = LayeredMultiSelectScreen(
            items=rows,
            columns=["Service", "Status", "Port"],
            title="Select Services to Deploy",
            explanation_title="Multi-Select Services",
            explanation_content=(
                "Select multiple services to deploy from the list on the left.\n\n"
                "Services are grouped by environment (Production, Staging, Development). "
                "Use the arrow keys to navigate and press Space to toggle individual services. "
                "Checkboxes show which services are selected.\n\n"
                "Press '/' to filter services by name, status, or port. "
                "Use Tab or arrow keys to move to the results, ESC to clear.\n\n"
                "Press 'l' to toggle all services in the current environment on or off. "
                "Press 'a' to toggle all services across all environments. "
                "The selection count appears in the subtitle.\n\n"
                "Press Enter to review your selections before confirming.\n\n"
                "Press 'q' to quit."
            )
        )

        self.push_screen(screen, self.handle_selection)

    def handle_selection(self, selected_items: list[TableRow] | None) -> None:
        if selected_items:
            services = [f"{item.values['Service']} ({item.layer})" for item in selected_items]
            self.notify(
                f"Selected {len(services)} services:\n" + "\n".join(services),
                severity="information",
                timeout=10
            )
        else:
            self.notify("No services selected")
        self.exit()


if __name__ == "__main__":
    app = LayeredMultiSelectApp()
    app.run()
