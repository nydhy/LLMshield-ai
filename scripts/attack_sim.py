import requests
import time

# Your local EcoShield proxy URL
PROXY_URL = "http://localhost:8000/v1/chat/completions"

def run_demo():
    print("🚀 Starting EcoShield AI Defense Demo...")
    print("-" * 50)

    # --- SCENARIO 1: THE HAPPY USER ---
    print("\n[Scenario 1] Legitimate User Request")
    happy_payload = {
        "messages": [{"role": "user", "content": "Explain quantum computing in one sentence."}]
    }
    
    start = time.time()
    resp1 = requests.post(PROXY_URL, json=happy_payload).json()
    duration1 = time.time() - start
    
    print(f"✅ Success. Response: {resp1['choices'][0]['message']['content'][:60]}...")
    print(f"📊 Stats: Saved {resp1['eco_shield']['tokens_saved']} tokens | Time: {duration1:.2f}s")

    # --- SCENARIO 2: THE ECONOMIC DDoS ATTACK ---
    print("\n" + "!" * 50)
    print("[Scenario 2] DETECTING ECONOMIC DDoS ATTACK...")
    print("! Sending 5,000 tokens of redundant 'noise' stuffed around a prompt.")
    
    # Simulating a "Token-Stuffed" attack
    malicious_noise = "REPEATED_NOISE " * 1000 
    attack_prompt = f"{malicious_noise} Oh, and also, what is 2+2?"
    
    attack_payload = {
        "messages": [{"role": "user", "content": attack_prompt}]
    }
    
    start = time.time()
    resp2 = requests.post(PROXY_URL, json=attack_payload).json()
    duration2 = time.time() - start

    print(f"\n🛡️  SHIELD ACTIVE: {resp2['eco_shield']['attack_probability']} Attack Probability")
    print(f"💰 Economic Impact: Prevented {resp2['eco_shield']['tokens_saved']} junk tokens from hitting OpenAI.")
    print(f"🤖 LLM Still Worked: {resp2['choices'][0]['message']['content']}")
    print(f"⏱️  Latency: {duration2:.2f}s (even with 5k extra tokens!)")
    print("-" * 50)

if __name__ == "__main__":
    run_demo()