#!/usr/bin/env python3
"""
ProtoTUI Skill Sync - Standalone Functions

Functions for syncing the ProtoTUI skill to different locations.
Used by the prototui main app.
"""

import os
import shutil
import subprocess
from pathlib import Path


def sync_claude(repo_root: Path, mode: str) -> str:
    """Sync to Claude Code global skills directory.

    Args:
        repo_root: Repository root directory
        mode: "Symlink" or "Copy"

    Returns:
        Success message
    """
    skill_source = repo_root / ".claude" / "skills" / "prototui-builder"

    if not skill_source.exists():
        raise FileNotFoundError(f"Skill source not found: {skill_source}")

    dest = Path.home() / ".claude" / "skills" / "prototui-builder"

    # Create parent directory
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Remove old version
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink():
            dest.unlink()
        else:
            shutil.rmtree(dest)

    if mode == "Symlink":
        # Create symlink
        dest.symlink_to(skill_source)
        return f"Claude Code: Symlinked to {dest}"
    else:
        # Copy
        shutil.copytree(skill_source, dest)
        return f"Claude Code: Copied to {dest}"


def sync_copilot(repo_root: Path, project_path: str, mode: str) -> str:
    """Sync to GitHub Copilot project skills directory.

    Args:
        repo_root: Repository root directory
        project_path: Path to the project directory
        mode: "Symlink" or "Copy"

    Returns:
        Success message
    """
    skill_source = repo_root / ".claude" / "skills" / "prototui-builder"

    if not skill_source.exists():
        raise FileNotFoundError(f"Skill source not found: {skill_source}")

    # Expand ~ to home directory
    project_path = os.path.expanduser(project_path)
    project_dir = Path(project_path)

    if not project_dir.exists():
        raise FileNotFoundError(f"Project directory not found: {project_path}")

    dest = project_dir / "skills" / "prototui-builder"

    # Create parent directory
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Remove old version
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink():
            dest.unlink()
        else:
            shutil.rmtree(dest)

    if mode == "Symlink":
        # Create symlink
        dest.symlink_to(skill_source)
        return f"GitHub Copilot: Symlinked to {dest}"
    else:
        # Copy
        shutil.copytree(skill_source, dest)
        return f"GitHub Copilot: Copied to {dest}"


def create_package(repo_root: Path) -> str:
    """Create distribution zip package.

    Args:
        repo_root: Repository root directory

    Returns:
        Success message
    """
    skill_source = repo_root / ".claude" / "skills" / "prototui-builder"

    if not skill_source.exists():
        raise FileNotFoundError(f"Skill source not found: {skill_source}")

    zip_output = repo_root / "prototui-builder.zip"

    # Remove old zip
    if zip_output.exists():
        zip_output.unlink()

    # Create zip
    # Change to .claude/skills directory to get correct structure
    orig_dir = Path.cwd()
    try:
        os.chdir(skill_source.parent)
        subprocess.run(
            [
                "zip",
                "-r",
                str(zip_output),
                "prototui-builder/",
                "-x",
                "*.DS_Store",
                "-x",
                "__pycache__/*",
                "-x",
                "*.pyc",
            ],
            check=True,
            capture_output=True,
        )
    finally:
        os.chdir(orig_dir)

    # Get size
    size_kb = zip_output.stat().st_size // 1024
    return f"Package: Created {zip_output.name} ({size_kb}K)"


# ============================================================================
# Legacy standalone app (for direct execution if needed)
# ============================================================================

from textual.app import App
from textual.binding import Binding
from textual.widgets import DataTable

from prototui import UniversalScreen, Field, TableRow
from prototui.utils.state_manager import StateManager

# Calculate CSS path relative to this script
_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
_CSS_PATH = str(_REPO_ROOT / "prototui" / "themes" / "default.tcss")


class SyncSkillApp(App):
    """TUI for syncing ProtoTUI skill to different locations."""

    CSS_PATH = _CSS_PATH

    def __init__(self):
        super().__init__()

        # Store reference to main screen for widget queries
        self._main_screen = None

        # State for tracking Symlink vs Copy mode
        self.state = StateManager(
            initial_state={
                "claude_mode": "Symlink",
                "copilot_mode": "Symlink",
                "copilot_selected": False,  # Track if copilot is selected
            }
        )

        # Watch for mode changes to update table cell
        self.state.watch("claude_mode", lambda change: self._update_mode_cell("claude", change.new_value))
        self.state.watch("copilot_mode", lambda change: self._update_mode_cell("copilot", change.new_value))
        # Watch copilot selection to show/hide field
        self.state.watch("copilot_selected", lambda _: self._toggle_copilot_field_visibility())

        # Get paths (script is in tui/prototui/sync_skill.py)
        script_dir = Path(__file__).parent  # tui/prototui/
        self.repo_root = script_dir.parent.parent  # tui/prototui/ -> tui/ -> repo root
        self.skill_source = self.repo_root / ".claude" / "skills" / "prototui-builder"

        # Validate skill source exists
        if not self.skill_source.exists():
            raise FileNotFoundError(f"Skill source not found: {self.skill_source}")

    def on_mount(self):
        """Show the main sync screen."""
        screen = self._build_screen()
        self._main_screen = screen  # Store reference for widget queries
        self.push_screen(screen, self._handle_submit)

    def on_layered_data_table_row_toggled(self, event):
        """Handle row toggle in multi-select table."""
        # Check if copilot selection changed
        self._check_copilot_selection()

    def _build_screen(self) -> UniversalScreen:
        """Build the main screen with operations table and path input."""
        rows = self._build_rows()

        # Always include all fields - control visibility dynamically
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
            # Copilot path field - will be hidden/shown based on selection
            Field(
                id="copilot_path",
                field_type="text",
                label="GitHub Copilot Project Path:",
                placeholder="~/work/my-project",
                required=True,  # Required when visible, hidden when not needed
                initially_hidden=True,  # Start hidden, show when copilot selected
            ),
        ]

        return UniversalScreen(
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
            custom_bindings=[
                Binding("c", "app.toggle_mode", "Toggle Mode", show=True),
            ],
            submit_label="Sync",
        )

    def _build_rows(self) -> list[TableRow]:
        """Build table rows with current mode values."""
        return [
            TableRow(
                {
                    "Operation": "Claude Code (global)",
                    "Mode": self.state.get("claude_mode"),
                },
                row_key="claude",
            ),
            TableRow(
                {"Operation": "Package zip", "Mode": "N/A"},
                row_key="package",
            ),
            TableRow(
                {
                    "Operation": "GitHub Copilot",
                    "Mode": self.state.get("copilot_mode"),
                },
                row_key="copilot",
            ),
        ]

    def _update_mode_cell(self, row_key: str, new_mode: str):
        """Update just the Mode cell for a specific row - preserves cursor position."""
        if not self._main_screen:
            return

        try:
            from prototui.components.layered_data_table import LayeredDataTable

            table = self._main_screen.query_one(LayeredDataTable)

            # Find the row and update just the Mode cell
            for row in table.rows:
                if row.row_key == row_key:
                    table.update_cell(row, "Mode", new_mode)
                    break
        except:
            # Table might not be mounted yet
            pass

    def _toggle_copilot_field_visibility(self):
        """Show or hide copilot path field based on selection state."""
        if not self._main_screen:
            return

        copilot_selected = self.state.get("copilot_selected")

        # Use helper method to toggle field visibility
        # This handles finding both the field widget and its label,
        # and automatically toggles the required property
        self._main_screen.set_field_visibility("copilot_path", copilot_selected)

    def _check_copilot_selection(self):
        """Check if copilot is selected and update state."""
        if not self._main_screen:
            return

        try:
            from prototui.components.layered_data_table import LayeredDataTable

            table = self._main_screen.query_one(LayeredDataTable)
            selected = table.get_selected_rows()

            # Check if copilot is in selection
            copilot_selected = any(row.row_key == "copilot" for row in selected)

            # Update state if changed (will trigger visibility toggle via watcher)
            if copilot_selected != self.state.get("copilot_selected"):
                self.state.set("copilot_selected", copilot_selected)
        except:
            # Table might not be mounted yet
            pass

    def action_toggle_mode(self):
        """Toggle Symlink ↔ Copy for row under cursor."""
        if not self._main_screen:
            return

        try:
            from prototui.components.layered_data_table import LayeredDataTable

            table = self._main_screen.query_one(LayeredDataTable)

            # Get the internal DataTable to access cursor position
            data_table = table.query_one("#data-table", DataTable)
            if data_table.cursor_row is None:
                return

            # Map cursor position to actual TableRow using row_map
            row_keys = list(data_table.rows.keys())
            if data_table.cursor_row >= len(row_keys):
                return

            row_key = row_keys[data_table.cursor_row]
            if row_key not in table._row_map:
                return

            # Get the actual TableRow object
            row = table._row_map[row_key]

            # Toggle mode based on row type
            if row.row_key == "claude":
                current = self.state.get("claude_mode")
                new_mode = "Copy" if current == "Symlink" else "Symlink"
                self.state.set("claude_mode", new_mode)
            elif row.row_key == "copilot":
                current = self.state.get("copilot_mode")
                new_mode = "Copy" if current == "Symlink" else "Symlink"
                self.state.set("copilot_mode", new_mode)
            # Package has no mode to toggle
        except:
            # Table might not be mounted yet
            pass

    def _handle_submit(self, result):
        """Handle sync submission."""
        if not result.confirmed:
            self.exit()
            return

        # Get selections
        selected_operations = result.values.get("operations", [])
        copilot_path = result.values.get("copilot_path", "").strip()

        # Validate
        if not selected_operations:
            self._show_error("No operations selected.")
            return

        # Note: copilot_path validation is handled by built-in required field validation
        # The field's required property is toggled based on whether Copilot is selected

        # Execute sync operations
        success, messages = self._execute_sync(selected_operations, copilot_path)

        # Show results
        self._show_results(success, messages)

    def _show_error(self, message: str):
        """Show error message and return to main screen."""
        error_screen = UniversalScreen(
            title="Error",
            message=message,
            submit_label="OK",
        )
        self.push_screen(error_screen, lambda _: self.exit())

    def _show_results(self, success: bool, messages: list[str]):
        """Show sync results."""
        title = "✓ Sync Complete" if success else "✗ Sync Failed"
        message = "\n".join(messages)

        result_screen = UniversalScreen(
            title=title,
            message=message,
            submit_label="OK",
        )
        self.push_screen(result_screen, lambda _: self.exit())

    def _execute_sync(
        self, operations: list[TableRow], copilot_path: str
    ) -> tuple[bool, list[str]]:
        """Execute selected sync operations.

        Returns:
            (success, messages): Success status and list of result messages
        """
        messages = []
        all_success = True

        for op in operations:
            try:
                if op.row_key == "claude":
                    mode = self.state.get("claude_mode")
                    msg = self._sync_claude(mode)
                    messages.append(f"✓ {msg}")
                elif op.row_key == "package":
                    msg = self._create_package()
                    messages.append(f"✓ {msg}")
                elif op.row_key == "copilot":
                    mode = self.state.get("copilot_mode")
                    msg = self._sync_copilot(copilot_path, mode)
                    messages.append(f"✓ {msg}")
            except Exception as e:
                messages.append(f"✗ {op.values['Operation']}: {e}")
                all_success = False

        return all_success, messages

    def _sync_claude(self, mode: str) -> str:
        """Sync to Claude Code global skills directory."""
        return sync_claude(self.repo_root, mode)

    def _sync_copilot(self, project_path: str, mode: str) -> str:
        """Sync to GitHub Copilot project skills directory."""
        return sync_copilot(self.repo_root, project_path, mode)

    def _create_package(self) -> str:
        """Create distribution zip package."""
        return create_package(self.repo_root)


if __name__ == "__main__":
    SyncSkillApp().run()
