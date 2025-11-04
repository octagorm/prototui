"""
Pattern: Persistent Storage

Use this for applications that need to save configuration across sessions.

Example use cases:
- Multi-repo PR workflows with shared CHANGE branch
- Tool preferences and settings
- Session state management
- User configuration for CLI tools

Features:
- JSON-based configuration persistence
- Form screen with conditional field visibility
- Pre-filled inputs from saved configuration
- Review step before submission
- Toast notifications for feedback
- External editor integration
- Simulated metarepo PR workflow

Run: python patterns/persistent_storage.py
"""

# Add parent directory to path to import utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import subprocess
from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Header, Footer, Input, Label
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.binding import Binding

from utilities.layered_data_table import LayeredDataTable, TableRow
from utilities.explanation_panel import ExplanationPanel


CONFIG_FILE = Path(__file__).parent / "persistent_storage.json"


class ConfigManager:
    """Simple JSON-based configuration manager."""

    def __init__(self, config_file: Path):
        self.config_file = config_file

    def load(self) -> dict:
        """Load configuration from JSON file."""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def save(self, config: dict) -> None:
        """Save configuration to JSON file."""
        try:
            # Atomic write: write to temp file, then rename
            temp_file = self.config_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(config, f, indent=2)
            temp_file.replace(self.config_file)
        except IOError as e:
            raise Exception(f"Failed to save config: {e}")

    def get(self, key: str, default=None):
        """Get a configuration value."""
        config = self.load()
        return config.get(key, default)

    def set(self, key: str, value) -> None:
        """Set a configuration value."""
        config = self.load()
        config[key] = value
        self.save(config)


class PRFormScreen(ModalScreen[dict | None]):
    """Form screen for creating PRs with conditional CHANGE branch input."""

    BINDINGS = [
        Binding("enter", "submit", "Submit", show=True, priority=True),
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(self, selected_repos: list[dict], saved_change_branch: str | None, main_branch: str = "main"):
        super().__init__()
        self.selected_repos = selected_repos
        self.saved_change_branch = saved_change_branch
        self.main_branch = main_branch
        self._review_mode = False
        self._submitted_values = None

        # Determine available PR options based on repo states
        change_pr_status = [r["pr_to_change"] for r in selected_repos]
        all_have_merged_change = all(status == "Merged" for status in change_pr_status)
        any_have_change_pr = any(status != "None" for status in change_pr_status)

        self.all_have_merged_change = all_have_merged_change
        self.any_have_change_pr = any_have_change_pr

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="pr-form-container"):
            # Left: Form
            with Vertical(id="pr-form-pane"):
                yield Label("Select PR Direction", id="pr-direction-label")

                # Build PR direction options based on state
                pr_rows = []
                if self.all_have_merged_change:
                    # Only show CHANGE -> main option
                    pr_rows.append(
                        TableRow(
                            {"Source": "CHANGE branch", "Target": f"{self.main_branch}"},
                            row_key="change_to_main"
                        )
                    )
                else:
                    # Show feature -> CHANGE and feature -> main
                    pr_rows.append(
                        TableRow(
                            {"Source": "feature/FOO-123", "Target": "CHANGE branch"},
                            row_key="feature_to_change"
                        )
                    )
                    pr_rows.append(
                        TableRow(
                            {"Source": "feature/FOO-123", "Target": self.main_branch},
                            row_key="feature_to_main"
                        )
                    )

                yield LayeredDataTable(
                    id="pr-direction-table",
                    columns=["Source", "Target"],
                    rows=pr_rows,
                    select_mode="radio",
                    show_layers=False,
                    filterable=False,
                    show_column_headers=True,
                    auto_height=True
                )

                # CHANGE branch name input (conditional)
                yield Label("CHANGE Branch Name", id="change-branch-label", classes="conditional-field")
                yield Input(
                    placeholder="e.g., feature/CHANGE-12345",
                    value=self.saved_change_branch or "",
                    id="change-branch-input",
                    classes="conditional-field"
                )

            # Right: Explanation
            with VerticalScroll(id="pr-explanation-pane"):
                repos_list = "\n".join(f"  • {r['name']}" for r in self.selected_repos)

                # Build explanation based on repo states
                explanation_text = f"Repositories:\n{repos_list}\n\n"

                if self.all_have_merged_change:
                    explanation_text += "[bold green]All repos have merged CHANGE PRs[/bold green]\n"
                    explanation_text += "Next step: Create PRs to {}\n\n".format(self.main_branch)
                elif self.any_have_change_pr:
                    explanation_text += "[bold yellow]Note:[/bold yellow] Some repos have CHANGE PRs\n"
                    explanation_text += "Only showing feature branch options\n\n"

                explanation_text += "1. Select PR direction (source → target)\n"
                explanation_text += "2. If target is CHANGE, specify branch name\n"
                explanation_text += "3. Press Enter to review\n"
                explanation_text += "4. Press Enter again to confirm"

                yield ExplanationPanel(
                    f"Create PR for {len(self.selected_repos)} repo(s)",
                    explanation_text
                )

        yield Footer()

    def on_mount(self) -> None:
        # Make panes non-focusable
        self.query_one("#pr-form-pane").can_focus = False
        self.query_one("#pr-explanation-pane").can_focus = False

        # Focus the PR direction table
        def focus_table():
            table = self.query_one("#pr-direction-table", LayeredDataTable)
            table.focus()

        self.call_after_refresh(focus_table)

        # Initially hide CHANGE branch field
        self.call_after_refresh(self._update_change_field_visibility)

    def on_layered_data_table_row_selected(self, event: LayeredDataTable.RowSelected) -> None:
        """Handle PR direction selection change."""
        self._update_change_field_visibility()

    def _update_change_field_visibility(self) -> None:
        """Show/hide CHANGE branch field based on PR direction selection."""
        table = self.query_one("#pr-direction-table", LayeredDataTable)
        selected = table.get_selected_rows()

        label = self.query_one("#change-branch-label", Label)
        input_field = self.query_one("#change-branch-input", Input)

        # Show CHANGE field if target is CHANGE (feature_to_change)
        if selected and selected[0].row_key == "feature_to_change":
            # Show CHANGE branch field and focus it
            label.styles.display = "block"
            input_field.styles.display = "block"
            # Focus the input field when it becomes visible
            self.call_after_refresh(lambda: input_field.focus())
        else:
            # Hide CHANGE branch field
            label.styles.display = "none"
            input_field.styles.display = "none"

    def action_submit(self) -> None:
        """Validate and submit form."""
        if self._review_mode:
            # Confirm and dismiss
            self.dismiss(self._submitted_values)
            return

        # Get PR direction selection
        direction_table = self.query_one("#pr-direction-table", LayeredDataTable)
        selected = direction_table.get_selected_rows()

        if not selected:
            self.notify("Please select a PR direction", severity="warning")
            return

        direction = selected[0].row_key

        # Parse direction into source and target
        if direction == "feature_to_change":
            source = "issue"
            target = "change"
        elif direction == "feature_to_main":
            source = "issue"
            target = "main"
        elif direction == "change_to_main":
            source = "change"
            target = "main"
        else:
            self.notify("Invalid PR direction", severity="error")
            return

        values = {"source": source, "target": target, "repos": self.selected_repos}

        # Validate CHANGE branch if target is CHANGE
        if target == "change":
            change_input = self.query_one("#change-branch-input", Input)
            change_branch = change_input.value.strip()

            if not change_branch:
                change_input.add_class("error")
                self.notify("CHANGE branch name is required", severity="error")
                return

            change_input.remove_class("error")
            values["change_branch"] = change_branch

        # Show review
        self._submitted_values = values
        self._show_review()
        self._review_mode = True

    def _show_review(self) -> None:
        """Show review in explanation pane."""
        values = self._submitted_values
        source = values["source"]
        target = values["target"]

        # Format source and target descriptions
        if source == "change":
            source_desc = "CHANGE branch"
        else:
            source_desc = "Issue branch (feature/FOO-123)"

        if target == "change":
            target_desc = f"CHANGE branch ({values['change_branch']})"
        else:
            target_desc = f"Main branch ({self.main_branch})"

        repos_list = "\n".join(f"  • {r['name']}" for r in values["repos"])

        explanation = self.query_one(ExplanationPanel)

        review_text = (
            f"[bold]Action:[/bold] Create {len(values['repos'])} pull request(s)\n"
            f"[bold]Source:[/bold] {source_desc}\n"
            f"[bold]Target:[/bold] {target_desc}\n\n"
            f"[bold]Repositories:[/bold]\n{repos_list}\n\n"
            f"This will create PRs from {source_desc} to {target_desc}.\n\n"
            "[bold]Press Enter to confirm[/bold]\n"
            "[bold]Press Escape to cancel[/bold]"
        )

        explanation.update_content("⚠️  Review PR Creation", review_text)

    def action_cancel(self) -> None:
        """Cancel form."""
        if self._review_mode:
            # Go back to editing
            self._review_mode = False
            explanation = self.query_one(ExplanationPanel)
            repos_list = "\n".join(f"  • {r['name']}" for r in self.selected_repos)
            explanation.update_content(
                f"Create PR for {len(self.selected_repos)} repo(s)",
                f"Repositories:\n{repos_list}\n\n"
                "1. Select target: CHANGE or Main\n"
                "2. If CHANGE, specify branch name\n"
                "3. Press Enter to review\n"
                "4. Press Enter again to confirm"
            )
        else:
            self.dismiss(None)


class SelectionScreen(ModalScreen[str]):
    """Modal screen with a simple list selection (arrow keys + Enter)."""

    BINDINGS = [
        Binding("enter", "select", "Select", show=True),
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(self, title: str, options: list[tuple[str, str]]):
        """
        Args:
            title: Question/prompt to display
            options: List of (value, display_text) tuples
        """
        super().__init__()
        self.title_text = title
        self.options = options

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="selection-dialog"):
            yield Label(self.title_text, id="selection-label")
            table = LayeredDataTable(
                id="selection-table",
                columns=["Option"],
                rows=[TableRow({"Option": display}, row_key=value) for value, display in self.options],
                select_mode="single",
                show_layers=False,
                filterable=False
            )
            yield table
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#selection-table", LayeredDataTable)
        # Ensure table is visible and focused
        table.can_focus = True
        self.set_focus(table)

    def action_select(self) -> None:
        """Select the current option."""
        table = self.query_one("#selection-table", LayeredDataTable)
        cursor_row = table.get_cursor_row()
        if cursor_row and cursor_row.row_key:
            self.dismiss(cursor_row.row_key)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


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


class MetarepoDashboard(Screen):
    """Main dashboard screen with persistent configuration."""

    BINDINGS = [
        Binding("p", "create_pr", "Create PR", show=True),
        Binding("m", "merge_pr", "Merge PR", show=True),
        Binding("space", "toggle_repo", "Select", show=True),
        Binding("a", "toggle_all", "Toggle All", show=True),
        Binding("o", "open_config", "Open Config", show=True),
        Binding("i", "info", "Info", show=True),
        Binding("q", "request_quit", "Quit", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager(CONFIG_FILE)

        # Simulated metarepo state (in-memory only)
        # PR status: None, Open, Merged
        self.repos = [
            {"name": "frontend", "current_branch": "feature/FOO-123", "pr_to_change": "None", "pr_to_main": "None"},
            {"name": "backend", "current_branch": "feature/FOO-123", "pr_to_change": "None", "pr_to_main": "None"},
            {"name": "shared-lib", "current_branch": "feature/FOO-123", "pr_to_change": "None", "pr_to_main": "None"},
            {"name": "api-gateway", "current_branch": "feature/FOO-123", "pr_to_change": "None", "pr_to_main": "None"},
            {"name": "mobile-app", "current_branch": "feature/FOO-123", "pr_to_change": "None", "pr_to_main": "None"},
        ]

        # Simulated remote main branch name (could be "main" or "master")
        self.main_branch = "main"

        # Two-press confirmation state for merge
        self._pending_merge_action = None  # "change" or "main"
        self._pending_merge_repos = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main-container"):
            with Vertical(id="content-pane"):
                yield LayeredDataTable(
                    id="repos-table",
                    columns=["Repository", "Current Branch", "PR to CHANGE", "PR to Main"],
                    rows=self._build_table_rows(),
                    select_mode="multi",
                    show_layers=False,
                    filterable=True
                )

            with VerticalScroll(id="explanation-pane"):
                yield ExplanationPanel(
                    "Metarepo PR Workflow",
                    self._get_status_text()
                )

        yield Footer()

    def on_mount(self) -> None:
        self._update_subtitle()

        # Make explanation pane non-focusable
        explanation_pane = self.query_one("#explanation-pane")
        explanation_pane.can_focus = False

    def _get_status_text(self) -> str:
        """Generate status text for explanation panel."""
        change_branch = self.config_manager.get("change_branch", "Not set")

        return (
            f"[bold]Configuration:[/bold]\n"
            f"CHANGE Branch: {change_branch}\n"
            f"Config File: {CONFIG_FILE.name}\n\n"
            f"[bold]Actions:[/bold]\n"
            f"• (p) Create PR - create pull requests\n"
            f"• (m) Merge PR - merge open pull requests\n"
            f"• (o) Open config file in editor\n"
            f"• (Space) Select repository\n"
            f"• (a) Toggle all repositories\n"
            f"• (i) Show pattern information\n\n"
            f"[bold]Workflow:[/bold]\n"
            f"1. Select repos with Space\n"
            f"2. Create PRs to CHANGE (p)\n"
            f"3. Merge CHANGE PRs (m)\n"
            f"4. Create PRs to main (p)\n"
            f"5. Merge main PRs (m)\n\n"
            f"PR statuses: None → Open → Merged"
        )

    def _build_table_rows(self) -> list[TableRow]:
        """Build table rows from current repo state."""
        rows = []
        for repo in self.repos:
            rows.append(
                TableRow(
                    {
                        "Repository": repo["name"],
                        "Current Branch": repo["current_branch"],
                        "PR to CHANGE": repo["pr_to_change"],
                        "PR to Main": repo["pr_to_main"]
                    },
                    row_key=repo["name"]
                )
            )
        return rows

    def _update_table(self) -> None:
        """Update table with current repo state."""
        table = self.query_one(LayeredDataTable)
        table.set_rows(self._build_table_rows())

    def _update_explanation(self, title: str = None, content: str = None) -> None:
        """Update explanation panel."""
        panel = self.query_one(ExplanationPanel)
        if title is None:
            panel.update_content("Metarepo PR Workflow", self._get_status_text())
        else:
            panel.update_content(title, content)

    def _update_subtitle(self) -> None:
        """Update subtitle with selection count."""
        table = self.query_one(LayeredDataTable)
        selected = table.get_selected_rows()
        count = len(selected)
        self.sub_title = f"Metarepo Dashboard ({count} selected)"

    def _get_selected_repos(self) -> list[dict]:
        """Get list of selected repository objects."""
        table = self.query_one(LayeredDataTable)
        selected_rows = table.get_selected_rows()
        selected_names = {row.row_key for row in selected_rows}
        return [repo for repo in self.repos if repo["name"] in selected_names]

    def on_layered_data_table_row_toggled(self, event: LayeredDataTable.RowToggled) -> None:
        """Handle row selection changes."""
        self._update_subtitle()

    def action_toggle_repo(self) -> None:
        """Toggle current row selection."""
        table = self.query_one(LayeredDataTable)
        table.toggle_current_row()

    def action_toggle_all(self) -> None:
        """Toggle all rows."""
        table = self.query_one(LayeredDataTable)
        table.toggle_all_rows()
        self._update_subtitle()

    def action_create_pr(self) -> None:
        """Create PR for selected repositories using form screen."""
        # Clear any pending merge confirmation
        self._pending_merge_action = None
        self._pending_merge_repos = None

        selected = self._get_selected_repos()

        if not selected:
            self.notify("No repositories selected. Use Space to select repos.", severity="warning")
            return

        # Get saved CHANGE branch (if any)
        saved_change_branch = self.config_manager.get("change_branch")

        def handle_pr_form_result(result: dict | None) -> None:
            if not result:
                return  # Cancelled

            target = result["target"]
            repos = result["repos"]

            if target == "change":
                change_branch = result["change_branch"]
                # Save the CHANGE branch if it changed
                if change_branch != saved_change_branch:
                    self.config_manager.set("change_branch", change_branch)
                    self._update_explanation()  # Refresh status display
                self._create_prs_to_change(repos, change_branch)
            else:
                self._create_prs_to_main(repos)

        self.app.push_screen(
            PRFormScreen(selected, saved_change_branch, self.main_branch),
            handle_pr_form_result
        )

    def action_merge_pr(self) -> None:
        """Merge open PRs for selected repositories (two-press confirmation)."""
        selected = self._get_selected_repos()

        if not selected:
            self.notify("No repositories selected. Use Space to select repos.", severity="warning")
            self._pending_merge_action = None
            return

        # Check which repos have open PRs
        has_open_change = [r for r in selected if r["pr_to_change"] == "Open"]
        has_open_main = [r for r in selected if r["pr_to_main"] == "Open"]

        if not has_open_change and not has_open_main:
            self.notify("No open PRs found for selected repositories.", severity="warning")
            self._pending_merge_action = None
            return

        # Determine which PR type(s) are available
        available_types = []
        if has_open_change:
            available_types.append(("change", has_open_change))
        if has_open_main:
            available_types.append(("main", has_open_main))

        # If both types available, need to choose
        if len(available_types) > 1:
            def handle_merge_choice(choice: str | None) -> None:
                if not choice:
                    self._pending_merge_action = None
                    self._update_explanation()
                    return

                repos_to_merge = has_open_change if choice == "change" else has_open_main
                self._show_merge_confirmation(choice, repos_to_merge)

            self.app.push_screen(
                SelectionScreen(
                    f"Merge PRs for {len(selected)} repo(s):",
                    [
                        ("change", f"CHANGE PRs ({len(has_open_change)} open)"),
                        ("main", f"Main PRs ({len(has_open_main)} open)")
                    ]
                ),
                handle_merge_choice
            )
        else:
            # Only one type available
            pr_type, repos = available_types[0]
            self._show_merge_confirmation(pr_type, repos)

    def _show_merge_confirmation(self, pr_type: str, repos: list[dict]) -> None:
        """Show merge confirmation in explanation pane (two-press pattern)."""
        # Check if this is the second press
        if self._pending_merge_action == pr_type and self._pending_merge_repos == [r["name"] for r in repos]:
            # Second press - execute merge
            self._pending_merge_action = None
            self._pending_merge_repos = None

            if pr_type == "change":
                self._merge_prs_to_change(repos)
            else:
                self._merge_prs_to_main(repos)

            self._update_explanation()  # Reset to default view
        else:
            # First press - show confirmation in explanation pane
            self._pending_merge_action = pr_type
            self._pending_merge_repos = [r["name"] for r in repos]

            # Get the actual branch name for display
            if pr_type == "change":
                change_branch = self.config_manager.get("change_branch", "CHANGE")
                target_display = f"{change_branch}"
            else:
                target_display = f"{self.main_branch}"

            repos_list = "\n".join(f"  • {r['name']}" for r in repos)

            merge_text = (
                f"This will merge {len(repos)} pull request(s):\n\n"
                f"{repos_list}\n\n"
                f"[bold]Target:[/bold] {target_display}\n\n"
                "This action cannot be undone in this simulation.\n\n"
                "[bold]Press (m) again to confirm merge[/bold]\n"
                "[bold]Press any other key to cancel[/bold]"
            )

            self._update_explanation(
                f"⚠️  Confirm Merge to {target_display}",
                merge_text
            )

    def _merge_prs_to_change(self, repos: list[dict]) -> None:
        """Merge PRs to CHANGE branch (simulated)."""
        for repo in repos:
            if repo["pr_to_change"] == "Open":
                repo["pr_to_change"] = "Merged"

        self._update_table()
        repo_names = ", ".join(r['name'] for r in repos)
        self.notify(f"✓ Merged {len(repos)} PR(s) to CHANGE: {repo_names}", severity="information", timeout=5)

    def _merge_prs_to_main(self, repos: list[dict]) -> None:
        """Merge PRs to main branch (simulated)."""
        for repo in repos:
            if repo["pr_to_main"] == "Open":
                repo["pr_to_main"] = "Merged"

        self._update_table()
        repo_names = ", ".join(r['name'] for r in repos)
        self.notify(f"✓ Merged {len(repos)} PR(s) to main: {repo_names}", severity="information", timeout=5)

    def _create_prs_to_change(self, repos: list[dict], change_branch: str) -> None:
        """Create PRs to CHANGE branch (simulated)."""
        for repo in repos:
            if repo["pr_to_change"] == "None":
                repo["pr_to_change"] = "Open"

        self._update_table()
        repo_names = ", ".join(r['name'] for r in repos)
        self.notify(f"✓ Created {len(repos)} PR(s) to {change_branch}: {repo_names}", severity="information", timeout=5)

    def _create_prs_to_main(self, repos: list[dict]) -> None:
        """Create PRs to main branch (simulated)."""
        for repo in repos:
            if repo["pr_to_main"] == "None":
                repo["pr_to_main"] = "Open"

        self._update_table()
        repo_names = ", ".join(r['name'] for r in repos)
        self.notify(f"✓ Created {len(repos)} PR(s) to main: {repo_names}", severity="information", timeout=5)

    def action_open_config(self) -> None:
        """Open configuration file in external editor."""
        # Clear any pending merge confirmation
        self._pending_merge_action = None
        self._pending_merge_repos = None

        # Ensure config file exists
        if not CONFIG_FILE.exists():
            self.config_manager.save({})

        def handle_editor_choice(choice: str) -> None:
            if not choice:
                return

            editor_commands = {
                "idea": ["idea", str(CONFIG_FILE)],
                "vscode": ["code", str(CONFIG_FILE)],
                "vim": ["vim", str(CONFIG_FILE)],
            }

            command = editor_commands.get(choice)
            if command:
                try:
                    subprocess.Popen(command)
                    self.notify(f"✓ Opened {CONFIG_FILE.name} in {command[0]}", severity="information")
                except FileNotFoundError:
                    self.notify(f"✗ Editor '{command[0]}' not found. Config at: {CONFIG_FILE}", severity="error", timeout=8)
                except Exception as e:
                    self.notify(f"✗ Failed to open config: {e}", severity="error", timeout=5)

        self.app.push_screen(
            SelectionScreen(
                "Open config file with:",
                [
                    ("idea", "IntelliJ IDEA"),
                    ("vscode", "VS Code"),
                    ("vim", "Vim"),
                ]
            ),
            handle_editor_choice
        )

    def action_info(self) -> None:
        """Show pattern information."""
        # Clear any pending merge confirmation
        self._pending_merge_action = None
        self._pending_merge_repos = None

        self._update_explanation(
            "Persistent Storage Pattern",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "[bold]What This Pattern Demonstrates:[/bold]\n\n"
            "Configuration Persistence:\n"
            "• Saves data to JSON file between sessions\n"
            "• Loads configuration on startup\n"
            "• Atomic writes prevent corruption\n"
            "• Can update saved values through form\n\n"
            "Form-Based Workflow:\n"
            "• Custom form screen similar to FormScreen utility\n"
            "• Conditional field visibility (CHANGE field shows/hides)\n"
            "• Radio selection for target branch\n"
            "• Pre-filled inputs with saved values\n"
            "• Built-in review step before confirmation\n\n"
            "Toast Notifications:\n"
            "• Quick feedback without blocking UI\n"
            "• Success/error messages with icons\n"
            "• Auto-dismiss with timeout\n\n"
            "Smart Workflow Logic:\n"
            "• Multi-step PR workflow (branch → CHANGE → main)\n"
            "• Shared configuration across repos\n"
            "• Simulated state management\n\n"
            "[bold]Use Cases:[/bold]\n"
            "• Multi-repo workflows\n"
            "• Tool preferences/settings\n"
            "• Session state management\n"
            "• User configuration for CLI tools\n\n"
            "[bold]What's Persisted:[/bold]\n"
            f"• CHANGE branch name → {CONFIG_FILE.name}\n"
            "• Repo PR statuses are simulated (in-memory)\n\n"
            "[bold]Key Implementation:[/bold]\n"
            "• ConfigManager utility for JSON read/write\n"
            "• PRFormScreen with conditional fields\n"
            "• Two-pane form layout (2/3 form, 1/3 explanation)\n"
            "• Dynamic show/hide based on selection\n"
            "• Review step with detailed explanation\n"
            "• Toast notifications for feedback"
        )

    def action_request_quit(self) -> None:
        """Request quit with confirmation."""
        self.app.push_screen(ConfirmQuitScreen())


class PersistentStorageApp(App):
    """
    Application demonstrating persistent storage pattern.

    This pattern shows:
    - JSON-based configuration persistence
    - Form screen with conditional field visibility
    - Pre-filled inputs from saved config
    - Review step before confirmation
    - Toast notifications for user feedback
    - External editor integration
    - Metarepo PR workflow simulation
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

    #prompt-dialog {
        width: 60;
        height: auto;
        background: $panel;
        border: solid $primary;
        padding: 1 2;
    }

    #prompt-label {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    #prompt-input {
        width: 100%;
    }

    #selection-dialog {
        align: center middle;
        width: 70;
        height: auto;
        background: $panel;
        border: solid $primary;
        padding: 1 2;
    }

    #selection-label {
        width: 100%;
        height: auto;
        text-align: center;
        padding: 1 0;
        content-align: center middle;
    }

    #selection-table {
        width: 100%;
        height: 10;
        min-height: 5;
    }

    /* PR Form Screen */
    #pr-form-container {
        width: 100%;
        height: 100%;
    }

    #pr-form-pane {
        width: 2fr;
        height: 100%;
        padding: 2 2;
    }

    #pr-form-pane Label {
        margin-top: 1;
        margin-bottom: 0;
    }

    #pr-form-pane #pr-direction-label {
        margin-top: 0;
    }

    #pr-form-pane #pr-direction-table {
        height: auto;
        max-height: 12;
        margin-bottom: 1;
    }

    #pr-form-pane Input {
        margin-top: 0;
        margin-bottom: 1;
    }

    #pr-form-pane Input.error {
        border: tall red;
    }

    #pr-explanation-pane {
        width: 1fr;
        height: 100%;
        background: $panel;
        border-left: solid $primary;
        padding: 1 2;
    }
    """

    def on_mount(self) -> None:
        self.title = "Persistent Storage Pattern"
        self.push_screen(MetarepoDashboard())


if __name__ == "__main__":
    from utilities.terminal_compat import run_app

    app = PersistentStorageApp()
    run_app(app)  # Handles colors + IntelliJ mouse issues
