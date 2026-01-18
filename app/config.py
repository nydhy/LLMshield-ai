# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # These names MUST match the keys in your .env
    gemini_api_key: str
    token_company_key: str
    phoenix_project_name: str = "EcoShield-AI"
    
    # LLM API configuration
    gemini_model: str = "gemini-2.5-flash-lite"  # Default Gemini model (google-genai SDK format)
    evaluator_model: str = "gemini-2.5-flash-lite"  # Model for LLM-as-judge evaluator
    
    # Compression and evaluation settings
    default_compression_aggressiveness: float = 0.5  # Default compression level
    penalty_compression_aggressiveness: float = 0.8  # Higher compression for flagged users (reduced from 0.9)
    penalty_ttl_seconds: int = 3600  # Time-to-live for penalty box (1 hour)
    
    # Entropy thresholds
    entropy_weird_threshold: float = 6.5  # H > 6.5 = WEIRD (Block)
    entropy_suspicious_threshold: float = 5.5  # 5.5 < H <= 6.5 = SUSPICIOUS

    # Tell Pydantic to look for a .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache()
def get_settings():
    """
    Caching ensures we don't re-read the .env file every time 
    we need a setting, keeping your MacBook fast.
    """
    return Settings()