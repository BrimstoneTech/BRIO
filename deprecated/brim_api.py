"""
BRIM API (brim_api.py)

Exposes BRIM Core logic via REST API.
Includes:
- API access control (basic)
- Rate limiting (in-memory)
- Input sanitization
"""

import os
import time
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

from brim_core import BRIMCore
from brim_storage import StorageManager
from brim_models import ChatRequest, ChatResponse, FeedbackRequest
from brim_security import InputSanitizer

app = FastAPI(title="BRIM AI API", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core
storage = StorageManager()
brim = BRIMCore(storage)

# Basic Rate Limiting
request_counts: Dict[str, list] = {}
RATE_LIMIT = 60  # requests per minute


def check_rate_limit(request: Request):
    client_ip = request.client.host
    current_time = time.time()

    if client_ip not in request_counts:
        request_counts[client_ip] = []

    # Clean old requests
    request_counts[client_ip] = [
        t for t in request_counts[client_ip] if t > current_time - 60
    ]

    if len(request_counts[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    request_counts[client_ip].append(current_time)


# API Routes


@app.post(
    "/chat", response_model=ChatResponse, dependencies=[Depends(check_rate_limit)]
)
async def chat(request: ChatRequest):
    # 1. Sanitize Input
    clean_message = InputSanitizer.sanitize(request.message)

    if not clean_message:
        raise HTTPException(status_code=400, detail="Empty message")

    if not InputSanitizer.validate_length(clean_message):
        raise HTTPException(status_code=400, detail="Message too long")

    # 2. Process via BRIM Core
    response_text = brim.process_input(clean_message)

    # 3. Get metadata
    status = brim.get_status()

    return ChatResponse(
        response=response_text,
        emotional_state=status["emotional_state"],
        confidence=status["decision_metrics"]["success_rate"],
    )


@app.post("/feedback", dependencies=[Depends(check_rate_limit)])
async def feedback(request: FeedbackRequest):
    result = brim.provide_feedback(request.interaction_id, request.feedback)
    return {"message": result}


@app.get("/status", dependencies=[Depends(check_rate_limit)])
async def status():
    return brim.get_status()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
