
import unittest
import sys
import os

# Add parent directory to path to import brim_visuals
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brim_visuals import VisualStateManager, SystemContext, VisualState

class TestVisualProtocols(unittest.TestCase):
    def setUp(self):
        self.manager = VisualStateManager()
        
    def test_protocol_1_user_override(self):
        """User interaction should override everything else"""
        # Context: Dead battery (10%), Nighttime (3 AM), But User is Active
        context = SystemContext(
            battery_level=0.10,
            current_hour=3,
            user_active=True,
            is_charging=False
        )
        state = self.manager.update(context)
        # Should remain ACTIVE
        self.assertEqual(state, VisualState.ACTIVE)
        
    def test_protocol_2_charging(self):
        """Charging should keep AI awake even if battery is low"""
        # Context: Charging, 10% battery, No user
        context = SystemContext(
            battery_level=0.10,
            current_hour=12,
            user_active=False,
            is_charging=True
        )
        state = self.manager.update(context)
        self.assertEqual(state, VisualState.ACTIVE)
        
    def test_protocol_3_battery_hysteresis(self):
        """Verify enter/exit thresholds for battery sleep"""
        # 1. Start Normal
        ctx = SystemContext(battery_level=0.5, user_active=False)
        self.manager.update(ctx)
        self.assertEqual(self.manager.current_state, VisualState.ACTIVE)
        
        # 2. Drop to 18% (Should NOT trigger sleep yet, threshold is 15%)
        ctx.battery_level = 0.18
        self.manager.update(ctx)
        self.assertEqual(self.manager.current_state, VisualState.ACTIVE)
        
        # 3. Drop to 14% (Trigger Sleep)
        ctx.battery_level = 0.14
        # First update triggers transition
        state = self.manager.update(ctx)
        self.assertEqual(state, VisualState.SLEEPING)
        # Second update completes transition
        state = self.manager.update(ctx) 
        self.assertEqual(state, VisualState.ASLEEP)
        
        # 4. Rise to 19% (Should STAY Asleep due to hysteresis)
        ctx.battery_level = 0.19
        state = self.manager.update(ctx)
        self.assertEqual(state, VisualState.ASLEEP)
        
        # 5. Rise to 21% (Exit Sleep)
        ctx.battery_level = 0.21
        # Transition out
        state = self.manager.update(ctx)
        self.assertEqual(state, VisualState.WAKING)
        # Complete
        state = self.manager.update(ctx)
        self.assertEqual(state, VisualState.ACTIVE)

    def test_protocol_4_circadian_rhythm(self):
        """Verify sleep during night hours"""
        # Context: 3 AM, Good battery, No user
        ctx = SystemContext(
            battery_level=0.8,
            current_hour=3, 
            user_active=False
        )
        
        # Transition to Sleep
        self.manager.update(ctx) # SLEEPING
        state = self.manager.update(ctx) # ASLEEP
        self.assertEqual(state, VisualState.ASLEEP)
        
        # Context: 7 AM (Wake up)
        ctx.current_hour = 7
        self.manager.update(ctx) # WAKING
        state = self.manager.update(ctx) # ACTIVE
        self.assertEqual(state, VisualState.ACTIVE)

if __name__ == '__main__':
    unittest.main()
