"""Active speaker tracking — diarization PRIMARY, face tracking FALLBACK.

Speaker identification priority:
1. Audio diarization (PRIMARY) — speech comes from humans, audio-based identification
2. Face/video tracking (FALLBACK) — only when diarization confidence is low
3. Any avatar model (cartoon faces, dinosaurs, custom avatars) — not limited to real faces
"""
