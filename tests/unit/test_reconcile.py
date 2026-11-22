"""M7 unit tests — cross-chunk speaker identity reconciliation."""

from __future__ import annotations

import pytest

from engine.diarization.models import SpeakerSegment
from engine.diarization.reconcile import (
    ReconciliationResult,
    merge_duplicate_turns,
    merge_speakers,
    reconcile_speakers,
    split_speaker,
)


def _seg(speaker: str, start: float, end: float, conf: float = 0.9) -> SpeakerSegment:
    return SpeakerSegment(speaker_id=speaker, start=start, end=end, confidence=conf)


# ─── Basic Reconciliation ──────────────────────────────────────


class TestReconcileSpeakers:
    def test_single_chunk_passthrough(self):
        result = reconcile_speakers([[_seg("spk_0", 0, 5), _seg("spk_1", 5, 9)]])
        assert isinstance(result, ReconciliationResult)
        assert len(result.global_speakers) == 2
        assert result.matches == []
        assert result.unmatched == []
        # local ids map to global ids
        assert set(result.speaker_map) == {(0, "spk_0"), (0, "spk_1")}
        # all segments relabeled to a global id
        assert {s.speaker_id for s in result.segments} == set(
            result.global_speakers
        )

    def test_overlap_links_speakers(self):
        # Chunk 0: 0-12s, chunk 1: 10-22s (2s overlap, like spec §9)
        chunk0 = [_seg("A", 0, 6), _seg("B", 6, 12)]
        chunk1 = [_seg("X", 10, 12), _seg("Y", 12, 22)]
        result = reconcile_speakers([chunk0, chunk1])
        # B and X share 2s of speech -> same global speaker
        assert result.speaker_map[(0, "B")] == result.speaker_map[(1, "X")]
        # A and Y stay distinct
        assert len(result.global_speakers) == 3
        assert len(result.matches) == 1
        assert result.matches[0].overlap == pytest.approx(2.0)

    def test_transitive_identity_across_chunks(self):
        # Speaker 1 appears in all three chunks via 2s overlaps.
        chunk0 = [_seg("a", 0, 12)]
        chunk1 = [_seg("b", 10, 22)]
        chunk2 = [_seg("c", 20, 30)]
        result = reconcile_speakers([chunk0, chunk1, chunk2])
        globals_ = {result.speaker_map[k] for k in [(0, "a"), (1, "b"), (2, "c")]}
        assert len(globals_) == 1
        assert result.global_speakers == ["spk_1"]

    def test_below_threshold_no_link(self):
        chunk0 = [_seg("A", 0, 10.1)]
        chunk1 = [_seg("B", 10.0, 20)]  # only 0.1s shared < 0.15 min
        result = reconcile_speakers([chunk0, chunk1])
        assert len(result.global_speakers) == 2
        assert (0, "A") in result.unmatched
        assert (1, "B") in result.unmatched

    def test_one_to_one_prevents_collapse(self):
        # Two speakers in each chunk; each matches its own counterpart.
        chunk0 = [_seg("A", 0, 11.5), _seg("B", 11.5, 12)]
        chunk1 = [_seg("X", 10, 11.4), _seg("Y", 11.4, 22)]
        result = reconcile_speakers([chunk0, chunk1])
        # A<->X (1.4s) and B<->Y (0.5s); A must NOT link to Y
        ga = result.speaker_map[(0, "A")]
        gx = result.speaker_map[(1, "X")]
        gb = result.speaker_map[(0, "B")]
        gy = result.speaker_map[(1, "Y")]
        assert ga == gx
        assert gb == gy
        assert ga != gb

    def test_new_speaker_mid_video(self):
        # Chunk 2 introduces a speaker not heard in the overlap window.
        chunk0 = [_seg("A", 0, 12)]
        chunk1 = [_seg("B", 10, 22)]
        chunk2 = [_seg("C", 25, 30)]  # gap: no overlap with chunk1
        result = reconcile_speakers([chunk0, chunk1, chunk2])
        assert result.speaker_map[(0, "A")] == result.speaker_map[(1, "B")]
        assert len(result.global_speakers) == 2

    def test_global_ids_first_appearance_order(self):
        chunk0 = [_seg("B", 5, 12), _seg("A", 0, 4)]
        result = reconcile_speakers([chunk0])
        assert result.speaker_map[(0, "A")] == "spk_1"
        assert result.speaker_map[(0, "B")] == "spk_2"

    def test_confidence_and_source_preserved(self):
        result = reconcile_speakers([[_seg("A", 0, 5, conf=0.7)]])
        seg = result.segments[0]
        assert seg.confidence == 0.7

    def test_to_dict_shape(self):
        result = reconcile_speakers(
            [[_seg("A", 0, 12)], [_seg("B", 10, 20)]]
        ).to_dict()
        assert "speaker_map" in result
        assert result["matches"][0]["overlap"] == pytest.approx(2.0)
        assert result["segment_count"] >= 1


# ─── Dedup of Overlapping Turns ────────────────────────────────


class TestMergeDuplicateTurns:
    def test_overlap_duplicates_merged(self):
        # Same speech diarized twice via chunk overlap
        merged = merge_duplicate_turns(
            [_seg("spk_1", 10, 12, 0.8), _seg("spk_1", 11.5, 14, 0.9)]
        )
        assert len(merged) == 1
        assert merged[0].start == 10
        assert merged[0].end == 14
        assert merged[0].confidence == 0.9

    def test_gap_boundary(self):
        merged = merge_duplicate_turns(
            [_seg("spk_1", 0, 1), _seg("spk_1", 1.04, 2)], gap=0.05
        )
        assert len(merged) == 1
        merged2 = merge_duplicate_turns(
            [_seg("spk_1", 0, 1), _seg("spk_1", 1.2, 2)], gap=0.05
        )
        assert len(merged2) == 2

    def test_different_speakers_preserved(self):
        merged = merge_duplicate_turns(
            [_seg("spk_1", 0, 5), _seg("spk_2", 2, 6)]
        )
        assert len(merged) == 2

    def test_empty(self):
        assert merge_duplicate_turns([]) == []

    def test_output_sorted(self):
        merged = merge_duplicate_turns(
            [_seg("spk_1", 5, 6), _seg("spk_1", 0, 1)]
        )
        assert [s.start for s in merged] == [0, 5]


# ─── Editor Override: merge / split ────────────────────────────


class TestMergeSplit:
    def test_merge_speakers(self):
        segs = [_seg("spk_1", 0, 1), _seg("spk_2", 2, 3), _seg("spk_1", 4, 5)]
        out = merge_speakers(segs, from_id="spk_2", to_id="spk_1")
        assert {s.speaker_id for s in out} == {"spk_1"}
        # inputs untouched
        assert segs[1].speaker_id == "spk_2"

    def test_split_after_time(self):
        segs = [_seg("spk_1", 0, 1), _seg("spk_1", 10, 11), _seg("spk_1", 20, 21)]
        out = split_speaker(segs, "spk_1", "spk_2", after=10.0)
        assert [s.speaker_id for s in out] == ["spk_1", "spk_2", "spk_2"]

    def test_split_all(self):
        segs = [_seg("spk_1", 0, 1), _seg("spk_1", 2, 3)]
        out = split_speaker(segs, "spk_1", "spk_9", after=None)
        assert {s.speaker_id for s in out} == {"spk_9"}
