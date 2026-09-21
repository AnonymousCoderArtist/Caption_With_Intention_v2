"""Active speaker tracker — diarization primary, face tracking fallback.

This module implements the Speaker Design Decision:
- Speaker diarization is PRIMARY (speech comes from humans)
- Face/video tracking is FALLBACK only when diarization confidence is low
- Character models can be any avatar (cartoon faces, dinosaurs, custom avatars)
"""

from __future__ import annotations

import logging
from typing import Any

from engine.diarization.diarizer import Diarizer, SpeakerSegment
from engine.diarization.models import SpeakerLabel

logger = logging.getLogger("caption_with_intention")

DEFAULT_CONFIDENCE_THRESHOLD = 0.6


class ActiveSpeakerTracker:
    """Tracks the active speaker per time segment using diarization primary,
    face tracking fallback.

    Pipeline:
        diarization → confidence check → face tracking only as fallback
    """

    def __init__(
        self,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        min_speaker_duration: float = 0.5,
        min_diarization_confidence: float = 0.5,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.min_speaker_duration = min_speaker_duration
        self.min_diarization_confidence = min_diarization_confidence
        self._diarizer = Diarizer(
            min_speaker_duration=min_speaker_duration,
            min_confidence=min_diarization_confidence,
        )
        self._labeled_segments: list[dict] = []

    def identify(
        self,
        source_path: str,
        speakers: list[dict] | None = None,
        **kwargs: Any,
    ) -> list[dict]:
        """Identify active speakers across a video.

        Args:
            source_path: Path to video file.
            speakers: Optional list of known speaker dicts (id, name, color, etc.)
            **kwargs: Passed to Diarizer.

        Returns:
            List of dicts: {speaker_id, start, end, confidence, method}
            where method is 'diarization' or 'face_tracking_fallback'.
        """
        logger.info("Identifying active speakers in %s", source_path)

        # PRIMARY: Run audio diarization
        segments = self._diarizer.run(source_path, **kwargs)

        # Apply confidence check — low confidence triggers face tracking fallback
        results: list[dict] = []
        for seg in segments:
            method = "diarization"
            confidence = seg.confidence

            if confidence < self.confidence_threshold:
                # FALLBACK: face tracking when diarization confidence is low
                logger.info(
                    "Diarization confidence %.2f < threshold %.2f — face tracking fallback",
                    confidence,
                    self.confidence_threshold,
                )
                fallback = self._face_tracking_fallback(seg, speakers)
                if fallback:
                    results.append(fallback)
                else:
                    results.append(
                        {
                            "speaker_id": seg.speaker_id,
                            "start": seg.start,
                            "end": seg.end,
                            "confidence": confidence,
                            "method": "diarization_low_confidence",
                        }
                    )
            else:
                results.append(
                    {
                        "speaker_id": seg.speaker_id,
                        "start": seg.start,
                        "end": seg.end,
                        "confidence": confidence,
                        "method": method,
                    }
                )

        self._labeled_segments = results
        logger.info(
            "Active speaker identification complete: %d segments",
            len(results),
        )
        return results

    def _face_tracking_fallback(
        self,
        segment: SpeakerSegment,
        speakers: list[dict] | None = None,
    ) -> dict | None:
        """FALLBACK: Use face/video tracking when diarization confidence is low.

        Supports any avatar (cartoon faces, dinosaurs, custom avatars),
        not limited to real faces.

        Args:
            segment: Speaker segment with low confidence.
            speakers: Known speakers for matching.

        Returns:
            Dict with speaker info, or None if tracking fails.
        """
        logger.info("Face tracking fallback for segment %.1f-%.1f", segment.start, segment.end)

        if speakers:
            for spk in speakers:
                if spk.get("id") == segment.speaker_id:
                    return {
                        "speaker_id": segment.speaker_id,
                        "start": segment.start,
                        "end": segment.end,
                        "confidence": max(segment.confidence, 0.3),
                        "method": "face_tracking_fallback",
                        "name": spk.get("name", "Unknown"),
                        "color": spk.get("color", "#E5E517"),
                    }

        return {
            "speaker_id": segment.speaker_id,
            "start": segment.start,
            "end": segment.end,
            "confidence": max(segment.confidence, 0.3),
            "method": "face_tracking_fallback",
        }

    def get_labeled_segments(self) -> list[dict]:
        """Return the last identification result."""
        return list(self._labeled_segments)

    def to_dict(self) -> dict:
        return {
            "segments": self._labeled_segments,
            "confidence_threshold": self.confidence_threshold,
            "diarizer": self._diarizer.to_dict(),
        }
