from pydantic import BaseModel, Field, field_validator

from app.security.input_guard import sanitize_persona, sanitize_query


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    system_message: str | None = Field(None, max_length=500)  # guests only

    @field_validator("message")
    @classmethod
    def _clean_message(cls, v: str) -> str:
        v = sanitize_query(v)
        if not v:
            raise ValueError("Message is empty")
        return v

    @field_validator("system_message")
    @classmethod
    def _clean_persona(cls, v: str | None) -> str | None:
        return sanitize_persona(v) if v else None