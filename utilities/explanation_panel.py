"""
ExplanationPanel Utility: Reusable side panel for help/explanation text.

A simple Static widget designed for two-pane layouts showing explanatory content.

Key Features:
- Non-focusable (doesn't interfere with tab navigation)
- Dynamic content updates with proper layout recalculation
- Works correctly inside VerticalScroll containers
- Properly expands to show all content without truncation

Usage:
    from utilities.explanation_panel import ExplanationPanel

    # In your screen's compose():
    with VerticalScroll(id="explanation-pane"):
        yield ExplanationPanel(
            "My Title",
            "Explanation content here...\\n\\nSupports multiple lines."
        )

    # To update content dynamically:
    panel = self.query_one(ExplanationPanel)
    panel.update_content("New Title", "New content...")

CSS Setup (Important):
    The ExplanationPanel should NOT have a height specified in CSS.
    Let it naturally expand within its VerticalScroll container.

    Correct CSS:
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
        /* DO NOT set height here - let it expand naturally */
    }
    ```

    Avoid:
    ```css
    ExplanationPanel {
        height: auto;  /* Can cause truncation with dynamic content */
    }
    ```

Technical Notes:
- Uses `refresh(layout=True)` to force layout recalculation on updates
- No explicit height allows natural expansion within VerticalScroll
- The parent VerticalScroll handles scrolling when content exceeds viewport
"""

from textual.widgets import Static


class ExplanationPanel(Static):
    """Side panel showing help/explanation text.

    This widget is designed to be placed inside a VerticalScroll container
    in two-pane layouts. It automatically expands to fit all content and
    properly updates when content changes.
    """

    # Prevent this panel from being focusable
    can_focus = False

    def __init__(self, title: str, content: str):
        """
        Initialize the explanation panel.

        Args:
            title: Bold title shown at the top
            content: Body content (supports Textual markup)
        """
        super().__init__()
        self.panel_title = title
        self.panel_content = content

    def render(self) -> str:
        """Render the panel content with title and body."""
        return f"[bold]{self.panel_title}[/bold]\n\n{self.panel_content}"

    def update_content(self, title: str, content: str) -> None:
        """
        Update panel content dynamically.

        Uses refresh(layout=True) to ensure proper layout recalculation
        when content changes, preventing truncation issues.

        Args:
            title: New title
            content: New content
        """
        self.panel_title = title
        self.panel_content = content
        # layout=True forces layout recalculation for dynamic content
        self.refresh(layout=True)
