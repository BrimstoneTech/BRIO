"""
Brio Storage Module (brio_storage.py)

Purpose: Data persistence layer for Brio interactions, emotions, and metadata
Characteristics:
- Abstracted database operations
- JSON export/import functionality
- User profile management
- Non-dependent on core logic (can be replaced)

Author: Brio System
Version: 1.0
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class InteractionRecord:
    """Single interaction with metadata"""

    timestamp: datetime
    user_input: str
    brio_response: str
    user_feedback: Optional[str]
    emotion_state: dict
    decision_factors: dict

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_input": self.user_input,
            "brio_response": self.brio_response,
            "user_feedback": self.user_feedback,
            "emotion_state": self.emotion_state,
            "decision_factors": self.decision_factors,
        }


@dataclass
class UserProfile:
    """User profile and preferences"""

    user_id: str
    username: str
    created_at: datetime
    interaction_count: int = 0
    feedback_count: int = 0
    learning_adjustment: float = 0.0
    preferred_feedback_style: str = "neutral"  # positive, neutral, formal, casual

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "created_at": self.created_at.isoformat(),
            "interaction_count": self.interaction_count,
            "feedback_count": self.feedback_count,
            "learning_adjustment": self.learning_adjustment,
            "preferred_feedback_style": self.preferred_feedback_style,
        }


# ============================================================================
# DATABASE INTERFACE
# ============================================================================


class StorageManager:
    """
    Central storage interface for all persistence operations.

    Can be replaced with alternative storage (cloud, NoSQL, etc)
    without affecting core Brio logic.
    """

    def __init__(self, db_path: str = "brio_interactions.db"):
        self.db_path = db_path
        self._persistent_conn = None

        # For in-memory database, we must keep the connection open
        if self.db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(":memory:")

        self._init_database()

    def _get_connection(self):
        """Helper to get a database connection"""
        if self._persistent_conn:
            return self._persistent_conn
        return sqlite3.connect(self.db_path)

    def _close_connection(self, conn):
        """Helper to close connection (only if not persistent)"""
        if not self._persistent_conn:
            conn.close()

    def _init_database(self):
        """Initialize SQLite database with required tables"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                user_input TEXT,
                brio_response TEXT,
                user_feedback TEXT,
                emotion_state TEXT,
                decision_factors TEXT
            )
        """)

        # Emotional timeline table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emotional_timeline (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                emotion_state TEXT
            )
        """)

        # User profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                created_at TEXT,
                interaction_count INTEGER,
                feedback_count INTEGER,
                learning_adjustment REAL,
                preferred_feedback_style TEXT
            )
        """)

        # Feedback history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_history (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                interaction_id INTEGER,
                feedback TEXT,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
            )
        """)

        conn.commit()
        if not self._persistent_conn:
            conn.close()

    # ========================================================================
    # INTERACTION STORAGE
    # ========================================================================

    def save_interaction(self, record: InteractionRecord) -> int:
        """
        Save interaction to database.

        Returns:
            interaction_id for reference
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO interactions 
            (timestamp, user_input, brio_response, user_feedback, emotion_state, decision_factors)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                record.timestamp.isoformat(),
                record.user_input,
                record.brio_response,
                record.user_feedback,
                json.dumps(record.emotion_state),
                json.dumps(record.decision_factors),
            ),
        )

        interaction_id = cursor.lastrowid
        conn.commit()
        if not self._persistent_conn:
            conn.close()

        return interaction_id

    def update_interaction_feedback(self, interaction_id: int, feedback: str) -> bool:
        """Update feedback on an existing interaction"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE interactions
            SET user_feedback = ?
            WHERE id = ?
        """,
            (feedback, interaction_id),
        )

        conn.commit()
        if not self._persistent_conn:
            conn.close()

        return cursor.rowcount > 0

    def get_interaction(self, interaction_id: int) -> Optional[InteractionRecord]:
        """Retrieve a specific interaction"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT timestamp, user_input, brio_response, user_feedback, 
                   emotion_state, decision_factors
            FROM interactions
            WHERE id = ?
        """,
            (interaction_id,),
        )

        row = cursor.fetchone()
        if not self._persistent_conn:
            conn.close()

        if not row:
            return None

        return InteractionRecord(
            timestamp=datetime.fromisoformat(row[0]),
            user_input=row[1],
            brio_response=row[2],
            user_feedback=row[3],
            emotion_state=json.loads(row[4]),
            decision_factors=json.loads(row[5]),
        )

    def get_recent_interactions(self, limit: int = 10) -> List[InteractionRecord]:
        """Get recent interactions"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT timestamp, user_input, brio_response, user_feedback,
                   emotion_state, decision_factors
            FROM interactions
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()
        if not self._persistent_conn:
            conn.close()

        interactions = []
        for row in rows:
            interactions.append(
                InteractionRecord(
                    timestamp=datetime.fromisoformat(row[0]),
                    user_input=row[1],
                    brio_response=row[2],
                    user_feedback=row[3],
                    emotion_state=json.loads(row[4]),
                    decision_factors=json.loads(row[5]),
                )
            )

        return interactions

    def get_interaction_count(self) -> int:
        """Get total interaction count"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM interactions")
        count = cursor.fetchone()[0]
        if not self._persistent_conn:
            conn.close()

        return count

    # ========================================================================
    # EMOTIONAL TIMELINE
    # ========================================================================

    def save_emotional_snapshot(self, emotion_state: dict) -> None:
        """Save emotional state snapshot"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO emotional_timeline (timestamp, emotion_state)
            VALUES (?, ?)
        """,
            (
                datetime.now().isoformat(),
                json.dumps(emotion_state),
            ),
        )

        conn.commit()
        if not self._persistent_conn:
            conn.close()

    def get_emotional_timeline(self, limit: int = 100) -> List[Tuple[str, dict]]:
        """Get emotional state timeline"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT timestamp, emotion_state
            FROM emotional_timeline
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()
        if not self._persistent_conn:
            conn.close()

        return [(row[0], json.loads(row[1])) for row in rows]

    # ========================================================================
    # USER PROFILES
    # ========================================================================

    def create_user(self, user_id: str, username: str) -> UserProfile:
        """Create new user profile"""
        conn = self._get_connection()
        cursor = conn.cursor()

        profile = UserProfile(
            user_id=user_id,
            username=username,
            created_at=datetime.now(),
        )

        cursor.execute(
            """
            INSERT INTO user_profiles 
            (user_id, username, created_at, interaction_count, feedback_count, 
             learning_adjustment, preferred_feedback_style)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                profile.user_id,
                profile.username,
                profile.created_at.isoformat(),
                profile.interaction_count,
                profile.feedback_count,
                profile.learning_adjustment,
                profile.preferred_feedback_style,
            ),
        )

        conn.commit()
        if not self._persistent_conn:
            conn.close()

        return profile

    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id, username, created_at, interaction_count, feedback_count,
                   learning_adjustment, preferred_feedback_style
            FROM user_profiles
            WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        if not self._persistent_conn:
            conn.close()

        if not row:
            return None

        return UserProfile(
            user_id=row[0],
            username=row[1],
            created_at=datetime.fromisoformat(row[2]),
            interaction_count=row[3],
            feedback_count=row[4],
            learning_adjustment=row[5],
            preferred_feedback_style=row[6],
        )

    def update_user(self, profile: UserProfile) -> bool:
        """Update user profile"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE user_profiles
            SET username = ?, interaction_count = ?, feedback_count = ?,
                learning_adjustment = ?, preferred_feedback_style = ?
            WHERE user_id = ?
        """,
            (
                profile.username,
                profile.interaction_count,
                profile.feedback_count,
                profile.learning_adjustment,
                profile.preferred_feedback_style,
                profile.user_id,
            ),
        )

        conn.commit()
        if not self._persistent_conn:
            conn.close()

        return cursor.rowcount > 0

    # ========================================================================
    # EXPORT/IMPORT
    # ========================================================================

    def export_to_json(self, filepath: str = "brio_export.json") -> str:
        """Export all interactions and timeline to JSON"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get all interactions
        cursor.execute("""
            SELECT timestamp, user_input, brio_response, user_feedback,
                   emotion_state, decision_factors
            FROM interactions
            ORDER BY timestamp ASC
        """)
        interactions_rows = cursor.fetchall()

        # Get emotional timeline
        cursor.execute("""
            SELECT timestamp, emotion_state
            FROM emotional_timeline
            ORDER BY timestamp ASC
        """)
        timeline_rows = cursor.fetchall()

        if not self._persistent_conn:
            conn.close()

        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_interactions": len(interactions_rows),
            },
            "interactions": [
                {
                    "timestamp": row[0],
                    "user_input": row[1],
                    "brio_response": row[2],
                    "user_feedback": row[3],
                    "emotion_state": json.loads(row[4]),
                    "decision_factors": json.loads(row[5]),
                }
                for row in interactions_rows
            ],
            "emotional_timeline": [
                {
                    "timestamp": row[0],
                    "emotion_state": json.loads(row[1]),
                }
                for row in timeline_rows
            ],
        }

        with open(filepath, "w") as f:
            json.dump(export_data, f, indent=2)

        return filepath

    def clear_all_data(self) -> bool:
        """Clear all stored data (USE WITH CAUTION)"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM interactions")
        cursor.execute("DELETE FROM emotional_timeline")
        cursor.execute("DELETE FROM feedback_history")
        cursor.execute("DELETE FROM user_profiles")

        conn.commit()
        if not self._persistent_conn:
            conn.close()

        return True

    def get_statistics(self) -> Dict:
        """Get database statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM interactions")
        interaction_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_profiles")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM emotional_timeline")
        timeline_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM interactions 
            WHERE user_feedback IS NOT NULL
        """)
        feedback_count = cursor.fetchone()[0]

        if not self._persistent_conn:
            conn.close()

        return {
            "total_interactions": interaction_count,
            "total_users": user_count,
            "emotional_snapshots": timeline_count,
            "feedback_records": feedback_count,
            "database_file": self.db_path,
        }


