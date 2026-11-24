# Automatic captions

The editor toolbar has an **Auto captions** button. It copies the imported video to the local Python service, transcribes it with faster-whisper in 60 second windows, and replaces the project with an editable caption draft.

## Use
1. `uv sync --extra dev --extra asr`, FFmpeg on PATH, then start the editor.
2. Import the video, click Auto captions, choose a model, Generate captions.
3. Review words, timing and speakers. Save the project JSON.

CLI alternative: `uv run python scripts/make_project.py video.mp4 --output video.cwi.json --asr-model base.en`, then open the JSON and import the video.

## Models
`base.en` is faster (about 150 MB download). `small.en` gives better words (about 500 MB). The first run downloads the model once and needs internet. English only.

## Limits
- Speakers are not separated. Captions stay unassigned and flagged for review; assign speakers by hand.
- No sound-effect or music cues are generated.
- Words and timing on old or noisy audio can be wrong. It is a draft.
- One job at a time. Progress is per 60 second window. Cancel takes effect between windows.
- Measured: a 45 second clip with base.en and a cached model took about 5 s (22 captions) on a 2 core Linux machine. Not measured on a long video, Windows, Arch or a weak PC.
- Errors for missing FFmpeg, missing speech add-on and model download failure are coded; the download failure path was not exercised.
