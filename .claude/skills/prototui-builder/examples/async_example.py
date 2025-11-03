"""
Async utilities example using UniversalScreen.

Demonstrates:
- retry_with_backoff for unreliable operations
- poll_until for waiting on conditions
- run_parallel for concurrent operations

Run with: python -m examples.async_example
"""

import asyncio
import random
from textual.app import App
from textual.binding import Binding

from prototui import UniversalScreen, Field, TableRow
from prototui.utils.async_helpers import (
    retry_with_backoff,
    poll_until,
    run_parallel,
)


class AsyncExampleApp(App):
    """Demonstrate async utilities with a simulated deployment workflow."""

    CSS_PATH = "../prototui/themes/default.tcss"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._deployment_status = "pending"
        self._services = ["api-gateway", "auth-service", "user-service"]
        self._service_results = {}

    def on_mount(self) -> None:
        """Show service selection screen."""
        rows = [
            TableRow({"Service": service, "Status": "Ready"})
            for service in self._services
        ]

        screen = UniversalScreen(
            title="Deploy Services",
            fields=[
                Field(
                    id="services",
                    field_type="table",
                    columns=["Service", "Status"],
                    rows=rows,
                    select_mode="multi",
                    show_layers=False,
                    show_column_headers=True,
                    required=True
                )
            ],
            explanation_title="Select Services to Deploy",
            explanation_content=(
                "This example demonstrates async utilities:\n\n"
                "• retry_with_backoff - Retries flaky operations\n"
                "• poll_until - Polls deployment status\n"
                "• run_parallel - Deploys services concurrently\n\n"
                "Select one or more services to deploy."
            ),
            submit_label="Deploy",
            custom_bindings=[
                Binding("i", "app.info", "Info", show=True),
            ]
        )

        self.push_screen(screen, self._handle_deploy)

    def action_info(self) -> None:
        """Show info about async utilities."""
        info_screen = UniversalScreen(
            title="Async Utilities Information",
            message=(
                "async_helpers module provides:\n\n"
                "• retry_with_backoff()\n"
                "  Retries operations with exponential backoff\n"
                "  Useful for: API calls, network operations\n\n"
                "• poll_until()\n"
                "  Polls a condition until true or timeout\n"
                "  Useful for: Waiting for deployments, builds\n\n"
                "• run_parallel()\n"
                "  Runs multiple operations concurrently\n"
                "  Useful for: Batch operations, parallel fetches\n\n"
                "• run_parallel_with_limit()\n"
                "  Parallel execution with concurrency limit\n"
                "  Useful for: Rate-limited APIs\n\n"
                "• run_with_timeout()\n"
                "  Runs operation with timeout\n"
                "  Useful for: Long-running operations"
            ),
            explanation_title="Utilities",
            explanation_content="All utilities are async and return results or raise exceptions.",
            submit_label="OK"
        )
        self.push_screen(info_screen)

    async def _handle_deploy(self, result) -> None:
        """Handle deployment request."""
        if not result.confirmed:
            self.exit()
            return

        selected = result.values.get("services", [])
        if not selected:
            self.exit()
            return

        service_names = [row.values["Service"] for row in selected]

        # Show deploying screen
        deploying_screen = UniversalScreen(
            title="Deploying...",
            message=(
                f"Deploying {len(service_names)} service(s):\n\n"
                + "\n".join(f"  • {name}" for name in service_names)
                + "\n\nPlease wait..."
            ),
            explanation_title="In Progress",
            explanation_content="Services are being deployed in parallel with retry logic.",
            allow_submit=False
        )

        # Push screen without callback (we'll pop it manually)
        self.push_screen(deploying_screen)

        # Deploy services in parallel
        try:
            await self._deploy_services(service_names)
            self.pop_screen()  # Remove deploying screen
            self._show_results(service_names)
        except Exception as e:
            self.pop_screen()  # Remove deploying screen
            self._show_error(str(e))

    async def _deploy_services(self, service_names: list[str]) -> None:
        """Deploy multiple services in parallel with retry logic."""
        # Create deployment operations for each service
        operations = [
            lambda name=name: self._deploy_single_service(name)
            for name in service_names
        ]

        # Run all deployments in parallel
        results = await run_parallel(*operations)

        # Store results
        for name, result in zip(service_names, results):
            self._service_results[name] = result

    async def _deploy_single_service(self, service_name: str) -> str:
        """Deploy a single service with retry logic."""
        self.log(f"Deploying {service_name}...")

        # Simulate deployment with retry_with_backoff
        result = await retry_with_backoff(
            lambda: self._unreliable_deploy(service_name),
            max_retries=3,
            initial_delay=0.5,
            backoff_factor=2.0,
            on_retry=lambda attempt, ex: self.log(
                f"{service_name}: Retry {attempt} after error: {ex}"
            )
        )

        self.log(f"{service_name}: Deployment initiated, polling status...")

        # Poll for deployment completion
        success = await poll_until(
            lambda: self._check_deployment_complete(service_name),
            interval=0.5,
            timeout=10.0,
            on_check=lambda n: self.log(f"{service_name}: Check #{n}")
        )

        if success:
            return f"✓ {service_name} deployed successfully"
        else:
            return f"✗ {service_name} deployment timed out"

    async def _unreliable_deploy(self, service_name: str) -> str:
        """Simulate an unreliable deployment operation that might fail."""
        await asyncio.sleep(0.2)

        # 40% chance of failure to demonstrate retry logic
        if random.random() < 0.4:
            raise Exception(f"Network error deploying {service_name}")

        return f"{service_name} deployment started"

    async def _check_deployment_complete(self, service_name: str) -> bool:
        """Simulate checking if deployment is complete."""
        await asyncio.sleep(0.3)

        # 30% chance of completion each check
        return random.random() < 0.3

    def _show_results(self, service_names: list[str]) -> None:
        """Show deployment results."""
        results_text = "\n".join(
            self._service_results.get(name, f"? {name} - unknown")
            for name in service_names
        )

        success_count = sum(
            1 for result in self._service_results.values()
            if "✓" in result
        )

        results_screen = UniversalScreen(
            title="Deployment Complete",
            message=(
                f"Deployed {len(service_names)} service(s):\n\n"
                f"{results_text}\n\n"
                f"Success: {success_count}/{len(service_names)}"
            ),
            explanation_title="Results",
            explanation_content=(
                "Deployment used async utilities:\n"
                "• retry_with_backoff for unreliable operations\n"
                "• poll_until to wait for completion\n"
                "• run_parallel to deploy concurrently"
            ),
            submit_label="OK"
        )

        self.push_screen(results_screen, lambda _: self.exit())

    def _show_error(self, error: str) -> None:
        """Show error screen."""
        error_screen = UniversalScreen(
            title="Deployment Failed",
            message=f"✗ Error during deployment:\n\n{error}",
            explanation_title="Error",
            explanation_content="Check logs for details.",
            submit_label="OK"
        )

        self.push_screen(error_screen, lambda _: self.exit())


def main():
    """Run the app."""
    app = AsyncExampleApp()
    app.run()


if __name__ == "__main__":
    main()
