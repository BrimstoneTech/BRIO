"""
BRIM Monitoring & Watchdog Module (brim_monitoring.py)

Purpose: Monitors system health, module liveness, and logs errors.
         Acts as the "Protective Instinct" for Brio's software integrity.
"""

import time
import logging
import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"

@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus = HealthStatus.HEALTHY
    last_heartbeat: float = field(default_factory=time.time)
    error_count: int = 0
    latency_ms: float = 0.0

class SystemWatchdog:
    """
    Monitors all Brio modules. 
    If a module stops heartbeat or spikes in errors, the Watchdog alerts brim_main.
    """
    
    def __init__(self, log_file="brio_safeguard.log"):
        self.components: Dict[str, ComponentHealth] = {}
        self.start_time = time.time()
        
        # Configure logging
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
        self.logger = logging.getLogger("BrioWatchdog")

    def register_component(self, name: str):
        self.components[name] = ComponentHealth(name=name)
        self.logger.info(f"Registered component for monitoring: {name}")

    def heartbeat(self, name: str, latency: float = 0.0):
        """Modules call this to signal they are alive"""
        if name in self.components:
            comp = self.components[name]
            comp.last_heartbeat = time.time()
            comp.latency_ms = latency
            comp.status = HealthStatus.HEALTHY
        else:
            self.register_component(name)

    def log_error(self, name: str, error_msg: str, severity: str = "ERROR"):
        """Record a failure event"""
        if name in self.components:
            self.components[name].error_count += 1
            if self.components[name].error_count > 5:
                self.components[name].status = HealthStatus.DEGRADED
        
        log_msg = f"[{name}] {error_msg}"
        if severity == "CRITICAL":
            self.logger.critical(log_msg)
            if name in self.components:
                self.components[name].status = HealthStatus.CRITICAL
        else:
            self.logger.error(log_msg)

    def get_system_status(self) -> Dict:
        """Determines overall system health"""
        status_report = {
            "overall": HealthStatus.HEALTHY.value,
            "uptime": time.time() - self.start_time,
            "details": {}
        }
        
        now = time.time()
        for name, comp in self.components.items():
            # Check for stalled heartbeat (stalled for > 10 seconds)
            if now - comp.last_heartbeat > 10.0:
                comp.status = HealthStatus.FAILED
                self.log_error(name, "Heartbeat Stalled", "CRITICAL")
            
            status_report["details"][name] = {
                "status": comp.status.value,
                "latency": comp.latency_ms,
                "errors": comp.error_count
            }
            
            if comp.status == HealthStatus.FAILED or comp.status == HealthStatus.CRITICAL:
                status_report["overall"] = HealthStatus.CRITICAL.value

        return status_report

    def save_health_snapshot(self, filename="brio_health.json"):
        report = self.get_system_status()
        with open(filename, 'w') as f:
            json.dump(report, f, indent=4)
