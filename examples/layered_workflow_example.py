"""
Layered workflow example combining StateManager and async utilities.

Demonstrates a realistic Spring Boot microservices PR workflow:
- Multi-layer dependency management
- Parallel PR creation with retry
- Polling for PR approvals and build status
- State tracking with real-time UI updates
- User-controlled progression through layers

Run with: python -m examples.layered_workflow_example
"""

import asyncio
import random
from textual.app import App
from textual.binding import Binding

from prototui import UniversalScreen, Field, TableRow
from prototui.utils.state_manager import StateManager, StateChange
from prototui.utils.async_helpers import (
    retry_with_backoff,
    poll_until,
    run_parallel,
)


# Simulated API configuration
# In real usage, replace these with actual Bitbucket/Jenkins clients
BITBUCKET_BASE_URL = "https://bitbucket.example.com"
JENKINS_BASE_URL = "https://jenkins.example.com"


class LayeredWorkflowApp(App):
    """
    Demonstrate a layered microservices PR workflow.

    Simulates managing PRs across dependency layers where:
    - Layer 1 services have no dependencies
    - Layer 2 depends on Layer 1
    - Layer 3 depends on Layer 2

    Workflow:
    1. Select layer with (l)
    2. Create PRs with (c)
    3. Refresh to poll PRs and builds with (r)
    4. Merge approved PRs with (m)
    5. Update dependencies with (u)
    6. Repeat for next layer
    """

    CSS_PATH = "../prototui/themes/default.tcss"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Service definitions with layers
        self._services = {
            "Layer 1": ["common-utils", "config-service"],
            "Layer 2": ["auth-service", "user-service"],
            "Layer 3": ["api-gateway", "notification-service"],
        }

        # Initialize state manager
        initial_state = {}
        for layer_services in self._services.values():
            for service in layer_services:
                initial_state[f"{service}_pr_status"] = "None"
                initial_state[f"{service}_pr_url"] = ""
                initial_state[f"{service}_build_status"] = "-"
                initial_state[f"{service}_version"] = "1.0.0-SNAPSHOT"

        self.state = StateManager(initial_state=initial_state)

        # Set up state watchers
        self._setup_watchers()

        # Pending action (for two-press confirmation)
        self._pending_action = None
        self._pending_services = None

        # Track if operation is in progress
        self._operation_in_progress = False

    def _setup_watchers(self) -> None:
        """Set up watchers to update UI on state changes."""
        for layer_services in self._services.values():
            for service in layer_services:
                # Watch all state changes and trigger UI updates
                for suffix in ["_pr_status", "_build_status", "_version"]:
                    self.state.watch(
                        f"{service}{suffix}",
                        lambda change: self._on_state_change(change)
                    )

    def _on_state_change(self, change: StateChange) -> None:
        """Handle state changes by updating the UI."""
        # Log the change
        service = change.key.replace("_pr_status", "").replace("_build_status", "").replace("_version", "")
        field = change.key.split("_")[-1] if "_" in change.key else "?"
        self.log(f"{service}.{field}: {change.old_value} → {change.new_value}")

        # Update the table
        self._update_dashboard_table()

    def _update_dashboard_table(self) -> None:
        """Update the dashboard table with current state."""
        if not isinstance(self.screen, UniversalScreen):
            return

        # Build new rows from current state
        rows = []
        for layer_name, services in self._services.items():
            for service in services:
                pr_status = self.state.get(f"{service}_pr_status")
                build_status = self.state.get(f"{service}_build_status")
                version = self.state.get(f"{service}_version")

                rows.append(
                    TableRow(
                        {
                            "Service": service,
                            "PR Status": pr_status,
                            "Build": build_status,
                            "Version": version,
                        },
                        layer=layer_name,
                        row_key=service,
                    )
                )

        # Find the table widget and update it
        try:
            from prototui.components.layered_data_table import LayeredDataTable

            table = self.screen.query_one(LayeredDataTable)
            table.set_rows(rows)
        except Exception as e:
            self.log(f"Failed to update table: {e}")

    def _update_explanation(self, content: str) -> None:
        """Update the explanation panel content."""
        if isinstance(self.screen, UniversalScreen):
            try:
                from prototui.components.explanation_panel import ExplanationPanel

                panel = self.screen.query_one(ExplanationPanel)
                panel.update_content(content)
            except Exception as e:
                self.log(f"Failed to update explanation: {e}")

    def on_mount(self) -> None:
        """Show the main dashboard."""
        self._show_dashboard()

    def _show_dashboard(self) -> None:
        """Display the layered services dashboard."""
        rows = []

        # Build table rows grouped by layer
        for layer_name, services in self._services.items():
            for service in services:
                pr_status = self.state.get(f"{service}_pr_status")
                build_status = self.state.get(f"{service}_build_status")
                version = self.state.get(f"{service}_version")

                rows.append(
                    TableRow(
                        {
                            "Service": service,
                            "PR Status": pr_status,
                            "Build": build_status,
                            "Version": version,
                        },
                        layer=layer_name,
                        row_key=service,
                    )
                )

        screen = UniversalScreen(
            title="Microservices PR Workflow",
            fields=[
                Field(
                    id="services",
                    field_type="table",
                    columns=["Service", "PR Status", "Build", "Version"],
                    rows=rows,
                    select_mode="multi",
                    show_layers=True,
                    show_column_headers=True,
                    auto_height=False,
                    required=False,
                )
            ],
            explanation_title="Layered Deployment",
            explanation_content=(
                "Manage PRs across dependency layers.\n\n"
                "Workflow:\n"
                "1. (l) Select layer\n"
                "2. (c) Create PRs\n"
                "3. (r) Refresh - poll status\n"
                "4. (m) Merge approved\n"
                "5. (r) Refresh - monitor builds\n"
                "6. (u) Update dependencies\n"
                "7. Commit/push manually\n"
                "8. Next layer\n\n"
                "Press (i) for detailed info"
            ),
            allow_submit=False,
            custom_bindings=[
                Binding("l", "app.select_layer", "Select Layer", show=True),
                Binding("c", "app.create_prs", "Create PRs", show=True),
                Binding("m", "app.merge_prs", "Merge", show=True),
                Binding("u", "app.update_deps", "Update Deps", show=True),
                Binding("r", "app.refresh", "Refresh", show=True),
                Binding("i", "app.info", "Info", show=True),
            ],
        )

        self.push_screen(screen, self._handle_dashboard_close)

    def _handle_dashboard_close(self, result) -> None:
        """Handle dashboard dismissal."""
        self.exit()

    def action_select_layer(self) -> None:
        """Select all services in the current layer, deselect others."""
        if not isinstance(self.screen, UniversalScreen):
            return

        try:
            from prototui.components.layered_data_table import LayeredDataTable

            table = self.screen.query_one(LayeredDataTable)
            current_layer = table.get_cursor_layer()

            if not current_layer:
                self._update_explanation("No layer at cursor position.")
                return

            # Select all rows in this layer
            table.select_rows_by_layer(current_layer)

            self._update_explanation(
                f"Selected all services in {current_layer}\n\n"
                "Use hotkeys to perform operations on selected services."
            )

        except Exception as e:
            self.log(f"Failed to select layer: {e}")

    def action_create_prs(self) -> None:
        """Create PRs for selected services (with confirmation)."""
        if self._operation_in_progress:
            self._update_explanation("Operation in progress. Please wait.")
            return

        selected = self._get_selected_services()
        if not selected:
            self._update_explanation(
                "No services selected.\n\n"
                "Use Space to select services, or (l) to select a layer."
            )
            self._pending_action = None
            return

        # Two-press confirmation
        if self._pending_action == "create_prs" and self._pending_services == selected:
            # Second press - execute
            self._pending_action = None
            self._pending_services = None
            self._update_explanation(f"Creating PRs for {len(selected)} services...")
            asyncio.create_task(self._create_prs(selected))
        else:
            # First press - show confirmation
            self._pending_action = "create_prs"
            self._pending_services = selected
            self._update_explanation(
                f"Create PRs for {len(selected)} service(s)?\n\n"
                + "\n".join(f"  • {s}" for s in selected)
                + "\n\nPress (c) again to confirm,\nor select different services to cancel."
            )

    async def _create_prs(self, services: list[str]) -> None:
        """Create PRs for multiple services."""
        self._operation_in_progress = True

        try:
            # Show "..." in PR Status column while creating
            for service in services:
                self.state.set(f"{service}_pr_status", "...")

            # Create PRs in parallel
            operations = [
                lambda s=service: self._create_single_pr(s)
                for service in services
            ]

            await run_parallel(*operations)

            self._update_explanation(
                f"✓ Created PRs for {len(services)} service(s)\n\n"
                "Next: Press (r) to poll for approvals"
            )

        except Exception as e:
            self._update_explanation(f"✗ Failed to create PRs:\n{e}")
        finally:
            self._operation_in_progress = False

    async def _create_single_pr(self, service: str) -> None:
        """Create a PR for a single service (simulated)."""
        self.log(f"Creating PR for {service}...")

        # Simulate API call with retry
        result = await retry_with_backoff(
            lambda: self._simulate_bitbucket_create_pr(service),
            max_retries=3,
            initial_delay=0.3,
            backoff_factor=2.0,
            on_retry=lambda attempt, ex: self.log(
                f"{service}: Retry #{attempt} after error: {ex}"
            ),
        )

        # Update state
        self.state.set(f"{service}_pr_status", "Open")
        self.state.set(f"{service}_pr_url", result["url"])

        self.log(f"{service}: PR created - {result['url']}")

    async def _simulate_bitbucket_create_pr(self, service: str) -> dict:
        """Simulate Bitbucket PR creation (may fail randomly)."""
        await asyncio.sleep(0.2)

        # 20% chance of API failure to demonstrate retry
        if random.random() < 0.2:
            raise Exception("Bitbucket API timeout")

        return {
            "url": f"{BITBUCKET_BASE_URL}/projects/PROJ/repos/{service}/pull-requests/123",
            "id": random.randint(100, 999),
        }

    def action_refresh(self) -> None:
        """Refresh status - poll all PRs and builds that need polling."""
        if self._operation_in_progress:
            self._update_explanation("Operation in progress. Please wait.")
            return

        # Find what needs polling
        to_poll_prs = []
        to_poll_builds = []

        for layer_services in self._services.values():
            for service in layer_services:
                pr_status = self.state.get(f"{service}_pr_status")
                build_status = self.state.get(f"{service}_build_status")

                # Poll open PRs
                if pr_status == "Open":
                    to_poll_prs.append(service)

                # Poll pending builds
                if build_status == "Pending":
                    to_poll_builds.append(service)

        if not to_poll_prs and not to_poll_builds:
            self._update_explanation(
                "Nothing to refresh.\n\n"
                "Create PRs first with (c),\n"
                "or merge PRs to trigger builds."
            )
            return

        msg_parts = ["Refreshing:\n"]
        if to_poll_prs:
            msg_parts.append(f"  • {len(to_poll_prs)} PR(s)")
        if to_poll_builds:
            msg_parts.append(f"  • {len(to_poll_builds)} build(s)")
        msg_parts.append("\n\nPolling...")

        self._update_explanation("\n".join(msg_parts))

        # Run async operation
        asyncio.create_task(self._refresh_all(to_poll_prs, to_poll_builds))

    async def _refresh_all(self, pr_services: list[str], build_services: list[str]) -> None:
        """Refresh PRs and builds."""
        self._operation_in_progress = True

        try:
            # Show "..." while polling
            for service in pr_services:
                self.state.set(f"{service}_pr_status", "...")
            for service in build_services:
                self.state.set(f"{service}_build_status", "...")

            # Poll PRs and builds in parallel
            operations = []

            for service in pr_services:
                operations.append(lambda s=service: self._poll_single_pr(s))

            for service in build_services:
                operations.append(lambda s=service: self._monitor_single_build(s))

            if operations:
                await run_parallel(*operations)

            # Count results
            approved = sum(
                1 for s in pr_services
                if self.state.get(f"{s}_pr_status") == "Approved"
            )
            builds_done = sum(
                1 for s in build_services
                if self.state.get(f"{s}_build_status") in ("Success", "Failed")
            )

            msg_parts = ["✓ Refresh complete:\n"]
            if pr_services:
                msg_parts.append(f"  • {approved}/{len(pr_services)} PR(s) approved")
            if build_services:
                msg_parts.append(f"  • {builds_done}/{len(build_services)} build(s) done")
            msg_parts.append("\n\nNext: Press (m) to merge approved PRs")

            self._update_explanation("\n".join(msg_parts))

        except Exception as e:
            self._update_explanation(f"✗ Failed to refresh:\n{e}")
        finally:
            self._operation_in_progress = False

    async def _poll_single_pr(self, service: str) -> None:
        """Poll a single PR for approval status (simulated)."""
        self.log(f"Polling PR for {service}...")

        # Poll with timeout
        approved = await poll_until(
            lambda: self._simulate_check_pr_approved(service),
            interval=0.5,
            timeout=3.0,
            on_check=lambda n: self.log(f"{service}: Approval check #{n}")
        )

        if approved:
            self.state.set(f"{service}_pr_status", "Approved")
            self.log(f"{service}: PR approved!")
        else:
            # Still open, not approved yet
            self.state.set(f"{service}_pr_status", "Open")
            self.log(f"{service}: PR not yet approved")

    async def _simulate_check_pr_approved(self, service: str) -> bool:
        """Simulate checking PR approval status."""
        await asyncio.sleep(0.3)
        # 40% chance of approval on each check
        return random.random() < 0.4

    def action_merge_prs(self) -> None:
        """Merge approved PRs (with confirmation)."""
        if self._operation_in_progress:
            self._update_explanation("Operation in progress. Please wait.")
            return

        selected = self._get_selected_services()
        if not selected:
            self._update_explanation(
                "No services selected.\n\n"
                "Select services and press (m) to merge."
            )
            self._pending_action = None
            return

        # Filter to approved PRs
        approved = [
            s for s in selected
            if self.state.get(f"{s}_pr_status") == "Approved"
        ]

        if not approved:
            self._update_explanation(
                "No approved PRs in selection.\n\n"
                "Refresh with (r) to check approval status."
            )
            self._pending_action = None
            return

        # Two-press confirmation
        if self._pending_action == "merge_prs" and self._pending_services == approved:
            # Second press - execute
            self._pending_action = None
            self._pending_services = None
            self._update_explanation(f"Merging {len(approved)} PR(s)...")
            asyncio.create_task(self._merge_prs(approved))
        else:
            # First press - show confirmation
            self._pending_action = "merge_prs"
            self._pending_services = approved
            self._update_explanation(
                f"Merge {len(approved)} approved PR(s)?\n\n"
                + "\n".join(f"  • {s}" for s in approved)
                + "\n\nPress (m) again to confirm."
            )

    async def _merge_prs(self, services: list[str]) -> None:
        """Merge approved PRs."""
        self._operation_in_progress = True

        try:
            # Show "..." while merging
            for service in services:
                self.state.set(f"{service}_pr_status", "...")

            # Merge in parallel
            operations = [
                lambda s=service: self._merge_single_pr(s)
                for service in services
            ]

            await run_parallel(*operations)

            self._update_explanation(
                f"✓ Merged {len(services)} PR(s)\n\n"
                "Builds queued.\n"
                "Next: Press (r) to monitor builds"
            )

        except Exception as e:
            self._update_explanation(f"✗ Failed to merge PRs:\n{e}")
        finally:
            self._operation_in_progress = False

    async def _merge_single_pr(self, service: str) -> None:
        """Merge a single PR (simulated)."""
        self.log(f"Merging PR for {service}...")

        await retry_with_backoff(
            lambda: self._simulate_bitbucket_merge_pr(service),
            max_retries=3,
            initial_delay=0.3,
        )

        self.state.set(f"{service}_pr_status", "Merged")
        self.state.set(f"{service}_build_status", "Pending")

        self.log(f"{service}: PR merged, build queued")

    async def _simulate_bitbucket_merge_pr(self, service: str) -> None:
        """Simulate PR merge."""
        await asyncio.sleep(0.2)

        # 10% chance of conflict
        if random.random() < 0.1:
            raise Exception("Merge conflict detected")

    async def _monitor_single_build(self, service: str) -> None:
        """Monitor a single Jenkins build (simulated)."""
        self.log(f"Monitoring build for {service}...")

        # Poll for build completion
        success = await poll_until(
            lambda: self._simulate_check_jenkins_build_complete(service),
            interval=0.5,
            timeout=3.0,
            on_check=lambda n: self.log(f"{service}: Build check #{n}")
        )

        if success:
            # Simulate extracting version from artifact
            new_version = f"1.{random.randint(1, 5)}.{random.randint(0, 20)}"
            self.state.set(f"{service}_build_status", "Success")
            self.state.set(f"{service}_version", new_version)
            self.log(f"{service}: Build succeeded - version {new_version}")
        else:
            # Still pending
            self.state.set(f"{service}_build_status", "Pending")
            self.log(f"{service}: Build still in progress")

    async def _simulate_check_jenkins_build_complete(self, service: str) -> bool:
        """Simulate checking Jenkins build status."""
        await asyncio.sleep(0.3)
        # 50% chance of completion on each check
        return random.random() < 0.5

    def action_update_deps(self) -> None:
        """Update dependencies in next layer (with confirmation)."""
        if self._operation_in_progress:
            self._update_explanation("Operation in progress. Please wait.")
            return

        selected = self._get_selected_services()
        if not selected:
            self._update_explanation(
                "No services selected.\n\n"
                "Select services and press (u) to update dependencies."
            )
            self._pending_action = None
            return

        # Filter to services with successful builds
        successful = [
            s for s in selected
            if self.state.get(f"{s}_build_status") == "Success"
        ]

        if not successful:
            self._update_explanation(
                "No successful builds in selection.\n\n"
                "Refresh with (r) to check build status."
            )
            self._pending_action = None
            return

        # Find dependent services
        dependent_services = []
        layer_names = list(self._services.keys())

        for service in successful:
            # Find service's layer
            service_layer = None
            for layer_name, layer_services in self._services.items():
                if service in layer_services:
                    service_layer = layer_name
                    break

            if service_layer:
                # Find next layer
                layer_idx = layer_names.index(service_layer)
                if layer_idx + 1 < len(layer_names):
                    next_layer = layer_names[layer_idx + 1]
                    dependent_services.extend(self._services[next_layer])

        # Remove duplicates
        dependent_services = list(set(dependent_services))

        if not dependent_services:
            self._update_explanation(
                "No dependent services.\n\n"
                "Selected services are in the last layer."
            )
            self._pending_action = None
            return

        # Two-press confirmation
        if self._pending_action == "update_deps" and self._pending_services == (successful, dependent_services):
            # Second press - execute
            self._pending_action = None
            self._pending_services = None
            self._update_explanation(f"Updating {len(dependent_services)} service(s)...")
            asyncio.create_task(self._update_deps(successful, dependent_services))
        else:
            # First press - show confirmation
            self._pending_action = "update_deps"
            self._pending_services = (successful, dependent_services)
            self._update_explanation(
                f"Update pom.xml in {len(dependent_services)} service(s)?\n\n"
                + "\n".join(f"  • {s}" for s in dependent_services)
                + f"\n\nUsing versions from:\n"
                + "\n".join(
                    f"  • {s}: {self.state.get(f'{s}_version')}"
                    for s in successful
                )
                + "\n\nPress (u) again to confirm."
            )

    async def _update_deps(self, source_services: list[str], target_services: list[str]) -> None:
        """Update dependencies (simulated)."""
        self._operation_in_progress = True

        try:
            # Simulate updating pom.xml files
            await asyncio.sleep(1.0)

            self._update_explanation(
                f"✓ Updated pom.xml in {len(target_services)} service(s)\n\n"
                "Next steps:\n"
                "1. Commit and push changes manually\n"
                "   (git add, commit, push)\n"
                "2. Navigate to next layer\n"
                "3. Press (l) to select it\n"
                "4. Press (c) to create PRs"
            )

        except Exception as e:
            self._update_explanation(f"✗ Failed to update dependencies:\n{e}")
        finally:
            self._operation_in_progress = False

    def action_info(self) -> None:
        """Show workflow information in explanation panel."""
        self._pending_action = None
        self._update_explanation(
            "Layered Workflow\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "State Management:\n"
            "• StateManager tracks service state\n"
            "• Watchers update UI in real-time\n"
            "• '...' shown while polling\n\n"
            "Async Utilities:\n"
            "• run_parallel() - Concurrent ops\n"
            "• retry_with_backoff() - Reliability\n"
            "• poll_until() - Wait for changes\n\n"
            "Workflow:\n"
            "1. (l) Select layer\n"
            "2. (c) Create PRs (press twice)\n"
            "3. (r) Refresh - poll PR status\n"
            "4. (m) Merge approved (press twice)\n"
            "5. (r) Refresh - monitor builds\n"
            "6. (u) Update deps (press twice)\n"
            "7. Manually commit and push\n"
            "8. Repeat for next layer\n\n"
            "Two-press Confirmation:\n"
            "Actions (c, m, u) require two presses:\n"
            "First shows what will happen,\n"
            "second confirms and executes.\n\n"
            "Manual Steps:\n"
            "After (u) updating dependencies,\n"
            "you must manually commit and push\n"
            "changes before creating PRs for\n"
            "the next layer.\n\n"
            "Real Usage:\n"
            "Replace _simulate_*() with\n"
            "actual Bitbucket/Jenkins APIs.\n"
            "See code comments for examples."
        )

    def _get_selected_services(self) -> list[str]:
        """Get currently selected services from the dashboard."""
        if not isinstance(self.screen, UniversalScreen):
            return []

        values = self.screen._collect_values()
        selected_rows = values.get("services", [])

        return [row.row_key for row in selected_rows if row.row_key]


def main():
    """Run the app."""
    app = LayeredWorkflowApp()
    app.run()


if __name__ == "__main__":
    main()
