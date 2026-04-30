import pytest

from tool import APP_FILE_PATH, TEST_FILE_PATH, extract_get_routes, parse_generated_files


def test_parse_generated_files_returns_required_files():
    text = """
=== demo_app/main.py ===
from fastapi import FastAPI

app = FastAPI()

=== demo_app/test_main.py ===
def test_example():
    assert True
"""

    files = parse_generated_files(text)

    assert files[APP_FILE_PATH].startswith("from fastapi import FastAPI")
    assert files[TEST_FILE_PATH].startswith("def test_example")


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
