# ADR-011: Gemini via Vertex AI as LLM

**Status:** Accepted  
**Date:** 2026-05-17

## Context

The pipeline requires an LLM for: draft generation, QA/style scoring, semantic deduplication, and topic summarization. The original plan used Claude via the Anthropic API.

The deployment target is GCP (ADR-010), and Vertex AI hosts Gemini natively. Using Gemini via Vertex AI means:
- Single billing (all LLM costs on GCP invoice)
- IAM-based authentication via service account — no API key to manage in Secret Manager
- Native GCP integration
- LangGraph/LangChain has first-class `ChatVertexAI` support, requiring no pipeline structural changes

## Decision

Use **Gemini 3.1 Pro via Vertex AI** as the default LLM for all pipeline nodes.

Model IDs (configurable in `config.yaml`):
- Default: `gemini-3.1-pro-preview`
- Fast/cheap operations (dedup check, topic summary): `gemini-3.1-flash-lite`

### LangChain Integration

```python
from langchain_google_vertexai import ChatVertexAI

llm = ChatVertexAI(
    model_name="gemini-2.5-pro",
    project=settings.gcp_project,
    location=settings.gcp_region,   # e.g. "us-central1"
)
```

Authentication is handled automatically via the Cloud Run service account (`sa-pipeline`) — no API key needed. Locally, use `gcloud auth application-default login`.

### Model Routing by Node

| Pipeline Node | Model | Reason |
|---|---|---|
| Draft generation | `gemini-3.1-pro-preview` | High quality, nuanced output |
| QA / style check | `gemini-3.1-pro-preview` | Careful structured scoring |
| Semantic dedup | `gemini-3.1-flash-lite` | Simple yes/no comparison, cost-sensitive |
| Topic summary | `gemini-3.1-flash-lite` | Short output, runs every signal |

## Consequences

- Replace `anthropic` dependency with `langchain-google-vertexai` and `google-cloud-aiplatform`
- `config.yaml` `model:` field changes to model name string (same interface, different value)
- Local development requires `gcloud auth application-default login` — no `.env` API key needed
- Model routing adds minor complexity (two model instances) but significantly reduces cost for high-frequency cheap operations
- If Gemini quality is insufficient for a specific node (e.g. QA scoring), the `ChatVertexAI` call can be swapped per-node without changing pipeline structure
