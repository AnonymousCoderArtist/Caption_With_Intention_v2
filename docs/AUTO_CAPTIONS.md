# Automatic captions

The editor toolbar has an **Auto captions** button. Two engines turn the speech in the imported video into an editable caption draft:

- **Browser speech (default).** The Web Speech API recognizes the video's audio track while it plays locally at 1x speed (`SpeechRecognition.start(audioTrack)`; Chrome/Edge 135+, Firefox 160+, not Safari). Nothing to install. On-device mode (the default checkbox) downloads a small language pack once and then works offline; with the checkbox off, audio goes to the browser vendor's speech service and needs internet.
- **Speech models.** The video is copied to the local Python service and transcribed with faster-whisper in 60 second windows. More accurate word timing, but needs FFmpeg, the `asr` add-on and a one-time model download.

Where the browser cannot do browser speech (Safari, old Chrome), the panel selects a speech model instead and the browser option is disabled.

## Use
1. Import the video, click Auto captions, keep the Browser speech engine, Generate captions.
2. For the speech models instead: `uv sync --extra dev --extra asr`, FFmpeg on PATH, restart the editor, then pick a model in the Engine list.
3. Review words, timing and speakers. Save the project JSON.

CLI alternative: `uv run python scripts/make_project.py video.mp4 --output video.cwi.json --asr-model base.en`, then open the JSON and import the video.

## Models
`base.en` is faster (about 150 MB download). `small.en` gives better words (about 500 MB). The first run downloads the model once and needs internet. English only.

## Limits
- Speakers are not separated. Captions stay unassigned and flagged for review; assign speakers by hand.
- No sound-effect or music cues are generated.
- Words and timing on old or noisy audio can be wrong. It is a draft.
- Browser speech runs in real time (a 10 minute video takes 10 minutes) and returns phrase-level results only: word timings are spread evenly inside each phrase, so per-word styling and timing need extra review. The measured fps comes from `requestVideoFrameCallback` during playback (30 fps assumed when unavailable).
- Browser speech events carry provenance `source_model: web-speech-api` and the browser's per-phrase confidence when it provides one.
- Speech models: one job at a time. Progress is per 60 second window. Cancel takes effect between windows.
- Measured: a 45 second clip with base.en and a cached model took about 5 s (22 captions) on a 2 core Linux machine. Not measured on a long video, Windows, Arch or a weak PC.
- Errors for missing FFmpeg, missing speech add-on and model download failure are coded; the download failure path was not exercised.
- Browser speech was verified end to end up to recognition start in headless Chromium 159 (UI, default engine, fallback, playback hand-off, `/api/captions/build`); the recognition itself crashes headless Chromium (no speech service backend), so real recognition quality is unverified and needs a real Chrome, Edge or Firefox 160+.
