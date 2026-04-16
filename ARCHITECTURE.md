# LN70 — The Scenario Engine

## Data Model — Three Layers

### Layer 1 — Scenario (reusable template)
Stores everything needed to configure a simulation.

| Field | Description |
|-------|-------------|
| `persona` | Who the LLM plays (e.g., Dave the farmer) |
| `setting` | Physical context description |
| `context` | Full situation brief used in the system prompt |
| `learning_objectives` | List with IDs, descriptions, detection hints |
| `evaluation_criteria` | Scoring rubric for the learner |

### Layer 2 — Session (one learner's run)
| Field | Description |
|-------|-------------|
| `scenario` | FK to Scenario |
| `learner` | FK to User |
| `status` | `in_progress` / `completed` |
| `assessment_state` | JSON snapshot of current progress |

### Layer 3 — Message (the conversation)
| Field | Description |
|-------|-------------|
| `session` | FK to Session |
| `role` | `user` or `assistant` |
| `content` | The raw message text |
| `assessment_metadata` | Structured JSON returned by LLM alongside message |
| `timestamp` | When sent |
| `sequence` | Ordering within session |

## LLM Framework Decision

### Options Evaluated
**LangChain** Over-engineered; fights our data model; leaky abstractions; heavy dependencies
**LlamaIndex** Wrong fit — designed for RAG/document retrieval, not conversation
**Anthropic SDK (direct)** Full control, transparent, lightweight, fits our architecture perfectly

### Why Direct SDK Wins

LangChain's memory features (`ConversationBufferMemory`, `ChatMessageHistory`) solve problems **our Django models already solve better**:

- `Session` → is our conversation container
- `Message` → is our memory/history store
- `ContextManager` → is our memory strategy layer
- `Scenario` → is our prompt configuration

Using LangChain would mean fighting it to persist state into Django models and debugging hidden prompt manipulation. We don't need that.

**Dependency:** `anthropic` SDK only.

## Prompt Architecture

The system prompt is built dynamically from the Scenario record. Swapping to a different scenario = a new database record. Zero code changes.

```
[SYSTEM PROMPT]
  → Persona instructions         (scenario.persona)
  → Setting & context            (scenario.setting + scenario.context)
  → Behavioural rules            (Dave's personality traits)
  → Structured output contract   (exact JSON format LLM must return)
  → Learning objectives list     (so LLM knows what to assess against)

[CONVERSATION HISTORY]
  → Managed messages (strategy applied by ContextManager)

[USER'S LATEST MESSAGE]
```

## Structured Output Contract

Every LLM response returns two things simultaneously — a conversational reply AND a structured assessment JSON:

```json
{
  "message": "Yeah she's been off her tucker since Tuesday arvo...",
  "assessment": {
    "objectives_addressed": ["LO1", "LO3"],
    "objective_progress": {
      "LO1": { "status": "met", "evidence": "Student asked about feeding timeline" },
      "LO2": { "status": "not_yet", "evidence": null },
      "LO3": { "status": "partial", "evidence": "Asked about pasture type" },
      "LO4": { "status": "not_yet", "evidence": null },
      "LO5": { "status": "not_yet", "evidence": null }
    },
    "overall_score": 2,
    "scenario_state": "history_gathering",
    "flags": ["student_seems_uncertain"]
  }
}
```

The LLM is instructed via the system prompt to always respond in this exact JSON envelope. The `parser.py` module validates and extracts it server-side. On parse failure → retry with stricter prompt, then graceful error.

## Conversation History & Memory Management

Memory is not a framework feature — it is a database query against the `Message` model.

```
User sends message
       ↓
ContextManager queries Message table for this Session
       ↓
Applies chosen strategy
       ↓
Returns ordered [{role, content}] list
       ↓
Prompt builder assembles final API payload
       ↓
Anthropic SDK sends it
```

### Memory Strategies (swappable behind ContextManager interface)

| Strategy | How It Works | Trade-off |
|----------|-------------|-----------|
| **Full history** | Send every message | Simple, accurate — hits token limits on long sessions |
| **Sliding window** | Send last N messages only | Cheap — loses early context |
| **Summarization** | Summarize old turns, keep recent ones | Best of both — more complex |

**Approach:** Start with full history. Build `ContextManager` as a swappable service class. Implement summarization fallback when message count exceeds a configurable threshold.

## API Design

### Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/sessions/` | Start a new session for a scenario |
| `POST` | `/api/sessions/{id}/messages/` | Send a message, receive Dave's response + assessment |
| `GET` | `/api/sessions/{id}/` | Get full session state and progress summary |

### Message Flow (`POST /api/sessions/{id}/messages/`)
1. Receive `content` from learner
2. Save user `Message` record
3. `ContextManager` fetches and filters conversation history
4. `PromptBuilder` assembles full payload from Scenario + history
5. `LLMService` calls Anthropic SDK
6. `Parser` extracts `message` + `assessment` from JSON response
7. Save assistant `Message` record with `assessment_metadata`
8. Return `message` + `assessment` to client

## Resilience Around LLM Calls

| Failure Mode | Handling |
|---|---|
| Transient API errors (rate limits, 500s) | Retry with exponential backoff |
| Request hangs | Timeout enforcement |
| Malformed JSON response | Retry with stricter prompt nudge → fallback to safe error state |
| All retries exhausted | Return graceful error response, log full context |

LLM calls are **never made directly from views** — always via `LLMService`. Every call logs: input tokens, output tokens, latency, model used, errors.

---

## Project Structure

```
project/
├── core/                    # Shared utilities, base classes, User model
├── frontend/                # Django TemplateViews + Tailwind/jQuery templates
│   └── templates/frontend/
│       ├── login.html
│       ├── register.html
│       ├── scenario_select.html
│       └── chat.html
├── learning_sessions/       # Session + Message models, API views
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   └── urls.py
├── llm/                     # LLMService, ContextManager, prompt builders, parser
│   ├── client.py
│   ├── prompt_builder.py
│   ├── context_manager.py
│   ├── parser.py
│   ├── schemas.py           # Pydantic models for LLM responses
│   └── service.py
├── scenarios/               # Scenario + LearningObjective models
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   └── management/commands/seed_scenarios.py
└── oauth/                   # Google OAuth integration
```