from engine.generated_files import parse_generated_files
from engine.llm import request_model

def build_generation_prompt(task, files, error_context, project_context, agent_rules):
    file_context = "\n\n".join(
        f"=== {path} ===\n{code}"
        for path, code in files.items()
    )

    prompt = f"""
    You are a senior Python developer.

    Modify the FastAPI app and its tests according to the task.

    Follow these project rules:

    {agent_rules}

    Return ONLY valid JSON.
    Do not wrap the JSON in Markdown.
    Do not add explanations before or after the JSON.

    The JSON must match this schema:

    {{
      "files": [
        {{
          "path": "demo_app/main.py",
          "content": "full updated content of demo_app/main.py"
        }},
        {{
          "path": "demo_app/test_main.py",
          "content": "full updated content of demo_app/test_main.py"
        }}
      ]
    }}

    Both files are required.
    Return full file contents, not a diff or patch.

    Always add or update tests for the feature you implement.
    Keep existing tests unless the task explicitly requires changing behavior.

    Do not remove existing endpoints unless the task explicitly asks for removal.
    If a route already exists, keep it exactly unless the task asks to change it.
    When fixing previous errors, preserve all existing routes from the provided files.

    Preserve all imports required by existing code.

    Do not weaken existing behavior or replace dynamic behavior with hardcoded values.

    When Previous errors contains Ruff F821, fix missing imports before making any other changes.

    Task:
    {task}

    Previous errors:
    {error_context}

    Relevant project context:
    {project_context}

    Files:
    {file_context}

    """

    return prompt

def generate_code(task, files, error_context, project_context, agent_rules):
    prompt = build_generation_prompt(
        task,
        files,
        error_context,
        project_context,
        agent_rules,
    )

    model_response = request_model(prompt)

    return parse_generated_files(model_response)
