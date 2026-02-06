import pytest
import sys
import os
import sqlite3
from datetime import datetime

# Add project root to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from brim_emotions import EmotionEngine, EmotionType, EmotionTrigger
from brim_core import DecisionEngine, LearningSystem, BRIMCore
from brim_storage import StorageManager, InteractionRecord


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
def brim_core(test_storage):
    """Fixture for BRIMCore with in-memory storage"""
    return BRIMCore(storage_manager=test_storage)
