"""
User Penalty Service for Adaptive Compression with TTL Cache.
Tracks token costs and applies time-bound penalties (higher compression) 
to users flagged for WEIRD requests with high token costs.
"""
from typing import Dict, Optional
from collections import defaultdict
import threading
from cachetools import TTLCache
from opentelemetry import trace

# Initialize the tracer for this service
tracer = trace.get_tracer(__name__)


class UserPenaltyService:
    """
    Service that tracks user behavior and applies adaptive compression penalties.
    Uses TTL cache to automatically expire penalties after 1 hour.
    
    Logic:
    1. Track token costs for each request
    2. Calculate running average of token costs
    3. When a request is flagged as "WEIRD" (invalid) AND token cost > average:
       - Flag the user fingerprint for higher compression (stored in TTL cache)
    4. Future requests from flagged users use higher compression aggressiveness
    5. Penalties automatically expire after TTL (1 hour)
    """
    
    def __init__(self, base_compression: float = 0.5, penalty_compression: float = 0.8, ttl_seconds: int = 3600):
        """
        Initialize the penalty service with TTL cache.
        
        Args:
            base_compression: Default compression aggressiveness (0.5)
            penalty_compression: Higher compression for flagged users (0.8)
            ttl_seconds: Time-to-live for penalty flags in seconds (3600 = 1 hour)
        """
        self.base_compression = base_compression
        self.penalty_compression = penalty_compression
        
        # Thread-safe storage
        self._lock = threading.Lock()
        
        # TTL Cache for flagged users (automatically expires after TTL)
        # maxsize=1000, ttl=3600 (1 hour)
        self._flagged_users: TTLCache[str, bool] = TTLCache(maxsize=1000, ttl=ttl_seconds)
        
        # Track token costs (running list for average calculation)
        self._token_costs: list[int] = []
        
        # Track per-user token costs (for potential per-user averages in future)
        self._user_token_costs: Dict[str, list[int]] = defaultdict(list)
        
        # Running average calculation (for efficiency)
        self._total_tokens = 0
        self._request_count = 0
    
    def get_compression_for_user(self, fingerprint: str) -> float:
        """
        Get the compression aggressiveness for a user fingerprint.
        Returns higher compression if user is flagged (checks TTL cache).
        
        Args:
            fingerprint: User fingerprint (user_id|ip_address)
            
        Returns:
            Compression aggressiveness (base or penalty level)
        """
        with self._lock:
            is_flagged = self._flagged_users.get(fingerprint, False)
            
            if is_flagged:
                with tracer.start_as_current_span("EcoShield_Penalty_Applied") as span:
                    span.set_attribute("user.fingerprint", fingerprint)
                    span.set_attribute("compression.aggressiveness", self.penalty_compression)
                    span.set_attribute("penalty.reason", "flagged_for_weird_high_cost")
                    span.set_attribute("penalty.ttl_remaining", "check_cache")
                return self.penalty_compression
            else:
                return self.base_compression
    
    def record_token_cost(self, fingerprint: str, token_cost: int):
        """
        Record token cost for a request to calculate running average.
        
        Args:
            fingerprint: User fingerprint
            token_cost: Total tokens used (input + output)
        """
        with self._lock:
            # Update running average
            self._token_costs.append(token_cost)
            self._total_tokens += token_cost
            self._request_count += 1
            
            # Track per-user costs
            self._user_token_costs[fingerprint].append(token_cost)
            
            # Limit history size (keep last 1000 requests for average)
            if len(self._token_costs) > 1000:
                old_cost = self._token_costs.pop(0)
                self._total_tokens -= old_cost
                self._request_count -= 1
    
    def flag_user_for_penalty(self, fingerprint: str, token_cost: int):
        """
        Flag a user fingerprint for penalty (higher compression) if they had WEIRD request 
        with token cost above average. Flag is stored in TTL cache (expires after 1 hour).
        
        This should be called when:
        - Evaluator says "WEIRD" (invalid) OR entropy > 6.5
        - AND token_cost > running_average
        
        Args:
            fingerprint: User fingerprint (user_id|ip_address)
            token_cost: Token cost of the WEIRD request
        """
        with self._lock:
            # Calculate current average
            avg_cost = self.get_average_token_cost()
            
            # Flag user if cost is above average (stored in TTL cache)
            if avg_cost and token_cost > avg_cost:
                self._flagged_users[fingerprint] = True
                
                with tracer.start_as_current_span("EcoShield_User_Flagged") as span:
                    span.set_attribute("user.fingerprint", fingerprint)
                    span.set_attribute("token_cost", token_cost)
                    span.set_attribute("average_token_cost", avg_cost)
                    span.set_attribute("penalty.compression", self.penalty_compression)
                    span.set_attribute("penalty.ttl_seconds", 3600)
                    span.set_attribute("penalty.reason", "weird_request_above_average_cost")
    
    def get_average_token_cost(self) -> Optional[float]:
        """
        Get the running average token cost across all requests.
        
        Returns:
            Average token cost, or None if no requests yet
        """
        with self._lock:
            if self._request_count == 0:
                return None
            return self._total_tokens / self._request_count
    
    def get_user_stats(self, fingerprint: str) -> Dict:
        """
        Get statistics for a specific user fingerprint.
        
        Args:
            fingerprint: User fingerprint
            
        Returns:
            Dict with user statistics
        """
        with self._lock:
            is_flagged = self._flagged_users.get(fingerprint, False)
            user_costs = self._user_token_costs.get(fingerprint, [])
            avg_cost = self.get_average_token_cost()
            
            return {
                "is_flagged": is_flagged,
                "compression_level": self.penalty_compression if is_flagged else self.base_compression,
                "request_count": len(user_costs),
                "average_token_cost": sum(user_costs) / len(user_costs) if user_costs else 0,
                "global_average": avg_cost,
                "penalty_ttl_seconds": 3600
            }
    
    def unflag_user(self, fingerprint: str):
        """
        Remove penalty flag from a user fingerprint (for admin/testing purposes).
        
        Args:
            fingerprint: User fingerprint
        """
        with self._lock:
            self._flagged_users.pop(fingerprint, None)
