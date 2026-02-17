import pytest
import sqlite3
import json
from datetime import datetime
from brio_storage import InteractionRecord


def test_save_and_retrieve_interaction(test_storage):
    record = InteractionRecord(
        timestamp=datetime.now(),
        user_input="Test input",
        brio_response="Test response",
        user_feedback=None,
        emotion_state={"joy": 0.5},
        decision_factors={"confidence": 0.8},
    )

    pk = test_storage.save_interaction(record)
    assert pk is not None

    retrieved = test_storage.get_interaction(pk)
    assert retrieved.user_input == "Test input"
    assert retrieved.brio_response == "Test response"
    assert retrieved.emotion_state["joy"] == 0.5


def test_user_profile_creation(test_storage):
    profile = test_storage.create_user("user123", "Tester")
    assert profile.user_id == "user123"
    assert profile.username == "Tester"

    retrieved = test_storage.get_user("user123")
    assert retrieved.username == "Tester"


def test_timeline_recording(test_storage):
    test_storage.save_emotional_snapshot({"joy": 0.8})
    timeline = test_storage.get_emotional_timeline()
    assert len(timeline) == 1
    assert timeline[0][1]["joy"] == 0.8


