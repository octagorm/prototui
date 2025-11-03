---
name: prototui-builder
description: This skill should be used when building terminal user interfaces (TUIs) with the ProtoTUI library. Use it for creating dashboards, forms, table selectors, multi-screen workflows, or any interactive terminal application using Textual. ProtoTUI provides one universal screen pattern (UniversalScreen) that handles all UI types, along with state management and async utilities.
---

# ProtoTUI Builder Skill

**Core Concept:** One screen pattern (`UniversalScreen`) for all UI types: tables, forms, dialogs, multi-screen workflows.

## Essential Setup

```python
from textual.app import App
from prototui import UniversalScreen, Field, TableRow

class MyApp(App):
    CSS_PATH = "prototui/themes/default.tcss"  # REQUIRED

    def on_mount(self):
        screen = UniversalScreen(
            title="Screen Title",
            fields=[...],
            explanation_title="Help",
            explanation_content="Instructions here",
            submit_label="OK"
        )
        self.push_screen(screen, self._handle_result)

    def _handle_result(self, result):
        if result.confirmed:  # Always check this first!
            # User pressed Enter - process result.values
            pass
        else:
            # User cancelled
            self.exit()
```

## Common Patterns (See Examples)

### Standalone Table Selection
**When:** Just picking item(s) from a list - the table is the whole screen.
**See:** `examples/table_example.py`

```python
screen = UniversalScreen(
    title="Select Repository",
    fields=[
        Field(
            id="repo",
            field_type="table",
            columns=["Name", "Status"],
            rows=rows,
            select_mode="single",  # No visual indicator needed - just press Enter
            auto_height=False      # Fill screen
        )
    ]
)
```

### Multi-Field Form with Table
**When:** Table is one field among several - need to see what's selected while moving between fields.
**See:** `examples/form_example.py`

```python
screen = UniversalScreen(
    title="Service Config",
    fields=[
        Field(id="name", field_type="text", label="Name:", required=True),
        Field(id="port", field_type="text", label="Port:", required=True),
        Field(
            id="env",
            field_type="table",
            label="Environment:",
            columns=["Environment"],
            rows=env_options,
            select_mode="radio",         # Shows ● so you can see selection
            show_column_headers=False,   # Cleaner for single column
            required=True
        )
    ]
)
```

**Key difference:** Use `select_mode="radio"` in multi-field forms for visual feedback. Use `"single"` for standalone tables where you just navigate and press Enter.

### Multi-Select Table
**See:** `examples/table_multiselect_example.py`

```python
Field(
    id="services",
    field_type="table",
    select_mode="multi",  # Shows ○/● checkboxes
    rows=rows
)
```

### Layered Tables
**When:** Grouping items by category (environment, service type, etc.)
**See:** `examples/layered_workflow_example.py`

```python
rows = [
    TableRow({"Service": "auth"}, layer="Production"),
    TableRow({"Service": "api"}, layer="Production"),
    TableRow({"Service": "test"}, layer="Development"),
]

Field(
    id="services",
    field_type="table",
    rows=rows,
    show_layers=True  # Shows "Production", "Development" headers
)
```

### Custom Hotkeys
**See:** `examples/workflow_example.py`

```python
screen = UniversalScreen(
    fields=[...],
    allow_submit=False,  # Disable Enter, use custom actions
    custom_bindings=[
        Binding("d", "app.describe", "Describe", show=True),
        Binding("r", "app.restart", "Restart", show=True),
    ]
)

# In App class - note "app." prefix is required!
def action_describe(self):
    if isinstance(self.screen, UniversalScreen):
        values = self.screen._collect_values()
        selected = values.get("services", [])
        # Do something
```

### Multi-Screen Workflow
**See:** `examples/workflow_example.py`

```python
def show_screen_a(self):
    self.push_screen(screen_a, self.show_screen_b)

def show_screen_b(self, result_a):
    if result_a.confirmed:
        self.push_screen(screen_b, self.show_screen_c)
    else:
        self.exit()
```

## Advanced Patterns

### State Management + Real-Time Updates
**See:** `examples/layered_workflow_example.py` (complete reference implementation)

```python
from prototui.utils.state_manager import StateManager

self.state = StateManager(initial_state={"service1_status": "Running"})
self.state.watch("service1_status", self._on_status_change)

def _on_status_change(self, change):
    self._update_table()  # Rebuild and update table rows

# Update table while preserving selection
table = self.screen.query_one(LayeredDataTable)
table.set_rows(new_rows)  # Uses row_key to maintain selection
```

### Conditional Field Visibility
**See:** Advanced Patterns section in examples

```python
# Always render field, use initially_hidden=True
Field(id="path", field_type="text", required=True, initially_hidden=True)

# Toggle visibility without rebuilding screen
self._main_screen.set_field_visibility("path", visible)
```

### Async Operations
**See:** `examples/async_example.py`

```python
from prototui.utils.async_helpers import retry_with_backoff, poll_until, run_parallel

# Retry API calls
result = await retry_with_backoff(lambda: api.create_pr(service), max_retries=3)

# Poll until condition is true
success = await poll_until(lambda: check_approval(pr), interval=5.0, timeout=300.0)

# Run operations in parallel
results = await run_parallel(*[lambda: process(svc) for svc in services])
```

## Quick Reference

### Field Parameters

**Text field:**
```python
Field(id="name", field_type="text", label="Name:", placeholder="hint", required=True)
```

**Table field:**
```python
Field(
    id="items",
    field_type="table",
    columns=["Col1", "Col2"],
    rows=[TableRow({"Col1": "val1", "Col2": "val2"}, row_key="unique-id")],
    select_mode="radio",    # "none"|"single"|"radio"|"multi"
    show_layers=True,
    auto_height=True,       # True for forms, False for standalone tables
    required=True
)
```

### Select Modes
- `"none"`: Read-only
- `"single"`: Enter to select, no indicator (for standalone tables)
- `"radio"`: Single select with ● (for forms with multiple fields)
- `"multi"`: Checkboxes

### Common Methods

```python
# Table updates
table.get_selected_rows()  # Returns list[TableRow]
table.set_rows(new_rows)   # Preserves selection by row_key
table.update_cell(row, "Status", "Running")

# State management
state.set("key", value)
state.get("key", default=None)
state.watch("key", callback)
```

## Critical Rules

1. **Always set** `CSS_PATH = "prototui/themes/default.tcss"`
2. **Always check** `result.confirmed` before accessing `result.values`
3. **Action prefix:** Use `"app.action_name"` in bindings, not `"action_name"`
4. **Use `row_key`** on TableRow for tracking across updates
5. **ESC unfocuses**, doesn't quit (Ctrl+Q quits)
6. **Don't repeat hotkeys** in explanation_content - footer shows them

## Common Mistakes

❌ `select_mode="single"` in multi-field form → No visual indicator
✅ `select_mode="radio"` in multi-field form → Shows ●

❌ Not checking `result.confirmed` → Crashes when user cancels
✅ Always check: `if result.confirmed:`

❌ `Binding("d", "describe", ...)` → Action won't work
✅ `Binding("d", "app.describe", ...)` → Correct prefix

## Examples Directory

**Start here:** Run these to understand the UX patterns

- `table_example.py` - Standalone table selection
- `form_example.py` - Multi-field form with table
- `workflow_example.py` - Multi-screen flow with custom hotkeys
- `layered_workflow_example.py` - **Reference implementation** with state management, real-time updates, async operations

```bash
python -m examples.workflow_example
python -m examples.layered_workflow_example
```

**When building a new TUI:**
1. Find the closest example to your use case
2. Copy the pattern
3. Modify for your needs
4. Check this doc for specific parameters

The examples demonstrate context-dependent patterns (like when to use `"radio"` vs `"single"`) better than written rules.
