"""Non-destructive caption split/merge. Absolute word timings stay fixed."""

from __future__ import annotations

import copy
import math
from itertools import pairwise


def edit_structure(data: dict, ids: list[str], operation: str, at: float = 0) -> dict:
    result = copy.deepcopy(data)
    selected = sorted(
        [e for e in result["events"] if e["id"] in set(ids)],
        key=lambda e: (e["start"], e["end"]),
    )
    if not selected or len(selected) != len(set(ids)):
        raise ValueError("Select existing captions.")
    if operation == "split":
        if len(selected) != 1 or not math.isfinite(at):
            raise ValueError("Select one caption and place the playhead between words.")
        event = selected[0]
        if not event["start"] < at < event["end"] or len(event["words"]) < 2:
            raise ValueError(
                "Split needs a playhead inside a caption with at least two timed words."
            )
        if any(w["start"] < at < w["end"] for w in event["words"]):
            raise ValueError(
                "Place the playhead between words, not inside a spoken word."
            )
        left = [w for w in event["words"] if w["end"] <= at]
        right = [w for w in event["words"] if w["start"] >= at]
        if not left or not right or len(left) + len(right) != len(event["words"]):
            raise ValueError("Split needs timed words on both sides of the playhead.")
        used = {e["id"] for e in result["events"]}
        n = 1
        while f"{event['id']}_split_{n}" in used:
            n += 1
        # Keep punctuation/spacing that lives in event text, not word tokens.
        left_text = " ".join(w["text"] for w in left)
        right_text = " ".join(w["text"] for w in right)
        cursor = 0
        starts = []
        for word in event["words"]:
            index = event["text"].find(word["text"], cursor)
            if index < 0:
                break
            starts.append(index)
            cursor = index + len(word["text"])
        if len(starts) == len(event["words"]):
            boundary = starts[len(left)]
            left_text = event["text"][:boundary].rstrip()
            right_text = event["text"][boundary:].lstrip()
        second = copy.deepcopy(event)
        second.update(
            id=f"{event['id']}_split_{n}",
            start=at,
            words=right,
            text=right_text,
            manual_override=True,
        )
        event.update(
            end=at,
            words=left,
            text=left_text,
            manual_override=True,
        )
        result["events"].insert(result["events"].index(event) + 1, second)
    elif operation == "merge":
        if len(selected) < 2:
            raise ValueError("Select at least two captions to merge.")
        first = selected[0]
        if any(
            (
                e["speaker_id"],
                e["type"],
                e["style"],
                e.get("off_camera"),
                e.get("exception_profile"),
            )
            != (
                first["speaker_id"],
                first["type"],
                first["style"],
                first.get("off_camera"),
                first.get("exception_profile"),
            )
            for e in selected
        ):
            raise ValueError(
                "Merge needs the same speaker, type, style and off-camera settings."
            )
        if any(b["start"] < a["end"] for a, b in pairwise(selected)):
            raise ValueError(
                "Overlapping captions cannot be merged. Their simultaneous timing is preserved."
            )
        if any(not e["words"] for e in selected):
            raise ValueError("Merge needs timed words in every selected caption.")
        notes = "\n\n".join(e.get("notes", "") for e in selected if e.get("notes"))
        reviewed = all(e.get("speaker_reviewed", False) for e in selected)
        reasons = list(
            dict.fromkeys(
                r for e in selected for r in e.get("speaker_review_reasons", [])
            )
        )
        first.update(
            notes=notes,
            speaker_reviewed=reviewed,
            speaker_review_reasons=reasons,
            speaker_review_required=any(
                e.get("speaker_review_required", False) for e in selected
            ),
            end=selected[-1]["end"],
            text=" ".join(e["text"] for e in selected),
            words=[w for e in selected for w in e["words"]],
            manual_override=True,
        )
        removed = {e["id"] for e in selected[1:]}
        result["events"] = [e for e in result["events"] if e["id"] not in removed]
    else:
        raise ValueError("Unknown caption structure operation.")
    return result
