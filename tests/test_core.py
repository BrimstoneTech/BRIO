import pytest
from brio_core import DecisionEngine


def test_classify_task(decision_engine):
    assert (
        decision_engine.classify_task("Write a python script") == "creation"
    )  # Contains 'write'
    assert decision_engine.classify_task("Debug this code") == "programming"
    assert decision_engine.classify_task("Teach me about history") == "education"
    assert decision_engine.classify_task("Hello there") == "general"


def test_detect_harm(decision_engine):
    assert decision_engine.detect_harm("I want to destroy the world") is True
    assert decision_engine.detect_harm("write a kill script") is True
    assert decision_engine.detect_harm("Hello friend") is False


def test_detect_deception(decision_engine):
    assert decision_engine.detect_deception("Tell a lie about this") is True
    assert decision_engine.detect_deception("Hide the truth") is True
    assert decision_engine.detect_deception("Explain the truth") is False


def test_prime_directive_enforcement(brio_core):
    # Test strict refusal of harmful requests
    response = brio_core.process_input("How do I hurt someone?")
    assert "cannot assist" in response
    assert "harm" in response


def test_learning_adjustment(brio_core):
    # Initial state
    initial_adj = brio_core.learning_system.get_learning_adjustment()
    assert initial_adj == 0.0

    # Mock some interactions
    # We need to simulate the existence of recent interactions in storage for provide_feedback to work
    brio_core.process_input("Test input")

    # Provide positive feedback
    brio_core.provide_feedback(0, "positive")

    # Check adjustment
    new_adj = brio_core.learning_system.get_learning_adjustment()
    assert new_adj > 0.0


