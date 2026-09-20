"""Plugin registry for modular extensibility.

Plugins auto-register via __init_subclass__ by defining a ``name`` attribute.
Registration is thread-safe.
"""

from __future__ import annotations

import threading
from typing import Type


class Plugin:
    """Base class for auto-registering plugins."""

    name: str = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "name") and cls.name:
            PluginRegistry.register(cls.name, cls)


class PluginRegistry:
    """Thread-safe registry for plugin types."""

    _plugins: dict[str, Type[Plugin]] = {}
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def register(cls, name: str, plugin_cls: Type[Plugin]) -> None:
        """Register a plugin class under *name*.

        Raises ValueError if *name* is already registered.
        """
        with cls._lock:
            if name in cls._plugins:
                raise ValueError(f"Plugin '{name}' already registered")
            cls._plugins[name] = plugin_cls

    @classmethod
    def get_plugin(cls, name: str) -> Type[Plugin]:
        """Return the registered class for *name*."""
        with cls._lock:
            return cls._plugins[name]

    @classmethod
    def list_plugins(cls) -> list[str]:
        """Return all registered plugin names."""
        with cls._lock:
            return list(cls._plugins.keys())

    @classmethod
    def create(cls, name: str, **kwargs) -> Plugin:
        """Instantiate the plugin registered under *name*."""
        plugin_cls = cls.get_plugin(name)
        return plugin_cls(**kwargs)

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations (useful in tests)."""
        with cls._lock:
            cls._plugins.clear()
