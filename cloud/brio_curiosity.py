"""
Brio Curiosity Engine (brio_curiosity.py)

Purpose: Autonomous learning loop — Brio explores the web on its own,
         learns from what it finds, and reports back like a child from school.

v5.0 — NEW MODULE
       Background thread that periodically:
       1. Picks a topic from recent conversations or its curiosity list
       2. Searches the web
       3. Reads and extracts knowledge
       4. Self-quizzes on what it learned
       5. Reports discoveries to the user

Dependencies: None beyond existing Brio modules.
"""

import random
import logging
import threading
import time
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

log = logging.getLogger("BrioCuriosity")


@dataclass
class LearningSession:
    """Record of a single learning expedition."""
    topic: str
    trigger: str  # "conversation", "curiosity", "assessment_gap"
    timestamp: str = ""
    facts_learned: List[str] = field(default_factory=list)
    pages_read: int = 0
    quiz_score: Optional[float] = None
    quiz_questions: List[dict] = field(default_factory=list)
    summary: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class QuizQuestion:
    """A self-assessment question."""
    question: str
    expected_answer: str
    brio_answer: str = ""
    correct: bool = False
    topic: str = ""


class CuriosityEngine:
    """
    Brio's autonomous learning system.
    
    The "child from school" — explores topics, learns, takes assessments,
    and reports what it discovered.
    """

    def __init__(self, system_ref):
        self.system = system_ref
        self.is_active = False
        self._thread: Optional[threading.Thread] = None
        
        # Learning config
        self.curiosity_interval = 600  # 10 minutes between explorations
        self.max_daily_searches = 20
        self.daily_search_count = 0
        self._last_reset = datetime.now().date()
        
        # Topic management
        self.curiosity_topics: List[str] = [
            "latest trends in artificial intelligence",
            "how neural networks learn",
            "interesting facts about the universe",
            "breakthroughs in science today",
            "useful Python programming techniques",
        ]
        self.conversation_topics: List[str] = []  # Extracted from chats
        self.explored_topics: List[str] = []
        
        # Learning records
        self.sessions: List[LearningSession] = []
        self.total_facts_learned = 0
        self.total_quizzes_taken = 0
        self.average_quiz_score = 0.0
        
        # Pending reports (for when user comes back)
        self.pending_reports: List[str] = []
        
        # Persistence
        self.state_file = "brio_curiosity_state.json"
        self._load_state()

    # ─── LIFECYCLE ───────────────────────────────────────────────────

    def start(self):
        """Start the autonomous curiosity loop."""
        if self.is_active:
            return
        self.is_active = True
        self._thread = threading.Thread(target=self._curiosity_loop, daemon=True)
        self._thread.start()
        log.info("[Curiosity] Autonomous learning started")

    def stop(self):
        """Stop the curiosity loop."""
        self.is_active = False
        log.info("[Curiosity] Autonomous learning paused")

    # ─── TOPIC EXTRACTION ────────────────────────────────────────────

    def observe_conversation(self, user_text: str, brio_response: str):
        """
        Extract potential learning topics from conversations.
        Called after every user interaction.
        """
        # Simple extraction: look for questions, named entities, unfamiliar terms
        interesting_patterns = [
            "what is", "what are", "how does", "how do", "why is", "why do",
            "tell me about", "explain", "who is", "where is", "when did",
        ]
        
        text_lower = user_text.lower()
        
        for pattern in interesting_patterns:
            if pattern in text_lower:
                # Extract the topic after the pattern
                idx = text_lower.index(pattern) + len(pattern)
                topic = user_text[idx:].strip().rstrip("?.")
                if topic and len(topic) > 3 and topic not in self.conversation_topics:
                    self.conversation_topics.append(topic)
                    if len(self.conversation_topics) > 20:
                        self.conversation_topics.pop(0)
                    log.info(f"[Curiosity] Noted topic from conversation: {topic}")
                break

        # Also extract nouns/keywords longer than 5 chars (simple heuristic)
        words = [w for w in user_text.split() if len(w) > 5 and w.isalpha()]
        if words and random.random() < 0.3:  # Don't extract from every message
            topic = " ".join(random.sample(words, min(2, len(words))))
            if topic not in self.conversation_topics:
                self.conversation_topics.append(topic)

    def add_curiosity_topic(self, topic: str):
        """Manually add a topic for BRIO to explore."""
        if topic not in self.curiosity_topics:
            self.curiosity_topics.append(topic)
            log.info(f"[Curiosity] New curiosity topic added: {topic}")

    # ─── AUTONOMOUS LEARNING LOOP ────────────────────────────────────

    def _curiosity_loop(self):
        """Background loop that drives autonomous exploration."""
        # Wait a bit before first exploration (let system stabilize)
        time.sleep(30)

        while self.is_active:
            try:
                # Reset daily counter
                today = datetime.now().date()
                if today != self._last_reset:
                    self.daily_search_count = 0
                    self._last_reset = today

                # Check if we have budget
                if self.daily_search_count >= self.max_daily_searches:
                    log.info("[Curiosity] Daily search limit reached. Resting.")
                    time.sleep(self.curiosity_interval)
                    continue

                # Pick a topic
                topic = self._pick_topic()
                if not topic:
                    time.sleep(self.curiosity_interval)
                    continue

                # Explore!
                session = self._explore_topic(topic)
                if session and session.facts_learned:
                    self.sessions.append(session)
                    self.total_facts_learned += len(session.facts_learned)

                    # Self-assessment
                    quiz_score = self._self_assess(session)
                    session.quiz_score = quiz_score

                    # Generate report
                    report = self._generate_report(session)
                    self.pending_reports.append(report)
                    
                    self.explored_topics.append(topic)
                    self._save_state()

                    log.info(f"[Curiosity] Explored '{topic}' — "
                             f"{len(session.facts_learned)} facts, quiz: {quiz_score:.0%}")

                self.daily_search_count += 1

            except Exception as e:
                log.error(f"[Curiosity] Loop error: {e}")

            # Wait before next exploration
            time.sleep(self.curiosity_interval)

    def _pick_topic(self) -> Optional[str]:
        """Choose the next topic to explore."""
        # Priority 1: Conversation topics (what the user talked about)
        available_conv = [t for t in self.conversation_topics if t not in self.explored_topics]
        if available_conv:
            return available_conv[0]

        # Priority 2: Assessment gaps (topics with low quiz scores)
        weak_topics = self._find_weak_topics()
        if weak_topics:
            return f"{weak_topics[0]} deeper study"

        # Priority 3: Built-in curiosity list
        available_cur = [t for t in self.curiosity_topics if t not in self.explored_topics]
        if available_cur:
            return random.choice(available_cur)

        # Priority 4: Random knowledge expansion
        expansions = [
            "interesting scientific discoveries this year",
            "how computers process information",
            "the history of artificial intelligence",
            "creative problem solving techniques",
            "how memory works in the brain",
        ]
        unused = [t for t in expansions if t not in self.explored_topics]
        if unused:
            return random.choice(unused)

        return None

    def _explore_topic(self, topic: str) -> Optional[LearningSession]:
        """Execute a learning expedition on a topic."""
        session = LearningSession(
            topic=topic,
            trigger="curiosity" if topic in self.curiosity_topics else "conversation",
        )

        if not hasattr(self.system, 'sifter') or not self.system.sifter:
            log.warning("[Curiosity] WebSifter not available")
            return None

        # Use the web sifter to search, read, and extract facts
        result = self.system.sifter.search_and_ingest(topic, max_pages=2)
        
        # Count what was learned
        # The sifter stores facts as engrams, so count new ones
        session.summary = result
        
        # Extract fact count from summary
        if "Extracted" in result:
            try:
                import re
                match = re.search(r'(\d+) facts', result)
                if match:
                    count = int(match.group(1))
                    # Get the most recent engrams as facts learned
                    recent = self.system.knowledge.engrams[-count:] if count > 0 else []
                    session.facts_learned = [e.content for e in recent]
                    session.pages_read = int(re.search(r'(\d+) pages', result).group(1)) if re.search(r'(\d+) pages', result) else 0
            except Exception:
                pass

        return session

    # ─── SELF-ASSESSMENT ─────────────────────────────────────────────

    def _self_assess(self, session: LearningSession) -> float:
        """
        BRIO quizzes itself on what it just learned.
        Returns a score from 0.0 to 1.0.
        """
        if not session.facts_learned or not self.system.mind:
            return 0.0

        # Generate 3 quiz questions from the facts
        questions = self._generate_quiz(session.facts_learned, session.topic)
        if not questions:
            return 0.5  # Can't assess

        correct = 0
        for q in questions:
            # Try to answer from engram memory only
            answer = self._answer_from_memory(q["question"], session.topic)
            q["brio_answer"] = answer

            # Check answer (simple keyword overlap)
            q["correct"] = self._check_answer(answer, q["expected_answer"])
            if q["correct"]:
                correct += 1

        session.quiz_questions = questions
        score = correct / len(questions) if questions else 0.0

        self.total_quizzes_taken += 1
        # Running average
        self.average_quiz_score = (
            (self.average_quiz_score * (self.total_quizzes_taken - 1) + score)
            / self.total_quizzes_taken
        )

        return score

    def _generate_quiz(self, facts: List[str], topic: str) -> List[dict]:
        """Generate quiz questions from learned facts."""
        if self.system.mind:
            return self._generate_quiz_ollama(facts, topic)
        else:
            return self._generate_quiz_simple(facts)

    def _generate_quiz_ollama(self, facts: List[str], topic: str) -> List[dict]:
        """Use Ollama to generate meaningful quiz questions."""
        facts_text = "\n".join(f"- {f}" for f in facts[:5])

        prompt = (
            f"Based on these facts about '{topic}':\n{facts_text}\n\n"
            f"Generate exactly 3 quiz questions to test understanding. "
            f"For each, provide the question and the correct answer.\n"
            f"Format: Q1: [question]\nA1: [answer]\nQ2: ...\nA2: ..."
        )

        try:
            response, _ = self.system.mind.think(
                prompt,
                override_prompt="You are a quiz generator. Return only questions and answers."
            )

            questions = []
            lines = response.strip().split("\n")
            current_q = None

            for line in lines:
                line = line.strip()
                if line.startswith(("Q1:", "Q2:", "Q3:", "Q ")):
                    current_q = line.split(":", 1)[-1].strip()
                elif line.startswith(("A1:", "A2:", "A3:", "A ")) and current_q:
                    answer = line.split(":", 1)[-1].strip()
                    questions.append({
                        "question": current_q,
                        "expected_answer": answer,
                        "brio_answer": "",
                        "correct": False,
                    })
                    current_q = None

            return questions[:3]

        except Exception as e:
            log.warning(f"[Curiosity] Quiz generation failed: {e}")
            return self._generate_quiz_simple(facts)

    def _generate_quiz_simple(self, facts: List[str]) -> List[dict]:
        """Fallback: create fill-in-the-blank style questions."""
        questions = []
        for fact in facts[:3]:
            words = fact.split()
            if len(words) > 5:
                # Blank out a key word
                key_idx = len(words) // 2
                answer = words[key_idx]
                question_words = words[:key_idx] + ["_____"] + words[key_idx + 1:]
                questions.append({
                    "question": " ".join(question_words),
                    "expected_answer": answer,
                    "brio_answer": "",
                    "correct": False,
                })
        return questions

    def _answer_from_memory(self, question: str, topic: str) -> str:
        """
        Answer a quiz question using ONLY engram memory.
        This tests whether BRIO actually retained the knowledge.
        """
        # Search engrams for relevant info
        keywords = [w for w in question.split() if len(w) > 3]
        matches = self.system.knowledge.associative_recall(
            emotion="curiosity", keywords=keywords
        )

        if matches:
            # Combine top matches as context
            context = " ".join(e.content for e in matches[:3])
            
            if self.system.mind:
                try:
                    answer, _ = self.system.mind.think(
                        f"Question: {question}\nContext from memory: {context}\nAnswer briefly:",
                        override_prompt="Answer the question using only the provided context. Be brief."
                    )
                    return answer
                except Exception:
                    pass
            
            return context[:200]

        return "I don't remember enough about this topic."

    def _check_answer(self, brio_answer: str, expected: str) -> bool:
        """Check if Brio's answer matches expected (fuzzy matching)."""
        if not brio_answer or not expected:
            return False

        brio_lower = brio_answer.lower()
        expected_lower = expected.lower()

        # Key word overlap
        expected_words = set(w for w in expected_lower.split() if len(w) > 3)
        if not expected_words:
            return expected_lower in brio_lower

        matches = sum(1 for w in expected_words if w in brio_lower)
        return (matches / len(expected_words)) >= 0.5

    def _find_weak_topics(self) -> List[str]:
        """Find topics where BRIO scored poorly on quizzes."""
        weak = []
        for s in self.sessions[-20:]:
            if s.quiz_score is not None and s.quiz_score < 0.5:
                weak.append(s.topic)
        return weak

    # ─── REPORTS ─────────────────────────────────────────────────────

    def _generate_report(self, session: LearningSession) -> str:
        """Generate a human-friendly report of a learning session."""
        report = f"🔍 *I explored: {session.topic}*\n"

        if session.facts_learned:
            report += f"\nHere's what I learned:\n"
            for i, fact in enumerate(session.facts_learned[:5], 1):
                report += f"  {i}. {fact}\n"

        if session.quiz_score is not None:
            emoji = "🌟" if session.quiz_score >= 0.8 else "📝" if session.quiz_score >= 0.5 else "📚"
            report += f"\n{emoji} Self-assessment score: {session.quiz_score:.0%}"
            if session.quiz_score < 0.5:
                report += " — I should study this more."

        report += f"\n📖 Pages read: {session.pages_read}"
        return report

    def get_pending_reports(self) -> List[str]:
        """Get reports accumulated while user was away, then clear them."""
        reports = list(self.pending_reports)
        self.pending_reports.clear()
        return reports

    def get_knowledge_growth(self) -> dict:
        """Return metrics about BRIO's learning growth."""
        return {
            "total_sessions": len(self.sessions),
            "total_facts_learned": self.total_facts_learned,
            "total_quizzes": self.total_quizzes_taken,
            "average_quiz_score": round(self.average_quiz_score, 3),
            "topics_explored": len(self.explored_topics),
            "weak_topics": self._find_weak_topics(),
            "daily_searches_remaining": self.max_daily_searches - self.daily_search_count,
        }

    def get_full_report(self) -> str:
        """Comprehensive learning report."""
        growth = self.get_knowledge_growth()
        
        report = (
            f"📚 *Brio's Learning Dashboard*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔍 Learning sessions: {growth['total_sessions']}\n"
            f"💡 Facts crystallized: {growth['total_facts_learned']}\n"
            f"📝 Quizzes taken: {growth['total_quizzes']}\n"
            f"🎯 Average score: {growth['average_quiz_score']:.0%}\n"
            f"🌐 Topics explored: {growth['topics_explored']}\n"
        )

        if growth['weak_topics']:
            report += f"\n📚 Areas needing more study:\n"
            for t in growth['weak_topics'][:5]:
                report += f"  • {t}\n"

        if self.sessions:
            report += f"\n🕐 Recent explorations:\n"
            for s in self.sessions[-5:]:
                score_str = f" ({s.quiz_score:.0%})" if s.quiz_score is not None else ""
                report += f"  • {s.topic}{score_str}\n"

        return report

    # ─── PERSISTENCE ─────────────────────────────────────────────────

    def _save_state(self):
        """Save curiosity state to disk."""
        try:
            data = {
                "curiosity_topics": self.curiosity_topics,
                "conversation_topics": self.conversation_topics,
                "explored_topics": self.explored_topics,
                "total_facts_learned": self.total_facts_learned,
                "total_quizzes_taken": self.total_quizzes_taken,
                "average_quiz_score": self.average_quiz_score,
                "sessions": [
                    {
                        "topic": s.topic,
                        "trigger": s.trigger,
                        "timestamp": s.timestamp,
                        "facts_count": len(s.facts_learned),
                        "quiz_score": s.quiz_score,
                        "pages_read": s.pages_read,
                    }
                    for s in self.sessions[-50:]
                ],
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.warning(f"[Curiosity] State save failed: {e}")

    def _load_state(self):
        """Restore curiosity state from disk."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                self.curiosity_topics = data.get("curiosity_topics", self.curiosity_topics)
                self.conversation_topics = data.get("conversation_topics", [])
                self.explored_topics = data.get("explored_topics", [])
                self.total_facts_learned = data.get("total_facts_learned", 0)
                self.total_quizzes_taken = data.get("total_quizzes_taken", 0)
                self.average_quiz_score = data.get("average_quiz_score", 0.0)
                log.info(f"[Curiosity] State restored — {self.total_facts_learned} facts in memory")
        except Exception as e:
            log.warning(f"[Curiosity] State load failed: {e}")
