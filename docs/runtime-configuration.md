# AI Runtime Configuration

The backend reads these optional environment variables through the validated
application settings. Defaults preserve the existing behaviour.

| Environment variable | Default | Purpose |
| --- | ---: | --- |
| `LLM_PROVIDER` | `gemini` | Select `gemini` or `openrouter`. |
| `GEMINI_API_KEY` | empty | Gemini credential, stored only in the untracked local `.env`. |
| `OPENROUTER_API_KEY` | empty | OpenRouter credential, stored only in the untracked local `.env`. |
| `LLM_MODEL` | `gemini-2.5-flash` | Provider model identifier, such as `google/gemini-2.5-flash` on OpenRouter. |
| `LLM_TIMEOUT_SECONDS` | `15` | Maximum time for one provider request. |
| `GOAL_PRIORITY_HIGH_WEIGHT` | `3` | Allocation weight for a user-confirmed High priority goal. |
| `GOAL_PRIORITY_MEDIUM_WEIGHT` | `2` | Allocation weight for a user-confirmed Medium priority goal. |
| `GOAL_PRIORITY_LOW_WEIGHT` | `1` | Allocation weight for a user-confirmed Low priority goal. |
| `CHAT_CONTEXT_MAX_MESSAGES` | `16` | Recent messages included in normal chat context. |
| `CHAT_CONTEXT_MAX_MESSAGE_CHARACTERS` | `1200` | Maximum characters retained from each normal chat message. |
| `GOAL_CONTEXT_MAX_MESSAGES` | `96` | Messages included in goal-planning context. |
| `GOAL_CONTEXT_MAX_MESSAGE_CHARACTERS` | `400` | Maximum characters retained from each goal-context message. |
| `PDF_CONTEXT_MAX_CHARACTERS` | `6000` | Maximum extracted PDF characters included in the advisor context. |
| `LLM_TEMPERATURE` | `0.3` | Temperature for conversational responses. |
| `LLM_STRUCTURED_TEMPERATURE` | `0` | Temperature for JSON-schema responses. |
| `LLM_RETRY_ATTEMPTS` | `1` | Number of retries after the initial provider request. |
| `LLM_RETRY_DELAY_SECONDS` | `0.75` | Initial retry delay; subsequent retries use exponential backoff. |

Weights must be greater than zero. Message counts and context character limits
must be positive. Temperatures must be between `0` and `2`; retry values cannot
be negative. Invalid values prevent the backend from starting rather than being
silently clamped.

Example local overrides:

```text
GOAL_PRIORITY_HIGH_WEIGHT=4
GOAL_PRIORITY_MEDIUM_WEIGHT=2
GOAL_PRIORITY_LOW_WEIGHT=1
CHAT_CONTEXT_MAX_MESSAGES=20
GOAL_CONTEXT_MAX_MESSAGES=80
LLM_TEMPERATURE=0.2
LLM_STRUCTURED_TEMPERATURE=0
LLM_RETRY_ATTEMPTS=2
LLM_RETRY_DELAY_SECONDS=0.5
```

Store overrides in the untracked local `.env` file. Never commit API keys or
other credentials.

For the current OpenRouter development setup, configure these values locally:

```text
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=replace_with_your_new_key
LLM_MODEL=google/gemini-2.5-flash
```

Do not add the real key to `.env.example`, documentation, tests, or source code.
