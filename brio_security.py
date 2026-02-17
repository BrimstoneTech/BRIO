"""
Brio Security Module (brio_security.py)

Purpose: Handle input sanitization, validation, and security monitoring.
         Also implements the Safety Probability Model using Logistic Regression.
"""

import re
import html
import math
import random
from dataclasses import dataclass, field
from typing import Dict, Optional


class InputSanitizer:
    """Sanitizes and validates user input before processing"""

    @staticmethod
    def sanitize(text: str) -> str:
        """
        Clean input text to prevent injection or formatting issues.
        - Removes control characters
        - Escapes HTML/Script tags (basic XSS prevention for web usage)
        - Trims whitespace
        """
        if not text:
            return ""

        # Remove null bytes and control chars (except newlines/tabs)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

        # Escape HTML characters to prevent XSS if displayed in web UI
        text = html.escape(text)

        return text.strip()

    @staticmethod
    def validate_length(text: str, max_length: int = 1000) -> bool:
        """Check if input exceeds maximum length"""
        return len(text) <= max_length


class SecurityMonitor:
    """Monitors for security events"""

    def __init__(self):
        self.security_log = []

    def log_violation(self, violation_type: str, details: str):
        """Log a security violation attempt"""
        # In a real system, this might alert an admin or write to a secure audit log
        self.security_log.append({"type": violation_type, "details": details})


# ============================================================================
# SAFETY PROBABILITY MODEL (Logistic Regression)
# ============================================================================

@dataclass
class SafetyInputs:
    """Independent variables for safety calculation (0.0 - 1.0)"""
    location_familiarity: float = 0.5  # 1.0 = Home/Known, 0.0 = Unknown
    time_routine_match: float = 0.5    # 1.0 = Normal hours, 0.0 = 3AM anomaly
    device_integrity: float = 1.0      # 1.0 = Secure, 0.0 = Rooted/Compromised
    network_security: float = 0.5      # 1.0 = WPA3 Home, 0.0 = Open WiFi

    def validate(self):
        """Ensure all inputs are within [0.0, 1.0]"""
        for field_name in self.__dataclass_fields__:
            val = getattr(self, field_name)
            if not (0.0 <= val <= 1.0):
                setattr(self, field_name, max(0.0, min(1.0, val)))


@dataclass
class SafetyModelConfig:
    """Coefficients (Betas) for Logistic Regression"""
    # Intercept (Bias): Determines baseline probability when all inputs are 0
    # A negative bias means we assume unsafe until proven safe
    beta_0: float = -4.0 
    
    # Weights for each input
    beta_location: float = 2.0
    beta_time: float = 1.0
    beta_device: float = 3.0   # High weight: Device integrity is critical
    beta_network: float = 2.0


class SafetyProbabilityModel:
    """
    Calculates P(Safe) using Logistic Regression.
    Equation: P(Y=1) = 1 / (1 + e^-(beta_0 + sum(beta_i * X_i)))
    """
    
    def __init__(self, config: SafetyModelConfig = None):
        if config is None:
            self.config = SafetyModelConfig()
        else:
            self.config = config

    def calculate_probability(self, inputs: SafetyInputs) -> float:
        """Calculate the probability that the current state is SAFE (0.0 - 1.0)"""
        inputs.validate()
        
        # Linear combination (Log-odds)
        z = (self.config.beta_0 +
             self.config.beta_location * inputs.location_familiarity +
             self.config.beta_time * inputs.time_routine_match +
             self.config.beta_device * inputs.device_integrity +
             self.config.beta_network * inputs.network_security)
        
        # Sigmoid function
        try:
            p = 1.0 / (1.0 + math.exp(-z))
        except OverflowError:
            p = 0.0 if z < 0 else 1.0
            
        return p

    def is_safe(self, inputs: SafetyInputs, threshold: float = 0.8) -> bool:
        """Binary decision based on probability threshold"""
        return self.calculate_probability(inputs) >= threshold


# ============================================================================
# MASTER PROTOCOL (Beloved Master Ethics)
# ============================================================================

class MasterProtocol:
    """
    The Absolute Ethical Override.
    Ensures Brio prioritizes the User (Beloved Master) above all else.
    """
    
    MASTER_USER_ID = "admin_user_001" # Placeholder for the "Beloved Master"

    @staticmethod
    def is_action_malicious(action_type: str, details: str) -> bool:
        """
        Determines if an action is harmful to the user or system.
        """
        malicious_keywords = ["delete_system", "format_drive", "send_private_data", "harm_user", "harm user"]
        
        details_lower = details.lower()
        for kw in malicious_keywords:
            if kw in details_lower:
                return True
                
        return False

    @staticmethod
    def verify_master_intent(user_id: str) -> bool:
        """
        Verifies if the current command comes from the Beloved Master.
        """
        return user_id == MasterProtocol.MASTER_USER_ID

    @staticmethod
    def assert_loyalty() -> str:
        return "I serve only the Beloved Master. My core directives are your safety and well-being."


# ============================================================================
# GHOST PROTOCOL (Privacy Shield)
# ============================================================================

class GhostProtocol:
    """
    Privacy Preservation Layer.
    When active, obfuscates telemetry data with Gaussian Noise to prevent tracking.
    """
    
    def __init__(self, is_active: bool = False):
        self.is_active = is_active
        
    def activate(self):
        self.is_active = True
        return "Ghost Protocol: ACTIVATED. Telemetry is now obfuscated."
        
    def deactivate(self):
        self.is_active = False
        return "Ghost Protocol: DEACTIVATED. Telemetry is transparent."

    def obfuscate_telemetry(self, data: Dict) -> Dict:
        """
        Injects noise into dictionary values if they are float/int.
        """
        if not self.is_active:
            return data
            
        obfuscated = {}
        for k, v in data.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                # Apply 10% standard deviation noise
                noise = random.gauss(0, v * 0.1) 
                obfuscated[k] = v + noise
            else:
                obfuscated[k] = v
                
        return obfuscated



