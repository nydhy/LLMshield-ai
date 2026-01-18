"""
EcoShield AI Proxy - Enhanced Security Middleware
Multi-layer DDoS protection with entropy analysis, LLM evaluation, and adaptive penalties.
"""
from fastapi import FastAPI, Request, HTTPException
from google import genai
from phoenix.otel import register
import logging
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from app.config import get_settings
from app.services.sieve import SieveService
from app.services.evaluator import PromptEvaluator
from app.services.penalty import UserPenaltyService
from app.services.detector import is_malicious, is_malicious_simple
from app.schemas.shield import ShieldRequest
from app.utils.identity import extract_user_fingerprint
from app.utils.entropy import calculate_shannon_entropy, classify_by_entropy

# 1. Initialize Configuration
settings = get_settings()

# Setup logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. Setup Arize Phoenix Tracing
# This makes your traces show up at http://localhost:6006
tracer_provider = register(
    project_name=settings.phoenix_project_name,
    endpoint="http://localhost:6006/v1/traces",
    auto_instrument=True
)

# 3. Initialize FastAPI & Services
app = FastAPI(title="EcoShield AI Proxy")

# 4. Initialize Gemini client (new google-genai SDK)
gemini_client = genai.Client(api_key=settings.gemini_api_key)
logger.info("Gemini API configured")

# Initialize services
sieve = SieveService(api_key=settings.token_company_key)
evaluator = PromptEvaluator(
    gemini_api_key=settings.gemini_api_key,
    evaluator_model=settings.evaluator_model
)
penalty_service = UserPenaltyService(
    base_compression=settings.default_compression_aggressiveness,
    penalty_compression=settings.penalty_compression_aggressiveness,
    ttl_seconds=settings.penalty_ttl_seconds
)

# 5. Instrument FastAPI to capture request traces
# This ensures all FastAPI requests create trace spans
FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

# Initialize tracer for custom spans
tracer = trace.get_tracer(__name__)

# Setup logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.post("/v1/chat/completions")
async def shielded_chat_proxy(request: Request):
    """
    Enhanced Gemini API endpoint with comprehensive DDoS protection:
    
    1. Identity & Fingerprinting: Extract dual-identity (X-User-ID + IP)
    2. Security Scanning: Surgical regex for role hijacking/instruction overrides
    3. Entropy Analysis: Shannon entropy to detect WEIRD/Suspicious prompts
    4. Adaptive Compression: System prompt pinning + user input compression
    5. LLM Tie-Breaker: For suspicious cases, use LLM-as-judge
    6. Penalty Box: Time-bound penalties (1 hour TTL) for flagged users
    7. Observability: Threat tagging and FinOps metrics in Phoenix
    """
    # Create main request span
    with tracer.start_as_current_span("EcoShield_Request") as main_span:
        try:
            body = await request.json()
            if not body.get("messages"):
                raise HTTPException(status_code=400, detail="No messages found")

            messages = body.get("messages", [])
            if not messages:
                raise HTTPException(status_code=400, detail="No messages found")

            # Get the latest user prompt
            user_message = messages[-1]
            raw_prompt = user_message.get("content", "")
            
            if not raw_prompt:
                raise HTTPException(status_code=400, detail="Empty prompt")

            # --- STEP 1: IDENTITY & FINGERPRINTING ---
            fingerprint = extract_user_fingerprint(request)
            main_span.set_attribute("user.fingerprint", fingerprint)
            
            # --- STEP 2: SECURITY SCANNING (SURGICAL REGEX) ---
            is_mal, threat_type = is_malicious(raw_prompt)
            if is_mal:
                main_span.set_attribute("threat_level", "HIGH")
                main_span.set_attribute("threat_type", threat_type)
                main_span.set_attribute("blocked", True)
                raise HTTPException(
                    status_code=403,
                    detail=f"Security Block: {threat_type.replace('_', ' ').title()} Detected"
                )

            # --- STEP 3: ENTROPY ANALYSIS ---
            entropy = calculate_shannon_entropy(raw_prompt)
            threat_level = classify_by_entropy(entropy)
            main_span.set_attribute("entropy_score", entropy)
            main_span.set_attribute("threat_level", threat_level)
            
            # WEIRD (HIGH): Block immediately
            if threat_level == "HIGH":
                main_span.set_attribute("blocked", True)
                main_span.set_attribute("block_reason", "high_entropy_weird")
                main_span.set_attribute("training_candidate", True)  # Dataset distillation
                
                # Estimate token cost for penalty calculation
                estimated_tokens = len(raw_prompt.split())
                penalty_service.record_token_cost(fingerprint, estimated_tokens)
                penalty_service.flag_user_for_penalty(fingerprint, estimated_tokens)
                
                raise HTTPException(status_code=400, detail="WEIRD")

            # --- STEP 4: GET ADAPTIVE COMPRESSION LEVEL ---
            compression_level = penalty_service.get_compression_for_user(fingerprint)
            main_span.set_attribute("compression.aggressiveness", compression_level)
            main_span.set_attribute("penalty_applied", compression_level > settings.default_compression_aggressiveness)

            # --- STEP 5: SYSTEM PROMPT PINNING + COMPRESSION ---
            # Only compresses user input, preserves system messages
            sieve_result = sieve.process_prompt(messages, aggressiveness=compression_level)
            
            # Extract compressed user content for evaluation
            compressed_messages = sieve_result["messages"]
            compressed_user_content = compressed_messages[-1]["content"] if compressed_messages else raw_prompt
            
            # FinOps metrics
            original_tokens = sieve_result["original_tokens"]
            compressed_tokens = sieve_result["compressed_tokens"]
            saved_tokens = sieve_result["saved_tokens"]
            savings_pct = sieve_result["savings_pct"]
            
            main_span.set_attribute("tokens.original", original_tokens)
            main_span.set_attribute("tokens.compressed", compressed_tokens)
            main_span.set_attribute("tokens.saved", saved_tokens)
            main_span.set_attribute("savings_pct", savings_pct)

            # --- STEP 6: LLM TIE-BREAKER FOR SUSPICIOUS CASES ---
            # If entropy is SUSPICIOUS, use LLM-as-judge for final verdict
            if threat_level == "SUSPICIOUS":
                with tracer.start_as_current_span("EcoShield_LLM_TieBreaker") as tie_span:
                    tie_span.set_attribute("entropy_score", entropy)
                    tie_span.set_attribute("entropy_range", "5.5-6.5")
                    
                    eval_result = evaluator.evaluate(compressed_user_content)
                    tie_span.set_attribute("evaluator.label", eval_result["label"])
                    tie_span.set_attribute("evaluator.score", eval_result["score"])
                    
                    if not eval_result["is_valid"]:
                        # LLM judge says invalid - treat as WEIRD
                        main_span.set_attribute("threat_level", "HIGH")
                        main_span.set_attribute("blocked", True)
                        main_span.set_attribute("block_reason", "llm_judge_invalid")
                        main_span.set_attribute("training_candidate", True)
                        
                        penalty_service.record_token_cost(fingerprint, original_tokens)
                        penalty_service.flag_user_for_penalty(fingerprint, original_tokens)
                        
                        raise HTTPException(status_code=400, detail="WEIRD")
                    else:
                        # LLM judge says valid - proceed but mark as suspicious
                        main_span.set_attribute("threat_level", "SUSPICIOUS")
                        tie_span.set_attribute("verdict", "valid_but_suspicious")
            else:
                # CLEAN: Run standard evaluator for additional validation
                eval_result = evaluator.evaluate(compressed_user_content)
                main_span.set_attribute("evaluator.label", eval_result["label"])
                main_span.set_attribute("evaluator.score", eval_result["score"])
                
                if not eval_result["is_valid"]:
                    main_span.set_attribute("threat_level", "HIGH")
                    main_span.set_attribute("blocked", True)
                    main_span.set_attribute("block_reason", "evaluator_invalid")
                    main_span.set_attribute("training_candidate", True)
                    
                    penalty_service.record_token_cost(fingerprint, original_tokens)
                    penalty_service.flag_user_for_penalty(fingerprint, original_tokens)
                    
                    raise HTTPException(status_code=400, detail="WEIRD")

            # --- STEP 7: CALL GEMINI WITH COMPRESSED MESSAGES ---
            # Only proceed if prompt passed all checks
            
            # Get model name from request or use default
            # Normalize model name: remove 'models/' prefix if present (SDK accepts both but prefers without)
            default_model = settings.gemini_model.replace('models/', '') if settings.gemini_model.startswith('models/') else settings.gemini_model
            requested_model = body.get('model', default_model)
            # Normalize requested model name too
            model_name = requested_model.replace('models/', '') if requested_model.startswith('models/') else requested_model
            
            # Convert messages format to Gemini conversation format
            # Gemini uses a conversation history format
            conversation_parts = []
            for msg in compressed_messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'system':
                    # Gemini doesn't have system messages, prepend to first user message
                    if conversation_parts:
                        conversation_parts[0] = f"System: {content}\n\n{conversation_parts[0]}"
                    else:
                        conversation_parts.append(f"System: {content}")
                elif role == 'user':
                    conversation_parts.append(content)
                elif role == 'assistant':
                    conversation_parts.append(content)
            
            # Prepare generation config
            generation_config = {}
            if 'temperature' in body:
                generation_config['temperature'] = body['temperature']
            if 'max_tokens' in body:
                generation_config['max_output_tokens'] = body['max_tokens']
            if 'top_p' in body:
                generation_config['top_p'] = body['top_p']
            
            # This call is manually traced (Gemini instrumentation may be available)
            response = None
            response_text = ""
            
            with tracer.start_as_current_span("Gemini_API_Call") as gemini_span:
                gemini_span.set_attribute("openinference.span.kind", "LLM")
                gemini_span.set_attribute("llm.vendor", "google")
                gemini_span.set_attribute("llm.model", model_name)
                
                try:
                    # Use new google-genai SDK API
                    # Build contents from conversation parts
                    contents_text = "\n\n".join(conversation_parts)
                    
                    # Prepare config for generation
                    from google.genai import types as genai_types
                    gen_config = None
                    if generation_config:
                        # Only include non-None values to avoid invalid config
                        config_kwargs = {}
                        if generation_config.get('temperature') is not None:
                            config_kwargs['temperature'] = generation_config['temperature']
                        if generation_config.get('max_output_tokens') is not None:
                            config_kwargs['max_output_tokens'] = generation_config['max_output_tokens']
                        if generation_config.get('top_p') is not None:
                            config_kwargs['top_p'] = generation_config['top_p']
                        
                        if config_kwargs:
                            gen_config = genai_types.GenerateContentConfig(**config_kwargs)
                    
                    # Generate content using new SDK
                    # Use model name without 'models/' prefix (official format per SDK docs)
                    response = gemini_client.models.generate_content(
                        model=model_name,  # Format: 'gemini-2.5-flash-lite' (without 'models/' prefix)
                        contents=contents_text,
                        config=gen_config
                    )
                    
                    # Extract text content from response
                    if hasattr(response, 'text'):
                        response_text = response.text
                    elif hasattr(response, 'parts') and response.parts:
                        # Extract text from parts
                        response_text = "".join([part.text for part in response.parts if hasattr(part, 'text')])
                    else:
                        response_text = ""
                    
                except Exception as e:
                    logger.error(f"Gemini API Error: {type(e).__name__}: {str(e)}")
                    gemini_span.record_exception(e)
                    gemini_span.set_status(Status(StatusCode.ERROR, str(e)))
                    main_span.set_attribute("error.type", "api_error")
                    main_span.set_attribute("error.message", str(e))
                    
                    # Check error type and provide appropriate status
                    error_str = str(e).lower()
                    if 'quota' in error_str or 'billing' in error_str or 'credits' in error_str:
                        raise HTTPException(
                            status_code=429,
                            detail=f"Gemini API quota/billing issue: {str(e)}. Please add credits to your account."
                        )
                    elif 'permission' in error_str or 'authentication' in error_str:
                        raise HTTPException(
                            status_code=401,
                            detail=f"Gemini API authentication failed: {str(e)}. Please check your API key."
                        )
                    elif 'rate' in error_str or 'limit' in error_str:
                        raise HTTPException(
                            status_code=429,
                            detail=f"Gemini API rate limit exceeded: {str(e)}"
                        )
                    else:
                        raise HTTPException(
                            status_code=502,
                            detail=f"Gemini API error: {str(e)}"
                        )

            # --- STEP 8: TRACK TOKEN COST FOR SUCCESSFUL REQUESTS ---
            # Extract token usage from Gemini response (new google-genai SDK format)
            total_tokens = 0
            prompt_tokens = 0
            completion_tokens = 0
            
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                total_tokens = usage.total_token_count
                prompt_tokens = usage.prompt_token_count
                completion_tokens = usage.candidates_token_count
                penalty_service.record_token_cost(fingerprint, total_tokens)
                
                main_span.set_attribute("gemini.total_tokens", total_tokens)
                main_span.set_attribute("gemini.prompt_tokens", prompt_tokens)
                main_span.set_attribute("gemini.completion_tokens", completion_tokens)
                gemini_span.set_attribute("llm.token_count.total", total_tokens)
                gemini_span.set_attribute("llm.token_count.prompt", prompt_tokens)
                gemini_span.set_attribute("llm.token_count.completion", completion_tokens)
            elif total_tokens == 0:
                # Fallback: estimate tokens if metadata not available
                estimated_tokens = len(response_text.split()) * 1.3  # Rough estimate
                penalty_service.record_token_cost(fingerprint, int(estimated_tokens))

            # --- STEP 9: RETURN RESPONSE + SECURITY STATS ---
            savings_ratio = saved_tokens / (original_tokens or 1)
            attack_probability = "HIGH" if savings_ratio > 0.8 else "LOW"
            
            main_span.set_attribute("blocked", False)
            main_span.set_attribute("attack_probability", attack_probability)
            
            # Convert Gemini response to compatible format (maintaining API compatibility)
            # Generate a response ID (Gemini doesn't provide one in the same format)
            import time
            response_id = f"chatcmpl-{int(time.time() * 1000)}"
            
            # Determine finish reason (new google-genai SDK format)
            finish_reason = "stop"  # default
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    finish_reason_map = {
                        1: "stop",
                        2: "length", 
                        3: "safety",
                        4: "recitation"
                    }
                    finish_reason = finish_reason_map.get(candidate.finish_reason, "stop")
            elif hasattr(response, 'finish_reason'):
                # New SDK might have finish_reason directly on response
                finish_reason = str(response.finish_reason) if response.finish_reason else "stop"
            
            return {
                "id": response_id,
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": response_text
                        },
                        "finish_reason": finish_reason
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                },
                "eco_shield": {
                    "mitigation": "active",
                    "threat_level": threat_level,
                    "entropy_score": round(entropy, 2),
                    "attack_probability": attack_probability,
                    "tokens_saved": saved_tokens,
                    "savings_ratio": f"{savings_ratio:.1%}",
                    "savings_pct": round(savings_pct, 2),
                    "evaluator_validated": True,
                    "evaluator_score": eval_result['score'],
                    "compression_level": compression_level,
                    "user_penalty_applied": compression_level > settings.default_compression_aggressiveness
                }
            }

        except HTTPException:
            # Re-raise HTTP exceptions (like our "WEIRD" error)
            raise
        except Exception as e:
            # Log the full error for debugging
            logger.error(f"Unexpected error in shielded_chat_proxy: {type(e).__name__}: {str(e)}", exc_info=True)
            main_span.record_exception(e)
            main_span.set_status(Status(StatusCode.ERROR, str(e)))
            main_span.set_attribute("error.type", type(e).__name__)
            raise HTTPException(
                status_code=500, 
                detail=f"Internal server error: {type(e).__name__}: {str(e)}"
            )


@app.get("/")
def read_root():
    return {"status": "ecoshield-ai is active 🚀"}


@app.post("/shield")
async def secure_endpoint(request: ShieldRequest):
    """Legacy endpoint for backward compatibility."""
    if is_malicious_simple(request.prompt):
        raise HTTPException(
            status_code=403, 
            detail="Security Block: Malicious Prompt Detected"
        )
    
    return {
        "status": "Safe",
        "processed_prompt": request.prompt,
        "note": "This prompt passed all security filters."
    }


if __name__ == "__main__":
    import uvicorn
    # Run from root as: python -m app.main
    uvicorn.run(app, host="0.0.0.0", port=8000)
