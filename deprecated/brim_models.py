from pydantic import BaseModel
from typing import Optional, Dict


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"


class ChatResponse(BaseModel):
    response: str
    emotional_state: Dict
    confidence: float


class FeedbackRequest(BaseModel):
    interaction_id: int
    feedback: str  # positive, negative, neutral
