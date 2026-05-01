from __future__ import annotations

from typing import Any, Dict


def _ensure_double_buffered(canvas_state: Dict[str, Any]) -> None:
    """In-place migration: wrap legacy flat canvas state into {"active": ..., "staged": {}}."""
    if "active" not in canvas_state:
        flat = dict(canvas_state)
        canvas_state.clear()
        canvas_state["active"] = flat
        canvas_state["staged"] = {}


def apply_op(canvas_state: Dict[str, Any], op: dict) -> None:
    """Mutate canvas_state in-place by applying a single canvas operation."""
    _ensure_double_buffered(canvas_state)

    op_type = op.get("op")
    comp_id = op.get("id")

    if op_type == "clear_staged":
        canvas_state["staged"].clear()
        return

    if not comp_id:
        return

    active = canvas_state["active"]
    staged = canvas_state["staged"]

    if op_type == "add":
        existing = active.get(comp_id)
        if existing:
            existing["data"] = {**(existing.get("data") or {}), **(op.get("data") or {})}
            existing["skeleton"] = False
        else:
            active[comp_id] = {
                "type": op.get("type"),
                "data": op.get("data"),
                "focused": False,
                "position": op.get("position"),
                "parent": op.get("parent"),
            }

    elif op_type == "stage":
        staged[comp_id] = {
            "type": op.get("type"),
            "data": op.get("data"),
            "focused": False,
            "position": op.get("position"),
            "parent": op.get("parent"),
        }

    elif op_type == "commit":
        comp = staged.pop(comp_id, None)
        if comp is not None:
            active[comp_id] = comp

    elif op_type == "swap":
        out_id = op.get("out_id")
        comp = staged.pop(comp_id, None)
        if comp is not None:
            active.pop(out_id, None)
            active[comp_id] = comp

    elif op_type == "update":
        if comp_id in active:
            active[comp_id]["data"] = op.get("data")
        elif comp_id in staged:
            staged[comp_id]["data"] = op.get("data")

    elif op_type == "remove":
        active.pop(comp_id, None)
        staged.pop(comp_id, None)

    elif op_type == "focus":
        for cid, comp in active.items():
            comp["focused"] = cid == comp_id

    elif op_type == "move":
        existing = active.get(comp_id)
        if existing:
            existing["position"] = op.get("position")
