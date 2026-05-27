from engine.generation import build_generation_prompt


def test_build_generation_prompt_includes_task_rules_context_and_files():
    prompt = build_generation_prompt(
        task="Add /info endpoint",
        files={"demo_app/main.py": "app code"},
        error_context="previous error",
        project_context="retrieved context",
        agent_rules="project rules",
    )

    assert "Add /info endpoint" in prompt
    assert "project rules" in prompt
    assert "previous error" in prompt
    assert "retrieved context" in prompt
    assert "=== demo_app/main.py ===" in prompt
    assert "app code" in prompt
    assert "Return ONLY valid JSON." in prompt
