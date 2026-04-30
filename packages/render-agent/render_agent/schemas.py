from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, model_validator

VALID_TYPES = {
    "step-view", "progress-bar", "timer", "alert",
    "recipe-grid", "recipe-option", "ingredient-list",
    "camera", "suggestion", "text-card",
}

VALID_ZONES = {
    "center", "top", "bottom", "left", "right",
    "corner-tl", "corner-tr", "corner-bl", "corner-br",
}

REQUIRED_DATA_KEYS: Dict[str, List[str]] = {
    "step-view": ["step_number", "total_steps", "recipe", "instruction"],
    "progress-bar": ["current", "total"],
    "timer": ["duration_seconds", "label", "auto_start"],
    "alert": ["text"],
    "recipe-grid": [],
    "recipe-option": ["title", "action"],
    "ingredient-list": ["items"],
    "camera": ["prompt"],
    "suggestion": ["heading", "body"],
    "text-card": ["body"],
}


class CanvasOp(BaseModel):
    op: Literal["add", "update", "remove", "focus", "move"]
    id: str
    type: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    position: Optional[str] = None
    parent: Optional[str] = None

    @model_validator(mode="after")
    def validate_op_fields(self) -> "CanvasOp":
        if self.op == "add":
            if not self.type:
                raise ValueError("type is required for op=add")
            if self.type not in VALID_TYPES:
                raise ValueError(f"unknown type '{self.type}', must be one of {sorted(VALID_TYPES)}")
            if self.data is None:
                raise ValueError("data is required for op=add")
            required = REQUIRED_DATA_KEYS.get(self.type, [])
            missing = [k for k in required if k not in self.data]
            if missing:
                raise ValueError(f"op=add type={self.type} missing required data keys: {missing}")
        if self.op == "move":
            if not self.position:
                raise ValueError("position is required for op=move")
            if self.position not in VALID_ZONES:
                raise ValueError(
                    f"invalid position '{self.position}', must be one of {sorted(VALID_ZONES)}"
                )
        return self
