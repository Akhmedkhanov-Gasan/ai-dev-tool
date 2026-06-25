import os
import requests

DEFAULT_MODEL = "qwen3-coder:30b"
DEFAULT_PROVIDER_URL = "http://localhost:11434/api/generate"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 45


def get_model() -> str:
    return os.getenv("AI_AGENT_MODEL", DEFAULT_MODEL)


def get_provider_url() -> str:
    return os.getenv("AI_AGENT_PROVIDER_URL", DEFAULT_PROVIDER_URL)


def get_request_timeout_seconds() -> float:
    raw_timeout = os.getenv("AI_AGENT_REQUEST_TIMEOUT_SECONDS")

    if raw_timeout is None:
        return DEFAULT_REQUEST_TIMEOUT_SECONDS

    try:
        timeout = float(raw_timeout)
    except ValueError as e:
        raise RuntimeError(
            "AI_AGENT_REQUEST_TIMEOUT_SECONDS must be a number."
        ) from e

    if timeout <= 0:
        raise RuntimeError(
            "AI_AGENT_REQUEST_TIMEOUT_SECONDS must be greater than 0."
        )

    return timeout


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
            timeout=get_request_timeout_seconds(),
        )

        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            "Provider request failed. Make sure the provider is running at "
            f"{get_provider_url()} and model {get_model()} is available. "
            f"Request timeout: {get_request_timeout_seconds()} seconds."
        ) from e

    data = response.json()

    if "response" not in data:
        raise RuntimeError(f"Provider response does not contain 'response': {data}")

    return data["response"]
