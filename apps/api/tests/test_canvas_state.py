from __future__ import annotations

import pytest
from canvas_state import apply_op, _ensure_double_buffered


def _fresh() -> dict:
    return {"active": {}, "staged": {}}


def _with_active(**comps) -> dict:
    return {"active": dict(comps), "staged": {}}


def _with_staged(**comps) -> dict:
    return {"active": {}, "staged": dict(comps)}


# ─── Migration ────────────────────────────────────────────────────────────────

def test_legacy_flat_state_migrated():
    state = {"comp-1": {"type": "timer", "data": {}}}
    _ensure_double_buffered(state)
    assert "active" in state
    assert "staged" in state
    assert state["active"] == {"comp-1": {"type": "timer", "data": {}}}
    assert state["staged"] == {}


def test_already_double_buffered_unchanged():
    state = {"active": {"x": {}}, "staged": {}}
    _ensure_double_buffered(state)
    assert state == {"active": {"x": {}}, "staged": {}}


def test_apply_op_migrates_legacy_state():
    state = {"comp-1": {"type": "timer"}}
    apply_op(state, {"op": "remove", "id": "comp-1"})
    assert "active" in state
    assert "comp-1" not in state["active"]


# ─── add ──────────────────────────────────────────────────────────────────────

def test_add_creates_in_active():
    state = _fresh()
    apply_op(state, {"op": "add", "id": "s1", "type": "step-view", "data": {"step_number": 1}})
    assert "s1" in state["active"]
    assert state["active"]["s1"]["type"] == "step-view"


def test_add_upserts_existing():
    state = _with_active(s1={"type": "step-view", "data": {"a": 1}, "skeleton": True})
    apply_op(state, {"op": "add", "id": "s1", "type": "step-view", "data": {"b": 2}})
    assert state["active"]["s1"]["skeleton"] is False
    assert state["active"]["s1"]["data"]["b"] == 2


# ─── stage ────────────────────────────────────────────────────────────────────

def test_stage_adds_to_staged_not_active():
    state = _fresh()
    apply_op(state, {"op": "stage", "id": "s2", "type": "step-view", "data": {"step_number": 2}})
    assert "s2" in state["staged"]
    assert "s2" not in state["active"]
    assert state["staged"]["s2"]["type"] == "step-view"


# ─── commit ───────────────────────────────────────────────────────────────────

def test_commit_moves_staged_to_active():
    comp = {"type": "step-view", "data": {}, "focused": False}
    state = _with_staged(s2=comp)
    apply_op(state, {"op": "commit", "id": "s2"})
    assert "s2" in state["active"]
    assert "s2" not in state["staged"]


def test_commit_noop_if_not_staged():
    state = _fresh()
    apply_op(state, {"op": "commit", "id": "nonexistent"})
    assert state == _fresh()


# ─── swap ─────────────────────────────────────────────────────────────────────

def test_swap_removes_out_and_commits_in():
    comp_old = {"type": "step-view", "data": {"step_number": 1}, "focused": False}
    comp_new = {"type": "step-view", "data": {"step_number": 2}, "focused": False}
    state = {"active": {"s1": comp_old}, "staged": {"s2": comp_new}}
    apply_op(state, {"op": "swap", "id": "s2", "out_id": "s1"})
    assert "s2" in state["active"]
    assert "s1" not in state["active"]
    assert "s2" not in state["staged"]


def test_swap_noop_if_in_id_not_staged():
    state = _with_active(s1={"type": "step-view", "data": {}})
    apply_op(state, {"op": "swap", "id": "s2", "out_id": "s1"})
    assert "s1" in state["active"]  # not removed


# ─── clear_staged ─────────────────────────────────────────────────────────────

def test_clear_staged_wipes_all_staged():
    state = _with_staged(a={"type": "timer"}, b={"type": "alert"})
    apply_op(state, {"op": "clear_staged"})
    assert state["staged"] == {}
    assert state["active"] == {}


# ─── update (total replacement) ───────────────────────────────────────────────

def test_update_replaces_data_in_active():
    state = _with_active(s1={"type": "step-view", "data": {"a": 1, "b": 2}})
    apply_op(state, {"op": "update", "id": "s1", "data": {"a": 99}})
    assert state["active"]["s1"]["data"] == {"a": 99}  # b is gone


def test_update_replaces_data_in_staged():
    state = _with_staged(s1={"type": "step-view", "data": {"a": 1}})
    apply_op(state, {"op": "update", "id": "s1", "data": {"z": 7}})
    assert state["staged"]["s1"]["data"] == {"z": 7}


def test_update_noop_for_unknown_id():
    state = _fresh()
    apply_op(state, {"op": "update", "id": "ghost", "data": {"x": 1}})
    assert state == _fresh()


# ─── remove ───────────────────────────────────────────────────────────────────

def test_remove_from_active():
    state = _with_active(s1={"type": "step-view"})
    apply_op(state, {"op": "remove", "id": "s1"})
    assert "s1" not in state["active"]


def test_remove_from_staged():
    state = _with_staged(s1={"type": "step-view"})
    apply_op(state, {"op": "remove", "id": "s1"})
    assert "s1" not in state["staged"]


def test_remove_noop_for_unknown_id():
    state = _fresh()
    apply_op(state, {"op": "remove", "id": "ghost"})
    assert state == _fresh()


# ─── focus ────────────────────────────────────────────────────────────────────

def test_focus_sets_focused_and_clears_others():
    state = _with_active(
        a={"type": "step-view", "focused": True},
        b={"type": "progress-bar", "focused": False},
    )
    apply_op(state, {"op": "focus", "id": "b"})
    assert state["active"]["a"]["focused"] is False
    assert state["active"]["b"]["focused"] is True


# ─── move ─────────────────────────────────────────────────────────────────────

def test_move_updates_position_in_active():
    state = _with_active(t1={"type": "timer", "position": "corner-br"})
    apply_op(state, {"op": "move", "id": "t1", "position": "top"})
    assert state["active"]["t1"]["position"] == "top"
