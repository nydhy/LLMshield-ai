# LLMshield AI - Streamlit Demo

Interactive web UI for demonstrating LLMshield AI's multi-layer DDoS protection capabilities.

## Features

The Streamlit demo provides a comprehensive interface to test and visualize:

- **Chat Interface:** Interactive chat with the LLMshield-protected API
- **Security Analysis:** Real-time threat level, entropy scores, and attack probability
- **Token Metrics:** Track tokens saved through compression and total usage
- **Demo Scenarios:** Pre-configured attack scenarios for testing security features
- **Session Statistics:** Aggregate stats across all requests in the session

## Quick Start

### Prerequisites

1. The LLMshield FastAPI server must be running on `http://localhost:8000`
2. Install dependencies (including Streamlit):

```bash
pip install -r requirements.txt
```

### Running the Demo

1. Start the LLMshield FastAPI server (if not already running):

```bash
python -m app.main
# or
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2. In a separate terminal, start the Streamlit app:

```bash
streamlit run streamlit_app.py
```

3. Open your browser to the URL shown in the terminal (typically `http://localhost:8501`)

## Usage Guide

### Basic Chat

1. Type a message in the chat input at the bottom
2. Press Enter or click Send
3. View the response and security analysis in the expandable "Security Analysis & Metrics" section

### Demo Scenarios

The sidebar includes pre-configured demo scenarios:

- **Normal Query:** Legitimate request that should pass all checks
- **High Entropy:** Random character attack that should be blocked
- **Token Stuffing:** Redundant noise attack that should be compressed
- **Suspicious:** Medium-entropy prompt that requires LLM-as-judge evaluation

Click any scenario button to load it into the chat input.

### Configuration Options

In the sidebar, you can configure:

- **Model:** Select the Gemini model to use
- **Temperature:** Control response randomness (0.0-1.0)
- **Max Tokens:** Maximum tokens in the response
- **User ID:** Optional user identifier for tracking (defaults to "demo-user")

### Understanding Security Metrics

**Threat Level:**
- 🟢 **CLEAN** (H ≤ 5.5): Normal text, passed all checks
- 🟡 **SUSPICIOUS** (5.5 < H ≤ 6.5): Unusual but validated by LLM-as-judge
- 🔴 **HIGH** (H > 6.5): WEIRD - Blocked immediately

**Entropy Score:**
Shannon entropy measures randomness. Higher scores indicate more random/suspicious content.

**Tokens Saved:**
The number of tokens saved through compression. High savings indicate token stuffing attacks.

**Attack Probability:**
- **LOW:** Normal request patterns
- **HIGH:** Significant token savings (>80%) indicating potential attack

**Compression Level:**
Aggressiveness of compression applied (0.0-1.0). Higher for flagged users.

**Penalty Applied:**
Indicates if the user is in the "penalty box" with increased compression.

## Security Features Demonstrated

1. **Identity & Fingerprinting:** User tracking via X-User-ID header
2. **Security Scanning:** Regex-based detection of role hijacking and instruction overrides
3. **Entropy Analysis:** Automatic detection of random/gibberish prompts
4. **Adaptive Compression:** System prompt pinning + user input compression
5. **LLM Tie-Breaker:** LLM-as-judge for suspicious cases
6. **Penalty Box:** Time-bound penalties for flagged users
7. **Observability:** All requests traced in Arize Phoenix

## Troubleshooting

### Service Not Running

If you see "LLMshield proxy service is not running":

1. Verify the FastAPI server is running: `curl http://localhost:8000/`
2. Check the server logs for errors
3. Ensure all environment variables (especially API keys) are set in `.env`

### Connection Errors

- Verify the `PROXY_URL` in `streamlit_app.py` matches your server configuration
- Check firewall settings if using a remote server
- Ensure both services are running on the expected ports (8000 for API, 8501 for Streamlit)

### API Errors

- Check that your `.env` file has valid `GEMINI_API_KEY` and `TOKEN_COMPANY_KEY`
- Verify API quotas/credits are available
- Review server logs for detailed error messages

## Architecture

```
┌─────────────────┐
│  Streamlit UI   │  (Browser: http://localhost:8501)
│  streamlit_app  │
└────────┬────────┘
         │ HTTP POST
         ▼
┌─────────────────┐
│  FastAPI Server │  (API: http://localhost:8000)
│   app/main.py   │
└────────┬────────┘
         │
         ├─► Security Layers
         ├─► Compression
         └─► Gemini API
```

## Additional Resources

- **API Documentation:** See `API_CONTRACT.md` for complete API reference
- **Phoenix Tracing:** View detailed traces at `http://localhost:6006`
- **Attack Simulation:** Run `scripts/attack_sim.py` for automated attack scenarios
