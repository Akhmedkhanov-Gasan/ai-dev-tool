from engine.routes import find_removed_get_routes
from tools.result import ToolResult


def inspect_removed_routes_tool(old_code: str, new_code: str) -> ToolResult:
    removed_routes = find_removed_get_routes(old_code, new_code)

    if removed_routes:
        message = f"Removed GET routes found: {sorted(removed_routes)}"
    else:
        message = "No removed GET routes found"

    return ToolResult(
        ok=not removed_routes,
        name="inspect_removed_routes",
        message=message,
        data={"removed_routes": removed_routes},
    )
