"""
Utility: Terminal Compatibility

Ensures your TUI works correctly across different terminals (iTerm2, IntelliJ IDEA, VS Code, etc.)

This utility fixes:
- Color support: Detects and enables truecolor in terminals that support it but don't advertise it
- Terminal detection: Identifies terminals and applies appropriate enhancements

IMPORTANT: Always use run_app() instead of app.run() to get these compatibility fixes.
Without this, colors will look worse in IntelliJ IDEA's terminal.

Note about IntelliJ IDEA:
- Mouse support works but can be slightly glitchy (fast scrolling, occasional jumps)
- This is a known limitation of IntelliJ's terminal emulator (JediTerm)
- Users can disable mouse via TUI_MOUSE=false env var if they prefer keyboard-only

Copy this into your project and use it as the default way to run your Textual apps.
"""

import os
import sys
from typing import Literal

ColorSystem = Literal["auto", "standard", "256", "truecolor", "windows"]


# Auto-enhance terminal on import (CRITICAL: Must happen before App instantiation)
def _auto_enhance_on_import():
    """
    Enhance terminal capabilities immediately on module import.

    This MUST run before any Textual App is instantiated, because Textual
    detects color support during App.__init__(), not during app.run().
    """
    # Check if user has already set COLORTERM
    if os.environ.get("COLORTERM"):
        return  # Already set, don't override

    # Check for user override
    user_override = os.environ.get("TUI_COLOR_SYSTEM", "").lower()
    if user_override:
        return  # Let enhance_terminal_for_tui handle this later

    # Detect terminal and set COLORTERM if appropriate
    colorterm = os.environ.get("COLORTERM", "").lower()
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    terminal_emulator = os.environ.get("TERMINAL_EMULATOR", "").lower()

    # If already has truecolor, nothing to do
    if "truecolor" in colorterm or "24bit" in colorterm:
        return

    # Detect terminals that support truecolor but don't advertise it
    should_enable_truecolor = False

    if term_program in ("iterm.app", "vscode", "hyper"):
        should_enable_truecolor = True
    elif "jetbrains" in term_program or "intellij" in term_program:
        should_enable_truecolor = True
    elif "jetbrains" in terminal_emulator or "jediterm" in terminal_emulator:
        should_enable_truecolor = True
    elif "256color" in term:
        # Upgrade 256 color terminals to truecolor (most modern terminals support it)
        should_enable_truecolor = True

    if should_enable_truecolor:
        os.environ["COLORTERM"] = "truecolor"


# Run enhancement immediately on import
_auto_enhance_on_import()


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
    terminal_emulator = os.environ.get("TERMINAL_EMULATOR", "").lower()

    # Explicit truecolor indicators
    if "truecolor" in colorterm or "24bit" in colorterm:
        return "truecolor"

    # Known terminals with truecolor support
    if term_program in ("iterm.app", "vscode", "hyper"):
        return "truecolor"

    # IntelliJ/JetBrains terminals support truecolor but don't advertise it
    # Check both TERM_PROGRAM and TERMINAL_EMULATOR (IntelliJ uses the latter)
    if "jetbrains" in term_program or "intellij" in term_program:
        return "truecolor"
    if "jetbrains" in terminal_emulator or "jediterm" in terminal_emulator:
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


def run_app(app, mouse=None, **run_kwargs):
    """
    Run a Textual app with automatic terminal compatibility fixes.

    This handles:
    - Color support: Enables truecolor in terminals like IntelliJ IDEA

    Args:
        app: The Textual App instance to run
        mouse: Enable/disable mouse support. Defaults to enabled.
               Set to False to disable mouse (keyboard-only mode).
        **run_kwargs: Additional arguments to pass to app.run()

    Usage:
        from utilities.terminal_compat import run_app

        app = MyApp()
        run_app(app)  # Auto-handles colors

        # Explicitly disable mouse (keyboard-only)
        run_app(app, mouse=False)

        # Or with custom run args:
        run_app(app, inline=True)
    """
    # Set environment variable for better color detection
    # Textual will automatically detect this
    enhance_terminal_for_tui()

    # Check for user override via env var
    user_mouse_override = os.environ.get("TUI_MOUSE", "").lower()
    if user_mouse_override in ("true", "1", "yes"):
        mouse = True
    elif user_mouse_override in ("false", "0", "no"):
        mouse = False

    # Note: We used to auto-disable mouse in IntelliJ, but that prevents
    # scrollbar dragging and clicking. Better to keep mouse enabled by default
    # even if scrolling is a bit glitchy. Users can disable via TUI_MOUSE=false if needed.

    # Set mouse parameter if user explicitly specified it
    if mouse is not None:
        run_kwargs["mouse"] = mouse

    return app.run(**run_kwargs)


# Escape hatches: User can override via environment variables
#
# Color system override:
#   export TUI_COLOR_SYSTEM=256        # Force 256 colors
#   export TUI_COLOR_SYSTEM=standard   # Force 16 colors (for old terminals)
#   export TUI_COLOR_SYSTEM=auto       # Let Textual decide
#
# Mouse support override:
#   export TUI_MOUSE=false             # Disable mouse (fixes IntelliJ IDEA issues)
#   export TUI_MOUSE=true              # Force enable mouse
