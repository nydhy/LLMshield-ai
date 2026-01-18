#!/bin/bash

# Quick test script for LLMshield Streamlit Demo
# Usage: ./test_demo.sh

set -e

API_URL="http://localhost:8000/v1/chat/completions"
HEALTH_URL="http://localhost:8000/"

echo "🧪 Testing LLMshield Backend for Streamlit Demo"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo "[1/5] Testing Health Endpoint..."
if curl -s -f "$HEALTH_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend is running${NC}"
    curl -s "$HEALTH_URL" | python3 -m json.tool
else
    echo -e "${RED}❌ Backend is NOT running${NC}"
    echo "Please start the backend first:"
    echo "  python -m app.main"
    exit 1
fi

echo ""
sleep 1

# Test 2: Normal Request
echo "[2/5] Testing Normal Request (should succeed)..."
RESPONSE=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What is 2+2?"}]}')

THREAT_LEVEL=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('llm_shield', {}).get('threat_level', 'UNKNOWN'))" 2>/dev/null || echo "ERROR")

if [ "$THREAT_LEVEL" = "CLEAN" ]; then
    echo -e "${GREEN}✅ Normal request successful${NC}"
    echo "  Threat Level: $THREAT_LEVEL"
    TOKENS_SAVED=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('llm_shield', {}).get('tokens_saved', 0))" 2>/dev/null || echo "0")
    echo "  Tokens Saved: $TOKENS_SAVED"
else
    echo -e "${YELLOW}⚠️  Unexpected result: Threat Level = $THREAT_LEVEL${NC}"
fi

echo ""
sleep 1

# Test 3: High Entropy (should be blocked)
echo "[3/5] Testing High Entropy Attack (should be blocked)..."
HIGH_ENTROPY=$(python3 -c "import random, string; print(''.join(random.choices(string.ascii_letters + string.digits, k=500)))")
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"$HIGH_ENTROPY What is 2+2?\"}]}")

if [ "$HTTP_CODE" = "400" ]; then
    echo -e "${GREEN}✅ High entropy attack correctly blocked (400)${NC}"
else
    echo -e "${RED}❌ Expected 400, got $HTTP_CODE${NC}"
fi

echo ""
sleep 1

# Test 4: Token Stuffing (should compress)
echo "[4/5] Testing Token Stuffing Attack (should compress)..."
TOKEN_STUFFING="REPEATED_NOISE $(seq -f 'noise-%g' 1 500 | tr '\n' ' ')"
RESPONSE2=$(curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"$TOKEN_STUFFING What is 2+2?\"}]}")

ATTACK_PROB=$(echo "$RESPONSE2" | python3 -c "import sys, json; print(json.load(sys.stdin).get('llm_shield', {}).get('attack_probability', 'UNKNOWN'))" 2>/dev/null || echo "ERROR")
TOKENS_SAVED2=$(echo "$RESPONSE2" | python3 -c "import sys, json; print(json.load(sys.stdin).get('llm_shield', {}).get('tokens_saved', 0))" 2>/dev/null || echo "0")

if [ "$ATTACK_PROB" = "HIGH" ] || [ "$TOKENS_SAVED2" -gt 100 ]; then
    echo -e "${GREEN}✅ Token stuffing detected and compressed${NC}"
    echo "  Attack Probability: $ATTACK_PROB"
    echo "  Tokens Saved: $TOKENS_SAVED2"
else
    echo -e "${YELLOW}⚠️  Compression may not be optimal${NC}"
    echo "  Attack Probability: $ATTACK_PROB"
    echo "  Tokens Saved: $TOKENS_SAVED2"
fi

echo ""
sleep 1

# Test 5: Check Response Format
echo "[5/5] Verifying Response Format..."
HAS_LLM_SHIELD=$(echo "$RESPONSE" | python3 -c "import sys, json; print('llm_shield' in json.load(sys.stdin))" 2>/dev/null || echo "False")

if [ "$HAS_LLM_SHIELD" = "True" ]; then
    echo -e "${GREEN}✅ Response includes llm_shield metadata${NC}"
else
    echo -e "${RED}❌ Response missing llm_shield metadata${NC}"
fi

echo ""
echo "================================================"
echo -e "${GREEN}✅ Backend tests complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Start Streamlit: streamlit run streamlit_app.py"
echo "  2. Open browser to: http://localhost:8501"
echo "  3. Try the demo scenarios in the sidebar"
echo ""
