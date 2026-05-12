from pathlib import Path

from engine.index import index_project, iter_project_files, search_project


def test_index_project_searches_indexed_files(tmp_path):
    readme_path = tmp_path / "README.md"
    readme_path.write_text("Docker validation uses compose.", encoding="utf-8")

    db_path = tmp_path / ".agent" / "project_index.sqlite"

    indexed_chunks = index_project(root=tmp_path, db_path=db_path)
    results = search_project("docker", db_path=db_path)

    assert indexed_chunks == 1
    assert results[0]["path"] == "README.md"
    assert "Docker" in results[0]["snippet"]


def test_iter_project_files_skips_runtime_directories(tmp_path):
    app_path = tmp_path / "demo_app"
    app_path.mkdir()
    (app_path / "main.py").write_text("app code", encoding="utf-8")

    venv_path = tmp_path / ".venv"
    venv_path.mkdir()
    (venv_path / "ignored.py").write_text("ignored", encoding="utf-8")

    indexed_paths = set(iter_project_files(Path(tmp_path)))

    assert Path("demo_app/main.py") in indexed_paths
    assert Path(".venv/ignored.py") not in indexed_paths
