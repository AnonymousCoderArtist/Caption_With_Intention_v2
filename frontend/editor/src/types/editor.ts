"""Editor API type stub for TypeScript interop.

The EditorAPI class in engine/editor/api.py is the Python
source of truth. This stub provides the TypeScript interface
type for the App component.
"""

from typing import Protocol, runtime_checkable
from typing import Optional, Any


@runtime_checkable
class EditorAPI(Protocol):
    """Protocol matching the EditorAPI Python class interface."""

    def get_project_summary(self) -> dict[str, Any]:
        ...

    def undo(self) -> dict[str, Any]:
        ...

    def redo(self) -> dict[str, Any]:
        ...

    def can_undo(self) -> dict[str, Any]:
        ...

    def can_redo(self) -> dict[str, Any]:
        ...
