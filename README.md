# AI Dev Tool

A small local AI coding agent that modifies a FastAPI demo app, updates tests, runs Ruff and Pytest, shows a diff, and asks before applying changes.

## Requirements

- Python 3.12+
- Ollama
- qwen2.5-coder model

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
Run:
python tool.py

Example task:
Add endpoint /status that returns {"service": "demo_app", "status": "running"}