from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.security.input_guard import sanitize_persona


class ConversationCreate(BaseModel):
    title: str = Field("New chat", max_length=80)
    system_message: str = Field("", max_length=500)
    mode: Literal["normal", "accurate"] = "normal"

    @field_validator("system_message")
    @classmethod
    def _clean(cls, v: str) -> str:
        return sanitize_persona(v)

    @field_validator("title")
    @classmethod
    def _title(cls, v: str) -> str:
        return v.strip() or "New chat"


class ConversationUpdate(BaseModel):
    title: str | None = Field(None, max_length=80)
    system_message: str | None = Field(None, max_length=500)
    mode: Literal["normal", "accurate"] | None = None

    @field_validator("system_message")
    @classmethod
    def _clean(cls, v: str | None) -> str | None:
        return sanitize_persona(v) if v is not None else None


class ConversationOut(BaseModel):
    id: str
    title: str
    system_message: str
    mode: str
    created_at: str
    updated_at: str