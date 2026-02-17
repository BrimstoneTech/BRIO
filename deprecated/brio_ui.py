"""
Brio UI Module (brio_ui.py)

Purpose: Manages the "Living Overlay" specific visuals.
         Translates Abstract Emotional/System States -> Concrete Visual Properties.
         Handles User Input for the Overlay (Radials, Toggles).
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from brio_emotions import EmotionType, EmotionalState

class MenuOption(Enum):
    WAKE_SLEEP_TOGGLE = "wake_sleep"
    SETTINGS = "settings"
    APPEARANCE = "appearance"
    DEBUG_LOG = "debug_log"

@dataclass
class HaloState:
    """Visual properties of the Brio Halo"""
    visible: bool = True
    color_hex: str = "#00FFFF"  # Teal default
    pulse_rate: float = 1.0     # Hz (Beats per second)
    opacity: float = 0.8        # 0.0 - 1.0

    def to_dict(self):
        return {
            "visible": self.visible,
            "color": self.color_hex,
            "pulse": self.pulse_rate,
            "opacity": self.opacity
        }

@dataclass
class OverlayState:
    """Complete state snapshot for the Renderer/Frontend"""
    halo: HaloState = field(default_factory=HaloState)
    menu_open: bool = False
    menu_options: List[str] = field(default_factory=list)
    active_notification: str = ""

    def to_dict(self):
        return {
            "halo": self.halo.to_dict(),
            "menu_open": self.menu_open,
            "options": self.menu_options,
            "notification": self.active_notification
        }

class OverlayController:
    """
    Controller that sits between the Backend Logic (Emotions/Logic) 
    and the Frontend Renderer (Android View / HTML Prototype)
    """
    
    def __init__(self):
        self.menu_visible = False
        
        # Color Map: Emotion -> Hex
        self.COLOR_MAP = {
            EmotionType.JOY: "#FFD700",         # Gold
            EmotionType.FRUSTRATION: "#FF4500", # OrangeRed
            EmotionType.EMPATHY: "#00CED1",     # DarkTurquoise (Teal)
            EmotionType.CURIOSITY: "#9370DB",   # MediumPurple
            EmotionType.CONCERN: "#FF6347",     # Tomato
            EmotionType.CONFIDENCE: "#32CD32"   # LimeGreen
        }

    def process_state(self, emotional_state: EmotionalState) -> OverlayState:
        """
        Convert raw emotional state into a visual overlay configuration.
        """
        # 1. Determine Color based on Dominant Emotion
        color = self.COLOR_MAP.get(emotional_state.dominant_emotion, "#FFFFFF")
        
        # 2. Determine Pulse Rate based on Intensity
        # Low intensity (0.2) -> Slow pulse (0.5 Hz)
        # High intensity (0.8) -> Fast pulse (2.0 Hz)
        intensity = emotional_state.get_intensity()
        pulse = 0.5 + (intensity * 2.0)
        
        halo = HaloState(
            visible=True,
            color_hex=color,
            pulse_rate=pulse,
            opacity=0.8
        )
        
        return OverlayState(
            halo=halo,
            menu_open=self.menu_visible,
            menu_options=[opt.value for opt in MenuOption] if self.menu_visible else []
        )

    def handle_input(self, action: str):
        """Handle user interactions with the overlay"""
        if action == "long_press" or action == "right_click":
            self.toggle_menu()
        elif action == "tap_outside":
            if self.menu_visible:
                self.close_menu()

    def toggle_menu(self):
        self.menu_visible = not self.menu_visible

    def close_menu(self):
        self.menu_visible = False

    def select_menu_option(self, option_value: str) -> str:
        """Process menu selection. Returns action command string."""
        self.close_menu()
        return f"EXECUTE:{option_value}"


