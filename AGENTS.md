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

### Terminal Compatibility (IMPORTANT)
**File:** `utilities/terminal_compat.py`

**CRITICAL**: Always use this instead of `app.run()` to ensure proper colors across terminals.

**Problems this solves:**
1. **Colors**: Some terminals (like IntelliJ) don't advertise truecolor support even though they have it

**The solution:**
- Detects terminal capabilities and enables truecolor when appropriate
- Sets `COLORTERM=truecolor` at import time (before App instantiation)
- Provides environment variable overrides for user control

**Usage:**
```python
from utilities.terminal_compat import run_app

app = MyApp()
run_app(app)  # Auto-handles colors!

# Disable mouse if preferred (keyboard-only mode):
run_app(app, mouse=False)

# With other run args:
run_app(app, inline=True)
```

**What it does automatically:**
- ✅ Detects IntelliJ/JetBrains terminal → enables truecolor
- ✅ Detects 256color terminals → upgrades to truecolor
- ✅ Sets `COLORTERM=truecolor` for child processes
- ✅ Respects user env var overrides

**Why this matters:** Without this, colors look washed out in IntelliJ IDEA's terminal. All patterns use this by default.

**About IntelliJ mouse behavior:**
IntelliJ's terminal (JediTerm) has slightly glitchy mouse scrolling - it can feel fast or jumpy. This is a known limitation of the terminal emulator. Users who prefer keyboard-only mode can disable mouse:

**Environment variable overrides:**
```bash
# Disable mouse globally (keyboard-only mode)
export TUI_MOUSE=false

# Force specific color system
export TUI_COLOR_SYSTEM=256
```

---

### ExplanationPanel
**File:** `utilities/explanation_panel.py`

Reusable side panel widget for two-pane layouts showing help/explanation text.

**Key features:**
- Non-focusable (doesn't interfere with tab navigation)
- Dynamic content updates with proper layout recalculation
- Works correctly inside VerticalScroll containers
- Properly expands to show all content without truncation

**Important CSS setup:**
- **DO NOT set `height`** on ExplanationPanel CSS
- Let it naturally expand within VerticalScroll
- Using `height: auto` can cause content truncation

**Usage:**
```python
from utilities.explanation_panel import ExplanationPanel
from textual.containers import VerticalScroll

# In compose()
with VerticalScroll(id="explanation-pane"):
    yield ExplanationPanel(
        "Help Title",
        "Explanation content here...\n\nSupports multiple lines."
    )

# Update content dynamically
panel = self.query_one(ExplanationPanel)
panel.update_content("New Title", "New content...")
```

**CSS (Correct):**
```css
#explanation-pane {
    width: 1fr;
    height: 100%;
    background: $panel;
    border-left: solid $primary;
    padding: 1 2;
}

ExplanationPanel {
    width: 100%;
    /* NO height property - let it expand naturally */
}
```

---

## Core Concepts

### Two-Pane Layout
Standard 2/3 content, 1/3 explanation:
```python
with Horizontal(id="main-container"):
    with Vertical(id="content-pane"):  # width: 2fr
        yield LayeredDataTable(...)
    with VerticalScroll(id="explanation-pane"):  # width: 1fr
        yield ExplanationPanel(title, content)
```

### Selection Modes
- **`single`** - Cursor only, no indicator (standalone tables)
- **`radio`** - Shows ● (tables in forms)
- **`multi`** - Shows ○/● (selecting multiple items)

### Common Patterns
- **Review Step** - Enter → review, Enter → confirm, ESC → back
- **Two-Press Confirmation** - First press shows what will happen, second press executes
- **Filtering** - Press `/` to filter table rows
- **Async Operations** - Use `asyncio.gather()` for parallel operations with real-time UI updates

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

**IMPORTANT:** This is a **copy-paste resource**, not a library. Do NOT import from prototui or add it as a dependency.

### For AI Agents (LLMs):
When helping users build a TUI:
1. **Browse** pattern files to find the closest match
2. **Copy** the entire pattern file into the user's project
3. **Copy** utilities the pattern uses (e.g., `layered_data_table.py`, `explanation_panel.py`) into the user's project (e.g., `your_project/utils/`)
4. **Adapt** the code to their specific needs - modify freely!
5. **Explain** which pattern you chose and what changes you made

### Why Copy Instead of Import?

✅ **Freedom to modify** - Change anything without breaking other projects
✅ **No dependencies** - Don't worry about prototui updates
✅ **Self-contained** - All code lives in your project
✅ **Learn by doing** - Reading and adapting the code teaches TUI patterns

### Step-by-Step Workflow:

1. **Find the pattern** that matches your use case (see Quick Pattern Selection above)
2. **Copy pattern file** → `your_project/screens/my_screen.py` (or however you want to organize it)
3. **Copy utilities** → `your_project/utils/` (create this directory if needed)
4. **Update imports** in the pattern file:
   ```python
   # Change this:
   from utilities.layered_data_table import LayeredDataTable

   # To this:
   from utils.layered_data_table import LayeredDataTable
   ```
5. **Customize** - Adapt data structures, actions, styling, and behavior
6. **Run** - Test and iterate

The patterns are complete, runnable examples. They demonstrate best practices through working code rather than written rules. Treat them as **educational templates**, not library code.
