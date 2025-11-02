"""
ProtoTUI Meta Tool

A unified TUI for managing ProtoTUI development tools.
Provides access to:
- Skill Sync: Sync prototui skill to global/project locations
- Installer Generator: Generate install.sh for TUI applications
"""

import shutil
from pathlib import Path

from textual.app import App
from textual.widgets import DataTable
from textual import on

# Calculate paths
_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
_CSS_PATH = str(_REPO_ROOT / "prototui" / "themes" / "default.tcss")

from prototui import UniversalScreen, Field, TableRow
from prototui.components.layered_data_table import LayeredDataTable
from prototui.utils.state_manager import StateManager

# Import installer generator functions
from .installer_gen import discover_apps, read_apps_config, generate_installer

# Import sync skill sync functions
from .sync_skill import sync_claude, sync_copilot, create_package


class ProtoTUIApp(App):
    """
    Main ProtoTUI meta-tool application.

    Provides a menu to access various ProtoTUI development tools.
    """

    CSS_PATH = _CSS_PATH

    BINDINGS = [
        ("c", "toggle_mode", "Toggle Mode"),
    ]

    def __init__(self):
        super().__init__()

        # State for Sync Skill mode tracking
        self.sync_state = StateManager(
            initial_state={
                "claude_mode": "Symlink",
                "copilot_mode": "Symlink",
                "copilot_selected": False,
            }
        )

        # Reference to current sync screen for mode updates
        self._sync_screen = None

        # Watch for mode changes to update table cell
        self.sync_state.watch("claude_mode", lambda change: self._update_sync_mode_cell("claude", change.new_value))
        self.sync_state.watch("copilot_mode", lambda change: self._update_sync_mode_cell("copilot", change.new_value))
        self.sync_state.watch("copilot_selected", lambda _: self._toggle_copilot_field_visibility())

    def on_mount(self):
        """Show the main menu on startup."""
        self._show_main_menu()

    def _show_main_menu(self):
        """Display the main tool selection menu."""
        tools = [
            TableRow(
                {"Tool": "Sync Skill", "Description": "Sync prototui skill globally or to project"},
                row_key="sync-skill"
            ),
            TableRow(
                {"Tool": "Generate Installer", "Description": "Create install.sh for TUI applications"},
                row_key="generate-installer"
            ),
        ]

        screen = UniversalScreen(
            title="ProtoTUI Tools",
            fields=[
                Field(
                    id="tool",
                    field_type="table",
                    columns=["Tool", "Description"],
                    rows=tools,
                    select_mode="single",
                    show_layers=False,
                    required=True,
                )
            ],
            explanation_title="Welcome",
            explanation_content=(
                "Use arrow keys to navigate.\n"
                "Press Enter to select and run a tool.\n\n"
                "Sync Skill:\n"
                "  Manages the prototui AI skill,\n"
                "  allowing you to sync it to Claude Code\n"
                "  globally or to specific projects.\n\n"
                "Generate Installer:\n"
                "  Creates install.sh for your TUI apps,\n"
                "  making them easy to distribute and\n"
                "  install for end users."
            ),
            submit_label="Run Tool"
        )

        self.push_screen(screen, self._handle_tool_selection)

    def _handle_tool_selection(self, result):
        """Handle the user's tool selection."""
        if not result.confirmed:
            self.exit()
            return

        selected = result.values.get("tool", [])
        if not selected:
            self.exit()
            return

        tool_key = selected[0].row_key

        if tool_key == "sync-skill":
            self._run_sync_skill()
        elif tool_key == "generate-installer":
            self._run_installer_generator()
        else:
            self.exit()

    def _run_sync_skill(self):
        """Show the sync skill screen."""
        # Reset sync state
        self.sync_state.set("claude_mode", "Symlink")
        self.sync_state.set("copilot_mode", "Symlink")
        self.sync_state.set("copilot_selected", False)

        # Build operations rows
        rows = [
            TableRow(
                {"Operation": "Claude Code (global)", "Mode": self.sync_state.get("claude_mode")},
                row_key="claude",
            ),
            TableRow(
                {"Operation": "Package zip", "Mode": "N/A"},
                row_key="package",
            ),
            TableRow(
                {"Operation": "GitHub Copilot", "Mode": self.sync_state.get("copilot_mode")},
                row_key="copilot",
            ),
        ]

        fields = [
            Field(
                id="operations",
                field_type="table",
                columns=["Operation", "Mode"],
                rows=rows,
                select_mode="multi",
                show_layers=False,
                show_column_headers=True,
            ),
            Field(
                id="copilot_path",
                field_type="text",
                label="GitHub Copilot Project Path:",
                placeholder="~/work/my-project",
                required=True,
                initially_hidden=True,
            ),
        ]

        screen = UniversalScreen(
            title="ProtoTUI Skill Sync",
            fields=fields,
            explanation_title="Instructions",
            explanation_content=(
                "1. Select operations with Space or Enter\n"
                "2. Press (c) to toggle Symlink ↔ Copy mode\n"
                "3. Provide Copilot path if selected\n"
                "4. Press Enter on 'Sync' to execute\n\n"
                "Mode:\n"
                "  • Symlink: Changes to skill source reflected immediately\n"
                "  • Copy: Snapshot copy (requires manual re-sync)"
            ),
            submit_label="Sync",
        )

        self._sync_screen = screen
        self.push_screen(screen, self._handle_sync_submit)

    def _update_sync_mode_cell(self, row_key: str, new_mode: str):
        """Update mode cell in sync skill table."""
        if not self._sync_screen:
            return

        try:
            from prototui.components.layered_data_table import LayeredDataTable
            table = self._sync_screen.query_one(LayeredDataTable)

            for row in table.rows:
                if row.row_key == row_key:
                    table.update_cell(row, "Mode", new_mode)
                    break
        except:
            pass

    def _toggle_copilot_field_visibility(self):
        """Show/hide copilot path field based on selection."""
        if not self._sync_screen:
            return

        copilot_selected = self.sync_state.get("copilot_selected")
        self._sync_screen.set_field_visibility("copilot_path", copilot_selected)

    @on(LayeredDataTable.RowToggled)
    def on_layered_data_table_row_toggled(self, event):
        """Handle row toggle in sync skill table to detect copilot selection."""
        if not self._sync_screen:
            return

        try:
            from prototui.components.layered_data_table import LayeredDataTable
            table = self._sync_screen.query_one(LayeredDataTable)
            selected = table.get_selected_rows()

            copilot_selected = any(row.row_key == "copilot" for row in selected)

            if copilot_selected != self.sync_state.get("copilot_selected"):
                self.sync_state.set("copilot_selected", copilot_selected)
        except:
            pass

    def action_toggle_mode(self):
        """Toggle Symlink ↔ Copy for row under cursor (c key)."""
        if not self._sync_screen:
            return

        try:
            from prototui.components.layered_data_table import LayeredDataTable
            table = self._sync_screen.query_one(LayeredDataTable)
            data_table = table.query_one("#data-table", DataTable)

            if data_table.cursor_row is None:
                return

            row_keys = list(data_table.rows.keys())
            if data_table.cursor_row >= len(row_keys):
                return

            row_key = row_keys[data_table.cursor_row]
            if row_key not in table._row_map:
                return

            row = table._row_map[row_key]

            if row.row_key == "claude":
                current = self.sync_state.get("claude_mode")
                new_mode = "Copy" if current == "Symlink" else "Symlink"
                self.sync_state.set("claude_mode", new_mode)
            elif row.row_key == "copilot":
                current = self.sync_state.get("copilot_mode")
                new_mode = "Copy" if current == "Symlink" else "Symlink"
                self.sync_state.set("copilot_mode", new_mode)
        except:
            pass

    def _handle_sync_submit(self, result):
        """Handle sync skill form submission."""
        if not result.confirmed:
            self._show_main_menu()
            return

        selected_operations = result.values.get("operations", [])
        copilot_path = result.values.get("copilot_path", "").strip()

        if not selected_operations:
            self._show_error("No operations selected", self._run_sync_skill)
            return

        # Execute sync operations
        messages = []
        all_success = True

        for op in selected_operations:
            try:
                if op.row_key == "claude":
                    mode = self.sync_state.get("claude_mode")
                    msg = sync_claude(_REPO_ROOT, mode)
                    messages.append(f"✓ {msg}")
                elif op.row_key == "package":
                    msg = create_package(_REPO_ROOT)
                    messages.append(f"✓ {msg}")
                elif op.row_key == "copilot":
                    mode = self.sync_state.get("copilot_mode")
                    msg = sync_copilot(_REPO_ROOT, copilot_path, mode)
                    messages.append(f"✓ {msg}")
            except Exception as e:
                messages.append(f"✗ {op.values['Operation']}: {e}")
                all_success = False

        # Show results
        title = "✓ Sync Complete" if all_success else "✗ Sync Failed"
        self._show_success("\n".join(messages), title=title)

    def _run_installer_generator(self):
        """Show mode selection screen for installer generator."""
        # Check if apps.yaml exists
        apps_yaml_exists = (_REPO_ROOT / "apps.yaml").exists()

        # Build mode options based on apps.yaml existence
        modes = [
            TableRow(
                {"Mode": "Auto-discover", "Description": "Scans for directories with main.py"},
                row_key="auto"
            ),
        ]

        explanation_parts = [
            "Use arrow keys to navigate.\n"
            "Press Enter to select a mode.\n\n"
            "Auto-discover:\n"
            "  Scans these directories for TUI apps:\n"
            "    tui/, app/, apps/, tools/, commands/,\n"
            "    cli/, and root level\n\n"
            "  Structure: folder-name/main.py\n"
            "  The folder name becomes the command name.\n"
            "  Description extracted from module docstring."
        ]

        if apps_yaml_exists:
            modes.append(TableRow(
                {"Mode": "Use apps.yaml", "Description": "Uses existing configuration file"},
                row_key="yaml"
            ))
            explanation_parts.append(
                "\n\n"
                "Use apps.yaml:\n"
                "  Uses explicit configuration from apps.yaml\n"
                "  file in your project root."
            )
        else:
            modes.append(TableRow(
                {"Mode": "Create apps.yaml", "Description": "Creates template configuration file"},
                row_key="create_yaml"
            ))
            explanation_parts.append(
                "\n\n"
                "Create apps.yaml:\n"
                "  Creates apps.yaml template from example.\n"
                "  You can then edit it and regenerate."
            )

        screen = UniversalScreen(
            title="Installer Generator - Select Mode",
            fields=[
                Field(
                    id="mode",
                    field_type="table",
                    columns=["Mode", "Description"],
                    rows=modes,
                    select_mode="single",
                    show_layers=False,
                    required=True,
                )
            ],
            explanation_title="Discovery Mode",
            explanation_content="".join(explanation_parts),
            submit_label="Continue"
        )

        self.push_screen(screen, self._handle_generator_mode_selection)

    def _handle_generator_mode_selection(self, result):
        """Handle installer generator mode selection."""
        if not result.confirmed:
            # User canceled, go back to main menu
            self._show_main_menu()
            return

        selected = result.values.get("mode", [])
        if not selected:
            self.exit()
            return

        mode_key = selected[0].row_key

        if mode_key == "auto":
            # Auto-discover apps
            apps = discover_apps(_REPO_ROOT)
            if not apps:
                self._show_error("No apps discovered", self._show_main_menu)
                return
            self._show_app_selection(apps)

        elif mode_key == "yaml":
            # Use existing apps.yaml
            config_path = _REPO_ROOT / "apps.yaml"
            try:
                config = read_apps_config(config_path)
                apps = config.get("apps", [])
                if not apps:
                    self._show_error("apps.yaml exists but contains no apps", self._run_installer_generator)
                    return
            except Exception as e:
                self._show_error(f"Failed to read apps.yaml: {e}", self._show_main_menu)
                return
            self._show_app_selection(apps)

        elif mode_key == "create_yaml":
            # Create apps.yaml from template
            self._create_apps_yaml_template()

    def _create_apps_yaml_template(self):
        """Create apps.yaml from template."""
        template_path = _SCRIPT_DIR / "apps.yaml.example"
        target_path = _REPO_ROOT / "apps.yaml"

        try:
            shutil.copy(template_path, target_path)
            self._show_success(
                f"Created apps.yaml from template\n\n"
                f"Location: {target_path}\n\n"
                f"Next steps:\n"
                f"1. Edit apps.yaml to define your apps\n"
                f"2. Run installer generator again\n"
                f"3. Select 'Use apps.yaml' mode",
                title="Template Created"
            )
        except Exception as e:
            self._show_error(f"Failed to create apps.yaml: {e}", self._run_installer_generator)

    def _show_app_selection(self, apps):
        """Show checklist of apps to include in installer."""
        app_rows = [
            TableRow(
                {"App": app["name"], "Description": app.get("description", "No description")},
                row_key=app["name"]
            )
            for app in apps
        ]

        screen = UniversalScreen(
            title="Select Apps to Include",
            fields=[
                Field(
                    id="apps",
                    field_type="table",
                    columns=["App", "Description"],
                    rows=app_rows,
                    select_mode="multi",
                    show_layers=False,
                    required=True,
                )
            ],
            explanation_title="Apps Found",
            explanation_content=(
                f"Found {len(apps)} app(s).\n\n"
                "Use Space to select/deselect apps.\n"
                "Press Enter on 'Generate' to create install.sh"
            ),
            submit_label="Generate"
        )

        # Store apps for later use
        self._available_apps = apps
        self.push_screen(screen, self._handle_app_selection)

    def _handle_app_selection(self, result):
        """Handle app selection and generate installer."""
        if not result.confirmed:
            # User canceled, go back to mode selection
            self._run_installer_generator()
            return

        selected_rows = result.values.get("apps", [])
        if not selected_rows:
            self._show_error("No apps selected", self._run_installer_generator)
            return

        # Filter apps to only selected ones
        selected_names = {row.row_key for row in selected_rows}
        selected_apps = [app for app in self._available_apps if app["name"] in selected_names]

        # Generate installer
        try:
            output_path = _REPO_ROOT / "install.sh"
            generate_installer(selected_apps, output_path)

            apps_list = ", ".join(app["name"] for app in selected_apps)
            self._show_success(
                f"Generated install.sh with {len(selected_apps)} app(s):\n{apps_list}\n\n"
                f"Location: {output_path}\n\n"
                "Users can now run:\n"
                "  git clone <repo> && cd <repo> && ./install.sh"
            )
        except Exception as e:
            self._show_error(f"Failed to generate installer: {e}", self._show_main_menu)

    def _show_error(self, message, callback=None):
        """Show error message."""
        error_screen = UniversalScreen(
            title="Error",
            message=message,
            submit_label="OK",
        )
        if callback is None:
            callback = lambda _: self.exit()
        self.push_screen(error_screen, callback)

    def _show_success(self, message, title="Success"):
        """Show success message."""
        success_screen = UniversalScreen(
            title=title,
            message=message,
            submit_label="OK",
        )
        self.push_screen(success_screen, lambda _: self.exit())


def main():
    """Entry point for the prototui command."""
    ProtoTUIApp().run()


if __name__ == "__main__":
    main()
