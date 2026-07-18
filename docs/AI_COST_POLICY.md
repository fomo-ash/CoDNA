# AI Cost Policy for Demo Release

## Purpose

This document records the AI cost constraints for the CodeDNA demo release.

The current project budget for OpenAI API usage is small:

```text
Total demo budget: $5
```

The demo will be shared with judges, not opened as a public beta.

Expected demo audience:

```text
5-6 judges
```

Expected AI usage:

```text
2 AI questions per imported repository
```

This policy must be followed when AI features are implemented.

## Current State

The current backend does not call OpenAI yet.

Implemented so far:

- GitHub OAuth.
- Repository discovery.
- Repository import.
- Async indexing scaffold.
- Repository cloning scaffold.
- Job status tracking.

Not implemented yet:

- Parsing.
- Embeddings.
- Semantic search.
- AI answers.

So current OpenAI cost is:

```text
$0
```

## Demo Budget Estimate

Assumption:

```text
6 judges x 1 repo each x 2 questions = 12 AI questions
```

Recommended answer model:

```text
gpt-5.6-luna
```

Reason:

- Lowest cost GPT-5.6 tier.
- Good enough for controlled demo answers.
- Better fit than higher-tier models under a $5 cap.

Estimated usage per question:

```text
Input context: 8k-12k tokens
Output answer: 800-1200 tokens
```

Estimated cost:

```text
Typical demo: $1-$3
Hard cap: $5
```

This assumes the backend sends only retrieved relevant chunks, not whole repositories.

## Required Limits

Before enabling AI answers, implement server-side limits.

Minimum required limits:

| Limit | Value |
| --- | --- |
| Questions per repository | `2` |
| Max retrieved context per answer | `8k-12k tokens` |
| Max answer output | `800-1200 tokens` |
| OpenAI monthly cap | `$5` |
| Model for answers | `gpt-5.6-luna` |
| Embedding model | `text-embedding-3-small` |

The frontend may display these limits, but enforcement must happen in the backend.

## Required Backend Tracking

Before making any OpenAI API call, add persistent usage tracking.

Track at minimum:

- User ID.
- Repository ID.
- Question count.
- Model used.
- Input tokens.
- Output tokens.
- Estimated cost.
- Created timestamp.

Suggested future table:

```text
ai_usage_events
```

Possible fields:

```text
id
user_id
repository_id
job_id
model
input_tokens
output_tokens
estimated_cost_usd
request_type
created_at
```

Do not rely only on OpenAI dashboard usage after the fact. The application needs its own guardrails.

## Required Runtime Guards

AI routes must check:

1. User is authenticated.
2. Repository belongs to the user.
3. Repository has completed indexing.
4. Repository has not exceeded question limit.
5. Retrieved context stays under token limit.
6. Monthly/demo budget has not been exceeded.
7. Output token limit is set on the model call.

If a limit is exceeded, return a clear API error instead of calling OpenAI.

Example response:

```json
{
  "detail": "AI question limit reached for this repository."
}
```

## Cost-Saving Rules

Follow these rules for the demo:

- Do not send whole files unless they are very small.
- Do not send whole repositories.
- Retrieve only top relevant chunks.
- Prefer concise answers.
- Cache repeated questions where possible.
- Use `text-embedding-3-small` for embeddings.
- Use `gpt-5.6-luna` for final answers.
- Do not use high-tier models by default.
- Do not run AI automatically after repository import.
- Do not generate summaries for every file during demo indexing.

## Suggested Demo AI Flow

```text
User asks question
        |
        v
Check per-repo question limit
        |
        v
Search relevant chunks
        |
        v
Trim context to max token budget
        |
        v
Call gpt-5.6-luna
        |
        v
Store usage event
        |
        v
Return answer with file references
```

## What Not To Build for the Demo

Avoid these until budget is larger:

- Unlimited chat.
- Auto-generated full repo summaries.
- Per-file AI summaries for every indexed file.
- High-reasoning model calls by default.
- AI answers before search/retrieval is implemented.
- Sending entire repositories to OpenAI.
- Background AI jobs without explicit user action.

## Recommended Environment Variables

Add these when AI routes are implemented:

```text
OPENAI_API_KEY=
OPENAI_ANSWER_MODEL=gpt-5.6-luna
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
AI_MAX_QUESTIONS_PER_REPOSITORY=2
AI_MAX_CONTEXT_TOKENS=12000
AI_MAX_OUTPUT_TOKENS=1200
AI_MONTHLY_BUDGET_USD=5
```

The API key must stay backend-only.

Never expose `OPENAI_API_KEY` through frontend environment variables.

## Practical Conclusion

The $5 budget is enough for a controlled judge demo if:

- Only 5-6 judges use it.
- Each repository gets only 2 AI questions.
- Context is retrieved and trimmed before calling OpenAI.
- The backend enforces limits before each call.
- Usage is tracked in the database.

The $5 budget is not enough for an open beta with many users and unlimited questions.
