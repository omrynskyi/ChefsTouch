from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from langchain_core.documents import Document
from pydantic import BaseModel, model_validator

VALID_ZONES = {"center", "top", "bottom", "left", "right", "corner-tl", "corner-tr", "corner-bl", "corner-br"}


class CanvasOp(BaseModel):
    op: Literal["add", "update", "remove", "focus", "move"]
    id: str
    html: Optional[str] = None   # required for add, update
    zone: Optional[str] = None   # required for move

    @model_validator(mode="after")
    def validate_op_fields(self) -> "CanvasOp":
        if self.op in ("add", "update") and not self.html:
            raise ValueError(f"html is required for op={self.op}")
        if self.op == "move":
            if not self.zone:
                raise ValueError("zone is required for op=move")
            if self.zone not in VALID_ZONES:
                raise ValueError(f"invalid zone '{self.zone}', must be one of {VALID_ZONES}")
        return self


class CanvasComponent(BaseModel):
    id: str
    html: Optional[str] = None
    zone: Optional[str] = None


class CanvasState(BaseModel):
    components: Dict[str, CanvasComponent] = {}

    def summary(self) -> str:
        if not self.components:
            return "empty"
        return ", ".join(
            f"{cid}(zone={c.zone or '?'})" for cid, c in self.components.items()
        )


class RenderInput(BaseModel):
    intent: str
    canvas_state: CanvasState
    context: str


class RenderOutput(BaseModel):
    ops: List[CanvasOp]
    errors: List[str] = []


class CSSEntry(BaseModel):
    """A single documented CSS class or data-component declaration stored in the vector index."""
    name: str                        # e.g. "card.glass" or 'data-component="timer"'
    description: str                 # what it does and when to use it
    tags: List[str]                  # semantic tags for retrieval
    example: Optional[str] = None   # minimal inline usage, not a full HTML block

    def to_document(self) -> Document:
        parts = [f"{self.name}: {self.description}"]
        if self.tags:
            parts.append(f"tags: {', '.join(self.tags)}")
        if self.example:
            parts.append(f"example: {self.example}")
        return Document(page_content=" | ".join(parts), metadata={"name": self.name})
