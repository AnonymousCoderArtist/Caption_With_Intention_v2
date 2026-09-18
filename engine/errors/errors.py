"""Error classification and reporting per spec §21."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ErrorCategory(str, Enum):
    fatal = "fatal"
    recoverable = "recoverable"
    model_unavailable = "model_unavailable"
    insufficient_disk = "insufficient_disk"
    unsupported_codec = "unsupported_codec"
    gpu_memory_exhaustion = "gpu_memory_exhaustion"
    low_ai_confidence = "low_ai_confidence"
    conflicting_speaker_attribution = "conflicting_speaker_attribution"
    malformed_caption_source = "malformed_caption_source"
    output_encode_failure = "output_encode_failure"
    validation_error = "validation_error"
    user_override = "user_override"


class CWIError(Exception):
    """Base exception for Caption With Intention."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.recoverable,
        recoverable: bool = True,
        stage: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.recoverable = recoverable
        self.stage = stage
        self.details = details or {}

    def __repr__(self) -> str:
        return (
            f"CWIError({self.category.value}: {self.message}"
            f", stage={self.stage}, recoverable={self.recoverable})"
        )

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "category": self.category.value,
            "recoverable": self.recoverable,
            "stage": self.stage,
            "details": self.details,
        }


class ProjectCorruptionError(CWIError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message,
            category=ErrorCategory.fatal,
            recoverable=False,
            details=details,
        )


class ModelUnavailableError(CWIError):
    def __init__(self, model_name: str):
        super().__init__(
            f"Model not available: {model_name}",
            category=ErrorCategory.model_unavailable,
            recoverable=True,
            details={"model": model_name},
        )


class LowConfidenceError(CWIError):
    def __init__(
        self,
        stage: str,
        confidence: float,
        threshold: float,
        item_id: Optional[str] = None,
    ):
        super().__init__(
            f"Low confidence {confidence:.3f} < {threshold:.3f} at {stage}",
            category=ErrorCategory.low_ai_confidence,
            recoverable=True,
            stage=stage,
            details={
                "confidence": confidence,
                "threshold": threshold,
                "item_id": item_id,
            },
        )


class ValidationError(CWIError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message,
            category=ErrorCategory.validation_error,
            recoverable=True,
            details=details,
        )


class OutputEncodeError(CWIError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message,
            category=ErrorCategory.output_encode_failure,
            recoverable=True,
            details=details or {},
        )
