---
name: prototui-builder
description: This skill should be used when building terminal user interfaces (TUIs) with the ProtoTUI library. Use it for creating dashboards, forms, table selectors, multi-screen workflows, or any interactive terminal application using Textual. ProtoTUI provides one universal screen pattern (UniversalScreen) that handles all UI types, along with state management and async utilities.
---

# ProtoTUI Builder Skill

## Overview

ProtoTUI is a Textual-based library providing **one universal pattern** for building terminal UIs. Instead of learning multiple screen types, use `UniversalScreen` for everything: forms, tables, dialogs, mixed inputs, and multi-screen workflows.

**Core Philosophy**: One screen pattern (`UniversalScreen`) handles all interface types through different parameter combinations.

### Key Components

- **UniversalScreen** - The universal screen pattern for all UI types
- **LayeredDataTable** - Tables with layer grouping and multi-select
- **StateManager** - Centralized state management with watchers
- **Async Helpers** - Utilities for retry, polling, and parallel execution

### Installation Check

Before using ProtoTUI, verify it's installed:

```python
# Import should work without errors
from prototui import UniversalScreen, Field, TableRow
```

If the import fails, install it:
```bash
pip install -e /path/to/prototui
```

---

## Quick Start Pattern

Every ProtoTUI app follows this structure:

```python
from textual.app import App
from prototui import UniversalScreen, Field, TableRow

class MyApp(App):
    # REQUIRED: Load the default theme
    CSS_PATH = "prototui/themes/default.tcss"

    def on_mount(self):
        screen = UniversalScreen(
            title="Screen Title",
            fields=[...],  # Optional fields
            explanation_title="Help Title",
            explanation_content="Help text in right pane",
            submit_label="OK"
        )
        self.push_screen(screen, self._handle_result)

    def _handle_result(self, result):
        if result.confirmed:  # User pressed Enter
            # Access result.values
            pass
        else:  # User pressed ESC
            # Handle cancellation
            pass
        self.exit()
```

**Critical requirements:**
1. Always set `CSS_PATH = "prototui/themes/default.tcss"`
2. Always check `result.confirmed` before accessing `result.values`
3. Use `self.push_screen(screen, callback)` for screen navigation

---

## Common UI Patterns

### 1. Table Selection (Single)

Use for selecting one item from a list:

```python
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
            select_mode="radio",  # Shows ● indicator (NOT "single"!)
            show_layers=False,
        )
    ],
    submit_label="Select"
)

def _handle_result(self, result):
    if result.confirmed:
        selected = result.values.get("service", [])
        if selected:
            service = selected[0]  # TableRow object
            name = service.values["Name"]
```

**Important:** Always use `select_mode="radio"` for single-select in forms, never `"single"` (no visual indicator).

### 2. Table Selection (Multi)

Use for selecting multiple items:

```python
screen = UniversalScreen(
    title="Select Services",
    fields=[
        Field(
            id="services",
            field_type="table",
            columns=["Name", "Status"],
            rows=rows,
            select_mode="multi",  # Shows ○/● checkboxes
        )
    ],
    submit_label="Continue"
)

def _handle_result(self, result):
    if result.confirmed:
        selected = result.values.get("services", [])  # List of TableRow
        for row in selected:
            print(row.values["Name"])
```

### 3. Layered Table

Use for grouped items (e.g., services by environment):

```python
rows = [
    TableRow({"Service": "auth", "Status": "Running"}, layer="Production"),
    TableRow({"Service": "api", "Status": "Running"}, layer="Production"),
    TableRow({"Service": "test-svc", "Status": "Stopped"}, layer="Development"),
]

screen = UniversalScreen(
    title="Services by Environment",
    fields=[
        Field(
            id="services",
            field_type="table",
            columns=["Service", "Status"],
            rows=rows,
            select_mode="multi",
            show_layers=True,  # Shows "Production", "Development" headers
        )
    ]
)
```

**Layer selection:** Use `(l)` hotkey to select entire layer:

```python
from textual.binding import Binding

custom_bindings=[
    Binding("l", "app.select_layer", "Select Layer", show=True)
]

def action_select_layer(self):
    from prototui.components.layered_data_table import LayeredDataTable
    table = self.screen.query_one(LayeredDataTable)
    current_layer = table.get_cursor_layer()
    table.select_rows_by_layer(current_layer)
```

### 4. Text Input Form

Use for collecting user input:

```python
screen = UniversalScreen(
    title="Configuration",
    fields=[
        Field(
            id="name",
            field_type="text",
            label="Service Name:",
            placeholder="my-service",
            required=True  # Validation!
        ),
        Field(
            id="port",
            field_type="text",
            label="Port:",
            placeholder="8080",
            required=True
        ),
    ],
    submit_label="Create"
)

def _handle_result(self, result):
    if result.confirmed:
        name = result.values.get("name", "").strip()
        port = result.values.get("port", "").strip()
        # Both guaranteed non-empty due to required=True
```

### 5. Mixed Form (Text + Table)

Combine text inputs and table selections:

```python
env_options = [
    TableRow({"Environment": "Production"}),
    TableRow({"Environment": "Staging"}),
    TableRow({"Environment": "Development"}),
]

screen = UniversalScreen(
    title="Deploy Service",
    fields=[
        Field(id="name", field_type="text", label="Name:", required=True),
        Field(
            id="environment",
            field_type="table",
            label="Environment:",
            columns=["Environment"],
            rows=env_options,
            select_mode="radio",
            show_column_headers=False,  # Cleaner for single column
            required=True
        ),
    ],
    submit_label="Deploy"
)
```

### 6. Message/Info Screen

Use for showing results or information:

```python
screen = UniversalScreen(
    title="Success",
    message="✓ Deployment completed!\n\nService: my-service\nEnvironment: Production",
    explanation_title="Result",
    explanation_content="The service is now running.",
    submit_label="OK"
)
```

### 7. Custom Hotkeys

Add custom actions with bindings:

```python
screen = UniversalScreen(
    title="Service Manager",
    fields=[...],
    allow_submit=False,  # Disable Enter (using custom actions)
    custom_bindings=[
        Binding("d", "app.describe", "Describe", show=True),
        Binding("r", "app.restart", "Restart", show=True),
    ]
)

# In App class:
def action_describe(self):
    if isinstance(self.screen, UniversalScreen):
        values = self.screen._collect_values()
        selected = values.get("services", [])
        # Do something with selection

def action_restart(self):
    # Custom action
    pass
```

**Critical:** Actions must be prefixed with `app.` in bindings.

---

## Advanced Patterns

### State Management

Use StateManager for centralized state with automatic change notifications:

```python
from prototui.utils.state_manager import StateManager

# Initialize
self.state = StateManager(initial_state={
    "service1_status": "Running",
    "service2_status": "Stopped",
})

# Watch changes
def on_status_change(change):
    print(f"{change.key}: {change.old_value} → {change.new_value}")

self.state.watch("service1_status", on_status_change)

# Update state - triggers watcher
self.state.set("service1_status", "Stopped")

# Get values
status = self.state.get("service1_status")
```

**Real-time table updates:** Combine StateManager with table updates:

```python
def _on_state_change(self, change):
    self._update_table()

def _update_table(self):
    # Build new rows from state
    rows = [
        TableRow(
            {"Service": "service1", "Status": self.state.get("service1_status")},
            row_key="service1"
        ),
        # ... more rows
    ]

    # Update table
    from prototui.components.layered_data_table import LayeredDataTable
    table = self.screen.query_one(LayeredDataTable)
    table.set_rows(rows)  # Preserves selection
```

### Async Utilities

Common async patterns for TUI applications:

**Retry with Backoff** - For unreliable operations (API calls, network):

```python
from prototui.utils.async_helpers import retry_with_backoff

result = await retry_with_backoff(
    lambda: api.create_pr(service),
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    on_retry=lambda attempt, ex: self.log(f"Retry #{attempt}: {ex}")
)
```

**Poll Until** - For waiting on conditions (approvals, builds):

```python
from prototui.utils.async_helpers import poll_until

success = await poll_until(
    lambda: check_if_approved(pr_id),
    interval=5.0,
    timeout=300.0,
    on_check=lambda n: self.log(f"Check #{n}")
)
```

**Run Parallel** - For concurrent operations:

```python
from prototui.utils.async_helpers import run_parallel

operations = [
    lambda: create_pr(svc1),
    lambda: create_pr(svc2),
    lambda: create_pr(svc3),
]

results = await run_parallel(*operations)
```

### Conditional Field Visibility

Show/hide fields based on other selections without rebuilding the screen:

```python
class MyApp(App):
    def __init__(self):
        super().__init__()
        self.state = StateManager(initial_state={"copilot_selected": False})
        self.state.watch("copilot_selected", lambda _: self._toggle_field())
        self._main_screen = None

    def on_mount(self):
        screen = self._build_screen()
        self._main_screen = screen  # Store reference
        self.push_screen(screen, self._handle_submit)

    def _build_screen(self):
        # Always render ALL fields
        fields = [
            Field(id="options", field_type="table", ...),
            # Conditional field - starts rendered, hidden via initially_hidden
            Field(id="path", field_type="text", required=True, initially_hidden=True),
        ]
        return UniversalScreen(title="Setup", fields=fields)

    def on_layered_data_table_row_toggled(self, event):
        # Update state when selection changes
        if self._main_screen:
            table = self._main_screen.query_one(LayeredDataTable)
            selected = any(row.row_key == "copilot" for row in table.get_selected_rows())
            if selected != self.state.get("copilot_selected"):
                self.state.set("copilot_selected", selected)

    def _toggle_field(self):
        # Helper handles: field widget, label, and required property
        if self._main_screen:
            self._main_screen.set_field_visibility(
                "path",
                self.state.get("copilot_selected")
            )
```

**Key steps**:
1. Always render the field in fields list
2. Use `initially_hidden=True` to prevent flicker on first render
3. Store screen reference: `self._main_screen = screen`
4. Use `set_field_visibility(field_id, visible)` helper

**Benefits**: No cursor jumping, automatic required validation, clean code.

### Two-Press Confirmation

Show confirmation in right pane (no modal):

```python
def action_delete(self):
    selected = self._get_selected()

    if self._pending_action == "delete" and self._pending_items == selected:
        # Second press - execute
        self._pending_action = None
        asyncio.create_task(self._do_delete(selected))
    else:
        # First press - show confirmation
        self._pending_action = "delete"
        self._pending_items = selected
        self._update_explanation(
            f"Delete {len(selected)} items?\n\n"
            + "\n".join(f"  • {item}" for item in selected)
            + "\n\nPress (d) again to confirm."
        )

def _update_explanation(self, content):
    from prototui.components.explanation_panel import ExplanationPanel
    panel = self.screen.query_one(ExplanationPanel)
    panel.update_content(content)
```

### Activity Indicators

Show "..." while operations are in progress:

```python
async def process_items(self, items):
    # Show "..." while processing
    for item in items:
        self.state.set(f"{item}_status", "...")

    # Process
    await run_parallel(*[
        lambda i=item: self._process_item(i)
        for item in items
    ])

    # State watchers automatically update table with results
```

### Refresh Pattern

Single hotkey to poll everything that needs polling:

```python
def action_refresh(self):
    # Find what needs polling
    to_poll_prs = [svc for svc in services if state.get(f"{svc}_pr") == "Open"]
    to_poll_builds = [svc for svc in services if state.get(f"{svc}_build") == "Pending"]

    if not to_poll_prs and not to_poll_builds:
        self._update_explanation("Nothing to refresh.")
        return

    asyncio.create_task(self._refresh_all(to_poll_prs, to_poll_builds))
```

### Multi-Screen Workflows

Chain screens properly:

```python
# Pattern: Screen A -> Screen B -> Screen C -> Exit
def show_screen_a(self):
    self.push_screen(screen_a, self.show_screen_b)

def show_screen_b(self, result_a):
    if result_a.confirmed:
        self.push_screen(screen_b, self.show_screen_c)
    else:
        self.exit()

def show_screen_c(self, result_b):
    if result_b.confirmed:
        self.push_screen(screen_c, lambda _: self.exit())
    else:
        # Pop to previous screen or exit
        self.pop_screen()
```

---

## API Reference

### Field Types

#### text

```python
Field(
    id="unique_id",           # Required
    field_type="text",        # Required
    label="Display Label:",   # Optional
    placeholder="hint...",    # Optional
    default_value="",         # Optional
    required=True,            # Optional - validates non-empty
    initially_hidden=False    # Optional - hide on first render
)
```

#### table

```python
Field(
    id="unique_id",           # Required
    field_type="table",       # Required
    columns=["Col1", "Col2"], # Required
    rows=[TableRow(...)],     # Required - list of TableRow objects
    label="Display Label:",   # Optional
    select_mode="radio",      # Optional - "none"|"single"|"radio"|"multi"
    show_layers=True,         # Optional - show layer groupings
    show_column_headers=True, # Optional - show column headers
    auto_height=True,         # Optional - size to content vs fill space
    required=True,            # Optional - validates has selection
    initially_hidden=False    # Optional - hide on first render
)
```

**Select modes:**
- `"none"`: Read-only table, no selection
- `"single"`: Enter to select, no visual indicator (not recommended)
- `"radio"`: Single select with ● showing current selection (PREFERRED for forms)
- `"multi"`: Multiple selection with ○/● checkboxes

### Screen Result Structure

```python
@dataclass
class ScreenResult:
    confirmed: bool  # True = Enter pressed, False = ESC pressed
    values: dict[str, Any]  # Field values by field id

# Examples:
result.values["name"]  # str - text field value
result.values["items"]  # list[TableRow] - table field selection
```

### TableRow

```python
@dataclass
class TableRow:
    values: dict[str, Any]  # Column name -> value mapping
    layer: Optional[str] = None  # Optional layer grouping
    row_key: Optional[str] = None  # Optional unique identifier

# Example:
row = TableRow(
    {"Name": "Task 1", "Status": "Done"},
    layer="Backend",
    row_key="task-1"
)
```

### UniversalScreen Parameters

```python
UniversalScreen(
    title: str,                              # Screen title
    fields: Optional[list[Field]] = None,    # List of fields
    message: str = "",                       # Main message (for info screens)
    explanation_title: str = "",             # Title for explanation panel
    explanation_content: str = "",           # Content for explanation panel
    explanation_hint: str = "",              # Hint text
    submit_label: str = "Submit",            # Label for submit action
    cancel_label: str = "Cancel",            # Label for cancel action
    allow_submit: bool = True,               # Whether Enter key submits
    custom_bindings: Optional[list[Binding]] = None,  # Custom key bindings
)
```

### LayeredDataTable Methods

```python
# Get selected rows
selected = table.get_selected_rows()  # Returns list[TableRow]

# Update a cell
table.update_cell(row, "Status", "Running")

# Replace all rows (preserves selection by row_key)
table.set_rows(new_rows)

# Select entire layer
table.select_rows_by_layer("Production")

# Get cursor's current layer
layer = table.get_cursor_layer()
```

### StateManager Methods

```python
# Get/set values
value = state.get("key", default=None)
state.set("key", value)

# Bulk updates
state.update({"key1": "value1", "key2": "value2"})

# Watch for changes
state.watch("key", callback)

# Check existence
if state.has("key"):
    ...

# Get all keys
keys = state.keys()

# Get/set entire state
state_dict = state.to_dict()
state.from_dict(new_state)
```

### Async Helpers

```python
# Retry with exponential backoff
result = await retry_with_backoff(
    operation: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    on_retry: Optional[Callable[[int, Exception], None]] = None
)

# Poll until condition is true
success = await poll_until(
    check_fn: Callable[[], Awaitable[bool]],
    interval: float = 1.0,
    timeout: Optional[float] = None,
    on_check: Optional[Callable[[int], None]] = None
)

# Run operations in parallel
results = await run_parallel(*operations)

# Run with concurrency limit
results = await run_parallel_with_limit(
    operations: list[Callable[[], Awaitable[T]]],
    limit: int = 5,
    on_complete: Optional[Callable[[int, T], None]] = None
)

# Run with timeout
result = await run_with_timeout(
    operation: Callable[[], Awaitable[T]],
    timeout: float,
    timeout_value: Optional[T] = None
)
```

---

## Best Practices

1. **Always set CSS_PATH**: Required for proper styling
   ```python
   CSS_PATH = "prototui/themes/default.tcss"
   ```

2. **Use `radio` for single-select in forms**: Shows ● indicator
   ```python
   select_mode="radio"  # NOT "single"
   ```

3. **Check `result.confirmed` before accessing values**: Always handle both paths
   ```python
   if result.confirmed:
       # Success path
   else:
       # Cancellation path
   ```

4. **Use `required=True` for mandatory fields**: Automatic validation
   ```python
   Field(id="name", field_type="text", required=True)
   ```

5. **Prefix actions with `app.`** in custom bindings:
   ```python
   Binding("d", "app.describe", "Describe", show=True)
   ```

6. **Use `row_key`** for tracking rows across updates:
   ```python
   TableRow({...}, row_key="unique-id")
   ```

7. **Show activity with "..."**: Use in state while operations run
   ```python
   self.state.set(f"{item}_status", "...")
   ```

8. **Update right pane, not modals**: Use explanation panel for feedback
   ```python
   panel.update_content("Processing...")
   ```

9. **Don't repeat hotkeys in descriptions**: Footer shows them automatically

---

## Common Mistakes

### ❌ Using `select_mode="single"`
No visual indicator - user can't tell what's selected.

### ✅ Use `select_mode="radio"`
Shows ● indicator - user sees current selection.

---

### ❌ Not checking `result.confirmed`
```python
def _handle_result(self, result):
    selected = result.values.get("items", [])  # Crash if user pressed ESC!
```

### ✅ Always check first
```python
def _handle_result(self, result):
    if result.confirmed:
        selected = result.values.get("items", [])
        # ...
    else:
        self.exit()
```

---

### ❌ Forgetting CSS_PATH
```python
class MyApp(App):
    def on_mount(self):
        # Missing CSS_PATH!
```

### ✅ Always include
```python
class MyApp(App):
    CSS_PATH = "prototui/themes/default.tcss"
```

---

### ❌ Wrong action prefix
```python
Binding("d", "describe", "Describe", show=True)  # Won't work!
```

### ✅ Use `app.` prefix
```python
Binding("d", "app.describe", "Describe", show=True)
```

---

### ❌ Repeating hotkeys in explanation
```python
explanation_content=(
    "• Press Space to toggle\n"  # Redundant!
    "• Press Enter to confirm\n"  # Redundant!
)
```

### ✅ Don't repeat - footer shows them
```python
explanation_content=(
    "Select items to process.\n\n"
    "Selected items will be processed in batch."
)
```

---

## Troubleshooting

### "Binding 'd' doesn't appear in footer"
**Cause**: Missing `show=True`.
**Fix**:
```python
Binding("d", "app.describe", "Describe", show=True)
```

### "Pressing 'd' does nothing"
**Cause**: Missing `app.` prefix.
**Fix**:
```python
Binding("d", "app.describe", ...)  # Not "describe"
```

### "Table has no visual selection indicator"
**Cause**: Using `select_mode="single"` or `"none"`.
**Fix**: Use `select_mode="radio"` for single-select in forms.

### "Required validation not working"
**Cause**: Field doesn't have `required=True`.
**Fix**: Add `required=True`. UniversalScreen handles validation automatically.

### "Custom bindings not working when field is focused"
**Cause**: This should work - custom bindings get `priority=True` automatically.
**Debug**: Check if action name has `app.` prefix and the action method exists.

### "Conditional field causes cursor jump"
**Cause**: Rebuilding screen instead of toggling visibility.
**Fix**: Use `set_field_visibility()` on existing screen, don't rebuild.

---

## Technical Details

### Dynamic Class Generation

**Why it exists**: Textual only reads class-level `BINDINGS`, not instance attributes.

**How UniversalScreen solves this**: Uses `__new__()` to dynamically create a subclass with the correct class-level `BINDINGS`.

**What this means**:
- Custom bindings automatically get `priority=True`
- Each `UniversalScreen` instance with different bindings is actually a different class
- This is transparent - just pass `custom_bindings` parameter

**If you need to subclass**:
```python
class MyCustomScreen(UniversalScreen):
    BINDINGS = [
        Binding("y", "confirm_yes", "Yes", show=True, priority=True),
    ]
    # Works fine - subclasses use normal instantiation
```

### ESC Behavior

**Critical**: ESC **unfocuses** fields, it does NOT quit or dismiss screens.

```python
# User presses ESC:
# 1. If a field is focused -> unfocus it (allows hotkeys to work)
# 2. If nothing is focused -> does nothing

# To quit: Ctrl+Q (Textual built-in)
```

**Design rationale**: ESC for unfocus allows hotkeys to work while editing. Otherwise, custom action keys wouldn't work when a text field is focused.

### Auto-Height vs Full-Height Tables

```python
# In forms (auto-size to content):
Field(..., auto_height=True)  # Default - sizes to number of rows

# Standalone screens (fill space):
Field(..., auto_height=False)  # Fills available vertical space
```

Use `auto_height=False` when the table is the only/primary content. Use `auto_height=True` for forms with multiple fields.

### Keyboard Reference

**Standard Keys**:
- **Ctrl+Q**: Quit application (Textual built-in)
- **ESC**: Unfocus current field (NOT quit/dismiss)
- **Enter**: Submit form / confirm (unless `allow_submit=False`)
- **Tab**: Next field
- **Shift+Tab**: Previous field
- **Space**: Toggle selection in tables (radio/multi modes)
- **Arrow Keys**: Navigate table rows (skips layer headers)

**Custom Keys**: Define with `custom_bindings` parameter.

---

## Examples

The library includes comprehensive examples:

- `table_example.py` - Single-select table
- `table_multiselect_example.py` - Multi-select table
- `form_example.py` - Multi-field form
- `workflow_example.py` - Multi-screen workflow with custom bindings
- `async_example.py` - Async utilities (retry, poll, parallel)
- `state_example.py` - State management with watchers
- `layered_workflow_example.py` - **Complete real-world application** demonstrating all advanced patterns

Run them to understand the UX:
```bash
python -m examples.workflow_example
python -m examples.layered_workflow_example
```

The `layered_workflow_example.py` is the **reference implementation** for complex ProtoTUI applications, demonstrating:
- Layered tables with state management
- Two-press confirmation pattern
- Real-time updates with "..." indicators
- Async operations with retry and polling
- Layer selection hotkey
- Refresh pattern

---

## Summary

**When implementing TUIs**:
1. Use `UniversalScreen` for everything
2. Use `select_mode="radio"` for single-select in forms
3. Use `select_mode="multi"` for multi-select
4. Always set `CSS_PATH = "prototui/themes/default.tcss"`
5. Always check `result.confirmed` before accessing `result.values`
6. Custom bindings need `app.` prefix in action names
7. ESC unfocuses (not closes), Ctrl+Q quits
8. Required fields validate automatically
9. Don't repeat hotkeys in descriptions (footer shows them)
10. Check `examples/` before implementing new patterns

**The library is designed to be simple**: One screen pattern, clear conventions, automatic validation, consistent keyboard handling. Follow these patterns and you'll build consistent, professional TUIs quickly.
