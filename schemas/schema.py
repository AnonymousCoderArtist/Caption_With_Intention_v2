"""Canonical project model — v1.0 schema definition."""

from __future__ import annotations

SCHEMA_VERSION = "ci-project-1"
DESIGN_SYSTEM = "caption-with-intention-v1.0"

PROJECT_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "CWIProject",
    "type": "object",
    "required": ["schema_version", "design_system", "video", "speakers", "events"],
    "properties": {
        "schema_version": {"type": "string", "const": SCHEMA_VERSION},
        "design_system": {"type": "string", "const": DESIGN_SYSTEM},
        "project_name": {"type": "string"},
        "video": {"$ref": "#/definitions/videoInfo"},
        "speakers": {"type": "array", "items": {"$ref": "#/definitions/speaker"}},
        "events": {"type": "array", "items": {"$ref": "#/definitions/captionEvent"}},
        "scenes": {"type": "array", "items": {"type": "object"}},
        "created_at": {"type": "string", "format": "date-time"},
        "modified_at": {"type": "string", "format": "date-time"},
        "profile_version": {"type": "string"},
        "notes": {"type": "string"},
    },
    "definitions": {
        "videoInfo": {
            "type": "object",
            "properties": {
                "width": {"type": "integer"},
                "height": {"type": "integer"},
                "fps": {"type": "number"},
                "duration": {"type": "number"},
                "source_hash": {"type": "string"},
            },
        },
        "speaker": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "category": {"type": "string", "enum": ["main", "supporting", "minor"]},
                "role": {"type": "string"},
                "color": {"type": "string"},
                "confidence": {"type": "number"},
                "off_camera": {"type": "boolean"},
            },
        },
        "captionEvent": {
            "type": "object",
            "required": ["id", "type", "start", "end"],
            "properties": {
                "id": {"type": "string"},
                "type": {"type": "string", "enum": ["dialogue", "sound_effect", "music", "speaker_overlap", "custom"]},
                "start": {"type": "number"},
                "end": {"type": "number"},
                "speaker_id": {"type": "string"},
                "off_camera": {"type": "boolean"},
                "text": {"type": "string"},
                "words": {"type": "array"},
            },
        },
    },
}
