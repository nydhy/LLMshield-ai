"""
Test script to verify Gemini API integration in EcoShield.
"""
import sys
import requests
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_gemini_integration():
    """Test Gemini API through EcoShield endpoint."""
    print("🧪 Testing Gemini Integration in EcoShield")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/v1/chat/completions"
    
    # Test 1: Check if server is running
    print("\n1. Checking if server is running...")
    try:
        resp = requests.get(f"{base_url}/", timeout=5)
        if resp.status_code == 200:
            print(f"   ✅ Server is running: {resp.json()}")
        else:
            print(f"   ❌ Server returned status {resp.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Server is not running. Please start it with: python -m app.main")
        return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 2: Simple chat completion
    print("\n2. Testing simple chat completion...")
    test_payload = {
        "model": "models/gemini-2.5-flash",
        "messages": [
            {"role": "user", "content": "Say 'Hello' in one word."}
        ],
        "max_tokens": 10
    }
    
    try:
        start = time.time()
        resp = requests.post(endpoint, json=test_payload, timeout=30)
        duration = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ Success! Response received in {duration:.2f}s")
            print(f"   💬 Response: {data['choices'][0]['message']['content']}")
            print(f"   🔢 Token usage: {data.get('usage', {}).get('total_tokens', 'N/A')} tokens")
            
            if 'eco_shield' in data:
                print(f"   🛡️  EcoShield stats:")
                print(f"      - Threat level: {data['eco_shield'].get('threat_level', 'N/A')}")
                print(f"      - Tokens saved: {data['eco_shield'].get('tokens_saved', 0)}")
        else:
            print(f"   ❌ Error: Status {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {e}")
    
    # Test 3: Longer conversation
    print("\n3. Testing with system message...")
    test_payload2 = {
        "model": "models/gemini-2.5-flash",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2+2? Answer in one word."}
        ]
    }
    
    try:
        resp = requests.post(endpoint, json=test_payload2, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   ✅ Success!")
            print(f"   💬 Response: {data['choices'][0]['message']['content']}")
        else:
            print(f"   ❌ Error: Status {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Gemini integration test complete!")

if __name__ == "__main__":
    test_gemini_integration()
