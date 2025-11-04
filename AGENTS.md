# ProtoTUI: Textual TUI Patterns for LLMs

**Purpose:** This is a reference resource for LLMs (like Claude) to help build Textual TUIs. The patterns and utilities here are meant to be **copied and adapted** into the codebase where you're building a TUI, not imported as a library.

The code is self-documenting with clear variable names, type hints, and comments. Read the pattern files directly - they show better than any written guide how to handle common TUI scenarios.

---

## Quick Pattern Selection

**Select ONE item from a grouped list, as a single screen?**
→ `patterns/layered_list_selection.py`

**Select MULTIPLE items from a grouped list, as a single screen?**
→ `patterns/layered_multi_select.py`

**Collect form input (text fields + selections)?**
→ `patterns/form_with_table_selection.py`

**Show a table as a dashboard with async operations with real-time updates?**
→ `patterns/async_state_dashboard.py`

---

## Pattern Files

### 1. Layered List Selection
**File:** `patterns/layered_list_selection.py`

**Use when:** Selecting ONE item from a grouped/layered list.

**Examples:**
- Select a service from environments (prod/staging/dev)
- Choose a repository by team or architecture layer
- Pick a resource from categories

**Key features:**
- Single selection (cursor-based, no visual indicator)
- Layered data with visual group headers
- Filter with `/` key
- Two-pane layout (content 2/3, explanation 1/3)
- Enter to submit with review step

**Run:** `python patterns/layered_list_selection.py`

---

### 2. Layered Multi-Select
**File:** `patterns/layered_multi_select.py`

**Use when:** Selecting MULTIPLE items from grouped/layered lists.

**Examples:**
- Select multiple services across environments
- Choose files from different directories
- Pick resources from multiple categories

**Key features:**
- Multi-select with Space (shows ☑ checkboxes)
- (l) to toggle entire layer on/off
- (a) to toggle all items
- Filter with `/` key
- Selection count in subtitle
- Two-pane layout with explanation panel
- Enter to submit with review step

**Run:** `python patterns/layered_multi_select.py`

---

### 3. Form with Table Selection
**File:** `patterns/form_with_table_selection.py`

**Use when:** Collecting mixed input - text fields + table selections.

**Examples:**
- Service configuration (name, port, environment selection)
- Resource creation (properties + category selection)
- Settings form with dropdown-like table selections

**Key features:**
- Text input fields with validation
- Table selection (radio mode with ● indicator)
- Required field validation
- Visual error feedback (red borders)
- Tab navigation between fields
- Enter to submit with review step
- Two-pane layout with explanation panel

**Why radio mode here?** When a table is part of a form with multiple fields, the ● indicator provides visual feedback while tabbing between fields. For standalone table selection, no indicator is needed (see layered_list_selection).

**Run:** `python patterns/form_with_table_selection.py`

---

### 4. Async State Dashboard
**File:** `patterns/async_state_dashboard.py`

**Use when:** Building dashboards that show async operations with real-time state updates.

**Examples:**
- Deployment pipeline dashboard
- Service health monitoring
- Build/CI job status tracking
- Multi-stage workflow management

**Key features:**
- Layered table showing service/resource status
- Real-time UI updates as operations complete
- Parallel async operations (asyncio.gather)
- Two-press confirmation pattern (prevents accidents)
- Custom action hotkeys (d, r, s, l, a, i)
- Multi-select for bulk operations
- State tracking with visual feedback ("Deploying...", "Running", "Failed")

**Run:** `python patterns/async_state_dashboard.py`

---

## Utility Files

All utilities are in `utilities/` and meant to be copied into your project.

### LayeredDataTable
**File:** `utilities/layered_data_table.py`

Reusable table widget with:
- Grouped/layered data with visual headers
- Three selection modes: `single`, `radio`, `multi`
- Filter with `/` key (when `filterable=True`)
- Layer-based selection helpers
- Selection state tracking
- **Automatic cursor position preservation** across table updates

**Usage:**
```python
from utilities.layered_data_table import LayeredDataTable, TableRow

rows = [
    TableRow(
        {"Service": "auth", "Status": "Running"},
        layer="Production",
        row_key="auth-prod"  # Used to preserve cursor position
    ),
    TableRow(
        {"Service": "api", "Status": "Running"},
        layer="Production",
        row_key="api-prod"
    ),
]

table = LayeredDataTable(
    id="services",
    columns=["Service", "Status"],
    rows=rows,
    select_mode="multi",
    show_layers=True,
    filterable=True
)

# Get selections
selected = table.get_selected_rows()  # Returns list[TableRow]

# Update table data (cursor stays on same row_key)
table.set_rows(updated_rows)
```

### FormScreen
**File:** `utilities/form_screen.py`

Reusable form screen with:
- Text input fields with validation
- Table selection field
- Required field checking
- Two-pane layout
- Review step before submission

**Usage:**
```python
from utilities.form_screen import FormScreen, TextField, TableSelectionField

text_fields = [
    TextField(id="name", label="Name", required=True),
    TextField(id="email", label="Email", placeholder="user@example.com"),
]

table_field = TableSelectionField(
    id="env",
    label="Environment",
    columns=["Name", "Region"],
    rows=[...],  # List of TableRow
    required=True
)

screen = FormScreen(
    text_fields=text_fields,
    table_field=table_field,
    title="Create Service"
)

self.push_screen(screen, callback)
```

### Async Helpers
**File:** `utilities/async_helpers.py`

Optional helpers for common async patterns. The patterns use `asyncio` directly, but these helpers show what's possible:
- `run_with_timeout()` - Run operation with timeout
- `poll_until()` - Poll a condition until true
- `run_parallel()` - Run operations in parallel (wraps `asyncio.gather()`)
- `run_parallel_with_limit()` - Parallel with concurrency limit
- `retry_with_backoff()` - Retry with exponential backoff
- `AsyncQueue` - Simple async queue

**Usage:**
```python
from utilities.async_helpers import run_parallel, retry_with_backoff

# Run multiple operations in parallel
results = await run_parallel(
    lambda: fetch_repos(),
    lambda: fetch_prs(),
    lambda: fetch_builds(),
)

# Retry unstable operation
result = await retry_with_backoff(
    lambda: unstable_api_call(),
    max_retries=5
)
```

### State Manager
**File:** `utilities/state_manager.py`

Simple state management with:
- Get/set/update/delete state
- Watch for state changes with callbacks
- Multi-step workflow state tracking

**Usage:**
```python
from utilities.state_manager import StateManager

state = StateManager()
state.set("current_step", 1)

# Watch for changes
def on_step_change(change):
    print(f"Step: {change.old_value} → {change.new_value}")

state.watch("current_step", on_step_change)
state.set("current_step", 2)  # Triggers callback
```

---

## Core Concepts

### Two-Pane Layout (Standard across all patterns)
```python
with Horizontal(id="main-container"):
    # Left: Main content (2fr = 2/3 of space)
    with Vertical(id="content-pane"):
        yield LayeredDataTable(...)

    # Right: Explanation panel (1fr = 1/3 of space)
    with VerticalScroll(id="explanation-pane"):
        yield ExplanationPanel(title, content)
```

**CSS:**
```python
#content-pane {
    width: 2fr;  # 2/3 of space
}

#explanation-pane {
    width: 1fr;  # 1/3 of space
    background: $panel;
    border-left: solid $primary;
}
```

### TableRow Structure
```python
from utilities.layered_data_table import TableRow

row = TableRow(
    values={"Service": "auth", "Status": "Running"},  # Column data
    layer="Production",  # Optional grouping
    row_key="auth-prod"  # Optional unique identifier
)
```

### Filtering Pattern
All table-based patterns support filtering with `/` key:
- Press `/` to show filter input
- Type to filter (matches any column)
- Tab or arrow keys move to filtered results
- ESC clears filter and returns to table
- Shows "X of Y matches" counter
- Auto-hides when empty and tabbing out

### Selection Modes

**Single mode** - Cursor only, no visual indicator
```python
table = LayeredDataTable(..., select_mode="single")
```
Use when: Table is the only/main content

**Radio mode** - Shows ● for selected item
```python
table = LayeredDataTable(..., select_mode="radio")
```
Use when: Table is part of a form with multiple fields

**Multi mode** - Shows ☑ checkboxes
```python
table = LayeredDataTable(..., select_mode="multi")
```
Use when: Selecting multiple items

### Review Step Pattern
Most patterns show a review step before final submission:
1. User fills out form/makes selection
2. Press Enter → show review in explanation panel
3. Press Enter again → confirm and submit
4. Press ESC → return to editing

### Quit Confirmation
```python
class ConfirmQuitScreen(Screen):
    BINDINGS = [
        Binding("y", "confirm_quit", "Yes", show=True),
        Binding("n", "cancel_quit", "No", show=True),
    ]

    def on_mount(self):
        self.notify("Are you sure you want to quit? (y/n)", severity="warning")

# In main screen
def action_request_quit(self):
    self.app.push_screen(ConfirmQuitScreen())
```

### Async Operations Pattern
```python
async def _deploy_services(self, services: list[str]) -> None:
    self._operation_in_progress = True

    try:
        # Show intermediate state
        for service in services:
            self.service_state[service]["status"] = "Deploying..."
        self._update_table()

        # Run in parallel
        tasks = [self._deploy_single_service(s) for s in services]
        await asyncio.gather(*tasks)

        # Update UI as each completes (in _deploy_single_service)
    finally:
        self._operation_in_progress = False
```

### Two-Press Confirmation Pattern
Prevents accidental destructive actions:
```python
def action_deploy(self):
    if self._pending_action == "deploy":
        # Second press - execute
        self._pending_action = None
        asyncio.create_task(self._do_deploy())
    else:
        # First press - show what will happen
        self._pending_action = "deploy"
        self._update_explanation(
            "Confirm Deploy",
            f"Deploy {count} services?\n\nPress (d) again to confirm."
        )
```

---

## Best Practices

### 1. Make Explanation Panes Non-Focusable
```python
def on_mount(self):
    explanation_pane = self.query_one("#explanation-pane")
    explanation_pane.can_focus = False
```

### 2. Update Subtitle for Context
```python
self.sub_title = f"Select Services ({count} selected)"
```

### 3. Consistent Binding Order
Primary action → Secondary actions → Utility → Quit
```python
BINDINGS = [
    Binding("enter", "submit", "Submit", show=True, priority=True),
    Binding("l", "toggle_layer", "Toggle Layer", show=True),
    Binding("a", "toggle_all", "Toggle All", show=True),
    Binding("q", "request_quit", "Quit", show=True),
]
```

### 4. Handle Tab When Nothing Focused
When no widget is focused, Tab/Shift+Tab events go to the App, not the Screen. Handle with `on_key()`:
```python
def on_key(self, event) -> None:
    if not self.focused and event.key == "tab":
        event.prevent_default()
        event.stop()
        # Focus your first field
```
See `utilities/form_screen.py` for complete example.

### 5. Use Reactive Properties for Real-Time Updates
```python
from textual.reactive import reactive

class MyScreen(Screen):
    filter_visible: reactive[bool] = reactive(False)

    def watch_filter_visible(self, visible: bool) -> None:
        # Automatically called when filter_visible changes
        filter_input = self.query_one("#filter-input")
        filter_input.display = visible
```

---

## Installation

All patterns use only Textual:
```bash
uv add textual
# or
pip install textual
```

---

## How to Use This Resource

1. **Browse the pattern files** to find the closest match for your use case
2. **Copy the entire pattern file** into your project as a starting point
3. **Copy any utilities** the pattern uses (`layered_data_table.py`, `form_screen.py`, etc.)
4. **Adapt to your needs** - change data structure, add actions, modify styling
5. **Read the code** - it's self-documenting with clear names and comments

The patterns are complete, runnable examples. They demonstrate best practices through working code rather than written rules.

**For LLMs:** When helping users build a TUI, reference these patterns and copy relevant code. Explain which pattern matches their use case and help adapt it to their specific needs.
