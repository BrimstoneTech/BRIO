import pytest
import sys
import os
import sqlite3
from datetime import datetime

# Add project root to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from brio_emotions import EmotionEngine, EmotionType, EmotionTrigger
from brio_core import DecisionEngine, LearningSystem, BrioCore
from brio_storage import StorageManager, InteractionRecord


@pytest.fixture
def emotion_engine():
    """Fixture for a fresh EmotionEngine"""
    return EmotionEngine()


@pytest.fixture
def decision_engine():
    """Fixture for a fresh DecisionEngine"""
    return DecisionEngine()


@pytest.fixture
def test_storage():
    """Fixture for in-memory database storage"""
    # Use in-memory DB for tests
    storage = StorageManager(db_path=":memory:")
    storage._init_database()
    return storage


@pytest.fixture
def brio_core(test_storage):
    """Fixture for BrioCore with in-memory storage"""
    return BrioCore(storage_manager=test_storage)


