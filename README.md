## AI Tutor

Run a local Streamlit-based AI tutoring app with Docker, configured via environment variables and a pluggable LLM provider.

### Quick start

1. Copy env template and set values:
   ```bash
   cp .env.example .env
   ```
   Required: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`.
   For optional Postgres service (profile `db`): set `POSTGRES_PASSWORD` (and optionally `POSTGRES_USER`, `POSTGRES_DB`).

2. Build and start:
   ```bash
   docker compose up --build
   ```

3. Open the app at `http://localhost:8501`.

### Check LLM availability quickly

- Inside the container:
  ```bash
  docker compose run --rm app uv run python hello_llm.py
  ```
  You should see an OK line with a short model response. If env is missing or the call fails, an error is printed.

### Development

- Source is mounted into the container for live reload: `./src:/app/src`.
- Session state is persisted to `./data`.

### Tests

- Unit tests run offline by default:
  ```bash
  docker compose --profile test run --rm test
  ```
- Integration tests that call the real LLM or web search can be enabled by setting the required env vars and running:
  ```bash
  docker compose --profile integration run --rm integration
  ```
  These tests are skipped automatically if required env vars are missing.

### LLM configuration

All LLM usage is configured via env in `.env`:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`

The client is constructed in `src/ai_tutor/llm/providers.py`. The UI does not call the LLM directly; it goes through services/graph.

### LangChain and LangGraph

- The app includes a LangChain-powered tutor with a LangGraph orchestration flow.
- In the UI sidebar, use the "Engine" selector to choose between the Basic engine and the LangGraph engine.
- LangChain model config is sourced from the same `.env` variables.

### Sessions

- Start a new session from the sidebar by choosing a subject (or “Write your subject choice”) and an optional learning goal.
- Duplicate prevention: starting a session with the same subject and goal loads the existing session instead of creating a new one.
- Manage sessions under “History”: select a session to load it, or click “Delete this session” to remove it.

### LangSmith (optional tracing/monitoring)

Enable LangSmith to trace and monitor chains/graphs by setting:

- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_API_KEY=...` (from LangSmith)
- `LANGCHAIN_ENDPOINT=` (optional; defaults to LangSmith cloud endpoint)
- `LANGCHAIN_PROJECT=ai-tutor` (optional project name)

With these set, the LangGraph engine will emit traces tagged with `ai_tutor` and `langgraph`.

### Optional web search (Tavily)

- Set `TAVILY_API_KEY` in `.env` to enable web search.
- In the UI sidebar, toggle "Enable web search (Tavily)" to let the tutor augment answers with brief, linked findings. Findings are advisory; the tutor still reasons independently.


