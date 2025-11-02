"""
Multi-field form example using UniversalScreen.

This example demonstrates:
- Multiple text input fields
- Radio button selection without layers (simple list)
- Multi-field form submission
- Result display

Run with: python -m examples.form_example
"""

from textual.app import App
from textual.binding import Binding

from prototui.screens.universal_screen import UniversalScreen, Field, ScreenResult
from prototui.components.layered_data_table import TableRow


class FormExampleApp(App):
    """Demonstrate UniversalScreen with a multi-field form."""

    CSS_PATH = "../prototui/themes/default.tcss"

    def on_mount(self) -> None:
        """Show the configuration form when app starts."""
        # Environment options (no layers - just a simple list)
        environment_options = [
            TableRow({"Environment": "Development"}),
            TableRow({"Environment": "Staging"}),
            TableRow({"Environment": "Production"}),
        ]

        screen = UniversalScreen(
            title="Service Configuration",
            message="Configure your service deployment settings.",
            fields=[
                Field(
                    id="service_name",
                    field_type="text",
                    label="Service Name:",
                    placeholder="e.g., api-gateway",
                    default_value="",
                    required=True
                ),
                Field(
                    id="port",
                    field_type="text",
                    label="Port:",
                    placeholder="e.g., 8080",
                    default_value="",
                    required=True
                ),
                Field(
                    id="environment",
                    field_type="table",
                    label="Environment:",
                    columns=["Environment"],
                    rows=environment_options,
                    select_mode="radio",
                    show_layers=False,  # No layers, just a simple list
                    show_column_headers=False,  # Hide the "Environment" column header
                    required=True
                )
            ],
            explanation_title="Configuration Form",
            explanation_content=(
                "Fill in the service details.\n\n"
                "This demonstrates a multi-field form with:\n"
                "• Text input fields with validation\n"
                "• Radio button selection for environment\n"
                "• Required field validation\n\n"
                "Use Tab to navigate between fields, and ESC to unfocus."
            ),
            explanation_hint="",
            submit_label="Create Service"
        )

        self.push_screen(screen, self._handle_form_result)

    def _handle_form_result(self, result: ScreenResult) -> None:
        """Handle form submission."""
        if result.confirmed:
            # Extract values (validation already done by UniversalScreen)
            service_name = result.values.get("service_name", "").strip()
            port = result.values.get("port", "").strip()
            environment_rows = result.values.get("environment", [])

            # Get selected environment
            environment = environment_rows[0].values.get("Environment", "")

            # Show success screen
            success_screen = UniversalScreen(
                title="Service Created",
                message=(
                    f"✓ Service configured successfully!\n\n"
                    f"  Service Name: {service_name}\n"
                    f"  Port: {port}\n"
                    f"  Environment: {environment}\n\n"
                    "In a real application, this would create and deploy the service."
                ),
                explanation_title="Success",
                explanation_content=(
                    "Configuration saved successfully!\n\n"
                    "This demonstrates how multi-field forms work with "
                    "UniversalScreen, combining text inputs and table selection."
                ),
                explanation_hint="Press Enter to close",
                submit_label="OK"
            )
            self.push_screen(success_screen, lambda _: self.exit())
        else:
            # User cancelled
            self.exit()


def main():
    """Run the app."""
    app = FormExampleApp()
    app.run()


if __name__ == "__main__":
    main()
