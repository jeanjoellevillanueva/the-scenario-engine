# LN70 — The Scenario Engine

---

## 1. What We Are Building

A configurable LLM-powered learning simulation platform. A learner enters a simulated situation, interacts with an LLM-driven character, and is assessed against learning objectives — without any scripting of conversation paths.

---

## 2. The Test Scenario

- **Setting:** Remote property outside Armidale, NSW, Australia
- **Character:** Dave, a farmer (played by the LLM) — helpful, not medically precise, anxious if the student seems unsure, throws in irrelevant details
- **Patient:** "Duchess" — a prize Hereford cow (female beef cattle, high value)
- **Presenting problem:** Off her feed, lethargic
- **Learner role:** Final-year veterinary science student

### Learning Objectives
| ID | Objective |
|----|-----------|
| LO1 | Gather relevant history (feeding, water intake, diet changes, symptom timeline) |
| LO2 | Perform systematic assessment (temperature, gait, manure, respiratory rate) |
| LO3 | Consider environmental factors (pasture, toxic plants, weather, sick animals) |
| LO4 | Identify at least two differential diagnoses |
| LO5 | Recommend a treatment plan with reasoning and follow-up |

---

## 3. Data Model — Three Layers

### Layer 1 — Scenario (reusable template)
Stores everything needed to configure a simulation. One record powers many sessions.

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

---

## 4. LLM Framework Decision

### Options Evaluated

| Framework | Verdict |
|-----------|---------|
| **LangChain** | ❌ Over-engineered; fights our data model; leaky abstractions; heavy dependencies |
| **LlamaIndex** | ❌ Wrong fit — designed for RAG/document retrieval, not conversation |
| **Anthropic SDK (direct)** | ✅ Full control, transparent, lightweight, fits our architecture perfectly |

### Why Direct SDK Wins

LangChain's memory features (`ConversationBufferMemory`, `ChatMessageHistory`) solve problems **our Django models already solve better**:

- `Session` → is our conversation container
- `Message` → is our memory/history store
- `ContextManager` → is our memory strategy layer
- `Scenario` → is our prompt configuration

Using LangChain would mean fighting it to persist state into Django models and debugging hidden prompt manipulation. We don't need that.

**Dependency:** `anthropic` SDK only.

---

## 5. The `llm/` Service Layer

Our own lightweight LLM framework — purpose-built, readable in 20 minutes.

```
llm/
├── client.py          ← thin wrapper around anthropic.Anthropic()
├── prompt_builder.py  ← builds system prompt from Scenario model
├── context_manager.py ← decides which messages go into the API call
├── parser.py          ← parses structured JSON out of LLM response
└── service.py         ← orchestrates all of the above
```

### Provider Abstraction (future-proofing)
```python
class BaseLLMClient:
    def complete(self, system_prompt, messages) -> LLMResponse:
        raise NotImplementedError

class AnthropicClient(BaseLLMClient): ...
class OpenAIClient(BaseLLMClient): ...   # drop-in swap if needed
```

---

## 6. Prompt Architecture

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

---

## 7. Structured Output Contract

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

---

## 8. Conversation History & Memory Management

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

---

## 9. API Design

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

---

## 10. Resilience Around LLM Calls

| Failure Mode | Handling |
|---|---|
| Transient API errors (rate limits, 500s) | Retry with exponential backoff |
| Request hangs | Timeout enforcement |
| Malformed JSON response | Retry with stricter prompt nudge → fallback to safe error state |
| All retries exhausted | Return graceful error response, log full context |

LLM calls are **never made directly from views** — always via `LLMService`. Every call logs: input tokens, output tokens, latency, model used, errors.

---

## 11. Project Structure

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

> **Note:** The app is named `learning_sessions` (not `sessions`) to avoid conflict with Django's built-in `django.contrib.sessions`.

---

## 12. Testing Philosophy

Don't chase coverage. Test what matters.

| What | Why |
|------|-----|
| Prompt builder output | Most critical logic — drives everything |
| Structured response parser | LLM output is unpredictable — must be robust |
| Context manager truncation logic | Correctness matters for token safety |
| API happy path (mocked LLM) | Proves full pipeline works end-to-end |
| LLM failure scenarios | Retry logic, timeout, malformed JSON |
| Model integrity | Scenario → Session → Message data layer |

---

## 13. The Configurability Guarantee

> The code never knows it is a vet scenario.

It only knows how to read a `Scenario` record and build a prompt from it. Deploying a new scenario — nursing triage, business negotiation, language practice — is an `INSERT` statement, not a pull request.

---

## 14. Quick Start

```bash
# 1. Create and activate virtual environment
python3 -m venv env
source env/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and other settings

# 4. Run migrations
python manage.py migrate

# 5. Seed the test scenario
python manage.py seed_scenarios

# 6. Create a superuser (optional, for admin access)
python manage.py createsuperuser

# 7. Run the server
python manage.py runserver

# 8. Run tests
pytest
```

---

## 15. Implementation Status

| Step | Status | Notes |
|------|--------|-------|
| Models | ✅ Done | `Scenario`, `LearningObjective`, `Session`, `Message` |
| LLM service layer | ✅ Done | `client.py`, `prompt_builder.py`, `context_manager.py`, `parser.py`, `service.py` |
| API views | ✅ Done | Session CRUD, message endpoint |
| Frontend | ✅ Done | Chat UI with Tailwind + jQuery |
| Tests | ✅ Done | Prompt builder, parser, context manager, API endpoints |
| Seed data | ✅ Done | Dave/Duchess veterinary scenario |
| Django admin | ✅ Done | Basic admin for scenarios and sessions |

### Headroom (Future)
- Streaming responses
- Async handling
- Observability logging for LLM interactions
- Summarization memory strategy
- Containerisation

The Test Scenario
A final-year veterinary science student is called out to a remote property outside Armidale.
A farmer, Dave, has called the university clinic because his prize Hereford, "Duchess," isn't
right. She's off her feed, lethargic, and Dave's worried.
The student (the user of your application) needs to:
• Talk to Dave to gather information about Duchess's symptoms, history, and
environment
• Ask the right questions to narrow down differentials
• Arrive at a reasonable diagnosis and propose a treatment plan
The LLM plays Dave. He's helpful but not medically precise. He describes what he sees in
plain language, gets a bit anxious if the student seems unsure, and occasionally throws in
irrelevant details about his other cattle or the weather. He's a farmer, not a vet.

Learning Objectives
The learning objectives for this scenario are:
1. Gather relevant history: Ask Dave about Duchess's feeding, water intake, recent
changes to pasture or diet, and timeline of symptoms.
2. Perform a systematic assessment: Inquire about specific clinical signs:
temperature, gait, manure consistency, respiratory rate, or other observable
indicators Dave may have noticed.
3. Consider environmental factors: Explore potential environmental causes such as
pasture type, toxic plants, recent weather, or exposure to other sick animals.
4. Identify differential diagnoses: Propose at least two plausible differential
diagnoses based on the information gathered.
5. Recommend a treatment plan: Suggest an appropriate treatment or management
plan with reasoning, including any immediate actions and follow-up.
These are the objectives your system should be configured with for this scenario. They should
drive the structured assessment data the LLM returns alongside each conversational response.

The Critical Requirement
You're implementing this scenario, but the system must be built so that a completely
different scenario (a nursing triage, a business negotiation, a language practice session,
etc.) is a configuration change, not a code change. The architecture matters as much as
the implementation.

What We Need to See
Core (Required)
• A Django backend with a data model for scenarios. Each scenario should define (at
minimum) a persona, setting, context, learning objectives, and evaluation criteria.
• An API that manages a multi-turn conversation between the user and the LLM,
operating within the configured scenario.
• The LLM must return structured data alongside its conversational response, not just
raw chat text. Think: which learning objectives have been touched, a current
assessment of the learner's progress, scenario state, or similar. How you achieve this
is up to you.
• Conversation history management. The system needs to know what's been said.
Depth (What we'd expect from a senior developer)
• A thoughtful approach to managing context as conversations grow. "Send
everything every time" is a valid starting point, but it's one you should be able to
reason about and justify or improve on.

• Resilience around LLM API integration. These services have failure modes. Your
code should handle them gracefully.
• Tests that show us your testing philosophy. We don't want 100% coverage for the
sake of it. We want to see what you choose to test and how.
• A clean, well-organised project that a new team member could pick up, understand,
and run with on day one. Your repository should reflect how you'd deliver real work
to a real team. We notice the things that experienced engineers do, and the things
they don't.
Headroom (Optional)
This is deliberately open-ended. If you have time and inclination, extend the project with
something you think adds genuine value. This could be anything, such as streaming
responses, async handling, observability and logging for LLM interactions, a Django admin
interface for scenario authoring, a more sophisticated memory or summarisation strategy,
containerisation, an evaluation rubric system, anything that interests you really.
We'd much rather see one well-executed enhancement than five half-finished ones.
