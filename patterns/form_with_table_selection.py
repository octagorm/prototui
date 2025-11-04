"""
Pattern: Form with Table Selection and Explanation Panel

Use this when collecting mixed input: text fields + table selection.

Example use cases:
- Service configuration (name, port, environment selection)
- Resource creation (properties + category selection)
- Settings form with dropdown-like table selections

Features:
- Two-pane layout (form + explanation panel)
- Text input fields with validation
- Table selection for choice fields (radio mode with visual indicator)
- Required field validation
- Enter to submit

Run: python patterns/form_with_table_selection.py
"""

# Add parent directory to path to import utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer
from textual.binding import Binding

# Import utilities
from utilities.form_screen import FormScreen, TextField, TableSelectionField
from utilities.layered_data_table import TableRow


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


class FormWithTableApp(App):
    """
    Application demonstrating form with table selection.

    This pattern shows:
    - Two-pane layout (form + explanation)
    - Text input fields with validation
    - Table selection (radio mode with ● indicator)
    - Mixed form inputs
    - Required field validation
    - Visual error feedback
    - Enter to submit
    """

    def on_mount(self) -> None:
        # Define text fields using TextField
        text_fields = [
            TextField(
                id="service_name",
                label="Service Name:",
                placeholder="e.g., api-gateway",
                required=True
            ),
            TextField(
                id="port",
                label="Port:",
                placeholder="e.g., 8080",
                required=True
            ),
            TextField(
                id="description",
                label="Description:",
                placeholder="Optional description",
                required=False
            ),
        ]

        # Define table selection field using TableSelectionField
        environment_rows = [
            TableRow({"Environment": "Development", "Region": "us-east-1"}),
            TableRow({"Environment": "Staging", "Region": "us-west-2"}),
            TableRow({"Environment": "Production", "Region": "eu-west-1"}),
        ]

        table_field = TableSelectionField(
            id="environment",
            label="Environment:",
            columns=["Environment", "Region"],
            rows=environment_rows,
            required=True
        )

        # Create form screen using FormScreen utility
        screen = FormScreen(
            text_fields=text_fields,
            table_field=table_field,
            title="Service Configuration",
            explanation_title="Configuration Form",
            explanation_content=(
                "Configure your service deployment settings.\n\n"
                "Fill in the service name and port number on the left. "
                "Both fields are required. The description field is optional.\n\n"
                "Use Tab to navigate between fields. When you reach the environment table, "
                "use the arrow keys to browse and press Space to select. "
                "A ● indicator shows your current selection.\n\n"
                "Press Enter to submit the form. If any required fields are missing, "
                "they'll be highlighted with a red border.\n\n"
                "Press ESC to unfocus any field, then 'q' to quit."
            ),
            on_quit=self.handle_quit
        )

        self.push_screen(screen, self.handle_form_submission)

    def handle_form_submission(self, values: dict | None) -> None:
        if values:
            env_row = values.get("environment")
            env = env_row.values if env_row else {}

            # Print to console
            print("\n" + "="*50)
            print("FORM SUBMITTED")
            print("="*50)
            print(f"Service Name: {values.get('service_name')}")
            print(f"Port: {values.get('port')}")
            print(f"Environment: {env.get('Environment')} ({env.get('Region')})")
            print(f"Description: {values.get('description') or 'N/A'}")
            print("="*50 + "\n")

            self.notify(
                f"Form submitted! Check console for details.",
                severity="information",
                timeout=3
            )
        else:
            print("\nForm cancelled\n")
            self.notify("Form cancelled")
        self.exit()

    def handle_quit(self) -> None:
        """Handle quit request from form."""
        self.push_screen(ConfirmQuitScreen())


if __name__ == "__main__":
    # Optional: Use terminal_setup for better colors across terminals (iTerm2, IntelliJ, VS Code)
    # from utilities.terminal_setup import run_app_with_best_colors
    # app = FormWithTableApp()
    # run_app_with_best_colors(app)

    app = FormWithTableApp()
    app.run()
