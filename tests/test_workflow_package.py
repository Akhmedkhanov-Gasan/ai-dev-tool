from workflow import run_agent_workflow


def test_workflow_package_exports_runner():
    assert callable(run_agent_workflow)