import subprocess
from unittest.mock import patch

import pytest

from engine.core.ffmpeg import run_ffmpeg


def test_ffmpeg_error_preserves_actionable_trailing_diagnostic():
    output = subprocess.CompletedProcess(
        ["ffmpeg"], 1, "", "build configuration " * 200 + "\nEncoder failed: width not divisible by 2"
    )
    with patch("engine.core.ffmpeg.subprocess.run", return_value=output), pytest.raises(RuntimeError) as error:
        run_ffmpeg(["ffmpeg"])
    assert "width not divisible by 2" in str(error.value)
    assert len(str(error.value)) < 1600
