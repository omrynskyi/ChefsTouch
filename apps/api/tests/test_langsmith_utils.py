from __future__ import annotations

from packages.agents.langsmith_utils import (
    get_langsmith_project,
    has_langsmith_api_key,
    langsmith_tracing_mode,
    should_upload_eval_results,
)


def test_tracing_true_without_key_disables_upload(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)

    assert has_langsmith_api_key() is False
    assert langsmith_tracing_mode() is False


def test_local_tracing_mode_is_preserved(monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "local")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)

    assert langsmith_tracing_mode() == "local"


def test_project_name_falls_back_to_langchain_env(monkeypatch):
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.setenv("LANGCHAIN_PROJECT", "legacy-project")

    assert get_langsmith_project("evals") == "legacy-project-evals"


def test_eval_upload_respects_explicit_disable(monkeypatch):
    monkeypatch.setenv("LANGSMITH_EVAL_UPLOAD_RESULTS", "false")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")

    assert should_upload_eval_results() is False
