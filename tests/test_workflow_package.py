from workflow import (
    resume_agent_workflow,
    run_agent_workflow,
    start_agent_workflow,
)


def test_workflow_package_exports_runner():
    assert callable(run_agent_workflow)
    assert callable(start_agent_workflow)
    assert callable(resume_agent_workflow)
