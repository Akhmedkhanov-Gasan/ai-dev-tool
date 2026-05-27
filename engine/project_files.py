APP_FILE_PATH = "demo_app/main.py"
TEST_FILE_PATH = "demo_app/test_main.py"


def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, code: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)


def read_project_files() -> dict[str, str]:
    return {
        APP_FILE_PATH: read_file(APP_FILE_PATH),
        TEST_FILE_PATH: read_file(TEST_FILE_PATH),
    }


def write_project_files(files: dict[str, str]):
    for path, code in files.items():
        write_file(path, code)