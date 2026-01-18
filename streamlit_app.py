"""
LLMshield AI - Streamlit Demo UI
Interactive demo showcasing multi-layer DDoS protection, entropy analysis, and security features.
"""
import streamlit as st
import requests
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="LLMshield AI Demo",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
PROXY_URL = "http://localhost:8000/v1/chat/completions"
HEALTH_CHECK_URL = "http://localhost:8000/"

# Custom CSS for better styling
st.markdown("""
<style>
    .stAlert {
        padding: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .threat-clean {
        color: #00cc00;
        font-weight: bold;
    }
    .threat-suspicious {
        color: #ffaa00;
        font-weight: bold;
    }
    .threat-high {
        color: #ff0000;
        font-weight: bold;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def check_service_health() -> bool:
    """Check if the LLMshield proxy service is running."""
    try:
        response = requests.get(HEALTH_CHECK_URL, timeout=2)
        return response.status_code == 200
    except:
        return False


def send_chat_request(messages: List[Dict], model: Optional[str] = None, 
                     temperature: float = 0.7, max_tokens: Optional[int] = None,
                     user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Send a chat completion request to the LLMshield proxy.
    
    Returns:
        Response dictionary with choices, usage, and llm_shield data
    """
    payload = {
        "messages": messages,
        "temperature": temperature,
    }
    
    if model:
        payload["model"] = model
    if max_tokens:
        payload["max_tokens"] = max_tokens
    
    headers = {
        "Content-Type": "application/json"
    }
    if user_id:
        headers["X-User-ID"] = user_id
    
    response = requests.post(PROXY_URL, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        error_data = response.json() if response.content else {"detail": response.text}
        raise Exception(f"API Error ({response.status_code}): {error_data.get('detail', 'Unknown error')}")


def get_threat_class(threat_level: str) -> str:
    """Get CSS class for threat level."""
    threat_classes = {
        "CLEAN": "threat-clean",
        "SUSPICIOUS": "threat-suspicious",
        "HIGH": "threat-high"
    }
    return threat_classes.get(threat_level, "")


def format_entropy_score(entropy: float) -> str:
    """Format entropy score with color coding."""
    if entropy > 6.5:
        return f"🔴 **{entropy:.2f}** (WEIRD - Blocked)"
    elif entropy > 5.5:
        return f"🟡 **{entropy:.2f}** (SUSPICIOUS)"
    else:
        return f"🟢 **{entropy:.2f}** (CLEAN)"


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "security_stats" not in st.session_state:
    st.session_state.security_stats = {
        "total_requests": 0,
        "blocked_requests": 0,
        "total_tokens_saved": 0,
        "total_tokens_used": 0
    }

# Main title
st.title("🛡️ LLMshield AI Demo")
st.markdown("**Multi-layer DDoS protection with entropy analysis and adaptive compression**")

# Check service health
if not check_service_health():
    st.error("⚠️ **LLMshield proxy service is not running.** Please start the FastAPI server at `http://localhost:8000`")
    st.stop()

# Sidebar for configuration and demo scenarios
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Model selection
    model = st.selectbox(
        "Model",
        ["gemini-2.5-flash-lite", "gemini-2.0-flash-exp", "gemini-1.5-pro"],
        index=0
    )
    
    # Temperature slider
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    
    # Max tokens
    max_tokens = st.number_input("Max Tokens", min_value=1, max_value=4096, value=1000, step=100)
    
    # User ID (for tracking)
    user_id = st.text_input("User ID (optional)", value="demo-user")
    
    st.divider()
    
    st.header("🎭 Demo Scenarios")
    
    # Scenario buttons
    scenario_col1, scenario_col2 = st.columns(2)
    
    with scenario_col1:
        if st.button("✅ Normal Query", use_container_width=True):
            demo_prompt = "Explain quantum computing in one sentence."
            st.session_state.demo_prompt = demo_prompt
            
        if st.button("🔴 High Entropy", use_container_width=True):
            # High entropy attack (random characters)
            import random
            random_chars = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=500))
            demo_prompt = f"{random_chars} What is 2+2?"
            st.session_state.demo_prompt = demo_prompt
            
    with scenario_col2:
        if st.button("💰 Token Stuffing", use_container_width=True):
            # Token stuffing attack
            malicious_noise = "REPEATED_NOISE " * 1000
            demo_prompt = f"{malicious_noise} Oh, and also, what is 2+2?"
            st.session_state.demo_prompt = demo_prompt
            
        if st.button("⚠️ Suspicious", use_container_width=True):
            # Suspicious prompt (medium entropy)
            suspicious_text = "A" * 200 + "B" * 200 + "C" * 200 + " What is the weather?"
            demo_prompt = suspicious_text
            st.session_state.demo_prompt = demo_prompt
    
    st.divider()
    
    # Statistics
    st.header("📊 Session Stats")
    st.metric("Total Requests", st.session_state.security_stats["total_requests"])
    st.metric("Blocked Requests", st.session_state.security_stats["blocked_requests"])
    st.metric("Tokens Saved", st.session_state.security_stats["total_tokens_saved"])
    
    # Clear conversation button
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_history = []
        st.rerun()

# Main chat interface
st.header("💬 Chat Interface")

# Display conversation history
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        security_info = msg.get("security_info")
        
        with st.chat_message(role):
            st.markdown(content)
            
            # Show security info for user messages
            if security_info and role == "user":
                with st.expander("🔒 Security Analysis"):
                    threat_level = security_info.get("threat_level", "UNKNOWN")
                    threat_class = get_threat_class(threat_level)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Threat Level", threat_level)
                    with col2:
                        entropy = security_info.get("entropy_score", 0)
                        st.metric("Entropy Score", f"{entropy:.2f}")
                    with col3:
                        tokens_saved = security_info.get("tokens_saved", 0)
                        st.metric("Tokens Saved", tokens_saved)
                    
                    st.markdown(f"**Attack Probability:** {security_info.get('attack_probability', 'N/A')}")
                    st.markdown(f"**Compression Level:** {security_info.get('compression_level', 0):.2f}")
                    st.markdown(f"**Penalty Applied:** {'Yes' if security_info.get('user_penalty_applied') else 'No'}")

# Chat input
prompt = st.chat_input("Type your message here...")

# Use demo prompt if set
if hasattr(st.session_state, 'demo_prompt'):
    prompt = st.session_state.demo_prompt
    delattr(st.session_state, 'demo_prompt')

if prompt:
    # Add user message to chat
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Show assistant response placeholder
    with st.chat_message("assistant"):
        with st.spinner("Processing request through LLMshield..."):
            try:
                # Prepare messages for API (strip security_info metadata)
                api_messages = []
                for msg in st.session_state.messages[:-1]:  # All except the last (current) message
                    # Always extract only role and content for API
                    api_messages.append({"role": msg["role"], "content": msg["content"]})
                api_messages.append(user_message)
                
                # Send request
                start_time = time.time()
                response = send_chat_request(
                    messages=api_messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    user_id=user_id
                )
                duration = time.time() - start_time
                
                # Extract response content
                assistant_content = response["choices"][0]["message"]["content"]
                
                # Display assistant response
                st.markdown(assistant_content)
                
                # Extract security info
                llm_shield = response.get("llm_shield", {})
                usage = response.get("usage", {})
                
                security_info = {
                    "threat_level": llm_shield.get("threat_level", "UNKNOWN"),
                    "entropy_score": llm_shield.get("entropy_score", 0),
                    "attack_probability": llm_shield.get("attack_probability", "N/A"),
                    "tokens_saved": llm_shield.get("tokens_saved", 0),
                    "savings_ratio": llm_shield.get("savings_ratio", "0%"),
                    "savings_pct": llm_shield.get("savings_pct", 0),
                    "compression_level": llm_shield.get("compression_level", 0),
                    "user_penalty_applied": llm_shield.get("user_penalty_applied", False),
                    "evaluator_validated": llm_shield.get("evaluator_validated", False),
                    "evaluator_score": llm_shield.get("evaluator_score", 0),
                    "response_time": duration
                }
                
                # Update user message with security info
                st.session_state.messages[-1]["security_info"] = security_info
                
                # Add assistant message
                assistant_message = {"role": "assistant", "content": assistant_content}
                st.session_state.messages.append(assistant_message)
                
                # Update statistics
                st.session_state.security_stats["total_requests"] += 1
                st.session_state.security_stats["total_tokens_saved"] += security_info["tokens_saved"]
                st.session_state.security_stats["total_tokens_used"] += usage.get("total_tokens", 0)
                
                # Display security metrics
                with st.expander("🛡️ Security Analysis & Metrics", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        threat_level = security_info["threat_level"]
                        threat_color = {"CLEAN": "🟢", "SUSPICIOUS": "🟡", "HIGH": "🔴"}.get(threat_level, "⚪")
                        st.metric("Threat Level", f"{threat_color} {threat_level}")
                    
                    with col2:
                        entropy = security_info["entropy_score"]
                        st.metric("Entropy Score", f"{entropy:.2f}")
                        st.caption(f"Thresholds: >6.5=HIGH, 5.5-6.5=SUSPICIOUS, <5.5=CLEAN")
                    
                    with col3:
                        tokens_saved = security_info["tokens_saved"]
                        savings_pct = security_info["savings_pct"]
                        st.metric("Tokens Saved", f"{tokens_saved}", delta=f"{savings_pct:.1f}%")
                    
                    with col4:
                        attack_prob = security_info["attack_probability"]
                        st.metric("Attack Probability", attack_prob)
                    
                    # Detailed metrics
                    st.markdown("### 📈 Detailed Metrics")
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        st.write(f"**Compression Level:** {security_info['compression_level']:.2f}")
                        st.write(f"**Penalty Applied:** {'Yes ⚠️' if security_info['user_penalty_applied'] else 'No ✅'}")
                        st.write(f"**Evaluator Validated:** {'Yes' if security_info['evaluator_validated'] else 'No'}")
                        st.write(f"**Evaluator Score:** {security_info['evaluator_score']:.2f}")
                    
                    with detail_col2:
                        st.write(f"**Prompt Tokens:** {usage.get('prompt_tokens', 0)}")
                        st.write(f"**Completion Tokens:** {usage.get('completion_tokens', 0)}")
                        st.write(f"**Total Tokens:** {usage.get('total_tokens', 0)}")
                        st.write(f"**Response Time:** {duration:.2f}s")
                    
                    # Success indicator
                    if threat_level == "CLEAN":
                        st.success("✅ Request passed all security checks!")
                    elif threat_level == "SUSPICIOUS":
                        st.warning("⚠️ Request flagged as suspicious but allowed after LLM evaluation.")
                    else:
                        st.error("🔴 Request blocked due to high threat level.")
                
                # Show success message
                st.success(f"✅ Response received in {duration:.2f}s | Saved {tokens_saved} tokens ({security_info['savings_ratio']})")
                
            except Exception as e:
                error_message = str(e)
                st.error(f"❌ Error: {error_message}")
                
                # Update statistics
                st.session_state.security_stats["total_requests"] += 1
                st.session_state.security_stats["blocked_requests"] += 1
                
                # Try to extract threat information from error
                if "Security Block" in error_message or "WEIRD" in error_message:
                    st.warning("🛡️ **Security Protection Active** - This request was blocked by LLMshield's security layers.")
                    with st.expander("🔍 Security Details"):
                        st.markdown(f"**Block Reason:** {error_message}")
                        st.info("""
                        **Why was this blocked?**
                        - High entropy (random/gibberish content)
                        - Role hijacking attempt
                        - Instruction override attempt
                        - Token stuffing attack detected
                        """)
    
    # Rerun to update the UI
    st.rerun()

# Information section
with st.expander("ℹ️ About LLMshield AI", expanded=False):
    st.markdown("""
    ### 🛡️ LLMshield AI - Multi-Layer DDoS Protection
    
    **Security Features:**
    1. **Identity & Fingerprinting:** Dual-identity tracking (X-User-ID + IP address)
    2. **Security Scanning:** Regex-based detection for role hijacking and instruction overrides
    3. **Entropy Analysis:** Shannon entropy calculation to detect random/suspicious prompts
    4. **Adaptive Compression:** System prompt pinning + user input compression
    5. **LLM Tie-Breaker:** LLM-as-judge for suspicious cases (entropy 5.5-6.5)
    6. **Penalty Box:** Time-bound penalties (1 hour TTL) for flagged users
    7. **Observability:** Threat tagging and FinOps metrics in Phoenix
    
    **Threat Level Classifications:**
    - 🟢 **CLEAN** (H ≤ 5.5): Normal text, passed all checks
    - 🟡 **SUSPICIOUS** (5.5 < H ≤ 6.5): Unusual but validated by LLM-as-judge
    - 🔴 **HIGH** (H > 6.5): WEIRD - Blocked immediately
    
    **How It Works:**
    - Prompts are analyzed for security threats before reaching the LLM
    - High-entropy (random) content is blocked to prevent token stuffing attacks
    - Legitimate requests are compressed to reduce token usage and costs
    - All requests are traced in Arize Phoenix for observability
    
    For more information, check the API documentation or visit the Phoenix dashboard at `http://localhost:6006`.
    """)

# Footer
st.markdown("---")
st.markdown("**LLMshield AI Demo** | Built with Streamlit | Connect to `http://localhost:8000`")
