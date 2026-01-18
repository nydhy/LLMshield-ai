# Timeout Configuration Guide

## Problem
API timeouts occur when Gemini API calls take longer than the default timeout (typically 10-20 seconds for complex requests). This guide shows how to prevent timeouts at multiple levels.

## Solutions

### 1. Client-Side Timeouts (Python requests)

**Fix in `attack_sim.py` and other scripts:**

```python
# Add explicit timeout (seconds)
response = requests.post(url, json=payload, timeout=60)
```

**Timeout values:**
- **Simple requests**: `timeout=30` (30 seconds)
- **Complex requests**: `timeout=60` (60 seconds)
- **Attack simulations**: `timeout=90` (90 seconds for large payloads)

**Why:**
- Gemini API calls typically take 2-5 seconds
- With compression, evaluation, and processing: 5-15 seconds
- Large payloads or complex prompts: 15-30+ seconds

### 2. Server-Side Timeouts (FastAPI/Uvicorn)

**Default FastAPI/Uvicorn timeouts:**
- No default request timeout (waits indefinitely)
- Consider adding timeout middleware for production

**To add timeout middleware:**

```python
# In app/main.py
from starlette.middleware.timeout import TimeoutMiddleware

app.add_middleware(TimeoutMiddleware, timeout=120.0)  # 2 minutes
```

### 3. Gemini API Client Timeouts

**The `google-genai` SDK has its own timeouts:**

```python
# Check SDK documentation for timeout configuration
# Most SDKs default to 60 seconds
gemini_client = genai.Client(api_key=settings.gemini_api_key)
```

### 4. External Service Timeouts (Sieve Service)

**Already configured in `app/services/sieve.py`:**

```python
response = requests.post(self.url, json=payload, headers=headers, timeout=10)
```

**Consider increasing if compression takes longer:**
```python
timeout=30  # Increase for large payloads
```

## Recommendations

### For Development/Testing:
```python
# Scripts (attack_sim.py, test scripts)
timeout=60  # 60 seconds is safe for most scenarios

# Simple API calls
timeout=30  # 30 seconds for quick tests
```

### For Production:
```python
# Client applications
timeout=60  # Balance between user experience and reliability

# Server-side
timeout=120  # Allow more time for complex processing
```

## Updated Files

I've updated `scripts/attack_sim.py` to include timeouts:
- Scenario 1: `timeout=60` (normal request)
- Scenario 2: `timeout=90` (large attack payload)

## Testing

After updating timeouts, run:
```bash
python scripts/attack_sim.py
```

If you still see timeouts:
1. Check server logs: `tail -f /tmp/llmshield.log`
2. Verify Gemini API is responding
3. Increase timeout values incrementally
4. Check network connectivity

## Best Practices

1. **Always set explicit timeouts** - Don't rely on defaults
2. **Use different timeouts for different scenarios** - Simple vs complex requests
3. **Log timeout errors** - Helps diagnose issues
4. **Handle timeout exceptions** - Graceful error handling

Example:
```python
try:
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
except requests.exceptions.Timeout:
    print("Request timed out after 60 seconds")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```
