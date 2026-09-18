"""M0 verification script — run to confirm all M0 features work."""

from __future__ import annotations

import sys
import json
import tempfile
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.project.engine import ProjectEngine
from engine.rules.colors import (
    MAIN_COLORS,
    SUPPORTING_COLORS,
    generate_minor_palette,
    color_distance_hex,
)
from engine.typography.mapping import (
    volume_to_size,
    pitch_to_weight,
    harmonics_to_width,
)
from engine.errors.errors import CWIError, ErrorCategory, ProjectCorruptionError, LowConfidenceError
from engine.logging.logger import setup_logging
from schemas.project import Project, Speaker, CaptionEvent, EventType, VideoInfo


def test_01_logging():
    """Test structured logging works."""
    print("✓ Testing logging...")
    logger = setup_logging(log_dir=tempfile.mkdtemp())
    logger.info("Logging test message")
    print("  Logging OK")


def test_02_project_create():
    """Test project creation."""
    print("✓ Testing project create...")
    engine = ProjectEngine()
    with tempfile.TemporaryDirectory() as tmp:
        project = engine.create("Test Project", project_dir=tmp)
        assert project.project_name == "Test Project"
        assert (Path(tmp) / "Test_Project.ci").exists()
    print("  Project create OK")


def test_03_project_open_save():
    """Test project open/save round-trip."""
    print("✓ Testing project open/save...")
    engine = ProjectEngine()
    with tempfile.TemporaryDirectory() as tmp:
        project = engine.create("RoundTrip", project_dir=tmp)
        engine2 = ProjectEngine()
        loaded = engine2.open(engine.project_path)
        assert loaded.project_name == "RoundTrip"
    print("  Project open/save OK")


def test_04_color_palette():
    """Test color palette assignments."""
    print("✓ Testing color palette...")
    assert len(MAIN_COLORS) == 6
    assert len(SUPPORTING_COLORS) == 12

    # Verify main colors are distinct
    distances = []
    colors = list(MAIN_COLORS.values())
    for i, c1 in enumerate(colors):
        for c2 in colors[i + 1:]:
            distances.append(color_distance_hex(c1, c2))
    assert min(distances) > 20, "Main colors too close"

    # Minor palette
    minor = generate_minor_palette(24)
    assert len(minor) == 24
    assert len(set(minor)) == 24
    print("  Color palette OK")


def test_05_typography_mapping():
    """Test typography mapping."""
    print("✓ Testing typography mapping...")
    # Volume → size
    assert volume_to_size(0.0) == 3.0
    assert volume_to_size(1.0) == 12.0

    # Pitch → weight
    assert pitch_to_weight(180) == 400
    assert pitch_to_weight(100) > 400
    assert pitch_to_weight(300) < 400

    # Harmonics → width
    assert harmonics_to_width(1.0, 0.0) > 100
    assert harmonics_to_width(0.0, 1.0) < 100
    print("  Typography mapping OK")


def test_06_error_classification():
    """Test error hierarchy."""
    print("✓ Testing error classification...")
    err = CWIError("test", category=ErrorCategory.recoverable)
    assert err.recoverable

    fatal = ProjectCorruptionError("test")
    assert not fatal.recoverable

    low_conf = LowConfidenceError("stage", 0.3, 0.5)
    assert low_conf.category == ErrorCategory.low_ai_confidence
    print("  Error classification OK")


def test_07_schema_validation():
    """Test project schema."""
    print("✓ Testing schema...")
    project = Project(project_name="SchemaTest")
    assert project.schema_version == "ci-project-1"

    spk = Speaker(id="spk_1", name="Test", category="main")
    event = CaptionEvent(
        id="evt_1", type=EventType.dialogue, start=0.0, end=1.0, text="Hi"
    )
    project.speakers.append(spk)
    project.events.append(event)
    data = project.model_dump()
    assert len(data["speakers"]) == 1
    assert len(data["events"]) == 1
    print("  Schema OK")


def test_08_design_system_profiles():
    """Test that all design system profiles load."""
    print("✓ Testing design system profiles...")
    from engine.rules.profile_loader import (
        load_profile,
        get_main_colors,
        get_supporting_colors,
        get_typography_profile,
        get_sync_profile,
        get_elements_profile,
    )

    for name in [
        "profile",
        "colors",
        "typography",
        "synchronization",
        "elements",
        "exceptions",
        "exports",
        "music",
        "sound_effects",
    ]:
        data = load_profile(name)
        assert isinstance(data, dict), f"Profile {name} not a dict"

    assert len(get_main_colors()) == 6
    assert len(get_supporting_colors()) == 12
    print("  Design system profiles OK")


def main():
    print("\n" + "=" * 60)
    print("  Caption With Intention — M0 Verification")
    print("=" * 60 + "\n")

    tests = [
        test_01_logging,
        test_02_project_create,
        test_03_project_open_save,
        test_04_color_palette,
        test_05_typography_mapping,
        test_06_error_classification,
        test_07_schema_validation,
        test_08_design_system_profiles,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 60 + "\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
