"""Unit tests for Protocol v1 message validation and payload builders."""

from doodlelink.models.stroke import Point, Stroke, ToolType
from doodlelink.network.protocol import (
    PROTOCOL_VERSION,
    build_clear_canvas,
    build_error,
    build_pair_success,
    build_ping,
    build_pong,
    build_redo,
    build_stroke_cancel,
    build_stroke_end,
    build_stroke_points,
    build_stroke_start,
    build_undo,
    validate_message,
)


def test_validate_message_version_and_type():
    # Not a dict
    valid, err = validate_message("invalid")
    assert not valid
    assert "JSON object" in err

    # Unsupported version
    valid, err = validate_message({"version": 99, "type": "ping"})
    assert not valid
    assert "Unsupported protocol version" in err

    # Missing type
    valid, err = validate_message({"version": PROTOCOL_VERSION})
    assert not valid
    assert "type" in err

    # Unknown type
    valid, err = validate_message({"version": PROTOCOL_VERSION, "type": "unknown_action"})
    assert not valid


def test_validate_pair_message():
    # Missing code
    valid, err = validate_message({"version": PROTOCOL_VERSION, "type": "pair"})
    assert not valid
    assert "code" in err

    # Valid pair
    valid, err = validate_message({"version": PROTOCOL_VERSION, "type": "pair", "code": "123456"})
    assert valid
    assert err is None


def test_validate_stroke_messages():
    # stroke_start missing stroke_id
    valid, err = validate_message({"version": PROTOCOL_VERSION, "type": "stroke_start", "width": 0.005})
    assert not valid
    assert "stroke_id" in err

    # stroke_start invalid width
    valid, err = validate_message(
        {"version": PROTOCOL_VERSION, "type": "stroke_start", "stroke_id": "s1", "width": 0.9}
    )
    assert not valid
    assert "width" in err

    # Valid stroke_start
    valid, err = validate_message(
        {
            "version": PROTOCOL_VERSION,
            "type": "stroke_start",
            "stroke_id": "s1",
            "width": 0.005,
            "points": [{"x": 0.5, "y": 0.5}],
        }
    )
    assert valid

    # stroke_points invalid
    valid, err = validate_message(
        {"version": PROTOCOL_VERSION, "type": "stroke_points", "stroke_id": "s1", "points": []}
    )
    assert not valid


def test_builders():
    stroke = Stroke(tool=ToolType.PEN, color="#DC2626", width=0.004)
    stroke.add_point(0.1, 0.2)

    msg = build_stroke_start(stroke, sequence=1, session_id="sess-1")
    assert msg["type"] == "stroke_start"
    assert msg["stroke_id"] == stroke.id
    assert msg["sequence"] == 1
    assert len(msg["points"]) == 1

    pts_msg = build_stroke_points(stroke.id, [Point(0.3, 0.4)], sequence=2, session_id="sess-1")
    assert pts_msg["type"] == "stroke_points"
    assert len(pts_msg["points"]) == 1

    end_msg = build_stroke_end(stroke.id, sequence=3, session_id="sess-1")
    assert end_msg["type"] == "stroke_end"

    undo_msg = build_undo(sequence=4, session_id="sess-1")
    assert undo_msg["type"] == "undo"

    redo_msg = build_redo(sequence=5, session_id="sess-1")
    assert redo_msg["type"] == "redo"

    clear_msg = build_clear_canvas(sequence=6, session_id="sess-1")
    assert clear_msg["type"] == "clear_canvas"

    cancel_msg = build_stroke_cancel(stroke.id, sequence=7, session_id="sess-1")
    assert cancel_msg["type"] == "stroke_cancel"

    ping = build_ping()
    assert ping["type"] == "ping"

    pong = build_pong()
    assert pong["type"] == "pong"

    pair_ok = build_pair_success(session_id="sess-1")
    assert pair_ok["type"] == "pair_success"

    err = build_error("BAD_CODE", "Invalid pairing code")
    assert err["type"] == "error"
    assert err["code"] == "BAD_CODE"
