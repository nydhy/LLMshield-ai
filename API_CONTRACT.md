# LLMshield AI Proxy - API Contract

## Base URL
```
http://localhost:8000  (development)
```

## Authentication
Currently, authentication is handled via API keys configured server-side. Frontend integration does not require explicit authentication headers for basic usage, but user identification is recommended via headers.

## Endpoints

### 1. Health Check

**GET** `/`

Returns the service status.

**Response:**
```json
{
  "status": "llmshield-ai is active 🚀",
  "service": "LLMshield AI Proxy",
  "version": "1.0.0"
}
```

---

### 2. Chat Completions (Main Endpoint)

**POST** `/v1/chat/completions`

Processes chat messages with multi-layer security protection and returns LLM responses.

**Request Headers:**
```
Content-Type: application/json
X-User-ID: <optional> User identifier for tracking
X-Forwarded-For: <optional> Client IP (if behind proxy)
```

**Request Body:**
```json
{
  "model": "gemini-2.5-flash-lite",  // Optional, defaults to server config
  "messages": [
    {
      "role": "system",  // Optional system message
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "What is 2+2?"
    }
  ],
  "temperature": 0.7,    // Optional, 0.0-1.0
  "max_tokens": 1000,    // Optional
  "top_p": 0.9          // Optional, 0.0-1.0
}
```

**Response (Success - 200):**
```json
{
  "id": "chatcmpl-1768749732390",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Four"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 11,
    "completion_tokens": 1,
    "total_tokens": 12
  },
  "llm_shield": {
    "mitigation": "active",
    "threat_level": "CLEAN",
    "entropy_score": 3.93,
    "attack_probability": "LOW",
    "tokens_saved": 2,
    "savings_ratio": "10.0%",
    "savings_pct": 10.0,
    "evaluator_validated": true,
    "evaluator_score": 0.0,
    "compression_level": 0.5,
    "user_penalty_applied": false
  }
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique response identifier |
| `choices[].message.role` | string | Always "assistant" |
| `choices[].message.content` | string | LLM-generated response text |
| `choices[].finish_reason` | string | "stop", "length", "safety", or "recitation" |
| `usage.prompt_tokens` | number | Tokens used in the prompt |
| `usage.completion_tokens` | number | Tokens generated in response |
| `usage.total_tokens` | number | Total tokens used |
| `llm_shield.mitigation` | string | Always "active" when security is enabled |
| `llm_shield.threat_level` | string | "CLEAN", "SUSPICIOUS", or "WEIRD" |
| `llm_shield.entropy_score` | number | Shannon entropy score (higher = more random/suspicious) |
| `llm_shield.attack_probability` | string | "LOW" or "HIGH" based on compression savings |
| `llm_shield.tokens_saved` | number | Tokens saved through compression |
| `llm_shield.savings_ratio` | string | Percentage of tokens saved (e.g., "10.0%") |
| `llm_shield.savings_pct` | number | Numeric savings percentage |
| `llm_shield.evaluator_validated` | boolean | Whether LLM-as-judge validated the prompt |
| `llm_shield.evaluator_score` | number | 0.0 = valid, 1.0 = invalid/malicious |
| `llm_shield.compression_level` | number | Compression aggressiveness used (0.0-1.0) |
| `llm_shield.user_penalty_applied` | boolean | Whether user is in penalty box |

**Error Responses:**

**400 Bad Request:**
```json
{
  "detail": "No messages found"
}
```
```json
{
  "detail": "Empty prompt"
}
```

**403 Forbidden (Security Block):**
```json
{
  "detail": "Security Block: Role Hijacking Detected"
}
```
```json
{
  "detail": "Security Block: Instruction Override Detected"
}
```
```json
{
  "detail": "Entropy Block: WEIRD prompt detected (H > 6.5). Blocked to prevent DDoS."
}
```

**429 Too Many Requests:**
```json
{
  "detail": "Gemini API rate limit exceeded: <error details>"
}
```
```json
{
  "detail": "Gemini API quota/billing issue: <error details>. Please add credits to your account."
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error: <error type>: <error message>"
}
```

**502 Bad Gateway:**
```json
{
  "detail": "Gemini API error: <error details>"
}
```

---

## Security Features

1. **Multi-Layer Protection:**
   - Regex-based security scanning (role hijacking, instruction overrides)
   - Shannon entropy analysis (detects random/gibberish prompts)
   - LLM-as-judge evaluation (validates suspicious prompts)
   - Adaptive compression (reduces token usage for flagged users)

2. **User Tracking:**
   - Dual-identity fingerprinting (X-User-ID + IP address)
   - Penalty box system (temporary restrictions for flagged users)

3. **Observability:**
   - All requests traced in Arize Phoenix (http://localhost:6006)
   - Token usage and security metrics included in responses

---

## Frontend Integration Example

### JavaScript/TypeScript

```typescript
interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface ChatRequest {
  model?: string;
  messages: ChatMessage[];
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
}

interface ChatResponse {
  id: string;
  choices: Array<{
    message: {
      role: string;
      content: string;
    };
    finish_reason: string;
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  llm_shield: {
    mitigation: string;
    threat_level: string;
    entropy_score: number;
    attack_probability: string;
    tokens_saved: number;
    savings_ratio: string;
    savings_pct: number;
    evaluator_validated: boolean;
    evaluator_score: number;
    compression_level: number;
    user_penalty_applied: boolean;
  };
}

async function chatCompletion(
  messages: ChatMessage[],
  options?: {
    model?: string;
    temperature?: number;
    max_tokens?: number;
    userId?: string;
  }
): Promise<ChatResponse> {
  const response = await fetch('http://localhost:8000/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(options?.userId && { 'X-User-ID': options.userId }),
    },
    body: JSON.stringify({
      model: options?.model || 'gemini-2.5-flash-lite',
      messages,
      temperature: options?.temperature,
      max_tokens: options?.max_tokens,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`API Error (${response.status}): ${error.detail}`);
  }

  return response.json();
}

// Usage example
const messages: ChatMessage[] = [
  { role: 'system', content: 'You are a helpful assistant.' },
  { role: 'user', content: 'What is 2+2?' },
];

try {
  const result = await chatCompletion(messages, {
    userId: 'user-123',
    temperature: 0.7,
  });
  
  console.log('Response:', result.choices[0].message.content);
  console.log('Security:', result.llm_shield.threat_level);
  console.log('Tokens used:', result.usage.total_tokens);
} catch (error) {
  console.error('Chat error:', error);
}
```

### React Hook Example

```typescript
import { useState, useCallback } from 'react';

interface UseChatReturn {
  sendMessage: (content: string) => Promise<void>;
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  security: ChatResponse['llm_shield'] | null;
}

function useChat(systemPrompt?: string): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>(
    systemPrompt ? [{ role: 'system', content: systemPrompt }] : []
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [security, setSecurity] = useState<ChatResponse['llm_shield'] | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    setIsLoading(true);
    setError(null);

    const userMessage: ChatMessage = { role: 'user', content };
    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);

    try {
      const response = await chatCompletion(updatedMessages);
      
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.choices[0].message.content,
      };
      
      setMessages([...updatedMessages, assistantMessage]);
      setSecurity(response.llm_shield);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [messages]);

  return { sendMessage, messages, isLoading, error, security };
}
```

---

## Rate Limiting & Best Practices

1. **User Identification:** Always send `X-User-ID` header to enable proper user tracking and penalty box functionality.

2. **Error Handling:** Check `llm_shield.threat_level` to inform users about security blocks.

3. **Token Usage:** Monitor `usage.total_tokens` for cost tracking.

4. **Security Metrics:** Use `llm_shield` data for dashboard/analytics.

5. **Model Selection:** Default model is `gemini-2.5-flash-lite` (cost-efficient). Override via `model` parameter if needed.

---

## Support

For issues or questions, check the service logs or Phoenix traces at `http://localhost:6006`.
