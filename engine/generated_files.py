import json

from pydantic import ValidationError

from engine.schemas import GeneratedFiles


REQUIRED_GENERATED_PATHS = {
    "demo_app/main.py",
    "demo_app/test_main.py",
}


def validate_generated_file_paths(files: dict[str, str]) -> None:
    missing_paths = REQUIRED_GENERATED_PATHS - set(files)
    extra_paths = set(files) - REQUIRED_GENERATED_PATHS

    if missing_paths:
        raise ValueError(f"Missing files in model response: {sorted(missing_paths)}")

    if extra_paths:
        raise ValueError(f"Unexpected files in model response: {sorted(extra_paths)}")


def parse_generated_files_json(text: str) -> dict[str, str]:
    try:
        data = json.loads(text)
        generated_files = GeneratedFiles.model_validate(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model response is not valid JSON: {e}") from e
    except ValidationError as e:
        raise ValueError(f"Model response does not match schema:\n{e}") from e

    files = {
        item.path.replace("\\", "/").strip(): item.content
        for item in generated_files.files
    }

    validate_generated_file_paths(files)

    return files


def parse_generated_files_legacy(text: str) -> dict[str, str]:
    files = {}
    current_path = None
    current_lines = []

    for line in text.splitlines():
        if line.strip().startswith("```"):
            continue

        if line.startswith("=== ") and line.endswith(" ==="):
            if current_path is not None:
                files[current_path] = "\n".join(current_lines).strip() + "\n"

            current_path = line.removeprefix("=== ").removesuffix(" ===").strip()
            current_lines = []
        elif current_path is not None:
            current_lines.append(line)

    if current_path is not None:
        files[current_path] = "\n".join(current_lines).strip() + "\n"

    validate_generated_file_paths(files)

    return files


def parse_generated_files(text: str) -> dict[str, str]:
    stripped_text = text.strip()

    if stripped_text.startswith("{"):
        return parse_generated_files_json(text)

    return parse_generated_files_legacy(text)
