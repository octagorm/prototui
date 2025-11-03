"""
Multi-select table example using UniversalScreen.

Run with: python -m examples.table_multiselect_example
"""

from textual.app import App

from prototui.screens.universal_screen import UniversalScreen, Field
from prototui.components.layered_data_table import TableRow


class MultiSelectExampleApp(App):
    """Demonstrate UniversalScreen with a multi-select table."""

    CSS_PATH = "../prototui/themes/default.tcss"

    def on_mount(self) -> None:
        """Show the multi-select table screen when app starts."""
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
            title="Select Repositories for PR Creation",
            fields=[
                Field(
                    id="repositories",
                    field_type="table",
                    columns=["Repository", "Changes", "Status"],
                    rows=rows,
                    select_mode="multi",  # Multi-select: Space to toggle, Enter to confirm
                    show_layers=True
                )
            ],
            explanation_title="Multi-Select Repositories",
            explanation_content=(
                "Select multiple repositories to create PRs for.\n\n"
                "This demonstrates:\n"
                "• Multi-select mode with ○/● checkboxes\n"
                "• Space to toggle individual items\n"
                "• Enter to confirm all selected items\n\n"
                "Use arrow keys to navigate and Space to toggle selection."
            ),
            explanation_hint="",
            submit_label="Create PRs"
        )

        # Push the screen and handle the result
        self.push_screen(screen, self._handle_selection)

    def _handle_selection(self, result) -> None:
        """Handle repository selection."""
        if result.confirmed and result.values.get("repositories"):
            selected_rows = result.values["repositories"]

            if selected_rows:
                # Build list of selected repository names
                repo_names = [row.values.get("Repository", "") for row in selected_rows]
                repos_text = "\n".join(f"  • {name}" for name in repo_names)

                # Show success screen
                success_screen = UniversalScreen(
                    title="Repositories Selected",
                    message=(
                        f"✓ Selected {len(selected_rows)} repositories:\n\n"
                        f"{repos_text}\n\n"
                        "In a real application, this would perform an action."
                    ),
                    explanation_title="Success",
                    explanation_content=(
                        f"{len(selected_rows)} repositories selected successfully!\n\n"
                        "This demonstrates how multi-select results are returned "
                        "as a list of TableRow objects."
                    ),
                    explanation_hint="Press Enter to close",
                    submit_label="OK"
                )
                self.push_screen(success_screen, lambda _: self.exit())
            else:
                # No repositories selected
                info_screen = UniversalScreen(
                    title="No Selection",
                    message="No repositories were selected.\n\nPlease select at least one repository to continue.",
                    explanation_title="Info",
                    explanation_content="Use Space to select items before confirming.",
                    explanation_hint="Press Enter to try again",
                    submit_label="Try Again"
                )
                self.push_screen(info_screen, lambda result: self.on_mount() if result.confirmed else self.exit())
        else:
            # User cancelled
            self.exit()


def main():
    """Run the app."""
    app = MultiSelectExampleApp()
    app.run()


if __name__ == "__main__":
    main()
