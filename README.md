# ProtoTUI

**One pattern for all terminal UI types.**

ProtoTUI is a Textual-based library providing reusable components for building consistent, professional terminal user interfaces with minimal code.

## What's in This Repo?

This repository contains three things:

1. **`prototui/`** - The library you import (`from prototui import UniversalScreen, Field, TableRow`)
2. **`tui/prototui/`** - The meta-tool for managing ProtoTUI development (skill sync, installer generator)
3. **`.claude/skills/prototui-builder/`** - AI skill for Claude Code/GitHub Copilot with comprehensive TUI building patterns

## Philosophy

Instead of learning multiple screen patterns, ProtoTUI provides **one**: `UniversalScreen`. It handles:
- Forms with text inputs
- Tables with single/multi-select
- Information/message screens
- Confirmation dialogs
- Mixed forms (text + tables)
- Multi-screen workflows

## Features

- ✅ **UniversalScreen** - One screen pattern for everything
- ✅ **LayeredDataTable** - Tables with layer grouping and selection
- ✅ **StateManager** - Centralized state with watchers
- ✅ **Async Helpers** - Retry, polling, parallel execution utilities
- ✅ **Real-time Updates** - State changes automatically update UI
- ✅ **Professional Themes** - Polished default styling

## Installation

### For Users: Building TUI Apps with ProtoTUI

**Step 1: Install the ProtoTUI meta-tool**

```bash
# Clone ProtoTUI
git clone https://github.com/octagorm/prototui.git
cd prototui

# Run the installer (installs prototui command to ~/bin)
./install.sh
```

This gives you the `prototui` command for:
- Syncing the AI skill to Claude Code or your projects
- Generating installers for your TUI apps

**Step 2: Use the ProtoTUI library in your TUI project**

```bash
cd ~/my-tui-project
python -m venv .venv
source .venv/bin/activate

# Install ProtoTUI library (for importing in your code)
pip install -e /path/to/prototui

# Now you can use it in your code
# from prototui import UniversalScreen, Field, TableRow
```

**Using the prototui meta-tool:**
```bash
# Sync the AI skill
prototui
# → Select "Sync Skill" → Choose Claude Code or GitHub Copilot

# Generate installer for your TUI app
prototui
# → Select "Generate Installer"
```

### For Developers: Contributing to ProtoTUI

If you want to develop ProtoTUI itself:

```bash
git clone https://github.com/octagorm/prototui.git
cd prototui
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

This installs ProtoTUI in editable mode with development tools (pytest, black, mypy).

## Quick Start

```python
from textual.app import App
from prototui import UniversalScreen, Field, TableRow

class MyApp(App):
    CSS_PATH = "prototui/themes/default.tcss"  # Required!

    def on_mount(self):
        rows = [
            TableRow({"Name": "Service 1", "Status": "Running"}),
            TableRow({"Name": "Service 2", "Status": "Stopped"}),
        ]

        screen = UniversalScreen(
            title="Select Service",
            fields=[
                Field(
                    id="service",
                    field_type="table",
                    columns=["Name", "Status"],
                    rows=rows,
                    select_mode="radio",  # Shows ● indicator
                    show_layers=False,
                )
            ],
            explanation_title="Services",
            explanation_content="Select a service to manage.",
            submit_label="Continue"
        )

        self.push_screen(screen, self._handle_selection)

    def _handle_selection(self, result):
        if result.confirmed:
            selected = result.values.get("service", [])
            if selected:
                service = selected[0].values["Name"]
                print(f"Selected: {service}")
        self.exit()

if __name__ == "__main__":
    MyApp().run()
```

## Examples

Run the included examples to see ProtoTUI in action:

```bash
cd ~/dev/prototui

# Basic examples
python -m examples.table_example
python -m examples.form_example
python -m examples.workflow_example

# Advanced examples
python -m examples.state_example           # State management
python -m examples.async_example           # Async utilities
python -m examples.layered_workflow_example  # Complete workflow
```

## ProtoTUI Development Tools

This repository includes **prototui** - a unified TUI tool for managing ProtoTUI development tasks.

### Quick Start

```bash
# Install prototui globally (one-time setup)
cd ~/Dev/textual-tui
./install.sh

# Use from anywhere
prototui
```

**prototui** provides:
- **Skill Sync**: Sync the `prototui-builder` AI skill to Claude Code or GitHub Copilot
- **Installer Generator**: Create `install.sh` for your TUI applications

See installation section above for setup information.

### AI Skill Integration

The `prototui-builder` skill provides AI assistants (Claude Code, GitHub Copilot) with comprehensive guidance for building TUI applications. Use **prototui** to sync the skill:

```bash
prototui
# Select: Sync Skill
# Choose: Claude Code (global) or GitHub Copilot (project-specific)
```

The skill provides:
- Quick start patterns and common UI examples
- Advanced patterns (state management, async utilities, conditional fields)
- Complete API reference for all components
- Best practices and common mistakes
- Troubleshooting guide
- Real-world examples and patterns

See `.claude/skills/prototui-builder/SKILL.md` for the complete reference.

## Key Components

### UniversalScreen

The main screen pattern. Handles all UI types:

```python
from prototui import UniversalScreen, Field

# Simple message
screen = UniversalScreen(
    title="Success",
    message="Operation completed!",
    submit_label="OK"
)

# Form with text input
screen = UniversalScreen(
    title="Enter Name",
    fields=[
        Field(id="name", field_type="text", label="Name:", required=True)
    ],
    submit_label="Submit"
)

# Table selection
screen = UniversalScreen(
    title="Select Items",
    fields=[
        Field(
            id="items",
            field_type="table",
            columns=["Name", "Value"],
            rows=table_rows,
            select_mode="multi",  # Multi-select with checkboxes
        )
    ],
    submit_label="Continue"
)
```

### StateManager

Centralized state with automatic change notifications:

```python
from prototui.utils.state_manager import StateManager

state = StateManager(initial_state={
    "service_status": "running",
    "last_update": "2024-01-01"
})

# Watch for changes
def on_status_change(change):
    print(f"{change.key}: {change.old_value} → {change.new_value}")

state.watch("service_status", on_status_change)

# Update state - triggers watcher
state.set("service_status", "stopped")
```

### Async Helpers

Utilities for async operations:

```python
from prototui.utils.async_helpers import (
    retry_with_backoff,
    poll_until,
    run_parallel,
)

# Retry unreliable operations
result = await retry_with_backoff(
    lambda: api.create_pr(service),
    max_retries=3,
    initial_delay=1.0,
)

# Poll until condition is true
approved = await poll_until(
    lambda: check_pr_approved(pr_id),
    interval=5.0,
    timeout=300.0,
)

# Run operations in parallel
results = await run_parallel(
    lambda: create_pr(svc1),
    lambda: create_pr(svc2),
    lambda: create_pr(svc3),
)
```

## Common Patterns

### Layered Table with State

Perfect for dashboards and monitoring tools:

```python
from prototui import UniversalScreen, Field, TableRow
from prototui.utils.state_manager import StateManager

# State tracking
state = StateManager(initial_state={
    "service1_status": "Running",
    "service2_status": "Stopped",
})

# Build rows from state
rows = [
    TableRow(
        {"Service": "service1", "Status": state.get("service1_status")},
        layer="Layer 1",
        row_key="service1"
    ),
    TableRow(
        {"Service": "service2", "Status": state.get("service2_status")},
        layer="Layer 2",
        row_key="service2"
    ),
]

# Watch state changes and update table
state.watch("service1_status", lambda change: update_table())
```

### Two-Press Confirmation

Show confirmation in right pane before executing:

```python
def action_delete(self):
    selected = get_selected_services()

    if self._pending_action == "delete" and self._pending_services == selected:
        # Second press - execute
        self._pending_action = None
        asyncio.create_task(self._delete(selected))
    else:
        # First press - show confirmation
        self._pending_action = "delete"
        self._pending_services = selected
        self._update_explanation(
            f"Delete {len(selected)} services?\n\n"
            + "\n".join(f"  • {s}" for s in selected)
            + "\n\nPress (d) again to confirm."
        )
```

### Real-time Updates with "..."

Show activity while polling:

```python
async def poll_services(self, services):
    # Show "..." while polling
    for service in services:
        self.state.set(f"{service}_status", "...")

    # Poll in parallel
    await run_parallel(*[
        lambda s=svc: self._poll_single(s)
        for svc in services
    ])

    # State watchers automatically update the table
```

## Project Structure

```
prototui/
├── prototui/
│   ├── __init__.py
│   ├── components/
│   │   ├── explanation_panel.py
│   │   └── layered_data_table.py
│   ├── screens/
│   │   └── universal_screen.py
│   ├── themes/
│   │   └── default.tcss
│   └── utils/
│       ├── async_helpers.py
│       └── state_manager.py
├── examples/
│   ├── table_example.py
│   ├── form_example.py
│   ├── workflow_example.py
│   ├── state_example.py
│   ├── async_example.py
│   └── layered_workflow_example.py
├── pyproject.toml
└── README.md
```

## Packaging & Distribution

Build TUI apps that users can install and run from anywhere, with automatic updates.

### Quick Start

1. **Define your apps** in `apps.yaml`:
```yaml
apps:
  - name: my-tui-app
    description: My awesome TUI application
    entry_point: app.main:run
```

2. **Generate installer**:
```bash
python scripts/generate-installer.py
```

3. **Users install**:
```bash
git clone <your-repo>
cd <your-repo>
./install.sh  # Interactive installer
```

4. **Run from anywhere**:
```bash
my-tui-app  # Just works!
```

See [PACKAGING.md](PACKAGING.md) for complete documentation on:
- Single and multi-app repos
- Auto-update configuration
- Entry point formats
- Distribution strategies

---

## Best Practices

1. **Always set CSS_PATH** - Required for proper styling:
   ```python
   CSS_PATH = "prototui/themes/default.tcss"
   ```

2. **Use `radio` mode for single-select in forms** - Shows ● indicator:
   ```python
   select_mode="radio"  # NOT "single"
   ```

3. **Check `result.confirmed` before accessing values**:
   ```python
   def _handle_result(self, result):
       if result.confirmed:  # User pressed Enter
           # Access result.values
       else:  # User pressed ESC
           # Handle cancellation
   ```

4. **Use `required=True` for mandatory fields** - Automatic validation:
   ```python
   Field(id="name", field_type="text", required=True)
   ```

5. **Prefix custom actions with `app.`** in bindings:
   ```python
   Binding("d", "app.delete", "Delete", show=True)
   ```

## Documentation

For detailed implementation patterns and technical reference, see the AI skill at `.claude/skills/prototui-builder/SKILL.md` - a comprehensive guide covering:
- Quick start and common patterns
- Advanced patterns and techniques
- Complete API reference
- Best practices and troubleshooting

## Requirements

- Python 3.8+
- Textual >= 0.50.0

## License

MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

**Development setup:**
```bash
git clone https://github.com/octagorm/prototui.git
cd prototui
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```
