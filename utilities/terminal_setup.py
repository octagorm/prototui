"""
Utility: Terminal Setup and Enhancement

Use this to ensure your TUI looks great across different terminals (iTerm2, IntelliJ, VS Code, etc.)

This utility helps with:
- Detecting terminal color capabilities
- Upgrading to truecolor when safe
- Providing escape hatches for users with older terminals

Copy this into your project and use before running your Textual app.
"""

import os
import sys
from typing import Literal

ColorSystem = Literal["auto", "standard", "256", "truecolor", "windows"]


def detect_color_support() -> ColorSystem:
    """
    Detect what color system the terminal supports.

    Returns:
        ColorSystem: The detected color system capability
    """
    # Check environment variables
    colorterm = os.environ.get("COLORTERM", "").lower()
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()

    # Explicit truecolor indicators
    if "truecolor" in colorterm or "24bit" in colorterm:
        return "truecolor"

    # Known terminals with truecolor support
    if term_program in ("iterm.app", "vscode", "hyper"):
        return "truecolor"

    # IntelliJ/JetBrains terminals support truecolor but don't advertise it
    if "jetbrains" in term_program or "intellij" in term_program:
        return "truecolor"

    # 256 color support
    if "256color" in term:
        return "256"

    # Basic color
    if "color" in term:
        return "standard"

    # Unknown, let Textual decide
    return "auto"


def enhance_terminal_for_tui(
    force_truecolor: bool = False,
    set_env_var: bool = True,
    quiet: bool = True
) -> ColorSystem:
    """
    Enhance terminal capabilities for better TUI rendering.

    This function:
    1. Detects current terminal capabilities
    2. Optionally upgrades to truecolor for modern terminals
    3. Optionally sets COLORTERM env var (affects child processes)

    Args:
        force_truecolor: Always use truecolor, even if not detected
        set_env_var: Set COLORTERM=truecolor in environment
        quiet: Don't print detection info

    Returns:
        ColorSystem: The detected color system (mainly for informational purposes)

    Usage:
        # Simple: Just enhance and run
        from utilities.terminal_setup import enhance_terminal_for_tui

        enhance_terminal_for_tui()  # Sets COLORTERM=truecolor
        app.run()  # Textual will auto-detect the enhanced colors

        # Aggressive: Force truecolor everywhere
        enhance_terminal_for_tui(force_truecolor=True)
        app.run()

        # Conservative: Detect but don't set env var
        enhance_terminal_for_tui(set_env_var=False)
        app.run()
    """
    # Check for user override via env var
    user_override = os.environ.get("TUI_COLOR_SYSTEM", "").lower()
    if user_override in ("auto", "standard", "256", "truecolor", "windows"):
        if not quiet:
            print(f"Using TUI_COLOR_SYSTEM override: {user_override}", file=sys.stderr)
        return user_override  # type: ignore

    if force_truecolor:
        color_system = "truecolor"
    else:
        color_system = detect_color_support()

        # Upgrade 256 color terminals to truecolor on modern systems
        # Most terminals since 2016 support it but don't advertise
        if color_system == "256":
            # Safe upgrade: modern terminals that report 256color usually support truecolor
            color_system = "truecolor"

    # Set environment variable so child processes benefit too
    if set_env_var and color_system == "truecolor":
        os.environ["COLORTERM"] = "truecolor"

    if not quiet:
        term = os.environ.get("TERM", "unknown")
        term_program = os.environ.get("TERM_PROGRAM", "unknown")
        print(f"Terminal: {term_program} ({term})", file=sys.stderr)
        print(f"Color system: {color_system}", file=sys.stderr)

    return color_system


def run_app_with_best_colors(app, **run_kwargs):
    """
    Convenience function: enhance terminal and run app in one call.

    Usage:
        from utilities.terminal_setup import run_app_with_best_colors

        app = MyApp()
        run_app_with_best_colors(app)

        # Or with custom run args:
        run_app_with_best_colors(app, mouse=False, inline=True)
    """
    # Set environment variable for better color detection
    # Textual will automatically detect this
    enhance_terminal_for_tui()

    return app.run(**run_kwargs)


# Escape hatch: User can set TUI_COLOR_SYSTEM environment variable to override
# Examples:
#   export TUI_COLOR_SYSTEM=256        # Force 256 colors
#   export TUI_COLOR_SYSTEM=standard   # Force 16 colors (for old terminals)
#   export TUI_COLOR_SYSTEM=auto       # Let Textual decide
