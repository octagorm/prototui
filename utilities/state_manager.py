"""
State management utilities for TUI applications.
"""

from typing import Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class StateChange:
    """Represents a state change event."""

    key: str
    """The state key that changed."""

    old_value: Any
    """Previous value."""

    new_value: Any
    """New value."""


class StateManager:
    """
    Simple state management with change tracking and callbacks.

    Example:
        ```python
        state = StateManager()

        # Set initial state
        state.set("repos", [])
        state.set("current_layer", "core")

        # Add a change listener
        def on_layer_change(change: StateChange):
            print(f"Layer changed from {change.old_value} to {change.new_value}")

        state.watch("current_layer", on_layer_change)

        # Update state (triggers callback)
        state.set("current_layer", "api")  # Prints: Layer changed from core to api
        ```

    Attributes:
        state: Internal state dictionary
        watchers: Dictionary of state key to list of callbacks
    """

    def __init__(self, initial_state: Optional[dict[str, Any]] = None) -> None:
        """
        Initialize the state manager.

        Args:
            initial_state: Initial state values
        """
        self._state: dict[str, Any] = initial_state or {}
        self._watchers: dict[str, list[Callable[[StateChange], None]]] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a state value.

        Args:
            key: State key
            default: Default value if key doesn't exist

        Returns:
            State value or default
        """
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a state value.

        Args:
            key: State key
            value: New value
        """
        old_value = self._state.get(key)

        # Only trigger watchers if value actually changed
        if old_value != value:
            self._state[key] = value

            # Notify watchers
            if key in self._watchers:
                change = StateChange(key, old_value, value)
                for watcher in self._watchers[key]:
                    watcher(change)

    def update(self, updates: dict[str, Any]) -> None:
        """
        Update multiple state values.

        Args:
            updates: Dictionary of state updates
        """
        for key, value in updates.items():
            self.set(key, value)

    def delete(self, key: str) -> None:
        """
        Delete a state value.

        Args:
            key: State key to delete
        """
        if key in self._state:
            old_value = self._state[key]
            del self._state[key]

            # Notify watchers
            if key in self._watchers:
                change = StateChange(key, old_value, None)
                for watcher in self._watchers[key]:
                    watcher(change)

    def clear(self) -> None:
        """Clear all state (does not trigger watchers)."""
        self._state.clear()

    def watch(self, key: str, callback: Callable[[StateChange], None]) -> None:
        """
        Watch a state key for changes.

        Args:
            key: State key to watch
            callback: Function to call when key changes
        """
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)

    def unwatch(self, key: str, callback: Callable[[StateChange], None]) -> None:
        """
        Stop watching a state key.

        Args:
            key: State key
            callback: Callback to remove
        """
        if key in self._watchers:
            self._watchers[key] = [
                w for w in self._watchers[key] if w != callback
            ]

    def has(self, key: str) -> bool:
        """
        Check if a state key exists.

        Args:
            key: State key

        Returns:
            True if key exists, False otherwise
        """
        return key in self._state

    def keys(self) -> list[str]:
        """Get all state keys."""
        return list(self._state.keys())

    def to_dict(self) -> dict[str, Any]:
        """Get a copy of the entire state as a dictionary."""
        return self._state.copy()

    def from_dict(self, state: dict[str, Any]) -> None:
        """
        Replace entire state from a dictionary.

        Args:
            state: New state dictionary
        """
        # Clear and update to trigger watchers properly
        old_keys = set(self._state.keys())
        new_keys = set(state.keys())

        # Remove deleted keys
        for key in old_keys - new_keys:
            self.delete(key)

        # Update/add keys
        for key, value in state.items():
            self.set(key, value)
