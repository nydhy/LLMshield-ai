# Gemini Migration Impact Analysis

## What Breaks Without Gemini Instrumentation

### ✅ **STILL WORKS** (Manual Tracing)
- All your **manual spans** will continue working:
  - `EcoShield_Request` (main span)
  - `EcoShield_LLM_TieBreaker` 
  - `EcoShield_Sieve_Process`
  - `EcoShield_Penalty_Applied`
  - `EcoShield_LLM_Evaluator`

- **FastAPI instrumentation** still works (request/response tracing)
- **Custom attributes** still work (entropy, threat_level, tokens, etc.)
- **Phoenix UI** still works (you can view all traces)
- **Application functionality** - everything works, just less detailed tracing

### ❌ **BREAKS** (Auto-Instrumentation)
- **Automatic child span** for `client.chat.completions.create()` call
  - Currently: Creates a child span showing OpenAI API details
  - Without: The API call won't appear as a child span in Phoenix
  
- **Automatic token usage tracking** in traces
  - Currently: OpenAIInstrumentor tracks tokens automatically
  - Without: You still extract tokens manually (line 317-322), but they won't appear in the auto-generated span

### 📊 **Impact Assessment: LOW**

**Why it's low impact:**
1. ✅ You already manually extract token usage (lines 317-322)
2. ✅ You already set attributes manually (lines 320-322)
3. ✅ Your main observability is via manual spans (which still work)
4. ✅ Application functionality is unaffected

**What you'll lose:**
- A detailed child span in Phoenix showing the raw OpenAI API call
- Automatic request/response logging for the LLM call
- Some convenience in Phoenix UI (less drill-down capability)

## Solution: Add Gemini Instrumentation

### Option 1: Use Google GenAI SDK Instrumentation (Recommended)

If you switch to Google's GenAI SDK:

```bash
pip install openinference-instrumentation-google-genai
```

Then in `app/main.py`:

```python
# Replace OpenAIInstrumentor with Google GenAI instrumentation
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

# 3. Auto-Instrument Google GenAI (Gemini)
GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)
```

### Option 2: Manual Wrapper (If No Instrumentation Available)

If there's no instrumentation library, wrap the Gemini call manually:

```python
# Manual wrapper for Gemini API call
with tracer.start_as_current_span("Gemini_API_Call") as gemini_span:
    gemini_span.set_attribute("openinference.span.kind", "LLM")
    gemini_span.set_attribute("llm.vendor", "google")
    gemini_span.set_attribute("llm.model", model_name)
    
    response = client.models.generate_content(...)
    
    # Extract token usage (Gemini format)
    if hasattr(response, 'usage_metadata'):
        usage = response.usage_metadata
        gemini_span.set_attribute("llm.token_count.total", usage.total_token_count)
        gemini_span.set_attribute("llm.token_count.prompt", usage.prompt_token_count)
        gemini_span.set_attribute("llm.token_count.completion", usage.candidates_token_count)
```

## Current Code (Lines to Watch)

### Main API Call (Line ~250)
```python
response = client.chat.completions.create(**body)
```
- **Currently**: Auto-instrumented by `OpenAIInstrumentor`
- **Without instrumentation**: Still works, but no auto child span

### Token Tracking (Lines 317-322)
```python
if hasattr(response, 'usage') and response.usage:
    total_tokens = response.usage.total_tokens
    penalty_service.record_token_cost(fingerprint, total_tokens)
    main_span.set_attribute("openai.total_tokens", total_tokens)
    main_span.set_attribute("openai.prompt_tokens", response.usage.prompt_tokens)
    main_span.set_attribute("openai.completion_tokens", response.usage.completion_tokens)
```
- **Still works**: You're manually extracting and setting attributes
- **Just change**: Update attribute names from `openai.*` to `gemini.*` or `llm.*`

## Recommendation

**Migration is SAFE** - Your manual tracing is robust and will continue working.

**Best practice**: Add manual wrapper around Gemini call (Option 2) to maintain the same level of observability, even if official instrumentation isn't available.
