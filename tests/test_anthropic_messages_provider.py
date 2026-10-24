import asyncio
import json
import time
from types import SimpleNamespace

import httpx
import pytest

from smart_search import jev_search, service
from smart_search.config import config
from smart_search.provider_errors import ProviderCallError
from smart_search.providers.anthropic_messages import AnthropicMessagesSearchProvider
from smart_search.sources import split_answer_and_sources


URL = "https://e.weather.com.cn/mweather15d/101010100.shtml"
SETTINGS = {
    "ANTHROPIC_API_URL": "https://relay.example/v1/messages/",
    "ANTHROPIC_API_KEY": "test-secret-key",
    "ANTHROPIC_MODEL": "gemini-3.8-flash-high",
}


def message():
    return {
        "type": "message", "role": "assistant", "stop_reason": "end_turn",
        "content": [
            {"type": "server_tool_use", "id": "search1", "name": "web_search", "input": {"query": "北京天气"}},
            {"type": "web_search_tool_result", "tool_use_id": "search1", "content": [
                {"type": "web_search_result", "url": URL, "title": "中国天气网"},
            ]},
            {"type": "text", "text": "北京天气：", "citations": [
                {"type": "web_search_result_location", "url": URL, "title": "中国天气网"},
            ]},
            {"type": "text", "text": "\n\n今天小雨，13℃。"},
        ],
    }


def mock_http(monkeypatch, handler):
    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))


@pytest.mark.asyncio
@pytest.mark.parametrize("api_url", ["https://relay.example/v1", "https://relay.example/v1/messages/"])
async def test_search_request_and_response(monkeypatch, api_url):
    def handler(request):
        assert str(request.url) == "https://relay.example/v1/messages"
        assert request.headers["Authorization"] == "Bearer test-secret-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        payload = json.loads(request.content)
        assert payload["model"] == "gemini-3.8-flash-high"
        assert payload["max_tokens"] == 2048
        assert payload["stream"] is False
        assert payload["system"]
        assert payload["messages"][0]["role"] == "user"
        assert "北京天气" in payload["messages"][0]["content"]
        assert payload["tools"] == [{
            "type": "web_search_20250305", "name": "web_search", "max_uses": 5,
            "allowed_domains": ["weather.com.cn"],
        }]
        assert "instructions" not in payload and "input" not in payload
        return httpx.Response(200, json=message())

    mock_http(monkeypatch, handler)
    provider = AnthropicMessagesSearchProvider(api_url, "test-secret-key", "gemini-3.8-flash-high")
    answer, sources = split_answer_and_sources(await provider.search("北京天气", include_domains=["weather.com.cn"]))
    assert answer == "北京天气：\n\n今天小雨，13℃。"
    assert len(sources) == 1 and sources[0]["url"] == URL
    assert provider.last_transport_attempts[0]["api_mode"] == "messages"


@pytest.mark.asyncio
async def test_synthesis_does_not_attach_search_tool(monkeypatch):
    def handler(request):
        payload = json.loads(request.content)
        assert "tools" not in payload
        assert payload["max_tokens"] == 4096
        assert request.headers["anthropic-version"] == "custom-version"
        return httpx.Response(200, json=message())

    mock_http(monkeypatch, handler)
    provider = AnthropicMessagesSearchProvider("https://relay.example/v1", "test-key", "model",
                                               max_tokens=4096, api_version="custom-version")
    assert await provider.synthesize("question", [])


@pytest.mark.asyncio
async def test_unrestricted_search_omits_domains(monkeypatch):
    def handler(request):
        tool = json.loads(request.content)["tools"][0]
        assert tool == {"type": "web_search_20250305", "name": "web_search", "max_uses": 2}
        return httpx.Response(200, json=message())

    mock_http(monkeypatch, handler)
    await AnthropicMessagesSearchProvider("https://relay.example/v1", "key", "model", max_uses=2).search("weather")


def stream_events():
    return [
        {"type": "message_start", "message": {"type": "message", "content": [], "stop_reason": None}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "北京天气："}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "\n\n今天小雨，13℃。"}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "citations_delta", "citation": {
            "type": "web_search_result_location", "url": URL, "title": "中国天气网",
        }}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn"}},
        {"type": "message_stop"},
    ]


@pytest.mark.asyncio
async def test_stream_reads_text_and_citations_without_waiting_for_eof(monkeypatch):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            for event in stream_events():
                yield ("event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n").encode()
            await asyncio.Event().wait()

    def handler(request):
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(200, stream=Stream())

    mock_http(monkeypatch, handler)
    provider = AnthropicMessagesSearchProvider("https://relay.example/v1", "key", "model", stream=True)
    answer, sources = split_answer_and_sources(await asyncio.wait_for(provider.search("weather"), 2))
    assert answer == "北京天气：\n\n今天小雨，13℃。"
    assert sources[0]["url"] == URL


@pytest.mark.asyncio
async def test_incomplete_stream_falls_back_to_non_stream(monkeypatch):
    requests = []

    def handler(request):
        stream = json.loads(request.content)["stream"]
        requests.append(stream)
        if stream:
            return httpx.Response(200, text='data: {"type":"ping"}\n\n')
        return httpx.Response(200, json=message())

    mock_http(monkeypatch, handler)
    provider = AnthropicMessagesSearchProvider("https://relay.example/v1", "key", "model", stream=True)
    assert await provider.search("weather")
    assert requests == [True, False]


@pytest.mark.asyncio
@pytest.mark.parametrize("payload,error_type", [
    ({"type": "error", "error": {"message": "bad test-secret-key"}}, "provider_error"),
    ({**message(), "stop_reason": "max_tokens"}, "provider_error"),
    ({**message(), "stop_reason": "pause_turn"}, "provider_error"),
    ({**message(), "content": []}, "provider_error"),
    ({**message(), "content": [{"type": "web_search_tool_result", "content": {
        "type": "web_search_tool_result_error", "error_code": "max_uses_exceeded",
    }}]}, "provider_error"),
    ({"choices": []}, "parse_error"),
    ([], "parse_error"),
])
async def test_invalid_responses_are_not_success(payload, error_type):
    provider = AnthropicMessagesSearchProvider("https://relay.example/v1", "test-secret-key", "model")
    with pytest.raises(ProviderCallError) as error:
        await provider._parse_completion_response(httpx.Response(200, json=payload))
    assert error.value.error_type == error_type
    assert "test-secret-key" not in str(error.value)


@pytest.mark.asyncio
async def test_service_configuration_routing_probe_and_disable(monkeypatch):
    assert config.update_config_values(SETTINGS)["ok"]
    assert json.loads(config.config_file.read_text(encoding="utf-8"))["ANTHROPIC_MODEL"] == SETTINGS["ANTHROPIC_MODEL"]
    assert service._provider_configured("anthropic-messages")
    configs = service._main_search_provider_configs(providers="messages")
    assert len(configs) == 1 and configs[0]["model"] == SETTINGS["ANTHROPIC_MODEL"]
    assert "allowed_domains" not in configs[0]
    assert "ANTHROPIC_ALLOWED_DOMAINS" not in config._CONFIG_KEYS
    assert config.get_config_info()["ANTHROPIC_API_KEY"] != SETTINGS["ANTHROPIC_API_KEY"]
    assert config.get_config_info()["primary_api_mode"] == "messages"
    channels = jev_search.available_channels(service, "北京天气", [], providers="anthropic-messages")
    assert len(channels) == 2
    assert {item["provider"] for item in channels} == {"anthropic-messages"}
    assert {item["capability"] for item in channels} == {"main_search", "web_search"}
    assert len({item["id"] for item in channels}) == 2
    mock_http(monkeypatch, lambda request: httpx.Response(200, json=message()))
    client = SimpleNamespace(deadline=time.monotonic() + 5, settings=SimpleNamespace(api_key=""))
    executor = jev_search.ChannelExecutor(service, client, include_domains=["weather.com.cn"])
    results = await executor.execute(channels[0], "北京天气")
    assert results[0]["kind"] == "model_answer"
    assert results[1]["url"] == URL
    assert (await service.test_provider_connection("anthropic-messages"))["ok"]
    override = service._main_search_override_config("anthropic-messages", {"ANTHROPIC_MODEL": "candidate"})
    assert override["model"] == "candidate"
    assert config.anthropic_settings()["model"] == SETTINGS["ANTHROPIC_MODEL"]
    config.set_config_value("ANTHROPIC_ENABLED", "false")
    assert not service._provider_configured("anthropic-messages")
    assert jev_search.available_channels(service, "北京天气", [], providers="anthropic-messages") == []
    assert (await service.test_provider_connection("anthropic-messages"))["status"] == "disabled"


@pytest.mark.parametrize("key,value", [
    ("ANTHROPIC_MAX_TOKENS", "0"), ("ANTHROPIC_MAX_TOKENS", "2.5"),
    ("ANTHROPIC_WEB_SEARCH_MAX_USES", "-1"), ("ANTHROPIC_STREAM", "maybe"),
])
def test_invalid_settings_fail_before_saving(key, value):
    assert not config.update_config_values({key: value})["ok"]


@pytest.mark.asyncio
async def test_include_domains_is_per_search_and_not_persisted(monkeypatch):
    config.update_config_values({**SETTINGS, "SMART_SEARCH_INTENT_ROUTER": "local"})
    requests = []

    def handler(request):
        requests.append(json.loads(request.content)["tools"][0])
        return httpx.Response(200, json=message())

    mock_http(monkeypatch, handler)
    first = await service.search("北京天气", providers="anthropic-messages",
                                 include_domains=["WEATHER.COM.CN,example.com", "weather.com.cn"])
    second = await service.search("北京天气", providers="anthropic-messages")
    assert first["ok"] and second["ok"]
    assert requests[0]["allowed_domains"] == ["weather.com.cn", "example.com"]
    assert "allowed_domains" not in requests[1]
    saved = json.loads(config.config_file.read_text(encoding="utf-8"))
    assert not any("DOMAIN" in key for key in saved)


@pytest.mark.asyncio
@pytest.mark.parametrize("provider,domains,field", [
    ("exa", ["weather.com.cn", "example.com"], "includeDomains"),
    ("zhipu", ["weather.com.cn"], "search_domain_filter"),
])
async def test_include_domains_reaches_other_supported_providers(monkeypatch, provider, domains, field):
    config.update_config_values({"SMART_SEARCH_INTENT_ROUTER": "local", f"{provider.upper()}_API_KEY": "key"})
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        if provider == "exa":
            return httpx.Response(200, json={"results": [{"url": URL, "title": "天气", "highlights": ["北京天气"]}]})
        return httpx.Response(200, json={"search_result": [{"link": URL, "title": "天气", "content": "北京天气"}]})

    mock_http(monkeypatch, handler)
    result = await service.search("北京天气", providers=provider, include_domains=domains)
    assert result["ok"]
    assert captured[0][field] == (domains if provider == "exa" else domains[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("provider,settings,domains", [
    ("openai-compatible", {"OPENAI_COMPATIBLE_API_URL": "https://relay.example/v1", "OPENAI_COMPATIBLE_API_KEY": "key"}, ["example.com"]),
    ("zhipu", {"ZHIPU_API_KEY": "key"}, ["example.com", "weather.com.cn"]),
])
async def test_unsupported_domain_filter_fails_without_network(provider, settings, domains):
    config.update_config_values({**settings, "SMART_SEARCH_INTENT_ROUTER": "local"})
    result = await service.search("北京天气", providers=provider, include_domains=domains)
    assert not result["ok"]
    assert result["error_type"] == "parameter_error"
    assert "--include-domains" in result["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", ["https://example.com", "example.com/path", "site:example.com", "*.example.com"])
async def test_include_domains_rejects_non_domains(domain):
    result = await service.search("weather", include_domains=[domain])
    assert result["error_type"] == "parameter_error"


@pytest.mark.asyncio
async def test_cli_forwards_include_domains_and_ai_help_documents_it(monkeypatch):
    from smart_search import cli
    from smart_search.skill_installer import _load_skill_files

    captured = {}

    async def fake_search(query, **kwargs):
        captured.update(kwargs)
        return {"ok": True, "content": "ok"}

    monkeypatch.setattr(service, "search", fake_search)
    args = cli.build_parser().parse_args([
        "search", "北京天气", "--providers", "anthropic-messages",
        "--include-domains", "weather.com.cn", "example.com", "--format", "json",
    ])
    assert await cli._run_async_impl(args) == 0
    assert captured["include_domains"] == ["weather.com.cn", "example.com"]
    files = dict(_load_skill_files())
    assert b"--include-domains" in files["SKILL.md"]
    assert b"--include-domains weather.com.cn" in files["references/command-patterns.md"]


@pytest.mark.asyncio
async def test_domain_filter_survives_fallback_without_unrestricted_channels(monkeypatch):
    config.update_config_values({
        **SETTINGS, "SMART_SEARCH_INTENT_ROUTER": "local", "ZHIPU_API_KEY": "zhipu-key", "XAI_API_KEY": "xai-key",
    })
    requests = []

    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if request.url.path.endswith("/messages"):
            assert payload["tools"][0]["allowed_domains"] == ["weather.com.cn"]
            return httpx.Response(401, json={"error": "unauthorized"})
        assert request.url.path.endswith("/web_search")
        assert payload["search_domain_filter"] == "weather.com.cn"
        return httpx.Response(200, json={"search_result": [{"link": URL, "title": "天气", "content": "北京天气"}]})

    mock_http(monkeypatch, handler)
    result = await service.search("北京天气", include_domains=["weather.com.cn"])
    assert result["ok"]
    assert len(requests) == 2
    assert "xai-responses" not in result["providers_used"]


