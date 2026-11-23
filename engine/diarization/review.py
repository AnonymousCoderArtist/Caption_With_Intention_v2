"""Expose attribution uncertainty without presenting ASR confidence as identity confidence."""

from __future__ import annotations


def attribution_review(
    words: list, segments: list[dict], speaker_id: str | None
) -> dict:
    reasons: set[str] = set()
    if not speaker_id:
        reasons.add("No speaker segment covers this speech.")
    coverages = []
    for word in words:
        duration = max(1e-6, word.end - word.start)
        intervals: dict[str, list[tuple[float, float]]] = {}
        for segment in segments:
            sid = segment.get("speaker_id")
            if not sid:
                continue
            start, end = (
                max(word.start, segment["start"]),
                min(word.end, segment["end"]),
            )
            if end > start:
                intervals.setdefault(sid, []).append((start, end))
        scores = {}
        for sid, spans in intervals.items():
            merged: list[list[float]] = []
            for start, end in sorted(spans):
                if merged and start <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], end)
                else:
                    merged.append([start, end])
            scores[sid] = min(1.0, sum(end - start for start, end in merged) / duration)
        ranked = sorted(scores.values(), reverse=True)
        coverage = scores.get(speaker_id, 0) if speaker_id else 0
        coverages.append(coverage)
        if coverage < 0.6:
            reasons.add("Limited diarization coverage near a word boundary.")
        if len(ranked) > 1 and ranked[1] >= 0.25 and ranked[0] - ranked[1] < 0.25:
            reasons.add("Competing speaker segments overlap this speech.")
    if words and max(w.end for w in words) - min(w.start for w in words) < 0.4:
        reasons.add("Very short turn, confirm the speaker by listening.")
    return {
        "speaker_review_required": bool(reasons),
        "speaker_review_reasons": sorted(reasons),
        "speaker_coverage": round(min(coverages), 4) if coverages else None,
    }
