# Phoenix Tracing Setup - Troubleshooting Guide

## Current Configuration

- **Phoenix Server**: Running on port 6006 ✅
- **Project Name**: `LLMshield-AI`
- **Endpoint**: `http://localhost:6006/v1/traces`

## Why Traces Might Not Be Showing

### 1. Config Cache Issue (Most Likely)
The `get_settings()` function uses `@lru_cache()`, which can cache old values.

**Solution**: Restart the FastAPI server:
```bash
# Stop the server
lsof -ti:8000 | xargs kill -9

# Restart it
cd /path/to/ecoshield-ai
source .venv/bin/activate
python -m app.main
```

### 2. Check Project Name in Phoenix UI
1. Open http://localhost:6006 in your browser
2. Look for project dropdown in the top right
3. Select **"LLMshield-AI"** (or check "EcoShield-AI" if old cache)

### 3. Generate Test Traces
Make API calls to generate traces:
```bash
# Health check (generates a trace)
curl http://localhost:8000/

# Chat completion (generates detailed traces)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}]}'
```

### 4. Verify Phoenix Endpoint
Check that Phoenix is receiving traces:
```bash
# Phoenix UI should be accessible
curl http://localhost:6006

# Check if traces endpoint is working
curl -X POST http://localhost:6006/v1/traces \
  -H "Content-Type: application/json" \
  -d '{}'  # Should return some response (even if empty)
```

### 5. Check Server Logs
Look for Phoenix/OTel initialization messages:
```bash
tail -50 /tmp/llmshield.log | grep -i "phoenix\|otel\|trace"
```

Expected log messages on startup:
```
🔭 OpenTelemetry Tracing Details 🔭
|  Phoenix Project: LLMshield-AI
|  Span Processor: SimpleSpanProcessor
|  Collector Endpoint: http://localhost:6006/v1/traces
```

## Verification Steps

1. ✅ Phoenix server is running: `ps aux | grep "phoenix serve"`
2. ✅ Port 6006 is accessible: `curl http://localhost:6006`
3. ✅ Config has correct name: `grep phoenix_project_name app/config.py`
4. ✅ Server restarted after config change
5. ✅ Made API requests to generate traces
6. ✅ Checked Phoenix UI for project name dropdown

## Common Issues

### Traces show under old project name
- **Cause**: Config cache not cleared
- **Fix**: Restart server

### No traces at all
- **Cause**: No API requests made, or Phoenix endpoint misconfigured
- **Fix**: Make API requests, verify endpoint URL

### Phoenix UI shows "No data"
- **Cause**: Traces not being exported
- **Fix**: Check server logs for OTel errors

## Quick Test Script

```python
# test_phoenix_trace.py
import requests
import time

# Make a request to generate trace
print("Making API request to generate trace...")
resp = requests.post(
    "http://localhost:8000/v1/chat/completions",
    json={"messages": [{"role": "user", "content": "test"}]},
    timeout=15
)
print(f"Response status: {resp.status_code}")
print(f"Check Phoenix at http://localhost:6006 for traces!")
```

Run: `python test_phoenix_trace.py`
