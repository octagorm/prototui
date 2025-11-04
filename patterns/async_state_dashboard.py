"""
Pattern: Async State Dashboard

Use this for dashboards that show async operations with real-time state updates.

Example use cases:
- Deployment pipeline dashboard
- Service health monitoring
- Build/CI job status tracking
- Multi-stage workflow management

Features:
- Layered table showing async state
- Real-time UI updates
- Parallel async operations
- Custom actions with hotkeys
- Two-press confirmation pattern
- State tracking with visual feedback

Run: python patterns/async_state_dashboard.py
"""

# Add parent directory to path to import utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import random
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.binding import Binding

from utilities.layered_data_table import LayeredDataTable, TableRow
from utilities.explanation_panel import ExplanationPanel


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


class DashboardScreen(Screen):
    """Main dashboard screen with async state management."""

    BINDINGS = [
        Binding("d", "deploy_layer", "Deploy Layer", show=True),
        Binding("l", "toggle_layer", "Toggle Layer", show=True),
        Binding("a", "toggle_all", "Toggle All", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("s", "restart_service", "Restart", show=True),
        Binding("i", "info", "Info", show=True),
        Binding("q", "request_quit", "Quit", show=True),
    ]

    def __init__(self):
        super().__init__()

        # Service definitions with layers
        self.services = {
            "Infrastructure": ["database", "cache", "message-queue"],
            "Core Services": ["auth-service", "config-service"],
            "API Layer": ["api-gateway", "user-service"],
        }

        # Service state (simulated)
        self.service_state = {}
        for layer_services in self.services.values():
            for service in layer_services:
                self.service_state[service] = {
                    "status": "Stopped",
                    "version": "1.0.0",
                    "uptime": "-"
                }

        # Pending action for two-press confirmation
        self._pending_action = None
        self._pending_services = None
        self._operation_in_progress = False

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main-container"):
            with Vertical(id="content-pane"):
                yield LayeredDataTable(
                    id="services-table",
                    columns=["Service", "Status", "Version", "Uptime"],
                    rows=self._build_table_rows(),
                    select_mode="multi",
                    show_layers=True,
                    filterable=True
                )

            with VerticalScroll(id="explanation-pane"):
                yield ExplanationPanel(
                    "Service Dashboard",
                    "Monitor and control services across layers.\n\n"
                    "Actions:\n"
                    "• (d) Deploy selected services (async)\n"
                    "• (r) Refresh status for all services\n"
                    "• (s) Restart selected services\n"
                    "• (i) Show detailed information\n\n"
                    "Use Space to select services, (l) to select entire layer, "
                    "or (a) to toggle all.\n\n"
                    "Status updates happen in real-time as operations complete."
                )

        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = "Service Dashboard (0 selected)"

        # Make explanation pane non-focusable
        explanation_pane = self.query_one("#explanation-pane")
        explanation_pane.can_focus = False

    def on_layered_data_table_row_toggled(self, event: LayeredDataTable.RowToggled) -> None:
        """Handle row selection changes to update subtitle."""
        self._update_subtitle()

    def _update_subtitle(self) -> None:
        table = self.query_one(LayeredDataTable)
        selected = table.get_selected_rows()
        count = len(selected)
        self.sub_title = f"Service Dashboard ({count} selected)"

    def _build_table_rows(self) -> list[TableRow]:
        """Build table rows from current service state."""
        rows = []
        for layer_name, layer_services in self.services.items():
            for service in layer_services:
                state = self.service_state[service]
                rows.append(
                    TableRow(
                        {
                            "Service": service,
                            "Status": state["status"],
                            "Version": state["version"],
                            "Uptime": state["uptime"]
                        },
                        layer=layer_name,
                        row_key=service
                    )
                )
        return rows

    def _update_table(self) -> None:
        """Update table with current service state."""
        table = self.query_one(LayeredDataTable)
        table.set_rows(self._build_table_rows())

    def _update_explanation(self, title: str, content: str) -> None:
        """Update explanation panel."""
        panel = self.query_one(ExplanationPanel)
        panel.update_content(title, content)

    def _get_selected_services(self) -> list[str]:
        """Get list of selected service names."""
        table = self.query_one(LayeredDataTable)
        selected_rows = table.get_selected_rows()
        return [row.row_key for row in selected_rows if row.row_key]

    def action_toggle_layer(self) -> None:
        """Toggle selection of all services in the current layer."""
        table = self.query_one(LayeredDataTable)
        current_layer = table.get_cursor_layer()

        if current_layer:
            table.toggle_rows_by_layer(current_layer)
            self._update_subtitle()

    def action_toggle_all(self) -> None:
        """Toggle selection of all services."""
        table = self.query_one(LayeredDataTable)
        table.toggle_all_rows()
        self._update_subtitle()

    def action_deploy_layer(self) -> None:
        """Deploy selected services (with two-press confirmation)."""
        if self._operation_in_progress:
            self._update_explanation("Operation in Progress", "Please wait for current operation to complete.")
            return

        selected = self._get_selected_services()
        if not selected:
            self._update_explanation(
                "No Services Selected",
                "Select services with Space, or press (l) to select entire layer."
            )
            self._pending_action = None
            return

        # Two-press confirmation
        if self._pending_action == "deploy" and self._pending_services == selected:
            # Second press - execute
            self._pending_action = None
            self._pending_services = None
            self._update_explanation("Deploying...", f"Deploying {len(selected)} service(s) in parallel...")
            asyncio.create_task(self._deploy_services(selected))
        else:
            # First press - show confirmation
            self._pending_action = "deploy"
            self._pending_services = selected
            self._update_explanation(
                "Confirm Deployment",
                f"Deploy {len(selected)} service(s)?\n\n"
                + "\n".join(f"  • {s}" for s in selected)
                + "\n\nPress (d) again to confirm."
            )

    async def _deploy_services(self, services: list[str]) -> None:
        """Deploy multiple services in parallel."""
        self._operation_in_progress = True

        try:
            # Show "..." status while deploying
            for service in services:
                self.service_state[service]["status"] = "Deploying..."
            self._update_table()

            # Deploy in parallel
            tasks = [self._deploy_single_service(s) for s in services]
            await asyncio.gather(*tasks)

            self._update_explanation(
                "Deployment Complete",
                f"✓ Successfully deployed {len(services)} service(s).\n\n"
                "Press (r) to refresh status."
            )

        except Exception as e:
            self._update_explanation("Deployment Failed", f"✗ Error: {e}")
        finally:
            self._operation_in_progress = False

    async def _deploy_single_service(self, service: str) -> None:
        """Deploy a single service (simulated with random delay)."""
        # Simulate deployment time
        await asyncio.sleep(random.uniform(1.0, 3.0))

        # Simulate occasional failures
        if random.random() < 0.1:
            self.service_state[service]["status"] = "Failed"
        else:
            # Generate new version
            major, minor, patch = map(int, self.service_state[service]["version"].split("."))
            patch += 1
            new_version = f"{major}.{minor}.{patch}"

            self.service_state[service]["status"] = "Running"
            self.service_state[service]["version"] = new_version
            self.service_state[service]["uptime"] = "0s"

        self._update_table()

    def action_refresh(self) -> None:
        """Refresh status for all services."""
        if self._operation_in_progress:
            self._update_explanation("Operation in Progress", "Please wait for current operation to complete.")
            return

        self._update_explanation("Refreshing...", "Polling service status...")
        asyncio.create_task(self._refresh_all_services())

    async def _refresh_all_services(self) -> None:
        """Refresh status for all services."""
        self._operation_in_progress = True

        try:
            # Simulate polling all services
            all_services = [s for services in self.services.values() for s in services]

            tasks = [self._refresh_single_service(s) for s in all_services]
            await asyncio.gather(*tasks)

            running = sum(1 for s in all_services if self.service_state[s]["status"] == "Running")

            self._update_explanation(
                "Refresh Complete",
                f"✓ Status updated for {len(all_services)} service(s)\n\n"
                f"{running} running, {len(all_services) - running} stopped/failed"
            )

        except Exception as e:
            self._update_explanation("Refresh Failed", f"✗ Error: {e}")
        finally:
            self._operation_in_progress = False

    async def _refresh_single_service(self, service: str) -> None:
        """Refresh status for a single service (simulated)."""
        await asyncio.sleep(random.uniform(0.1, 0.5))

        # Update uptime for running services
        if self.service_state[service]["status"] == "Running":
            current_uptime = self.service_state[service]["uptime"]
            if current_uptime != "-":
                # Simulate incrementing uptime
                seconds = int(current_uptime.rstrip("s")) + random.randint(1, 10)
                self.service_state[service]["uptime"] = f"{seconds}s"

        self._update_table()

    def action_restart_service(self) -> None:
        """Restart selected services."""
        if self._operation_in_progress:
            self._update_explanation("Operation in Progress", "Please wait for current operation to complete.")
            return

        selected = self._get_selected_services()
        if not selected:
            self._update_explanation(
                "No Services Selected",
                "Select services to restart."
            )
            self._pending_action = None
            return

        # Filter to running services
        running = [s for s in selected if self.service_state[s]["status"] == "Running"]

        if not running:
            self._update_explanation(
                "No Running Services",
                "Selected services are not running.\n\n"
                "Deploy them first with (d)."
            )
            self._pending_action = None
            return

        # Two-press confirmation
        if self._pending_action == "restart" and self._pending_services == running:
            # Second press - execute
            self._pending_action = None
            self._pending_services = None
            self._update_explanation("Restarting...", f"Restarting {len(running)} service(s)...")
            asyncio.create_task(self._restart_services(running))
        else:
            # First press - show confirmation
            self._pending_action = "restart"
            self._pending_services = running
            self._update_explanation(
                "Confirm Restart",
                f"Restart {len(running)} service(s)?\n\n"
                + "\n".join(f"  • {s}" for s in running)
                + "\n\nPress (s) again to confirm."
            )

    async def _restart_services(self, services: list[str]) -> None:
        """Restart multiple services."""
        self._operation_in_progress = True

        try:
            # Show "..." while restarting
            for service in services:
                self.service_state[service]["status"] = "Restarting..."
            self._update_table()

            # Restart in parallel
            tasks = [self._restart_single_service(s) for s in services]
            await asyncio.gather(*tasks)

            self._update_explanation(
                "Restart Complete",
                f"✓ Restarted {len(services)} service(s)."
            )

        except Exception as e:
            self._update_explanation("Restart Failed", f"✗ Error: {e}")
        finally:
            self._operation_in_progress = False

    async def _restart_single_service(self, service: str) -> None:
        """Restart a single service (simulated)."""
        await asyncio.sleep(random.uniform(0.5, 1.5))

        self.service_state[service]["status"] = "Running"
        self.service_state[service]["uptime"] = "0s"

        self._update_table()

    def action_info(self) -> None:
        """Show detailed information."""
        self._pending_action = None
        self._update_explanation(
            "Dashboard Information",
            "Async State Dashboard\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "This pattern demonstrates:\n\n"
            "Real-Time Updates:\n"
            "• Table updates as operations complete\n"
            "• Status shows '...' during operations\n"
            "• State changes are immediate\n\n"
            "Async Operations:\n"
            "• Multiple services deployed in parallel\n"
            "• Non-blocking UI updates\n"
            "• Background polling\n\n"
            "Two-Press Confirmation:\n"
            "• First press shows what will happen\n"
            "• Second press confirms and executes\n"
            "• Prevents accidental actions\n\n"
            "Use Cases:\n"
            "• CI/CD pipeline dashboards\n"
            "• Service health monitoring\n"
            "• Deployment workflows\n"
            "• Any multi-stage async process"
        )

    def action_request_quit(self) -> None:
        self.app.push_screen(ConfirmQuitScreen())


class AsyncStateDashboardApp(App):
    """
    Application demonstrating async state dashboard pattern.

    This pattern shows:
    - Layered table with real-time state updates
    - Parallel async operations
    - Two-press confirmation pattern
    - Dynamic status updates
    - Custom action hotkeys
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
    }
    """

    def on_mount(self) -> None:
        self.push_screen(DashboardScreen())


if __name__ == "__main__":
    app = AsyncStateDashboardApp()
    app.run()
