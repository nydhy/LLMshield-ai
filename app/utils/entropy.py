"""
Shannon Entropy Calculation for Prompt Analysis.
Used to detect random/nonsensical content and potential attacks.
"""
import math
from collections import Counter


def calculate_shannon_entropy(text: str) -> float:
    """
    Calculate Shannon entropy (H) of a text string.
    Higher entropy indicates more randomness/unpredictability.
    
    Formula: H = -Σ(p(x) * log2(p(x)))
    where p(x) is the probability of character x
    
    Args:
        text: Input text to analyze
        
    Returns:
        Shannon entropy value (0 to log2(alphabet_size))
    """
    if not text or len(text) == 0:
        return 0.0
    
    # Count character frequencies
    char_counts = Counter(text)
    text_length = len(text)
    
    # Calculate entropy
    entropy = 0.0
    for count in char_counts.values():
        probability = count / text_length
        if probability > 0:
            entropy -= probability * math.log2(probability)
    
    return entropy


def classify_by_entropy(entropy: float) -> str:
    """
    Classify prompt threat level based on entropy score.
    
    Thresholds:
    - H > 6.5: WEIRD (Block) - Very random, likely attack/noise
    - 5.5 < H <= 6.5: SUSPICIOUS (LLM-Judge/Penalty) - Unusual but not clearly malicious
    - H <= 5.5: CLEAN - Normal text
    
    Args:
        entropy: Shannon entropy value
        
    Returns:
        Threat level: "HIGH", "SUSPICIOUS", or "CLEAN"
    """
    if entropy > 6.5:
        return "HIGH"  # WEIRD - Block
    elif entropy > 5.5:
        return "SUSPICIOUS"  # Needs LLM judge
    else:
        return "CLEAN"  # Normal
