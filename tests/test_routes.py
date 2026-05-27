from engine.routes import extract_get_routes, find_removed_get_routes


def test_extract_get_routes_returns_get_routes():
    code = '''
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/items")
async def create_item():
    return {}
'''

    assert extract_get_routes(code) == {"/health"}


def test_find_removed_get_routes_returns_removed_routes():
    old_code = '''
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    return {"ready": True}
'''

    new_code = '''
@app.get("/health")
async def health():
    return {"status": "ok"}
'''

    assert find_removed_get_routes(old_code, new_code) == {"/ready"}
