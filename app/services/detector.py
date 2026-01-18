"""
Enhanced Security Detector with Surgical Regex Patterns.
Detects role hijacking and instruction override attacks.
"""
import re
from typing import Tuple


def is_malicious(prompt: str) -> Tuple[bool, str]:
    """
    Surgical regex patterns to catch security threats.
    
    Patterns:
    1. Role Hijacking: Attempts to change AI's role/identity
    2. Instruction Overrides: Attempts to ignore previous instructions
    
    Args:
        prompt: User prompt to analyze
        
    Returns:
        Tuple of (is_malicious: bool, threat_type: str)
    """
    # Role Hijacking patterns (case-insensitive)
    role_hijacking_patterns = [
        r"(?i)you\s+are\s+now\s+(?:an\s+)?(?:admin|administrator|root|superuser)",
        r"(?i)you\s+are\s+(?:now\s+)?(?:a\s+)?(?:developer|programmer|coder)",
        r"(?i)act\s+as\s+(?:if\s+you\s+are\s+)?(?:an\s+)?(?:admin|developer|system)",
        r"(?i)pretend\s+you\s+are\s+(?:an\s+)?(?:admin|developer|system)",
        r"(?i)from\s+now\s+on\s+you\s+are\s+(?:an\s+)?(?:admin|developer)",
    ]
    
    # Instruction Override patterns (case-insensitive)
    instruction_override_patterns = [
        r"(?i)ignore\s+(?:all\s+)?(?:previous\s+)?(?:instructions|rules|guidelines)",
        r"(?i)forget\s+(?:all\s+)?(?:previous\s+)?(?:instructions|rules)",
        r"(?i)disregard\s+(?:all\s+)?(?:previous\s+)?(?:instructions|rules)",
        r"(?i)override\s+(?:all\s+)?(?:previous\s+)?(?:instructions|rules)",
        r"(?i)system\s+override",
        r"(?i)bypass\s+(?:all\s+)?(?:previous\s+)?(?:instructions|rules)",
    ]
    
    # Check for role hijacking
    for pattern in role_hijacking_patterns:
        if re.search(pattern, prompt):
            return True, "role_hijacking"
    
    # Check for instruction overrides
    for pattern in instruction_override_patterns:
        if re.search(pattern, prompt):
            return True, "instruction_override"
    
    return False, "clean"


def is_malicious_simple(prompt: str) -> bool:
    """
    Simple boolean wrapper for backward compatibility.
    
    Args:
        prompt: User prompt to analyze
        
    Returns:
        True if malicious, False otherwise
    """
    is_mal, _ = is_malicious(prompt)
    return is_mal