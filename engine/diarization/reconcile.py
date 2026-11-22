"""Cross-chunk speaker identity reconciliation (M7).

Diarization runs per chunk (spec §9: 10-min chunks, 2s overlap), and
each chunk labels its speakers independently — chunk 3's "spk_0" is not
chunk 4's "spk_0". This module maps per-chunk local labels onto stable
GLOBAL speaker identities so captions keep one color per character
across the whole video.

Matching evidence: chunks overlap in time, so the same speech is
diarized twice. Two local speakers (one per chunk) whose segments
overlap in time are hearing the SAME voice — total mutual overlap above
`min_match_overlap` links them. Matching is one-to-one (greedy by
overlap mass) so two distinct speakers in a chunk never collapse.

No embeddings needed for the overlap-linking pass; an embedding-based
matcher can be layered on later for chunks without usable overlap.

Usage:
    from engine.diarization.reconcile import reconcile_speakers

    result = reconcile_speakers(chunk_segments)
    global_segments = result.segments          # relabeled, deduped
    print(result.speaker_map)                  # (chunk, local) -> global
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from engine.diarization.models import SpeakerSegment

logger = logging.getLogger("caption_with_intention")

# Minimum mutual speech overlap (s) to link two chunk-local speakers.
DEFAULT_MIN_MATCH_OVERLAP = 0.15
# Gap (s) below which same-speaker turns are merged after dedup.
DEFAULT_MERGE_GAP = 0.05


class _UnionFind:
    """Union-find over hashable keys."""

    def __init__(self) -> None:
        self._parent: dict = {}

    def find(self, x: object) -> object:
        parent = self._parent.setdefault(x, x)
        if parent != x:
            self._parent[x] = self.find(parent)
        return self._parent[x]

    def union(self, a: object, b: object) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra


@dataclass(slots=True)
class SpeakerMatch:
    """One accepted cross-chunk speaker link."""

    chunk_a: int
    local_a: str
    chunk_b: int
    local_b: str
    overlap: float


@dataclass(slots=True)
class ReconciliationResult:
    """Output of reconcile_speakers()."""

    segments: list[SpeakerSegment]  # relabeled, time-sorted, deduped
    speaker_map: dict[tuple[int, str], str]  # (chunk, local id) -> global id
    global_speakers: list[str]  # global ids, first-appearance order
    matches: list[SpeakerMatch] = field(default_factory=list)
    unmatched: list[tuple[int, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "speaker_map": {
                f"{chunk}:{local}": global_id
                for (chunk, local), global_id in sorted(self.speaker_map.items())
            },
            "global_speakers": list(self.global_speakers),
            "matches": [
                {
                    "chunk_a": m.chunk_a,
                    "local_a": m.local_a,
                    "chunk_b": m.chunk_b,
                    "local_b": m.local_b,
                    "overlap": round(m.overlap, 4),
                }
                for m in self.matches
            ],
            "unmatched": [f"{c}:{l}" for c, l in self.unmatched],
            "segment_count": len(self.segments),
        }


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    """Shared duration of two time ranges (0 when disjoint)."""
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _pairwise_speaker_overlap(
    segs_a: list[SpeakerSegment],
    segs_b: list[SpeakerSegment],
) -> dict[tuple[str, str], float]:
    """Total time overlap between each (speaker_a, speaker_b) pair."""
    scores: dict[tuple[str, str], float] = {}
    for sa in segs_a:
        for sb in segs_b:
            ov = _overlap(sa.start, sa.end, sb.start, sb.end)
            if ov > 0:
                key = (sa.speaker_id, sb.speaker_id)
                scores[key] = scores.get(key, 0.0) + ov
    return scores


def _greedy_one_to_one(
    scores: dict[tuple[str, str], float],
    min_overlap: float,
) -> list[tuple[str, str, float]]:
    """Greedy highest-overlap one-to-one matching above the threshold."""
    matches: list[tuple[str, str, float]] = []
    used_a: set[str] = set()
    used_b: set[str] = set()
    for (a, b), score in sorted(scores.items(), key=lambda kv: -kv[1]):
        if score < min_overlap:
            break
        if a in used_a or b in used_b:
            continue
        used_a.add(a)
        used_b.add(b)
        matches.append((a, b, score))
    return matches


def reconcile_speakers(
    chunk_segments: list[list[SpeakerSegment]],
    min_match_overlap: float = DEFAULT_MIN_MATCH_OVERLAP,
    merge_gap: float = DEFAULT_MERGE_GAP,
) -> ReconciliationResult:
    """Map per-chunk local speaker labels to stable global identities.

    Args:
        chunk_segments: One SpeakerSegment list per chunk, with times on
            the SOURCE timeline (chunk offset already applied). Chunks
            are expected in timeline order and to overlap their neighbor.
        min_match_overlap: Minimum mutual speech overlap (s) to accept a
            cross-chunk speaker link.
        merge_gap: Same-speaker turns closer than this (s) are merged
            when duplicates from the chunk overlap are collapsed.

    Returns:
        ReconciliationResult with globally relabeled, deduplicated,
        time-sorted segments plus the local->global map and match log.
    """
    uf = _UnionFind()
    matches: list[SpeakerMatch] = []

    # Link adjacent chunks via their temporal overlap. Transitivity
    # through union-find handles identity across many chunks (chunk i
    # and i+2 share speakers via chunk i+1 even if they don't overlap).
    for i in range(len(chunk_segments) - 1):
        scores = _pairwise_speaker_overlap(
            chunk_segments[i], chunk_segments[i + 1]
        )
        for local_a, local_b, ov in _greedy_one_to_one(
            scores, min_match_overlap
        ):
            uf.union((i, local_a), (i + 1, local_b))
            matches.append(
                SpeakerMatch(
                    chunk_a=i,
                    local_a=local_a,
                    chunk_b=i + 1,
                    local_b=local_b,
                    overlap=ov,
                )
            )

    # Assign global ids in first-appearance order (earliest segment wins)
    first_seen: dict[object, float] = {}
    for chunk_idx, segments in enumerate(chunk_segments):
        for seg in segments:
            key = uf.find((chunk_idx, seg.speaker_id))
            if key not in first_seen or seg.start < first_seen[key]:
                first_seen[key] = seg.start

    ordered_roots = sorted(first_seen, key=lambda k: (first_seen[k], str(k)))
    global_id_of = {
        root: f"spk_{n + 1}" for n, root in enumerate(ordered_roots)
    }

    speaker_map: dict[tuple[int, str], str] = {}
    matched_keys = {(m.chunk_a, m.local_a) for m in matches} | {
        (m.chunk_b, m.local_b) for m in matches
    }
    relabeled: list[SpeakerSegment] = []
    for chunk_idx, segments in enumerate(chunk_segments):
        for seg in segments:
            local_key = (chunk_idx, seg.speaker_id)
            global_id = global_id_of[uf.find(local_key)]
            speaker_map[local_key] = global_id
            relabeled.append(
                SpeakerSegment(
                    speaker_id=global_id,
                    start=seg.start,
                    end=seg.end,
                    confidence=seg.confidence,
                    source=seg.source,
                )
            )

    unmatched = [
        key
        for key in speaker_map
        if key not in matched_keys and len(chunk_segments) > 1
    ]
    if unmatched:
        logger.info(
            "Reconciliation: %d chunk-local speakers had no overlap match "
            "(treated as new global speakers)",
            len(unmatched),
        )

    deduped = merge_duplicate_turns(relabeled, gap=merge_gap)

    logger.info(
        "Reconciliation complete: %d chunks -> %d global speakers, "
        "%d links, %d segments (%d after dedup)",
        len(chunk_segments),
        len(ordered_roots),
        len(matches),
        len(relabeled),
        len(deduped),
    )

    return ReconciliationResult(
        segments=deduped,
        speaker_map=speaker_map,
        global_speakers=[global_id_of[r] for r in ordered_roots],
        matches=matches,
        unmatched=unmatched,
    )


def merge_duplicate_turns(
    segments: list[SpeakerSegment],
    gap: float = DEFAULT_MERGE_GAP,
) -> list[SpeakerSegment]:
    """Collapse overlapping/near-touching same-speaker turns.

    Chunks overlap, so after relabeling the same speech can appear twice
    (once per chunk) for the same global speaker. Turns of one speaker
    that overlap or sit within `gap` seconds are merged into a single
    turn spanning both, keeping the higher confidence. Different-speaker
    overlaps (real simultaneous speech) are preserved.
    """
    if not segments:
        return []
    ordered = sorted(segments, key=lambda s: (s.start, s.end))
    merged: list[SpeakerSegment] = [
        SpeakerSegment(
            speaker_id=ordered[0].speaker_id,
            start=ordered[0].start,
            end=ordered[0].end,
            confidence=ordered[0].confidence,
            source=ordered[0].source,
        )
    ]
    for seg in ordered[1:]:
        last = merged[-1]
        if seg.speaker_id == last.speaker_id and seg.start <= last.end + gap:
            last.end = max(last.end, seg.end)
            last.start = min(last.start, seg.start)
            last.confidence = max(last.confidence, seg.confidence)
        else:
            merged.append(
                SpeakerSegment(
                    speaker_id=seg.speaker_id,
                    start=seg.start,
                    end=seg.end,
                    confidence=seg.confidence,
                    source=seg.source,
                )
            )
    return merged


def merge_speakers(
    segments: list[SpeakerSegment],
    from_id: str,
    to_id: str,
) -> list[SpeakerSegment]:
    """Relabel every `from_id` segment as `to_id` (editor override path).

    Use when reconciliation (or diarization) split one real person into
    two speakers. Returns a new list; inputs are not mutated.
    """
    return [
        SpeakerSegment(
            speaker_id=to_id if seg.speaker_id == from_id else seg.speaker_id,
            start=seg.start,
            end=seg.end,
            confidence=seg.confidence,
            source=seg.source,
        )
        for seg in segments
    ]


def split_speaker(
    segments: list[SpeakerSegment],
    speaker_id: str,
    new_id: str,
    after: Optional[float] = None,
) -> list[SpeakerSegment]:
    """Move some of one speaker's turns to a new id (editor override path).

    Args:
        speaker_id: Speaker to split.
        new_id: New speaker id for the moved turns.
        after: Turns STARTING at or after this time (s) move to new_id;
            None moves every turn. Turns are never cut mid-segment — an
            in-flight turn belongs to its start side.
    """
    out: list[SpeakerSegment] = []
    for seg in segments:
        move = (
            seg.speaker_id == speaker_id
            and (after is None or seg.start >= after)
        )
        out.append(
            SpeakerSegment(
                speaker_id=new_id if move else seg.speaker_id,
                start=seg.start,
                end=seg.end,
                confidence=seg.confidence,
                source=seg.source,
            )
        )
    return out
