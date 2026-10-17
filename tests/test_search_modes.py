import asyncio
from types import SimpleNamespace

import pytest

from smart_search import service
from smart_search.jev import JevClient


def response(questions, values):
    return {"answers": {key: {"type": "noul", "noul": values.get(key, 0.01)} for key in questions}}


def configure_exa(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "exa-test")

    async def search(*args, **kwargs):
        return {"ok": True, "results": [{"url": "https://example.org/source", "content": "Retrieved result"}]}

    monkeypatch.setattr(service, "exa_search", search)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["jev", "hybrid"])
async def test_ordinary_search_has_one_judgment_and_ignores_research_options(monkeypatch, mode):
    configure_exa(monkeypatch)
    monkeypatch.setenv("SMART_SEARCH_INTENT_ROUTER", mode)
    monkeypatch.setenv("TYPESAFE_API_KEY", "jev-test")
    monkeypatch.setenv("SMART_SEARCH_JEV_MAX_ROUNDS", "10")
    monkeypatch.setenv("SMART_SEARCH_JEV_MAX_CHANNELS", "10")
    monkeypatch.setenv("SMART_SEARCH_JEV_FILTER_RESULTS", "true")
    monkeypatch.setenv("SMART_SEARCH_JEV_SYNTHESIZE", "true")
    calls = []

    async def judge(self, state, questions, timeout):
        assert "available_channels" in state, "ordinary search must not assess, filter, or synthesize"
        calls.append(state)
        return response(questions, {f"channel_{i}": 0.99 for i in range(len(state["available_channels"]))})

    monkeypatch.setattr(JevClient, "_request", judge)
    result = await service.search("Find this source", validation="strict", extra_sources=2)

    assert result["ok"]
    assert len(calls) == 1
    assert len(result["provider_attempts"]) == 1
    assert result["routing_decision"]["stop_reason"] == "single_pass"
    assert result["evidence_assessment"]["status"] == "not_evaluated"
    assert result["evidence_assessment"]["sufficient"] is None
    assert result["result_filter"]["enabled"] is False
    assert result["synthesis"]["status"] == "disabled"
    assert result["timeout_seconds"] == 300


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["local", "rules", "off"])
async def test_local_aliases_never_call_jev_even_when_key_exists(monkeypatch, mode):
    configure_exa(monkeypatch)
    monkeypatch.setenv("SMART_SEARCH_INTENT_ROUTER", mode)
    monkeypatch.setenv("TYPESAFE_API_KEY", "unused-jev-key")
    monkeypatch.setenv("INTENT_EMBEDDING_API_KEY", "unused-embedding-key")
    monkeypatch.setenv("INTENT_CLASSIFIER_API_KEY", "unused-classifier-key")

    async def forbidden(*args, **kwargs):
        raise AssertionError("local mode must not use a remote router")

    monkeypatch.setattr(JevClient, "_request", forbidden)
    result = await service.search("Find this source", fallback="off")

    assert result["ok"]
    assert result["jev_calls"] == []
    assert result["routing_decision"]["intent_router_mode"] == "local"
    assert not result["degraded"]


@pytest.mark.asyncio
async def test_missing_jev_uses_local_retrieval_unless_fallback_is_off(monkeypatch):
    configure_exa(monkeypatch)
    result = await service.search("Find this source")
    assert result["ok"]
    assert result["degraded"]
    assert result["jev_calls"] == []
    refused = await service.search("Find this source", fallback="off")
    assert not refused["ok"]
    assert refused["error_type"] == "config_error"


@pytest.mark.asyncio
async def test_context7_ordinary_search_selects_library_locally(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "jev-test")
    monkeypatch.setenv("CONTEXT7_API_KEY", "context7-test")
    calls = []

    async def judge(self, state, questions, timeout):
        assert "available_channels" in state, "no second Jev library selection"
        calls.append(state)
        return response(questions, {"channel_0": 0.99})

    async def library(*args, **kwargs):
        return {"ok": True, "results": [{"id": "/websites/react_dev", "title": "React", "description": "React documentation"}]}

    async def docs(library_id, query):
        assert library_id == "/websites/react_dev"
        return {"ok": True, "content": "useEffect cleanup documentation"}

    monkeypatch.setattr(JevClient, "_request", judge)
    monkeypatch.setattr(service, "context7_library", library)
    monkeypatch.setattr(service, "context7_docs", docs)
    result = await service.search("React useEffect API docs")
    assert result["ok"]
    assert len(calls) == 1
    assert "cleanup documentation" in result["content"]


@pytest.mark.asyncio
async def test_research_reads_discovered_source_before_citing(monkeypatch, tmp_path):
    monkeypatch.setenv("TYPESAFE_API_KEY", "jev-test")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-test")
    operations = []

    async def judge(self, state, questions, timeout):
        if "available_channels" in state:
            scores = {f"channel_{i}": 0.99 if (item["operation"] == "fetch" if operations else item["id"] == "tavily:search") else 0.01
                      for i, item in enumerate(state["available_channels"])}
        else:
            read = "fetch" in operations
            scores = {"useful": 0.99 if read else 0.1, "sufficient": 0.99 if read else 0.1}
        return response(questions, scores)

    async def search(*args, **kwargs):
        operations.append("search")
        return [{"url": "https://example.org/source", "content": "Discovery snippet"}]

    async def fetch(url):
        operations.append("fetch")
        return "Actual fetched primary source text"

    monkeypatch.setattr(JevClient, "_request", judge)
    monkeypatch.setattr(service, "call_tavily_search", search)
    monkeypatch.setattr(service, "call_tavily_extract", fetch)
    result = await service.research("Find evidence", evidence_dir=str(tmp_path / "evidence"))

    assert result["ok"]
    assert operations == ["search", "fetch"]
    assert result["gap_check"]["status"] == "closed"
    assert len(result["citations"]) == 1
    assert "Actual fetched" in result["content"]
    assert "Discovery snippet" not in result["content"]


@pytest.mark.asyncio
@pytest.mark.parametrize("fallback", ["auto", "off"])
async def test_empty_ordinary_channel_uses_only_same_capability_fallback(monkeypatch, fallback):
    monkeypatch.setenv("TYPESAFE_API_KEY", "jev-test")
    monkeypatch.setenv("CONTEXT7_API_KEY", "context7-test")
    monkeypatch.setenv("EXA_API_KEY", "exa-test")
    judgments, retrievals = [], []

    async def judge(self, state, questions, timeout):
        judgments.append(state)
        return response(questions, {f"channel_{i}": 0.99 if item["provider"] == "context7" else 0.01
                                   for i, item in enumerate(state["available_channels"])})

    async def library(*args, **kwargs):
        retrievals.append("context7")
        return {"ok": True, "results": []}

    async def exa(*args, **kwargs):
        retrievals.append("exa")
        return {"ok": True, "results": [{"url": "https://example.org/docs", "content": "Documentation"}]}

    monkeypatch.setattr(JevClient, "_request", judge)
    monkeypatch.setattr(service, "context7_library", library)
    monkeypatch.setattr(service, "exa_search", exa)
    result = await service.search("React API docs", fallback=fallback)
    assert len(judgments) == 1
    assert retrievals == (["context7", "exa"] if fallback == "auto" else ["context7"])
    assert result["ok"] == (fallback == "auto")
    assert {item["capability"] for item in result["provider_attempts"]} == {"docs_search"}
    assert result["evidence_assessment"]["status"] == "not_evaluated"


@pytest.mark.asyncio
async def test_ordinary_deadline_cancels_retrieval(monkeypatch):
    configure_exa(monkeypatch)
    cancelled = asyncio.Event()

    async def slow(*args, **kwargs):
        try:
            await asyncio.sleep(1)
        finally:
            cancelled.set()

    monkeypatch.setattr(service, "exa_search", slow)
    result = await service.search("Find this source", timeout_seconds=0.02)
    assert cancelled.is_set()
    assert not result["ok"]
    assert result["error_type"] == "timeout"
    assert result["timeout_phase"] == "retrieval"
    assert len(result["provider_attempts"]) == 1


@pytest.mark.asyncio
async def test_selected_model_keeps_configured_failure_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_URL", "https://relay.example/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "relay-test")
    monkeypatch.setenv("OPENAI_COMPATIBLE_MODEL", "primary")
    monkeypatch.setenv("OPENAI_COMPATIBLE_FALLBACK_MODELS", "backup")
    called = []

    def providers(configs, fallback):
        async def search(query, platform):
            called.append(configs[0]["model"])
            if configs[0]["model"] == "primary":
                raise RuntimeError("primary unavailable")
            return "Retrieved answer"
        return [SimpleNamespace(search=search)]

    monkeypatch.setattr(service, "_main_search_providers", providers)
    result = await service.search("Find this source")
    assert result["ok"]
    assert called == ["primary", "backup"]
    assert result["model"] == "backup"
    assert result["model_fallback_used"]
    assert result["jev_calls"] == []


@pytest.mark.asyncio
async def test_calibration_is_retired_without_remote_calls():
    result = await service.route_calibrate()
    assert result["deprecated"]
    assert not result["executed_remote"]


@pytest.mark.asyncio
async def test_empty_context7_document_does_not_become_a_read_citation(monkeypatch, tmp_path):
    monkeypatch.setenv("CONTEXT7_API_KEY", "ctx-test")

    async def libraries(*args, **kwargs):
        return {"ok": True, "results": [{"id": "/reactjs/react.dev", "title": "React"}]}

    async def docs(*args, **kwargs):
        return {"ok": True, "content": ""}

    monkeypatch.setattr(service, "context7_library", libraries)
    monkeypatch.setattr(service, "context7_docs", docs)
    result = await service.research("React API docs", budget="standard", evidence_dir=str(tmp_path))
    assert not result["ok"]
    assert result["citations"] == []
    assert result["evidence_items"] == []
