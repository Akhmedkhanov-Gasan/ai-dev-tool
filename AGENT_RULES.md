# Agent Rules

These rules define how the coding agent should modify this project.

## Code changes

- Make the smallest code change that satisfies the task.
- Do not add unrelated behavior.
- Do not remove existing endpoints unless the task explicitly asks for removal.
- If a route already exists, keep it exactly unless the task asks to change it.
- Do not weaken existing behavior or replace dynamic behavior with hardcoded values.
- Preserve all imports required by existing code.
- Do not remove imports unless they are unused after the change.

## Tests

- Always add or update tests for the feature being implemented.
- Keep existing tests unless the task explicitly requires changing behavior.
- Tests must verify concrete response status codes and JSON bodies when endpoints are changed.
- When fixing previous errors, preserve all existing routes from the provided files.

## Output format

- Return only the full updated files requested by the tool.
- Do not use markdown.
- Do not include explanations outside the requested file blocks.
