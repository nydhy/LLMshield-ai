"""
Identity and Fingerprinting Utilities.
Extracts dual-identity (X-User-ID + IP) to create unique fingerprints.
"""
from fastapi import Request


def extract_user_fingerprint(request: Request) -> str:
    """
    Extract dual-identity fingerprint from request.
    Combines X-User-ID header and leftmost IP from X-Forwarded-For.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Unique fingerprint string: "user_id|ip_address"
    """
    # Extract X-User-ID header
    user_id = request.headers.get("X-User-ID", "").strip()
    
    # Extract leftmost IP from X-Forwarded-For (first IP in chain)
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
        # Take the leftmost (original client) IP
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        # Fallback to direct client IP
        ip_address = request.client.host if request.client else "unknown"
    
    # Create fingerprint: "user_id|ip_address"
    # If no user_id, use just IP
    if user_id:
        fingerprint = f"{user_id}|{ip_address}"
    else:
        fingerprint = f"anonymous|{ip_address}"
    
    return fingerprint
