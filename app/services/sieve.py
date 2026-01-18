"""
Sieve Service with System Prompt Pinning and Strict Delimiters.
Only compresses user input, preserving system prompts for security.
"""
import requests
from typing import List, Dict, Optional
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Initialize the tracer for this service
tracer = trace.get_tracer(__name__)

# Strict delimiters for user input
USER_START = "[USER_START]"
USER_END = "[USER_END]"


class SieveService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.thetokencompany.com/v1/compress"

    def separate_messages(self, messages: List[Dict]) -> tuple[List[Dict], Optional[str]]:
        """
        Separate system and user messages for system prompt pinning.
        Only user messages should be compressed to preserve security guardrails.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Tuple of (system_messages, user_content)
        """
        system_messages = []
        user_content = None
        
        for msg in messages:
            role = msg.get("role", "")
            if role == "system":
                system_messages.append(msg)
            elif role == "user":
                # Get the last user message (most recent prompt)
                user_content = msg.get("content", "")
        
        return system_messages, user_content

    def wrap_user_input(self, user_content: str) -> str:
        """
        Wrap user input in strict delimiters to prevent instruction injection.
        
        Args:
            user_content: User's input text
            
        Returns:
            Wrapped user content with delimiters
        """
        return f"{USER_START}\n{user_content}\n{USER_END}"

    def process_prompt(self, messages: List[Dict], aggressiveness: float = 0.5) -> Dict:
        """
        Compresses user prompt using TheTokenCompany's bear-1 model.
        Implements system prompt pinning: only compresses user input, preserves system messages.
        Uses strict delimiters to prevent instruction injection.
        Instrumented with manual spans for Arize Phoenix.
        
        Args:
            messages: List of message dicts (standard chat format)
            aggressiveness: Compression aggressiveness (0.0-1.0)
            
        Returns:
            Dict with compressed messages, token metrics, and FinOps data
        """
        with tracer.start_as_current_span("LLMshield_Sieve_Process") as span:
            span.set_attribute("openinference.span.kind", "CHAIN")
            span.set_attribute("security.layer", "semantic_compression")
            
            # Separate system and user messages
            system_messages, user_content = self.separate_messages(messages)
            
            if not user_content:
                # No user content to compress
                return {
                    "messages": messages,
                    "original_tokens": 0,
                    "compressed_tokens": 0,
                    "saved_tokens": 0,
                    "savings_pct": 0.0,
                    "success": True
                }
            
            # Log original user content snippet
            span.set_attribute("input.value", user_content[:500] + "..." if len(user_content) > 500 else user_content)
            span.set_attribute("system_messages_count", len(system_messages))
            
            # Wrap user input in delimiters
            wrapped_user_input = self.wrap_user_input(user_content)
            
            # Compress only the user input (not system prompts)
            payload = {
                "model": "bear-1",
                "input": wrapped_user_input,
                "compression_settings": {"aggressiveness": aggressiveness}
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(self.url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                # Calculate metrics
                original_tokens = data.get("original_input_tokens", 0)
                compressed_tokens = data.get("output_tokens", 0)
                saved = original_tokens - compressed_tokens
                savings_pct = (saved / original_tokens * 100) if original_tokens > 0 else 0.0
                
                # Get compressed user content (remove delimiters if present)
                compressed_user_content = data.get("output", user_content)
                if USER_START in compressed_user_content:
                    compressed_user_content = compressed_user_content.replace(USER_START, "").replace(USER_END, "").strip()

                # Reconstruct messages: system messages + compressed user message
                compressed_messages = system_messages.copy()
                compressed_messages.append({
                    "role": "user",
                    "content": compressed_user_content
                })

                # Set attributes for Phoenix visualization (FinOps metrics)
                span.set_attribute("output.value", compressed_user_content[:500] + "..." if len(compressed_user_content) > 500 else compressed_user_content)
                span.set_attribute("tokens.original", original_tokens)
                span.set_attribute("tokens.compressed", compressed_tokens)
                span.set_attribute("tokens.saved", saved)
                span.set_attribute("savings_pct", savings_pct)
                span.set_attribute("compression.aggressiveness", aggressiveness)
                
                return {
                    "messages": compressed_messages,
                    "original_tokens": original_tokens,
                    "compressed_tokens": compressed_tokens,
                    "saved_tokens": saved,
                    "savings_pct": savings_pct,
                    "success": True
                }

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                # Fallback: return original messages if compression fails
                return {
                    "messages": messages,
                    "original_tokens": len(user_content.split()) if user_content else 0,  # crude estimate
                    "compressed_tokens": len(user_content.split()) if user_content else 0,
                    "saved_tokens": 0,
                    "savings_pct": 0.0,
                    "success": False
                }