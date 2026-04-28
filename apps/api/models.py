from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Session ──────────────────────────────────────────────────────────────────

class ConversationTurn(BaseModel):
    role: str                   # "user" | "assistant"
    content: str
    timestamp: datetime


class Session(BaseModel):
    session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    conversation: list[ConversationTurn] = Field(default_factory=list)
    active_recipe_id: uuid.UUID | None = None
    current_step: int | None = None
    canvas_state: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)


class SessionCreate(BaseModel):
    preferences: dict[str, Any] = Field(default_factory=dict)


class SessionUpdate(BaseModel):
    last_active: datetime | None = None
    conversation: list[ConversationTurn] | None = None
    active_recipe_id: uuid.UUID | None = None
    current_step: int | None = None
    canvas_state: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None


# ─── Recipe ───────────────────────────────────────────────────────────────────

class RecipeStep(BaseModel):
    step_number: int
    instruction: str
    tip: str | None = None


class Recipe(BaseModel):
    recipe_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    description: str
    duration_minutes: int = Field(gt=0)
    servings: int = Field(gt=0)
    tags: list[str] = Field(default_factory=list)
    steps: list[RecipeStep] = Field(default_factory=list)
    embedding: list[float] | None = None
    source: str = "generated"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RecipeInsert(BaseModel):
    title: str
    description: str
    duration_minutes: int = Field(gt=0)
    servings: int = Field(gt=0)
    tags: list[str] = Field(default_factory=list)
    steps: list[RecipeStep] = Field(default_factory=list)
    embedding: list[float] | None = None
    source: str = "generated"
