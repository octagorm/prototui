"""
State management example using UniversalScreen and StateManager.

Demonstrates:
- StateManager for centralized state management
- State watchers for reacting to changes
- Change tracking and notifications

Run with: python -m examples.state_example
"""

from textual.app import App
from textual.binding import Binding

from prototui import UniversalScreen, Field, TableRow
from prototui.utils.state_manager import StateManager, StateChange


class StateExampleApp(App):
    """Demonstrate StateManager with a service monitoring dashboard."""

    CSS_PATH = "../prototui/themes/default.tcss"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize state manager
        self.state = StateManager(
            initial_state={
                "api_gateway": "healthy",
                "auth_service": "healthy",
                "user_service": "healthy",
                "notification_service": "degraded",
                "metrics_service": "down",
            }
        )

        # Track state changes for display
        self._change_history: list[str] = []

        # Set up watchers for all services
        self._setup_watchers()

    def _setup_watchers(self) -> None:
        """Set up state change watchers."""
        # Watch all service states
        for service_name in self.state.keys():
            self.state.watch(service_name, self._on_service_state_change)

        # You could also watch specific keys:
        # self.state.watch("api_gateway", self._on_critical_service_change)

    def _on_service_state_change(self, change: StateChange) -> None:
        """Called whenever a service state changes."""
        self.log(
            f"State change: {change.key} "
            f"{change.old_value} -> {change.new_value}"
        )

        # Record change in history
        change_msg = f"{change.key}: {change.old_value} → {change.new_value}"
        self._change_history.append(change_msg)

        # You could trigger actions based on state changes:
        if change.new_value == "down":
            self.log(f"ALERT: {change.key} is DOWN!")
        elif change.old_value == "down" and change.new_value == "healthy":
            self.log(f"RECOVERED: {change.key} is now healthy")

    def on_mount(self) -> None:
        """Show the service status dashboard."""
        self._show_dashboard()

    def _show_dashboard(self) -> None:
        """Display the service status dashboard."""
        # Build table rows from current state
        rows = []
        for service_name in sorted(self.state.keys()):
            status = self.state.get(service_name)
            status_icon = self._get_status_icon(status)

            rows.append(
                TableRow(
                    {"Service": service_name, "Status": f"{status_icon} {status}"},
                    row_key=service_name
                )
            )

        # Show change history in message if any changes occurred
        history_msg = ""
        if self._change_history:
            recent_changes = self._change_history[-5:]  # Last 5 changes
            history_msg = (
                "\n\nRecent changes:\n"
                + "\n".join(f"  • {change}" for change in recent_changes)
            )

        screen = UniversalScreen(
            title="Service Status Dashboard",
            message=f"Monitoring {len(rows)} services{history_msg}",
            fields=[
                Field(
                    id="services",
                    field_type="table",
                    columns=["Service", "Status"],
                    rows=rows,
                    select_mode="radio",
                    show_layers=False,
                    show_column_headers=True,
                    auto_height=False,
                    required=True
                )
            ],
            explanation_title="State Management",
            explanation_content=(
                "This dashboard uses StateManager to track service states.\n\n"
                "Features:\n"
                "• Centralized state with get/set\n"
                "• Watchers notify on changes\n"
                "• Change tracking with old/new values\n\n"
                "Select a service and press 'u' to update its status."
            ),
            allow_submit=False,
            custom_bindings=[
                Binding("u", "app.update_status", "Update", show=True),
                Binding("i", "app.info", "Info", show=True),
                Binding("h", "app.history", "History", show=True),
            ]
        )

        self.push_screen(screen, self._handle_dashboard_close)

    def _get_status_icon(self, status: str) -> str:
        """Get icon for status."""
        icons = {
            "healthy": "✓",
            "degraded": "⚠",
            "down": "✗",
        }
        return icons.get(status, "?")

    def _handle_dashboard_close(self, result) -> None:
        """Handle dashboard dismissal."""
        # With allow_submit=False, this only happens on ESC
        self.exit()

    def action_update_status(self) -> None:
        """Update status of selected service."""
        if not isinstance(self.screen, UniversalScreen):
            return

        # Get current selection
        values = self.screen._collect_values()
        selected = values.get("services", [])

        if not selected:
            self._show_no_selection()
            return

        service_name = selected[0].row_key
        current_status = self.state.get(service_name)

        # Show status selection screen
        status_options = [
            TableRow({"Status": "healthy"}),
            TableRow({"Status": "degraded"}),
            TableRow({"Status": "down"}),
        ]

        # Pre-select current status by finding matching row
        for i, row in enumerate(status_options):
            if row.values["Status"] == current_status:
                # Mark as initially selected (we'll handle this in a moment)
                pass

        update_screen = UniversalScreen(
            title=f"Update {service_name}",
            message=f"Current status: {self._get_status_icon(current_status)} {current_status}",
            fields=[
                Field(
                    id="new_status",
                    field_type="table",
                    label="New Status:",
                    columns=["Status"],
                    rows=status_options,
                    select_mode="radio",
                    show_layers=False,
                    show_column_headers=False,
                    required=True
                )
            ],
            explanation_title="Change Status",
            explanation_content=(
                "Select the new status for this service.\n\n"
                "StateManager will:\n"
                "1. Update the state value\n"
                "2. Trigger all watchers for this key\n"
                "3. Track the change (old → new)"
            ),
            submit_label="Update"
        )

        self.push_screen(
            update_screen,
            lambda result: self._handle_status_update(result, service_name)
        )

    def _handle_status_update(self, result, service_name: str) -> None:
        """Handle status update."""
        if result.confirmed:
            selected = result.values.get("new_status", [])
            if selected:
                new_status = selected[0].values["Status"]

                # Update state - this triggers watchers!
                self.state.set(service_name, new_status)

                # Refresh dashboard to show new state
                self.pop_screen()  # Remove current dashboard
                self._show_dashboard()

    def action_info(self) -> None:
        """Show StateManager information."""
        info_screen = UniversalScreen(
            title="StateManager Information",
            message=(
                "StateManager provides:\n\n"
                "• get(key, default) - Get state value\n"
                "• set(key, value) - Set state value\n"
                "• update(dict) - Update multiple values\n"
                "• delete(key) - Delete state value\n"
                "• watch(key, callback) - Watch for changes\n"
                "• unwatch(key, callback) - Stop watching\n\n"
                "Watchers receive StateChange objects:\n"
                "  • key: The state key that changed\n"
                "  • old_value: Previous value\n"
                "  • new_value: New value\n\n"
                "Use cases:\n"
                "• Centralized app state\n"
                "• React to state changes\n"
                "• Track state history\n"
                "• Trigger side effects"
            ),
            explanation_title="State Management",
            explanation_content="StateManager only triggers watchers when values actually change.",
            submit_label="OK"
        )

        self.push_screen(info_screen)

    def action_history(self) -> None:
        """Show change history."""
        if not self._change_history:
            history_msg = "No state changes have occurred yet."
        else:
            history_msg = (
                f"Total changes: {len(self._change_history)}\n\n"
                + "\n".join(f"{i+1}. {change}" for i, change in enumerate(self._change_history))
            )

        history_screen = UniversalScreen(
            title="State Change History",
            message=history_msg,
            explanation_title="Change Log",
            explanation_content=(
                "All state changes are tracked by watchers.\n\n"
                "Each change shows:\n"
                "  service_name: old_value → new_value"
            ),
            submit_label="OK"
        )

        self.push_screen(history_screen)

    def _show_no_selection(self) -> None:
        """Show no selection message."""
        info_screen = UniversalScreen(
            title="No Selection",
            message="Please select a service first.",
            explanation_title="Info",
            explanation_content="Use arrow keys to navigate and Space to select.",
            submit_label="OK"
        )

        self.push_screen(info_screen)


def main():
    """Run the app."""
    app = StateExampleApp()
    app.run()


if __name__ == "__main__":
    main()
