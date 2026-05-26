import pytest

from engine.generated_files import parse_generated_files

APP_FILE_PATH = "demo_app/main.py"
TEST_FILE_PATH = "demo_app/test_main.py"

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


def test_parse_generated_files_returns_required_files_from_json():
    text = """
{
  "files": [
    {
      "path": "demo_app/main.py",
      "content": "from fastapi import FastAPI\\n\\napp = FastAPI()\\n"
    },
    {
      "path": "demo_app/test_main.py",
      "content": "def test_example():\\n    assert True\\n"
    }
  ]
}
"""

    files = parse_generated_files(text)

    assert files[APP_FILE_PATH].startswith("from fastapi import FastAPI")
    assert files[TEST_FILE_PATH].startswith("def test_example")


def test_parse_generated_files_rejects_json_with_missing_file():
    text = """
{
  "files": [
    {
      "path": "demo_app/main.py",
      "content": "from fastapi import FastAPI\\n\\napp = FastAPI()\\n"
    }
  ]
}
"""

    with pytest.raises(ValueError, match="Missing files"):
        parse_generated_files(text)


def test_parse_generated_files_rejects_json_with_extra_file():
    text = """
{
  "files": [
    {
      "path": "demo_app/main.py",
      "content": "from fastapi import FastAPI\\n\\napp = FastAPI()\\n"
    },
    {
      "path": "demo_app/test_main.py",
      "content": "def test_example():\\n    assert True\\n"
    },
    {
      "path": ".env",
      "content": "SECRET=value\\n"
    }
  ]
}
"""

    with pytest.raises(ValueError, match="Unexpected files"):
        parse_generated_files(text)
