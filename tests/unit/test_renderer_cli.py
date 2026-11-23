from unittest.mock import patch

import pytest

from engine.renderer.__main__ import main
from schemas.project import Project


def inputs(tmp_path):
    project = tmp_path / "captions.cwi.json"
    project.write_text(Project().model_dump_json())
    source = tmp_path / "source.mp4"
    source.touch()
    return project, source, tmp_path / "output.mp4"


def test_cli_loads_canonical_project_and_calls_renderer(tmp_path):
    project, source, output = inputs(tmp_path)
    with patch("engine.renderer.__main__.CwiRenderer") as renderer:
        renderer.return_value.render.side_effect = lambda source, destination: destination.write_bytes(b"new video")
        assert main(list(map(str, [project, source, output]))) == 0
        assert renderer.return_value.render.call_args.args[0] == source
        assert output.read_bytes() == b"new video"


def test_cli_refuses_overwrite_and_source_replacement(tmp_path):
    project, source, output = inputs(tmp_path)
    output.touch()
    for destination in [source, output]:
        with patch("engine.renderer.__main__.CwiRenderer") as renderer, pytest.raises(SystemExit):
            main(list(map(str, [project, source, destination])))
        renderer.assert_not_called()


def test_cli_explicit_output_overwrite(tmp_path):
    project, source, output = inputs(tmp_path)
    output.touch()
    with patch("engine.renderer.__main__.CwiRenderer") as renderer:
        renderer.return_value.render.side_effect = lambda source, destination: destination.write_bytes(b"new video")
        assert main([*map(str, [project, source, output]), "--overwrite"]) == 0


def test_render_uses_private_staging_and_preserves_source_caption_file(tmp_path):
    from engine.renderer import CwiRenderer
    source = tmp_path / "source.mp4"
    source.touch()
    existing = tmp_path / "captions.cwi.ass"
    existing.write_text("existing caption file")
    with patch("engine.renderer.renderer.run_ffmpeg") as run:
        CwiRenderer(Project()).render(source, tmp_path / "output.mp4")
        command = run.call_args.args[0]
        staged = command[command.index("-vf") + 1]
        assert "cwi-render-" in staged
        assert str(existing) not in staged
    assert existing.read_text() == "existing caption file"


def test_cli_failed_render_preserves_old_output(tmp_path):
    project, source, output = inputs(tmp_path)
    output.write_bytes(b"old video")
    with patch("engine.renderer.__main__.CwiRenderer") as renderer:
        renderer.return_value.render.side_effect = RuntimeError("encoding failed")
        with pytest.raises(SystemExit):
            main([*map(str, [project, source, output]), "--overwrite"])
    assert output.read_bytes() == b"old video"
    assert not list(tmp_path.glob(".cwi-output-*"))


def test_mp4_command_explicit_browser_codecs_and_muted_option(tmp_path):
    from engine.renderer import CwiRenderer
    command=CwiRenderer(Project(),audio_codec='aac')._build_ffmpeg_command(tmp_path/'source.mov',tmp_path/'captions.ass',tmp_path/'result.mp4')
    assert command[command.index('-c:a')+1]=='aac'
    assert command[command.index('-pix_fmt')+1]=='yuv420p'
    assert command[command.index('-c:v')+1]=='libx264'
    assert '+faststart' in command
    muted=CwiRenderer(Project(),preserve_audio=False)._build_ffmpeg_command(tmp_path/'s',tmp_path/'a',tmp_path/'o.mp4')
    assert '-an' in muted


def test_renderer_uses_rotated_display_dimensions():
    from pathlib import Path

    from engine.renderer.renderer import _probe_dimensions
    with patch('engine.media.probe.probe_video',return_value={'width':1280,'height':720,'display_width':720,'display_height':1280}):
        assert _probe_dimensions(Path('rotated.mp4'))==(720,1280)


def test_browser_mp4_pads_odd_dimensions_without_resizing_source(tmp_path):
    from engine.renderer import CwiRenderer

    command = CwiRenderer(Project(), audio_codec="aac")._build_ffmpeg_command(
        tmp_path / "source.mkv", tmp_path / "captions.ass", tmp_path / "result.mp4"
    )
    filters = command[command.index("-vf") + 1]
    assert filters.endswith("pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0")


def test_real_odd_dimension_source_exports_browser_mp4(tmp_path):
    import json
    import shutil
    import subprocess

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg tools are required for the real encode check")
    project, _, output = inputs(tmp_path)
    source = tmp_path / "odd.mkv"
    subprocess.run([
        "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=322x180:d=0.2",
        "-vf", "crop=321:179:exact=1", "-c:v", "ffv1", "-y", str(source),
    ], check=True, capture_output=True, timeout=15)
    assert main([str(project), str(source), str(output)]) == 0
    probe = subprocess.run([
        "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(output),
    ], check=True, capture_output=True, text=True, timeout=15)
    video = next(stream for stream in json.loads(probe.stdout)["streams"] if stream["codec_type"] == "video")
    assert (video["width"], video["height"], video["pix_fmt"], video["codec_name"]) == (322, 180, "yuv420p", "h264")
