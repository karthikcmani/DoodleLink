"""Protocol v1 event validation and payload builders."""

from __future__ import annotations

import time
from typing import Any

from doodlelink.models.stroke import Point, Stroke

PROTOCOL_VERSION = 1

VALID_TYPES = {
    "hello",
    "pair",
    "pair_success",
    "stroke_start",
    "stroke_points",
    "stroke_end",
    "stroke_cancel",
    "undo",
    "redo",
    "clear_canvas",
    "page_info",
    "page_switch",
    "ping",
    "pong",
    "error",
}


def validate_message(data: Any) -> tuple[bool, str | None]:
    """Validate that incoming JSON object conforms to Protocol v1.

    Returns (is_valid, error_reason).
    """
    if not isinstance(data, dict):
        return False, "Payload must be a JSON object"

    if data.get("version") != PROTOCOL_VERSION:
        return False, f"Unsupported protocol version: {data.get('version')}"

    msg_type = data.get("type")
    if not msg_type or msg_type not in VALID_TYPES:
        return False, f"Invalid or missing message type: {msg_type}"

    if msg_type == "pair":
        has_code = isinstance(data.get("code"), str) and bool(data["code"].strip())
        has_session = isinstance(data.get("session_id"), str) and bool(data["session_id"].strip())
        if not has_code and not has_session:
            return False, "Pair message requires either string 'code' or 'session_id'"

    elif msg_type == "stroke_start":
        if not data.get("stroke_id"):
            return False, "stroke_start requires 'stroke_id'"
        width = data.get("width")
        if width is None or not (0.0001 <= float(width) <= 0.5):
            return False, f"Invalid stroke width: {width}"
        points = data.get("points")
        if points is not None and not isinstance(points, list):
            return False, "points must be an array"

    elif msg_type == "stroke_points":
        if not data.get("stroke_id"):
            return False, "stroke_points requires 'stroke_id'"
        pts = data.get("points")
        if not isinstance(pts, list) or len(pts) == 0:
            return False, "stroke_points requires non-empty 'points' list"
        for p in pts:
            if not isinstance(p, dict) or "x" not in p or "y" not in p:
                return False, "Each point must contain 'x' and 'y'"

    elif msg_type in ("stroke_end", "stroke_cancel"):
        if not data.get("stroke_id"):
            return False, f"{msg_type} requires 'stroke_id'"

    elif msg_type == "page_switch":
        direction = data.get("direction")
        if direction not in ("next", "prev", "goto", "add"):
            return False, f"Invalid page_switch direction: {direction}"

    elif msg_type == "page_info":
        if not data.get("page_id"):
            return False, "page_info requires 'page_id'"

    return True, None


def build_pair_success(session_id: str, message: str = "Pairing successful") -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "pair_success",
        "session_id": session_id,
        "message": message,
    }


def build_error(code: str, message: str) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "error",
        "code": code,
        "message": message,
    }


def build_stroke_start(
    stroke: Stroke,
    sequence: int,
    session_id: str,
) -> dict[str, Any]:
    pts = [p.to_dict() for p in stroke.points]
    return {
        "version": PROTOCOL_VERSION,
        "type": "stroke_start",
        "session_id": session_id,
        "stroke_id": stroke.id,
        "sequence": sequence,
        "tool": stroke.tool.value,
        "color": stroke.color,
        "width": round(stroke.width, 6),
        "points": pts,
    }


def build_stroke_points(
    stroke_id: str,
    points: list[Point],
    sequence: int,
    session_id: str,
) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "stroke_points",
        "session_id": session_id,
        "stroke_id": stroke_id,
        "sequence": sequence,
        "points": [p.to_dict() for p in points],
    }


def build_stroke_end(stroke_id: str, sequence: int, session_id: str) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "stroke_end",
        "session_id": session_id,
        "stroke_id": stroke_id,
        "sequence": sequence,
    }


def build_stroke_cancel(stroke_id: str, sequence: int, session_id: str) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "stroke_cancel",
        "session_id": session_id,
        "stroke_id": stroke_id,
        "sequence": sequence,
    }


def build_undo(sequence: int, session_id: str) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "undo",
        "session_id": session_id,
        "sequence": sequence,
    }


def build_redo(sequence: int, session_id: str) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "redo",
        "session_id": session_id,
        "sequence": sequence,
    }


def build_clear_canvas(sequence: int, session_id: str) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "clear_canvas",
        "session_id": session_id,
        "sequence": sequence,
    }


def build_ping() -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "ping",
        "timestamp": round(time.time() * 1000, 2),
    }


def build_pong() -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "pong",
        "timestamp": round(time.time() * 1000, 2),
    }


def build_page_info(
    board_id: str,
    page_id: str,
    page_number: int,
    total_pages: int,
    strokes: list[Stroke],
    sequence: int,
    session_id: str,
) -> dict[str, Any]:
    serialized_strokes = []
    for s in strokes:
        serialized_strokes.append({
            "stroke_id": s.id,
            "tool": s.tool.value,
            "color": s.color,
            "width": round(s.width, 6),
            "points": [p.to_dict() for p in s.points],
        })
    return {
        "version": PROTOCOL_VERSION,
        "type": "page_info",
        "session_id": session_id,
        "sequence": sequence,
        "board_id": board_id,
        "page_id": page_id,
        "page_number": page_number,
        "total_pages": total_pages,
        "strokes": serialized_strokes,
    }


def build_page_switch(
    direction: str,
    page_id: str = "",
    sequence: int = 0,
    session_id: str = "",
) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": "page_switch",
        "session_id": session_id,
        "sequence": sequence,
        "direction": direction,
        "page_id": page_id,
    }

