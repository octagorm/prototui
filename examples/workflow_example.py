"""
Workflow example demonstrating multi-screen flow with UniversalScreen.

This example shows:
1. Multi-select table of tasks
2. Input screen to add description for selected tasks
3. Return to table with new "Description" column
4. Info screen showing completion

Run with: python -m examples.workflow_example
"""

from textual.app import App
from textual.binding import Binding

from prototui.screens.universal_screen import UniversalScreen, Field, ScreenResult
from prototui.components.layered_data_table import TableRow


class WorkflowExampleApp(App):
    """Demonstrate multi-screen workflow using UniversalScreen."""

    CSS_PATH = "../prototui/themes/default.tcss"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Initialize task data
        self._tasks = [
            TableRow(
                {"Task": "Implement login", "Status": "In Progress"},
                layer="Frontend",
                row_key="task-1"
            ),
            TableRow(
                {"Task": "Create API endpoints", "Status": "Pending"},
                layer="Backend",
                row_key="task-2"
            ),
            TableRow(
                {"Task": "Setup database", "Status": "Complete"},
                layer="Backend",
                row_key="task-3"
            ),
            TableRow(
                {"Task": "Write tests", "Status": "Pending"},
                layer="Testing",
                row_key="task-4"
            ),
            TableRow(
                {"Task": "Deploy to staging", "Status": "Pending"},
                layer="DevOps",
                row_key="task-5"
            ),
        ]

        # Track descriptions added by user
        self._descriptions: dict[str, str] = {}

        # Track if we've added the Description column yet
        self._description_column_added = False

    def on_mount(self) -> None:
        """Show the main task selection screen."""
        self._show_task_screen()

    def _show_task_screen(self) -> None:
        """Show the main task selection screen."""
        # Determine columns based on whether descriptions have been added
        if self._description_column_added:
            columns = ["Task", "Status", "Description"]
        else:
            columns = ["Task", "Status"]

        # Update task rows with descriptions if they exist
        for task in self._tasks:
            task_key = task.row_key or ""
            if task_key in self._descriptions:
                task.values["Description"] = self._descriptions[task_key]
            elif "Description" in task.values:
                task.values["Description"] = task.values.get("Description", "")

        screen = UniversalScreen(
            title="Task Management",
            fields=[
                Field(
                    id="tasks",
                    field_type="table",
                    columns=columns,
                    rows=self._tasks,
                    select_mode="multi",  # Multi-select for choosing multiple tasks
                    show_layers=True,
                    auto_height=False  # Fill available vertical space (not form-sized)
                )
            ],
            explanation_title="Manage Tasks",
            explanation_content=(
                "Select tasks using Space, then use 'd' to add descriptions.\n\n"
                "This demonstrates:\n"
                "• Multi-select table with checkboxes\n"
                "• Custom action keys (d, i)\n"
                "• Dynamic column updates\n"
                "• Persistent screen with allow_submit=False\n\n"
                "Check the footer for available actions."
            ),
            explanation_hint="",
            submit_label="Continue",
            allow_submit=False,  # Disable Enter key - use action keys instead
            custom_bindings=[
                Binding("d", "app.describe", "Describe", show=True),
                Binding("i", "app.info", "Info", show=True),
            ]
        )

        self.push_screen(screen, self._handle_task_screen_result)

    def _handle_task_screen_result(self, result: ScreenResult) -> None:
        """Handle task screen dismissal (only happens on ESC)."""
        # With allow_submit=False, this only gets called when ESC is pressed
        # User pressed ESC - exit the app
        self.exit()

    def action_describe(self) -> None:
        """Show description input for selected tasks."""
        self.log("action_describe called!")
        # Get the currently displayed screen
        if not isinstance(self.screen, UniversalScreen):
            return

        # Collect current values to see what's selected
        values = self.screen._collect_values()
        selected_tasks = values.get("tasks", [])

        if not selected_tasks:
            # No tasks selected, show info message
            info_screen = UniversalScreen(
                title="No Selection",
                message="Please select at least one task first.\n\nUse Space to toggle task selection.",
                explanation_title="Info",
                explanation_content="Select tasks before adding descriptions.",
                explanation_hint="Press Enter to continue",
                submit_label="OK"
            )
            self.push_screen(info_screen)
            return

        # Build task list for display
        task_names = [task.values.get("Task", "") for task in selected_tasks]
        tasks_text = "\n".join(f"  • {name}" for name in task_names)

        # Show input screen for description
        input_screen = UniversalScreen(
            title="Add Description",
            message=f"Adding description for {len(selected_tasks)} task(s):\n\n{tasks_text}",
            fields=[
                Field(
                    id="description",
                    field_type="text",
                    label="Description:",
                    placeholder="Enter description for selected tasks..."
                )
            ],
            explanation_title="Describe Tasks",
            explanation_content=(
                "Enter a description that will be added to all selected tasks.\n\n"
                "This description will appear in a new column in the task table."
            ),
            explanation_hint="Enter to save",
            submit_label="Save"
        )

        self.push_screen(input_screen, lambda result: self._handle_description(result, selected_tasks))

    def _handle_description(self, result: ScreenResult, selected_tasks: list[TableRow]) -> None:
        """Handle the description input result."""
        if result.confirmed:
            description = result.values.get("description", "").strip()

            if description:
                # Add description to selected tasks
                for task in selected_tasks:
                    task_key = task.row_key or ""
                    if task_key:
                        self._descriptions[task_key] = description

                # Mark that we need to show the Description column now
                if not self._description_column_added:
                    self._description_column_added = True

                # Pop current screen and show updated task screen
                self.pop_screen()
                self._show_task_screen()

                # Show success message
                success_screen = UniversalScreen(
                    title="Description Added",
                    message=(
                        f"✓ Added description to {len(selected_tasks)} task(s):\n\n"
                        f'"{description}"\n\n'
                        "The task table now shows the Description column."
                    ),
                    explanation_title="Success",
                    explanation_content="Description saved successfully!",
                    explanation_hint="Press Enter to continue",
                    submit_label="OK"
                )
                self.push_screen(success_screen)

    def action_info(self) -> None:
        """Show completion info."""
        self.log("action_info called!")
        total_tasks = len(self._tasks)
        described_tasks = len(self._descriptions)

        info_screen = UniversalScreen(
            title="Workflow Information",
            message=(
                f"Task Summary:\n\n"
                f"  Total tasks: {total_tasks}\n"
                f"  Tasks with descriptions: {described_tasks}\n"
                f"  Tasks pending: {total_tasks - described_tasks}\n\n"
                "This demonstrates how UniversalScreen can be used\n"
                "for both interactive forms and informational displays."
            ),
            explanation_title="Info",
            explanation_content=(
                "This workflow demonstrates:\n"
                "• Multi-select tables\n"
                "• Text input screens\n"
                "• Dynamic column updates\n"
                "• Info/message screens\n\n"
                "All using the same UniversalScreen pattern!"
            ),
            explanation_hint="Press Enter to continue",
            submit_label="OK"
        )

        self.push_screen(info_screen)


def main():
    """Run the app."""
    app = WorkflowExampleApp()
    app.run()


if __name__ == "__main__":
    main()
