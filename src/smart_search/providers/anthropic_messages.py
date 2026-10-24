"""Anthropic Messages search with server-side web search and structured citations."""
import json
from typing import Any

import httpx

from .openai_compatible import OpenAICompatibleSearchProvider, get_local_time_info
from ..provider_errors import ProviderCallError
from ..utils import search_prompt


class AnthropicMessagesSearchProvider(OpenAICompatibleSearchProvider):
    def __init__(self, api_url: str, api_key: str, model: str, *, max_tokens: int = 2048,
                 stream: bool = False, api_version: str = "2023-06-01",
                 max_uses: int = 5):
        base_url = api_url.strip().rstrip("/")
        if base_url.endswith("/messages"):
            base_url = base_url[:-len("/messages")]
        super().__init__(base_url, api_key, model, stream=stream)
        self.api_mode = "messages"
        self.max_tokens = max_tokens
        self.api_version = api_version
        self.max_uses = max_uses

    def get_provider_name(self) -> str:
        return "Anthropic Messages"

    def _api_endpoint(self) -> str:
        return f"{self.api_url}/messages"

    def _build_api_headers(self) -> dict:
        return {**super()._build_api_headers(), "anthropic-version": self.api_version}

    def _build_request_payload(self, instructions: str, user_content: str, *, stream: bool) -> dict[str, Any]:
        return {
            "model": self.model, "max_tokens": self.max_tokens, "stream": stream,
            "system": instructions, "messages": [{"role": "user", "content": user_content}],
        }

    async def search(self, query: str, platform: str = "", ctx=None, *, include_domains: list[str] | None = None) -> str:
        content = get_local_time_info() + "\n" + query
        if platform:
            content += f"\n\nFocus the search on these platforms: {platform}"
        payload = self._build_request_payload(search_prompt, content, stream=self.stream)
        tool = {"type": "web_search_20250305", "name": "web_search", "max_uses": self.max_uses}
        if include_domains:
            tool["allowed_domains"] = include_domains
        payload["tools"] = [tool]
        return await self._execute_with_transport_fallback(self._build_api_headers(), payload, ctx)

    def _message_content(self, data: Any) -> str:
        if not isinstance(data, dict):
            raise ProviderCallError("parse_error", "Messages response must be an object")
        if data.get("type") == "error" or data.get("error"):
            raise ProviderCallError("provider_error", f"Messages error: {data.get('error')}",
                                    additional_secrets=(self.api_key,))
        if data.get("type") != "message" or not isinstance(data.get("content"), list):
            raise ProviderCallError("parse_error", "Messages response has no message content")
        if data.get("stop_reason") not in {"end_turn", "stop_sequence"}:
            raise ProviderCallError("provider_error", f"Messages did not finish: {data.get('stop_reason')}")
        texts, sources = [], []
        for block in data["content"]:
            if not isinstance(block, dict):
                raise ProviderCallError("parse_error", "Invalid Messages content block")
            if block.get("type") == "text":
                text = block.get("text")
                if not isinstance(text, str):
                    raise ProviderCallError("parse_error", "Messages text block has no text")
                texts.append(text)
                sources = self._merge_citations(sources, self._normalize_citations(block.get("citations")))
            elif block.get("type") == "web_search_tool_result":
                results = block.get("content")
                if isinstance(results, dict) and results.get("type") == "web_search_tool_result_error":
                    raise ProviderCallError("provider_error", f"Messages web search failed: {results.get('error_code')}")
                if isinstance(results, list):
                    sources = self._merge_citations(sources, self._normalize_citations([
                        item for item in results if isinstance(item, dict) and item.get("type") == "web_search_result"
                    ]))
        answer = "".join(texts).strip()
        if not answer:
            raise ProviderCallError("provider_error", "Messages completed without text content")
        return self._append_sources(answer, sources)

    async def _parse_completion_response(self, response: httpx.Response, ctx=None) -> str:
        if response.text.lstrip().startswith(("event:", "data:")):
            return await self._parse_streaming_response(response, ctx)
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderCallError("parse_error", "Messages response was not JSON") from exc
        return self._message_content(data)

    async def _parse_streaming_response(self, response, ctx=None) -> str:
        message: dict[str, Any] | None = None
        blocks: dict[int, dict] = {}
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
            except ValueError as exc:
                raise ProviderCallError("parse_error", "Invalid Messages stream JSON") from exc
            if not isinstance(event, dict):
                raise ProviderCallError("parse_error", "Invalid Messages stream event")
            kind = event.get("type")
            if kind == "error":
                raise ProviderCallError("provider_error", f"Messages stream error: {event.get('error')}",
                                        additional_secrets=(self.api_key,))
            if kind == "message_start":
                message = event.get("message")
                if not isinstance(message, dict):
                    raise ProviderCallError("parse_error", "Messages stream has no message object")
            elif kind == "content_block_start":
                index, block = event.get("index"), event.get("content_block")
                if not isinstance(index, int) or not isinstance(block, dict):
                    raise ProviderCallError("parse_error", "Invalid Messages stream block")
                blocks[index] = block
            elif kind == "content_block_delta":
                block, delta = blocks.get(event.get("index")), event.get("delta")
                if block is None or not isinstance(delta, dict):
                    raise ProviderCallError("parse_error", "Messages delta has no content block")
                if delta.get("type") == "text_delta":
                    if not isinstance(delta.get("text"), str):
                        raise ProviderCallError("parse_error", "Invalid Messages text delta")
                    block["text"] = block.get("text", "") + delta["text"]
                elif delta.get("type") == "citations_delta":
                    block.setdefault("citations", []).append(delta.get("citation"))
            elif kind == "message_delta":
                if message is None or not isinstance(event.get("delta"), dict):
                    raise ProviderCallError("parse_error", "Messages delta has no message")
                message.update(event["delta"])
            elif kind == "message_stop":
                if message is None:
                    raise ProviderCallError("parse_error", "Messages stream ended without a message")
                message["content"] = [blocks[index] for index in sorted(blocks)]
                return self._message_content(message)
        raise ProviderCallError("parse_error", "Messages stream ended before message_stop")
