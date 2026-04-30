from __future__ import annotations

from typing import Any, Dict


def apply_op(canvas_state: Dict[str, Any], op: dict) -> None:
    """Mutate canvas_state in-place by applying a single canvas operation."""
    op_type = op.get("op")
    comp_id = op.get("id")
    if not comp_id:
        return

    if op_type == "add":
        existing = canvas_state.get(comp_id)
        if existing:
            existing["data"] = {**(existing.get("data") or {}), **(op.get("data") or {})}
            existing["skeleton"] = False
        else:
            canvas_state[comp_id] = {
                "type": op.get("type"),
                "data": op.get("data"),
                "focused": False,
                "position": op.get("position"),
                "parent": op.get("parent"),
            }

    elif op_type == "update":
        existing = canvas_state.get(comp_id)
        if existing:
            existing["data"] = {**(existing.get("data") or {}), **(op.get("data") or {})}

    elif op_type == "remove":
        canvas_state.pop(comp_id, None)

    elif op_type == "focus":
        for cid, comp in canvas_state.items():
            comp["focused"] = cid == comp_id

    elif op_type == "move":
        existing = canvas_state.get(comp_id)
        if existing:
            existing["position"] = op.get("position")
