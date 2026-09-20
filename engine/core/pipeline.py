"""Pipeline stage abstraction and executor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional


class PipelineStage(ABC):
    """Abstract base for a single pipeline stage."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Process *input_data* and return a result."""
        ...

    def configure(self, **kwargs) -> None:
        """Optional configuration hook. Default no-op."""
        pass


class Pipeline:
    """Runs a sequence of :class:`PipelineStage` stages."""

    def __init__(self):
        self._stages: list[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> "Pipeline":
        self._stages.append(stage)
        return self

    @property
    def stages(self) -> list[PipelineStage]:
        return list(self._stages)

    def run(self, input_data: Any) -> Any:
        """Execute stages sequentially, passing result to the next."""
        result = input_data
        for stage in self._stages:
            result = stage.execute(result)
        return result

    def run_parallel(
        self,
        input_data: Any,
        max_workers: int = 4,
    ) -> dict[str, Any]:
        """Execute all stages concurrently with the same input.

        Returns a dict mapping each stage name to its result.
        """
        results: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(stage.execute, input_data): stage.name
                for stage in self._stages
            }
            for future in futures:
                stage_name = futures[future]
                results[stage_name] = future.result()
        return results
