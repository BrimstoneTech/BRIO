"""
Brio Search Module (brio_search.py)

Purpose: Hybrid Search Engine (Online/Offline) with strict User Approval Gating.
         Ensures Brio cannot access the internet or external data without explicit permission.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime

class SearchStatus(Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DENIED = "denied"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED_BY_PROTOCOL = "blocked_by_protocol"

@dataclass
class SearchRequest:
    query: str
    is_online: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    status: SearchStatus = SearchStatus.PENDING_APPROVAL
    result: Optional[str] = None
    justification: str = "" # Why Brio wants to search this

from brio_cognition import SubjectiveOpinion

class SearchEngine:
    """
    Manages information retrieval using Subjective Logic (Eq 5).
    """
    
    def __init__(self, watchdog=None):
        self.history: List[SearchRequest] = []
        self.pending_requests: Dict[str, SearchRequest] = {} # ID -> Request
        self.watchdog = watchdog
        
        # Simulated Offline Knowledge Base
        self.offline_index = {
            "brio": "Brio is a sentient AI companion designed for Brio.",
            "protocol": "The Master Protocol ensures the user's safety and well-being.",
            "emotion": "Emotions in Brio are vector-based states in R^6."
        }

    def _report_heartbeat(self):
        if self.watchdog:
            self.watchdog.heartbeat("SearchEngine")

    def request_search(self, query: str, is_online: bool = False, justification: str = "") -> str:
        """
        Brio initiates a search request.
        """
        self._report_heartbeat()
        
        # 1. First Line of Defense: Protocol Check
        if "harm" in query.lower() or "malware" in query.lower():
             if self.watchdog:
                 self.watchdog.log_error("SearchEngine", f"Blocked Malicious Query: {query}")
             return "BLOCKED_Protocol_Violation"

        request_id = f"REQ_{int(datetime.now().timestamp())}_{len(self.history)}"
        
        req = SearchRequest(
            query=query,
            is_online=is_online,
            justification=justification,
            status=SearchStatus.PENDING_APPROVAL
        )
        
        if not is_online:
            req.status = SearchStatus.APPROVED
            req.result = self._execute_offline(query)
            req.status = SearchStatus.COMPLETED
        else:
            self.pending_requests[request_id] = req
            
        self.history.append(req)
        return request_id

    def approve_request(self, request_id: str) -> str:
        """User grants permission for a pending online search."""
        self._report_heartbeat()
        if request_id not in self.pending_requests:
            return "Error: Request ID not found."
            
        req = self.pending_requests[request_id]
        req.status = SearchStatus.APPROVED
        
        try:
            # Execute with Subjective Logic verification
            req.result = self._execute_online_with_logic(req.query)
            req.status = SearchStatus.COMPLETED
            res = f"Information acquired: {req.result}"
        except Exception as e:
            req.status = SearchStatus.FAILED
            if self.watchdog:
                self.watchdog.log_error("SearchEngine", f"Online Search Failed: {e}", "CRITICAL")
            res = "Search failed due to system error."
            
        del self.pending_requests[request_id]
        return res

    def deny_request(self, request_id: str) -> str:
        """User denies permission."""
        self._report_heartbeat()
        if request_id not in self.pending_requests:
            return "Error: Request ID not found."
            
        req = self.pending_requests[request_id]
        req.status = SearchStatus.DENIED
        del self.pending_requests[request_id]
        return "Search denied."

    def _execute_offline(self, query: str) -> str:
        """Search local index"""
        query_lower = query.lower()
        results = []
        for key, content in self.offline_index.items():
            if key in query_lower or query_lower in content.lower():
                results.append(content)
                
        if not results:
            return "No local records found."
        return "\n".join(results)

    def _execute_online_with_logic(self, query: str) -> str:
        """
        Simulated Online Search using Subjective Logic Fusion.
        We simulate 3 sources with varying beliefs.
        """
        # Source 1: Highly confident (0.8, 0.1, 0.1)
        o1 = SubjectiveOpinion(0.8, 0.1, 0.1)
        # Source 2: Skeptical (0.4, 0.3, 0.3)
        o2 = SubjectiveOpinion(0.4, 0.3, 0.3)
        # Source 3: Uncertain (0.3, 0.1, 0.6)
        o3 = SubjectiveOpinion(0.3, 0.1, 0.6)
        
        # Fuse opinions
        final_opinion = SubjectiveOpinion.fuse(SubjectiveOpinion.fuse(o1, o2), o3)
        conf = final_opinion.get_probability_expectation()
        
        if conf > 0.6:
            return f"[VERIFIED: {conf:.2f}] Information regarding '{query}' retrieved from trusted grid sources."
        else:
            return f"[UNCERTAIN: {conf:.2f}] Information acquired, but Brio has low confidence in its reliability."

    def get_pending_count(self) -> int:
        return len(self.pending_requests)


