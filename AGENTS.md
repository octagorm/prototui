# ProtoTUI: Textual TUI Patterns for LLMs

**Purpose:** This is a **skill/reference resource** for LLMs (like Claude) to help build Textual TUIs. The patterns and utilities here are meant to be **copied and adapted** into the codebase where you're building a TUI.

🚨 **This is NOT a library.** Do NOT import from prototui or add it as a dependency. Instead, **copy the files** into your project and modify them freely.

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

**Save configuration between sessions with persistent storage?**
→ `patterns/persistent_storage.py`

**Show stage-based progress bars across table columns with controllable gaps?**
→ `patterns/progress_bar_table.py`

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
- Multiple table selections (radio mode with ● indicator)
- **Conditional fields** (shown/hidden based on selections via `visible_when`)
- **Dynamic table rows** (tables that update based on other selections)
- Required field validation
- Visual error feedback (red borders)
- Tab navigation between fields
- Enter to submit with review step
- Two-pane layout with explanation panel

**Conditional fields example:**
```python
# Text field only shown when deployment_type is "kubernetes"
TextField(
    id="namespace",
    label="Kubernetes Namespace:",
    visible_when=lambda values: (
        values.get("deployment_type") and 
        values.get("deployment_type").row_key == "kubernetes"
    )
)

# Table field only shown for Kubernetes
TableSelectionField(
    id="replica_count",
    label="Replica Count:",
    columns=["Replicas", "Use Case"],
    rows=[...],
    visible_when=lambda values: (
        values.get("deployment_type") and 
        values.get("deployment_type").row_key == "kubernetes"
    )
)
```

**Dynamic table rows example:**
```python
# Update priority rows when environment changes
def update_priority_rows(form_screen):
    values = form_screen.get_current_values()
    env_row = values.get("environment")
    
    priority_table = form_screen.query_one("#priority", LayeredDataTable)
    
    if env_row.row_key == "prod":
        # Production gets more priority levels
        new_rows = [low, medium, high, critical]
    else:
        # Dev/Staging only gets low/medium
        new_rows = [low, medium]
    
    priority_table.set_rows(new_rows)

# Attach callback for selection changes
screen._table_selection_callback = lambda event: (
    update_priority_rows(screen) if event.data_table.id == "environment" else None
)
```

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

### 5. Persistent Storage
**File:** `patterns/persistent_storage.py`

**Use when:** Applications need to save configuration or state across sessions.

**Examples:**
- Multi-repo PR workflows with shared configuration
- Tool preferences and settings
- Session state management
- User configuration for CLI tools

**Key features:**
- JSON-based configuration persistence
- Form screen with conditional field visibility (CHANGE branch input shows/hides)
- Pre-filled inputs from saved configuration
- Review step before submission
- Toast notifications for feedback
- Metarepo PR workflow simulation
- Two-press confirmation for destructive actions

**What's persisted:**
- Configuration saved to `persistent_storage.json`
- Atomic writes prevent corruption
- Simple get/set API with ConfigManager

**Run:** `python patterns/persistent_storage.py`

---

### 6. Progress Bar Table
**File:** `patterns/progress_bar_table.py`

**Use when:** Visualizing stage-based progress across table columns with fine control over filled segments.

**Examples:**
- CI/CD pipeline stages (build → test → deploy → verify)
- Task workflow steps with visual progress
- Multi-column status indicators

**Key features:**
- **Stage-based progress** using list notation: `[1, 1.5, 2, 2.5, 3]`
  - Integers (1, 2, 3, 4) = fill progress columns
  - Decimals (1.5, 2.5, 3.5) = fill gaps between columns
- **Non-contiguous segments**: `[1, 2.5, 3]` skips column 2 but fills gap 2-3
- Pre-progress columns (ID, Type) with normal gaps
- Progress columns (Issue, Status, Owner, Priority) with controllable gaps
- Multi-select with properly padded checkboxes
- Dynamic column widths based on content
- `ProgressBarDataTable` subclass (extends LayeredDataTable with padded checkboxes)

**Technical details:**
- `GAP_WIDTH = 2` for visible gaps
- `cell_padding = 0` removes default DataTable gaps
- Manual trailing spaces create controllable gaps
- Rich Text for selective reverse styling

**Run:** `python patterns/progress_bar_table.py`

---

## Utility Files

All utilities are in `utilities/` and meant to be copied into your project.

### LayeredDataTable
**File:** `utilities/layered_data_table.py`

Reusable table widget with grouped/layered data, selection modes (`single`, `radio`, `multi`), filtering, and automatic cursor preservation.

**Usage:**
```python
from utilities.layered_data_table import LayeredDataTable, TableRow

rows = [
    TableRow({"Service": "auth", "Status": "Running"}, layer="Production", row_key="auth-prod"),
    TableRow({"Service": "api", "Status": "Running"}, layer="Production", row_key="api-prod"),
]

table = LayeredDataTable(
    id="services", columns=["Service", "Status"], rows=rows,
    select_mode="multi", show_layers=True, filterable=True
)

selected = table.get_selected_rows()  # Returns list[TableRow]
table.set_rows(updated_rows)  # Cursor stays on same row_key
```

**Custom subclass for progress bars:**
For patterns requiring padded checkboxes (like progress_bar_table), subclass and override `_update_checkbox()`:

```python
from utilities.layered_data_table import LayeredDataTable

class ProgressBarDataTable(LayeredDataTable):
    def _update_checkbox(self, row_key):
        # Custom checkbox logic with padding
        checkbox = "●" if row_key in self._selected_rows else "○"
        padded = f"  {checkbox}  "  # 2 spaces on each side
        self.query_one("#data-table").update_cell(row_key, "checkbox", padded)
```

### FormScreen
**File:** `utilities/form_screen.py`

Form screen with text/table fields, validation, conditional visibility, and review step.

```python
from utilities.form_screen import FormScreen, TextField, TableSelectionField

fields = [
    TextField(id="name", label="Name", required=True),
    TableSelectionField(id="env", label="Environment", columns=[...], rows=[...]),
    TextField(id="namespace", label="Namespace",
              visible_when=lambda vals: vals.get("env") is not None),  # Conditional
]

screen = FormScreen(fields=fields, title="Create Service")
self.push_screen(screen, callback)
```

### Async Helpers
**File:** `utilities/async_helpers.py`

Optional helpers: `run_parallel()`, `retry_with_backoff()`, `poll_until()`, `run_with_timeout()`, etc.

```python
from utilities.async_helpers import run_parallel, retry_with_backoff

results = await run_parallel(fetch_repos, fetch_prs, fetch_builds)
result = await retry_with_backoff(unstable_api_call, max_retries=5)
```

### State Manager
**File:** `utilities/state_manager.py`

Simple state management with get/set/watch callbacks.

```python
from utilities.state_manager import StateManager

state = StateManager()
state.watch("step", lambda change: print(f"{change.old_value} → {change.new_value}"))
state.set("step", 2)  # Triggers callback
```

### Terminal Compatibility (IMPORTANT)
**File:** `utilities/terminal_compat.py`

**Always use instead of `app.run()`** - auto-detects terminal capabilities and enables truecolor.

```python
from utilities.terminal_compat import run_app

run_app(MyApp())  # Auto-handles colors
run_app(app, mouse=False)  # Keyboard-only mode

# Environment overrides:
# export TUI_MOUSE=false
# export TUI_COLOR_SYSTEM=256
```

Fixes washed-out colors in IntelliJ and other terminals that don't advertise truecolor properly.

### ExplanationPanel
**File:** `utilities/explanation_panel.py`

Non-focusable side panel for two-pane layouts. **Important:** Don't set `height` on ExplanationPanel CSS - let it expand naturally in VerticalScroll.

```python
from utilities.explanation_panel import ExplanationPanel

with VerticalScroll(id="explanation-pane"):
    yield ExplanationPanel("Title", "Content...")

panel.update_content("New Title", "New content...")  # Dynamic updates
```

---

## Core Concepts

**Two-Pane Layout:** 2/3 content, 1/3 explanation (Horizontal with Vertical + VerticalScroll)

**Selection Modes:** `single` (cursor only), `radio` (● indicator), `multi` (○/● checkboxes)

**Common Patterns:** Review step (Enter→review→confirm, ESC→back), Two-press confirmation, `/` for filtering, `asyncio.gather()` for parallel async operations

**Installation:** `uv add textual` or `pip install textual`

---

## How to Use This Resource

**IMPORTANT:** This is a **copy-paste resource**, not a library. Do NOT import from prototui.

### For AI Agents (LLMs):
1. **Browse** patterns to find closest match
2. **Copy** pattern + utilities into user's project
3. **Update imports** (e.g., `from utilities.X` → `from utils.X`)
4. **Adapt** code freely - modify data structures, actions, styling
5. **Explain** which pattern you chose and changes made

### Why Copy Instead of Import?
✅ Freedom to modify ✅ No dependencies ✅ Self-contained ✅ Learn by doing

**Workflow:** Find pattern → Copy files → Update imports → Customize → Test

Patterns are educational templates showing best practices through working code, not library code.
