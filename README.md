# AI Dev Tool

A local AI coding agent for a small FastAPI demo project.

The tool asks a configured LLM provider to update `demo_app/main.py` and
`demo_app/test_main.py`, validates the candidate changes with Ruff and Pytest,
shows a diff, and requires a human review decision before applying anything.

## What It Does

- Generates full candidate versions of the FastAPI app and its tests.
- Preserves existing GET routes unless the task explicitly asks to remove them.
- Validates that generated app code still passes the original tests.
- Validates the full candidate with Ruff and Pytest.
- Retries failed generations up to the configured iteration limit.
- Supports dry runs, interactive approval, review-only mode, and review resume.
- Builds a local SQLite FTS index for project context retrieval.

## Project Layout

```text
agent.py                  CLI entry point for the local coding agent
AGENT_RULES.md            Project-specific instructions injected into prompts
engine/                   Core generation, validation, indexing, and schemas
workflow/                 LangGraph workflow nodes, routing, and review state
demo_app/                 FastAPI demo app modified by the agent
tests/                    Unit tests for the agent engine and workflow
Dockerfile                Container image that runs the test suite
docker-compose.yml        Validator service with Docker provider defaults
```

## Requirements

- Python 3.12+
- Ollama or another compatible `/api/generate` provider
- A coding model available to that provider

The default model in code is `qwen3-coder:30b`.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create or update `.env` if you need non-default provider settings:

```env
AI_AGENT_PROVIDER_URL=http://localhost:11434/api/generate
AI_AGENT_MODEL=qwen3-coder:30b
AI_AGENT_REQUEST_TIMEOUT_SECONDS=45
```

## Index Project Context

Build the local project index:

```powershell
python agent.py index
```

Search the index:

```powershell
python agent.py search "route validation"
```

The index is stored at `.agent/project_index.sqlite` and is used to provide
relevant project context to the model.

## Run The Agent

Run an interactive task:

```powershell
python agent.py "Add endpoint /status that returns {\"service\": \"demo_app\", \"status\": \"running\"}"
```

Run without applying changes:

```powershell
python agent.py --dry-run "Add endpoint /ready that returns {\"ready\": true}"
```

During a normal run, the agent:

1. Reads the current demo app and tests.
2. Retrieves relevant indexed project context.
3. Generates candidate files through the configured model provider.
4. Checks that existing GET routes were not removed.
5. Runs baseline validation against the original tests.
6. Runs candidate validation with Ruff and Pytest.
7. Shows a unified diff.
8. Applies changes only after approval.

## Review-Only Flow

Start a run and stop at the human review checkpoint:

```powershell
python agent.py --review-only "Add endpoint /info that returns app metadata"
```

The command prints a thread ID. Resume that review with exactly one decision:

```powershell
python agent.py --resume-thread <thread-id> --approve
python agent.py --resume-thread <thread-id> --reject
python agent.py --resume-thread <thread-id> --dry-run-review
```

Review state is stored under `.workflow/reviews`.

## Validation

Candidate validation uses:

```powershell
python -m ruff check demo_app
python -m pytest -v demo_app
python -c "import demo_app.main"
```

The validation step temporarily writes candidate files to disk, then restores
the original project files after validation.

## Tests

Run the full test suite:

```powershell
python -m pytest -v
```

Run Ruff manually:

```powershell
python -m ruff check .
```

## Docker

Build and run the validator container:

```powershell
docker compose run --rm validator
```

The compose file sets:

```env
PYTHONPATH=/app
AI_AGENT_PROVIDER_URL=http://host.docker.internal:11434/api/generate
AI_AGENT_MODEL=qwen3-coder:30b
```

## Current Scope

This tool is intentionally narrow. It is built around the included FastAPI demo
project and expects model responses to contain complete contents for:

- `demo_app/main.py`
- `demo_app/test_main.py`

The agent rejects missing files, unexpected files, invalid JSON responses, route
removals, Ruff failures, Pytest failures, and runtime import failures.
