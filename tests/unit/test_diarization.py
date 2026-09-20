"""M3 unit tests — caption exporters and speaker diarization."""

from __future__ import annotations

import pytest

from engine.exporters.srt import SrtExporter
from engine.exporters.vtt import VttExporter
from engine.exporters.ass import AssExporter
from engine.exporters.ttml import TtmlExporter
from engine.exporters.base import CaptionExporter
from engine.diarization.diarizer import Diarizer
from engine.diarization.models import SpeakerSegment, SpeakerLabel
from engine.active_speaker.active_speaker import ActiveSpeakerTracker
from engine.core.registry import PluginRegistry


# ─── SRT Exporter Tests ─────────────────────────────────────────────


class TestSrtExporter:
    def test_srt_export_basic(self):
        events = [
            {"start": 0.0, "end": 2.5, "text": "Hello."},
            {"start": 2.5, "end": 5.0, "text": "World."},
        ]
        result = SrtExporter().export(events)
        assert "WEBVTT" not in result  # SRT doesn't have WEBVTT header
        assert "1" in result
        assert "00:00:00,000 --> 00:00:02,500" in result
        assert "Hello." in result
        assert "2" in result
        assert "00:00:02,500 --> 00:00:05,000" in result
        assert "World." in result

    def test_srt_empty_events(self):
        exporter = SrtExporter()
        result = exporter.export([])
        assert result.strip() == ""

    def test_srt_index_incrementing(self):
        events = [
            {"start": 0.0, "end": 1.0, "text": "A"},
            {"start": 1.0, "end": 2.0, "text": "B"},
            {"start": 2.0, "end": 3.0, "text": "C"},
        ]
        result = SrtExporter().export(events)
        lines = result.strip().split("\n")
        # Indices should be 1, 2, 3
        assert lines[0] == "1"
        assert lines[4] == "2"
        assert lines[8] == "3"

    def test_srt_name(self):
        exporter = SrtExporter()
        assert exporter.name == "srt"


# ─── VTT Exporter Tests ─────────────────────────────────────────────


class TestVttExporter:
    def test_vtt_export_basic(self):
        events = [
            {"start": 0.0, "end": 2.5, "text": "Hello."},
            {"start": 2.5, "end": 5.0, "text": "World."},
        ]
        result = VttExporter().export(events)
        assert result.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.500" in result
        assert "Hello." in result
        assert "00:00:02.500 --> 00:00:05.000" in result
        assert "World." in result

    def test_vtt_empty_events(self):
        exporter = VttExporter()
        result = exporter.export([])
        # WEBVTT header + empty cue
        assert "WEBVTT" in result

    def test_vtt_name(self):
        exporter = VttExporter()
        assert exporter.name == "vtt"


# ─── ASS Exporter Tests ─────────────────────────────────────────────


class TestAssExporter:
    def test_ass_export_basic(self):
        events = [
            {"start": 0.0, "end": 2.5, "text": "Hello."},
            {"start": 2.5, "end": 5.0, "text": "World."},
        ]
        result = AssExporter().export(events)
        assert "[Script Info]" in result
        assert "[V4+ Styles]" in result
        assert "[Events]" in result
        assert "Dialogue: 0,0:00:00.00,0:00:02.50" in result
        assert "Dialogue: 0,0:00:02.50,0:00:05.00" in result

    def test_ass_escape_curly_braces(self):
        events = [
            {"start": 0.0, "end": 1.0, "text": "{important}"},
        ]
        result = AssExporter().export(events)
        assert "\\{important\\}" in result

    def test_ass_escape_backslash(self):
        events = [
            {"start": 0.0, "end": 1.0, "text": "path\\file"},
        ]
        result = AssExporter().export(events)
        assert "path\\\\file" in result

    def test_ass_newline_to_n(self):
        events = [
            {"start": 0.0, "end": 1.0, "text": "Line1\nLine2"},
        ]
        result = AssExporter().export(events)
        assert "\\N" in result

    def test_ass_name(self):
        exporter = AssExporter()
        assert exporter.name == "ass"


# ─── TTML Exporter Tests ─────────────────────────────────────────────


class TestTtmlExporter:
    def test_ttml_export_basic(self):
        events = [
            {"start": 0.0, "end": 2.5, "text": "Hello."},
            {"start": 2.5, "end": 5.0, "text": "World."},
        ]
        result = TtmlExporter().export(events)
        assert '<?xml version="1.0"' in result
        assert "<tt " in result
        assert "<head>" in result
        assert "<body>" in result
        assert "</tt>" in result
        assert "begin=\"00:00:00.000\"" in result
        assert "end=\"00:00:02.500\"" in result

    def test_ttml_speaker_attribute(self):
        events = [
            {"start": 0.0, "end": 1.0, "text": "Hi", "speaker_id": "spk_1"},
        ]
        result = TtmlExporter().export(events)
        assert 'xml:lang="spk_1"' in result

    def test_ttml_empty_events(self):
        exporter = TtmlExporter()
        result = exporter.export([])
        assert "<body>" in result
        assert "</body>" in result

    def test_ttml_name(self):
        exporter = TtmlExporter()
        assert exporter.name == "ttml"


# ─── Base Exporter Tests ─────────────────────────────────────────────


class TestCaptionExporterBase:
    def test_is_abstract(self):
        with pytest.raises(TypeError):
            CaptionExporter()

    def test_plugin_auto_registration(self):
        registry = PluginRegistry()
        # SrtExporter, VttExporter etc. auto-register via __init_subclass__
        assert "srt" in registry.list_plugins()
        assert "vtt" in registry.list_plugins()
        assert "ass" in registry.list_plugins()
        assert "ttml" in registry.list_plugins()


# ─── Diarization Tests ───────────────────────────────────────────────


class TestSpeakerSegment:
    def test_segment_creation(self):
        seg = SpeakerSegment(
            speaker_id="spk_1",
            start=0.0,
            end=5.0,
            confidence=0.8,
        )
        assert seg.speaker_id == "spk_1"
        assert seg.start == 0.0
        assert seg.end == 5.0
        assert seg.confidence == 0.8

    def test_segment_duration(self):
        seg = SpeakerSegment(
            speaker_id="spk_1",
            start=2.0,
            end=8.0,
            confidence=0.9,
        )
        assert seg.duration == 6.0

    def test_segment_to_dict(self):
        seg = SpeakerSegment(
            speaker_id="spk_1",
            start=0.0,
            end=3.0,
            confidence=0.7,
            source="test",
        )
        d = seg.to_dict()
        assert d["speaker_id"] == "spk_1"
        assert d["duration"] == 3.0
        assert d["source"] == "test"


class TestSpeakerLabel:
    def test_label_creation(self):
        label = SpeakerLabel(
            id="spk_1",
            name="Hero",
            category="main",
            color="#E5E517",
            confidence=0.9,
        )
        assert label.name == "Hero"
        assert label.category == "main"
        assert label.color == "#E5E517"

    def test_label_to_dict(self):
        label = SpeakerLabel(
            id="spk_1",
            name="Hero",
            off_camera=True,
            tags=["protagonist", "hero"],
        )
        d = label.to_dict()
        assert d["off_camera"] is True
        assert len(d["tags"]) == 2


class TestDiarizer:
    def test_diarizer_creation(self):
        diarizer = Diarizer()
        assert diarizer.min_speaker_duration == 0.5
        assert diarizer.min_confidence == 0.5

    def test_diarizer_custom_params(self):
        diarizer = Diarizer(
            min_speaker_duration=1.0,
            min_confidence=0.8,
        )
        assert diarizer.min_speaker_duration == 1.0
        assert diarizer.min_confidence == 0.8

    def test_diarizer_run_fallback(self, tmp_path):
        """Test diarizer runs and returns segments (even if just 1 fallback)."""
        diarizer = Diarizer(min_confidence=0.0)  # Accept all
        # Create a minimal audio file
        import subprocess
        audio_path = str(tmp_path / "test.wav")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                 audio_path],
                capture_output=True, timeout=15,
            )
            segments = diarizer.run(audio_path)
            assert isinstance(segments, list)
            for seg in segments:
                assert isinstance(seg, SpeakerSegment)
                assert seg.start < seg.end
                assert 0.0 <= seg.confidence <= 1.0
        except FileNotFoundError:
            pytest.skip("FFmpeg not available")

    def test_diarizer_get_segments(self):
        diarizer = Diarizer(min_confidence=0.0)
        segments = [
            SpeakerSegment("spk_1", 0.0, 5.0, 0.8),
            SpeakerSegment("spk_2", 5.0, 10.0, 0.7),
        ]
        # Direct attribute set via internal storage
        diarizer._segments = segments
        result = diarizer.get_segments()
        assert len(result) == 2
        assert result[0].speaker_id == "spk_1"

    def test_diarizer_to_dict(self):
        diarizer = Diarizer()
        diarizer._segments = [
            SpeakerSegment("spk_1", 0.0, 5.0, 0.8, source="test"),
        ]
        d = diarizer.to_dict()
        assert d["min_speaker_duration"] == 0.5
        assert len(d["segments"]) == 1
        assert d["segments"][0]["source"] == "test"


# ─── Active Speaker Tests ────────────────────────────────────────────


class TestActiveSpeakerTracker:
    def test_tracker_creation(self):
        tracker = ActiveSpeakerTracker()
        assert tracker.confidence_threshold == 0.6
        assert tracker.min_speaker_duration == 0.5
        assert tracker.min_diarization_confidence == 0.5

    def test_tracker_custom_threshold(self):
        tracker = ActiveSpeakerTracker(confidence_threshold=0.8)
        assert tracker.confidence_threshold == 0.8

    def test_tracker_to_dict(self):
        tracker = ActiveSpeakerTracker()
        d = tracker.to_dict()
        assert "segments" in d
        assert "confidence_threshold" in d
        assert "diarizer" in d
        assert d["segments"] == []  # No identification yet

    def test_get_labeled_segments_empty(self):
        tracker = ActiveSpeakerTracker()
        assert tracker.get_labeled_segments() == []
