# pydantic-ai-agent-pipeline

A production-ready AI agent service built with [Pydantic AI](https://github.com/pydantic/pydantic-ai), FastAPI, and Pydantic Logfire.

---

## Features

- **Type-Safe Agents**: Structured LLM outputs validated at runtime using Pydantic models.
- **Dependency Injection**: Safe runtime context management (`RunContext`) without global state.
- **Real-Time Streaming**: Server-Sent Events (SSE) and WebSocket support via FastAPI.
- **Observability**: Built-in OpenTelemetry and Pydantic Logfire tracing for agent spans and token usage.
- **Offline Testing**: Fast, deterministic unit tests powered by `TestModel` (no API keys required in CI).
- **Automated Evals**: Benchmark pipelines against golden datasets to prevent accuracy regressions.