"""
Table example using UniversalScreen with single-select table.

Run with: python -m examples.table_example
"""

from textual.app import App

from prototui.screens.universal_screen import UniversalScreen, Field
from prototui.components.layered_data_table import TableRow


class TableExampleApp(App):
    """Demonstrate UniversalScreen with a single-select table."""

    CSS_PATH = "../prototui/themes/default.tcss"

    def on_mount(self) -> None:
        """Show the table screen when app starts."""
        # Sample data with layers
        rows = [
            TableRow(
                {"Repository": "auth-service", "Changes": "Yes", "Status": "Modified"},
                layer="Core Services"
            ),
            TableRow(
                {"Repository": "user-service", "Changes": "No", "Status": "Clean"},
                layer="Core Services"
            ),
            TableRow(
                {"Repository": "api-gateway", "Changes": "Yes", "Status": "Modified"},
                layer="API Layer"
            ),
            TableRow(
                {"Repository": "notification-service", "Changes": "Yes", "Status": "Modified"},
                layer="API Layer"
            ),
            TableRow(
                {"Repository": "frontend-app", "Changes": "No", "Status": "Clean"},
                layer="Frontend"
            ),
            TableRow(
                {"Repository": "admin-dashboard", "Changes": "Yes", "Status": "Modified"},
                layer="Frontend"
            ),
        ]

        screen = UniversalScreen(
            title="Repository Management",
            fields=[
                Field(
                    id="repositories",
                    field_type="table",
                    columns=["Repository", "Changes", "Status"],
                    rows=rows,
                    select_mode="single",  # Single-select with no visual indicator
                    show_layers=True
                )
            ],
            explanation_title="Select Repository",
            explanation_content=(
                "Repositories organized by architectural layer.\n\n"
                "This demonstrates:\n"
                "• Single-select mode (no visual indicator)\n"
                "• Layered data grouping\n"
                "• Arrow key navigation\n\n"
                "Navigate with arrow keys and press Enter to select."
            ),
            explanation_hint="",
            submit_label="Select"
        )

        # Push the screen and handle the result
        self.push_screen(screen, self._handle_selection)

    def _handle_selection(self, result) -> None:
        """Handle repository selection."""
        if result.confirmed and result.values.get("repositories"):
            selected_rows = result.values["repositories"]
            if selected_rows:
                repo = selected_rows[0]
                repo_name = repo.values.get("Repository", "")

                # Show success screen
                success_screen = UniversalScreen(
                    title="Repository Selected",
                    message=(
                        f"✓ Selected: {repo_name}\n\n"
                        f"Layer: {repo.layer}\n"
                        f"Changes: {repo.values.get('Changes')}\n"
                        f"Status: {repo.values.get('Status')}\n\n"
                        "In a real application, this would perform an action."
                    ),
                    explanation_title="Success",
                    explanation_content="Repository selected successfully!",
                    explanation_hint="Press Enter to close",
                    submit_label="OK"
                )
                self.push_screen(success_screen, lambda _: self.exit())
        else:
            # User cancelled or no selection
            self.exit()


def main():
    """Run the app."""
    app = TableExampleApp()
    app.run()


if __name__ == "__main__":
    main()
