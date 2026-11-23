"""Pure caption batch edits, validated by the Editor before one undo commit."""

from __future__ import annotations

import copy
import math


def edit_batch(
    data: dict, ids: list[str], operation: str, delta: float = 0, ripple: bool = False
) -> dict:
    result = copy.deepcopy(data)
    selected = [e for e in result["events"] if e["id"] in set(ids)]
    if not selected or len({e["id"] for e in selected}) != len(set(ids)):
        raise ValueError("Select existing caption events.")
    if operation not in {"move", "delete"} or not math.isfinite(delta):
        raise ValueError("Choose a valid batch operation and finite shift.")
    if operation == "move":
        boundary = max(e["end"] for e in selected)
        targets = [
            e
            for e in result["events"]
            if e in selected or (ripple and e["start"] >= boundary)
        ]
        if min(e["start"] for e in targets) + delta < 0:
            raise ValueError("This shift would move a caption before zero.")
        for event in targets:
            shift_event(event, delta)
    else:
        intervals = []
        for event in sorted(selected, key=lambda e: e["start"]):
            if intervals and event["start"] <= intervals[-1][1]:
                intervals[-1][1] = max(intervals[-1][1], event["end"])
            else:
                intervals.append([event["start"], event["end"]])
        result["events"] = [e for e in result["events"] if e["id"] not in set(ids)]
        if ripple:
            for event in result["events"]:
                # Preserve captions crossing removed ranges; only fully later
                # material moves, by the union of deleted occupied time.
                shift = sum(
                    end - start for start, end in intervals if end <= event["start"]
                )
                shift_event(event, -shift)
    return result


def shift_event(event: dict, delta: float):
    event["start"] += delta
    event["end"] += delta
    for word in event["words"]:
        word["start"] += delta
        word["end"] += delta
        for syllable in word.get("syllables") or []:
            syllable["start"] += delta
            syllable["end"] += delta
