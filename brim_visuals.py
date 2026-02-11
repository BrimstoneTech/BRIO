"""
BRIM Visuals Module (brim_visuals.py)

Purpose: Manages the visual state of the mascot (Brio) and its habitat (The Ball).
         Determines when to show the character vs the container based on 
         system context (Battery, Time, Activity).
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class VisualState(Enum):
    HIDDEN = "hidden"            # App background / minimized
    ASLEEP = "ball_visible"      # The Support Ball (Dormant)
    WAKING = "transition_out"    # Animation: Ball Opening -> Brio Emerging
    ACTIVE = "brio_visible"      # Brio Character (Active Assistant)
    SLEEPING = "transition_in"   # Animation: Brio Retreating -> Ball Closing

@dataclass
class SystemContext:
    battery_level: float = 1.0   # 0.0 - 1.0
    current_hour: int = 12       # 0 - 23
    user_active: bool = True     # True if interacting
    is_charging: bool = False

class VisualStateManager:
    """
    Decides the visual state of the mascot.
    Implements the 'Ball Habitat' logic.
    """
    
    def __init__(self):
        self.current_state = VisualState.ACTIVE
        self._in_low_battery_mode = False  # Track hysteresis state
        
        # Configuration for Sleep Triggers
        self.SLEEP_BATTERY_ENTER = 0.15  # 15%
        self.SLEEP_BATTERY_EXIT = 0.20   # 20%
        self.SLEEP_START_HOUR = 1        # 1 AM
        self.SLEEP_END_HOUR = 6          # 6 AM
        
    def update(self, context: SystemContext) -> VisualState:
        """
        Update visual state based on new system context.
        Returns the new state.
        """
        
        # 1. Determine Target State based on Logic
        target_state = self._determine_target_state(context)
        
        # 2. Handle Transitions
        # If we are Active and want to be Asleep, we must animate (Sleeping) first
        if self.current_state == VisualState.ACTIVE and target_state == VisualState.ASLEEP:
            self.current_state = VisualState.SLEEPING
            return self.current_state
            
        # If we are Asleep and want to be Active, we must animate (Waking) first
        if self.current_state == VisualState.ASLEEP and target_state == VisualState.ACTIVE:
            self.current_state = VisualState.WAKING
            return self.current_state
            
        # If we were transitioning, complete the transition
        if self.current_state == VisualState.SLEEPING:
            self.current_state = VisualState.ASLEEP # Animation complete
        elif self.current_state == VisualState.WAKING:
            self.current_state = VisualState.ACTIVE # Animation complete
            
        return self.current_state
        
    def _determine_target_state(self, context: SystemContext) -> VisualState:
        """Core logic for habitat behavior - Implements Sleep/Wake Protocols"""
        
        # Protocol 1: User Override (Highest Priority)
        if context.user_active:
            return VisualState.ACTIVE

        # Protocol 2: Charging (Resource Abundance)
        if context.is_charging:
            # Optional: We could check time here for "Night Light" mode, 
            # but per protocol, charging = Awake/Active
            return VisualState.ACTIVE

        # Protocol 3: Biological Battery Protocol (Resource Scarcity)
        if self._in_low_battery_mode:
            # We are already low battery. Exit only if > 20%
            if context.battery_level > self.SLEEP_BATTERY_EXIT:
                self._in_low_battery_mode = False
            else:
                return VisualState.ASLEEP
        else:
            # We are normal. Enter low battery only if < 15%
            if context.battery_level < self.SLEEP_BATTERY_ENTER:
                self._in_low_battery_mode = True
                return VisualState.ASLEEP

        # Protocol 4: Circadian Rhythm Protocol (Time)
        # Sleep if between START and END hour
        if self.SLEEP_START_HOUR <= context.current_hour < self.SLEEP_END_HOUR:
            return VisualState.ASLEEP
            
        # Default: Awake
        return VisualState.ACTIVE

    def get_render_asset(self) -> str:
        """Returns the hypothetical asset path for the current state"""
        assets = {
            VisualState.HIDDEN: "assets/empty.glb",
            VisualState.ASLEEP: "assets/support_ball.glb",
            VisualState.WAKING: "assets/anim_ball_open.glb",
            VisualState.ACTIVE: "assets/brio_character.glb",
            VisualState.SLEEPING: "assets/anim_ball_close.glb"
        }
        return assets.get(self.current_state, "assets/error.glb")

    def _map_emotion_to_color(self, emotion_type: 'EmotionType') -> str:
        """Maps emotional dimension to a specific HEX color (Signature v3.0 Palette)"""
        from brim_emotions import EmotionType
        mapping = {
            EmotionType.JOY: "#99E2B4",         # Soft Green (Growth/Harmony)
            EmotionType.FRUSTRATION: "#FFB38A",  # Soft Orange (Transition/Positivity)
            EmotionType.EMPATHY: "#FFD8BE",    # Warm Peach (Inclusive/Welcoming)
            EmotionType.CURIOSITY: "#B79CED",   # Lavender (Creativity/Wisdom)
            EmotionType.CONCERN: "#E0E1DD",     # Warm Gray (Safety/Balance)
            EmotionType.CONFIDENCE: "#70D6FF",    # Light Blue (Trust/Reliability)
        }
        return mapping.get(emotion_type, "#70D6FF")
