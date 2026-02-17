import pytest
from brio_emotions import EmotionType, EmotionTrigger


def test_initial_state(emotion_engine):
    state = emotion_engine.get_state()
    assert state.joy == 0.5
    assert state.frustration == 0.2
    assert state.empathy == 0.7
    assert state.dominant_emotion == EmotionType.EMPATHY


def test_trigger_praise(emotion_engine):
    initial_joy = emotion_engine.get_state().joy
    emotion_engine.apply_trigger(EmotionTrigger.USER_PRAISE)
    new_joy = emotion_engine.get_state().joy
    assert new_joy > initial_joy


def test_trigger_harm_detection(emotion_engine):
    emotion_engine.apply_trigger(EmotionTrigger.HARM_DETECTION)
    state = emotion_engine.get_state()
    assert state.concern == 1.0
    assert state.dominant_emotion == EmotionType.CONCERN


def test_decay(emotion_engine):
    # Boost joy first
    emotion_engine.apply_trigger(EmotionTrigger.USER_PRAISE, intensity=0.3)
    boosted_joy = emotion_engine.get_state().joy

    # Apply decay
    emotion_engine.apply_decay(decay_rate=0.1)
    decayed_joy = emotion_engine.get_state().joy

    assert decayed_joy < boosted_joy
    assert decayed_joy >= 0.5  # Should decay towards baseline


def test_bounds_validation(emotion_engine):
    # Try to boost beyond 1.0 (internal logic checks this, but good to verify)
    for _ in range(10):
        emotion_engine.apply_trigger(EmotionTrigger.USER_PRAISE, intensity=0.3)

    assert emotion_engine.get_state().joy <= 1.0


