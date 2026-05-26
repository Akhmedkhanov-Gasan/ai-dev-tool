from agent import (
    extract_get_routes,
)

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
