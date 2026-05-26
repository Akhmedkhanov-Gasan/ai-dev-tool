from engine.index import format_search_results, search_project


def retrieve_project_context(task: str) -> str:
    try:
        results = search_project(task, limit=3)
    except Exception as e:
        return f"Project context index is not available: {e}"

    return format_search_results(results)