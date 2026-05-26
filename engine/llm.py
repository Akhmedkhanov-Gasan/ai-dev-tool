import os
import requests

DEFAULT_MODEL = "qwen3-coder:30b"
DEFAULT_PROVIDER_URL = "http://localhost:11434/api/generate"

def get_model() -> str:
    return os.getenv("AI_AGENT_MODEL", DEFAULT_MODEL)


def get_provider_url() -> str:
    return os.getenv("AI_AGENT_PROVIDER_URL", DEFAULT_PROVIDER_URL)

def request_model(prompt: str) -> str:
    try:
        # Send the prompt to the configured provider and return the raw model text.
        response = requests.post(
            get_provider_url(),
            json={
                "model": get_model(),
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )

        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            "Provider request failed. Make sure the provider is running at "
            f"{get_provider_url()} and model {get_model()} is available."
        ) from e

    data = response.json()

    if "response" not in data:
        raise RuntimeError(f"Provider response does not contain 'response': {data}")

    return data["response"]