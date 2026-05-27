def extract_get_routes(code: str) -> set[str]:
    # Collect existing GET routes so the model cannot silently remove API endpoints.
    routes = set()

    for line in code.splitlines():
        line = line.strip()

        if line.startswith('@app.get("') and line.endswith('")'):
            route = line.removeprefix('@app.get("').removesuffix('")')
            routes.add(route)

    return routes


def find_removed_get_routes(old_code: str, new_code: str) -> set[str]:
    old_routes = extract_get_routes(old_code)
    new_routes = extract_get_routes(new_code)

    return old_routes - new_routes
