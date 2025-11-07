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
- Conditional fields (fields shown/hidden based on other selections)
- Dynamic table rows (tables that update based on selections)
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
    - Conditional fields (shown/hidden based on selections)
    - Dynamic table rows (updated based on selections)
    - Required field validation
    - Visual error feedback
    - Enter to submit
    """

    def on_mount(self) -> None:
        # Define fields in the order they should appear
        # Mix text fields and table fields as needed for optimal UX
        
        # Define all rows first
        deployment_rows = [
            TableRow({"Type": "Docker", "Description": "Standard container"}, row_key="docker"),
            TableRow({"Type": "Kubernetes", "Description": "Orchestrated deployment"}, row_key="kubernetes"),
            TableRow({"Type": "VM", "Description": "Virtual machine"}, row_key="vm"),
        ]

        environment_rows = [
            TableRow({"Environment": "Development", "Region": "us-east-1"}, row_key="dev"),
            TableRow({"Environment": "Staging", "Region": "us-west-2"}, row_key="staging"),
            TableRow({"Environment": "Production", "Region": "eu-west-1"}, row_key="prod"),
        ]

        # Priority rows - will be updated dynamically based on environment
        priority_rows = [
            TableRow({"Priority": "Low", "SLA": "72 hours"}, row_key="low"),
            TableRow({"Priority": "Medium", "SLA": "24 hours"}, row_key="medium"),
        ]

        # Define fields in desired display order
        fields = [
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
            TableSelectionField(
                id="deployment_type",
                label="Deployment Type:",
                columns=["Type", "Description"],
                rows=deployment_rows,
                required=True
            ),
            # Conditional field: Only shown when deployment_type is "kubernetes"
            # Now appears RIGHT AFTER deployment_type (where it logically belongs)
            TextField(
                id="namespace",
                label="Kubernetes Namespace:",
                placeholder="e.g., production",
                required=False,
                visible_when=lambda values: (
                    values.get("deployment_type") and 
                    values.get("deployment_type").row_key == "kubernetes"
                )
            ),
            TableSelectionField(
                id="environment",
                label="Environment:",
                columns=["Environment", "Region"],
                rows=environment_rows,
                required=True
            ),
            TableSelectionField(
                id="priority",
                label="Priority:",
                columns=["Priority", "SLA"],
                rows=priority_rows,
                required=False
            ),
            # Conditional table: Only shown for Kubernetes deployments
            TableSelectionField(
                id="replica_count",
                label="Replica Count:",
                columns=["Replicas", "Use Case"],
                rows=[
                    TableRow({"Replicas": "1", "Use Case": "Development"}, row_key="1"),
                    TableRow({"Replicas": "3", "Use Case": "Standard HA"}, row_key="3"),
                    TableRow({"Replicas": "5", "Use Case": "High traffic"}, row_key="5"),
                ],
                required=False,
                visible_when=lambda values: (
                    values.get("deployment_type") and 
                    values.get("deployment_type").row_key == "kubernetes"
                )
            ),
        ]

        # Create form screen using FormScreen utility with mixed fields
        screen = FormScreen(
            fields=fields,  # Use new 'fields' parameter for mixed ordering
            title="Service Configuration",
            explanation_title="Configuration Form",
            explanation_content=(
                "Configure your service deployment settings.\n\n"
                "CONDITIONAL FIELDS:\n"
                "• Select 'Kubernetes' deployment type to reveal namespace and replica count fields\n"
                "• Select 'Production' environment to see additional priority levels\n\n"
                "NAVIGATION:\n"
                "• Tab to navigate between fields\n"
                "• Arrow keys to browse tables\n"
                "• Space to select in tables (● indicator)\n\n"
                "VALIDATION:\n"
                "• Service name and port are required\n"
                "• Deployment type and environment are required\n"
                "• Missing required fields show red border\n\n"
                "DYNAMIC BEHAVIOR:\n"
                "• Priority table updates when environment changes\n"
                "• Namespace field appears for Kubernetes\n"
                "• Replica count table appears for Kubernetes\n\n"
                "Press Enter to submit, ESC to unfocus, then 'q' to quit."
            ),
            on_quit=self.handle_quit
        )

        # Setup dynamic row updates
        # When environment changes, update priority rows
        def update_priority_rows(form_screen):
            """Update priority table rows based on selected environment."""
            from utilities.layered_data_table import LayeredDataTable
            
            # Get current form values
            values = form_screen.get_current_values()
            env_row = values.get("environment")
            
            if not env_row:
                return
            
            priority_table = form_screen.query_one("#priority", LayeredDataTable)
            
            if env_row.row_key == "prod":
                # Production: All priority levels
                new_rows = [
                    TableRow({"Priority": "Low", "SLA": "72 hours"}, row_key="low"),
                    TableRow({"Priority": "Medium", "SLA": "24 hours"}, row_key="medium"),
                    TableRow({"Priority": "High", "SLA": "4 hours"}, row_key="high"),
                    TableRow({"Priority": "Critical", "SLA": "1 hour"}, row_key="critical"),
                ]
            else:
                # Dev/Staging: Only Low/Medium
                new_rows = [
                    TableRow({"Priority": "Low", "SLA": "72 hours"}, row_key="low"),
                    TableRow({"Priority": "Medium", "SLA": "24 hours"}, row_key="medium"),
                ]
            
            priority_table.set_rows(new_rows)
            # Set default selection if nothing selected
            if not priority_table._selected_row and new_rows:
                priority_table._selected_row = new_rows[0].row_key
                priority_table._rebuild_table()

        # Attach callback for table selection changes
        screen._table_selection_callback = lambda event: (
            update_priority_rows(screen) if event.table_id == "environment" else None
        )

        # Set default selections after screen is mounted
        def set_defaults():
            from utilities.layered_data_table import LayeredDataTable
            
            # Default deployment type: docker
            deployment_table = screen.query_one("#deployment_type", LayeredDataTable)
            deployment_table._selected_row = "docker"
            deployment_table._rebuild_table()
            
            # Default environment: dev
            env_table = screen.query_one("#environment", LayeredDataTable)
            env_table._selected_row = "dev"
            env_table._rebuild_table()
            
            # Initialize priority rows based on default environment
            update_priority_rows(screen)

        self.push_screen(screen, self.handle_form_submission)
        screen.call_after_refresh(set_defaults)

    def handle_form_submission(self, values: dict | None) -> None:
        if values:
            deployment_row = values.get("deployment_type")
            deployment = deployment_row.values if deployment_row else {}

            env_row = values.get("environment")
            env = env_row.values if env_row else {}

            priority_row = values.get("priority")
            priority = priority_row.values if priority_row else {}

            replica_row = values.get("replica_count")
            replicas = replica_row.values if replica_row else {}

            # Print to console
            print("\n" + "="*50)
            print("FORM SUBMITTED")
            print("="*50)
            print(f"Service Name: {values.get('service_name')}")
            print(f"Port: {values.get('port')}")
            print(f"Description: {values.get('description') or 'N/A'}")
            print(f"Deployment Type: {deployment.get('Type')}")
            
            # Conditional field output
            if values.get('namespace'):
                print(f"Kubernetes Namespace: {values.get('namespace')}")
            
            print(f"Environment: {env.get('Environment')} ({env.get('Region')})")
            print(f"Priority: {priority.get('Priority', 'N/A')} ({priority.get('SLA', 'N/A')})")
            
            # Conditional table output
            if replicas:
                print(f"Replica Count: {replicas.get('Replicas')} ({replicas.get('Use Case')})")
            
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
    from utilities.terminal_compat import run_app

    app = FormWithTableApp()
    run_app(app)  # Handles colors + IntelliJ mouse issues
