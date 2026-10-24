import json

import pytest

from smart_search.config import Config


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ([
            {"user": "disabled", "key": "disabled-key", "is_enable": False},
            {"user": "first", "key": "first-key", "is_enable": True},
            {"user": "second", "key": "second-key", "is_enable": True},
        ], "first-key"),
        ([
            {"key": "second-key", "is_enable": True},
            {"key": "first-key", "is_enable": True},
        ], "second-key"),
        ([{"key": "disabled-key", "is_enable": False}], ""),
        ([
            {"key": "", "is_enable": True},
            {"key": "second-key", "is_enable": True},
        ], ""),
        ([], ""),
        ("legacy-key", "legacy-key"),
    ],
)
def test_tavily_uses_only_first_enabled_key(value, expected):
    config = Config()
    config.config_file.write_text(json.dumps({"TAVILY_API_KEY": value}), encoding="utf-8")

    assert config.tavily_api_key == expected
    assert config.get_saved_config(masked=False)["TAVILY_API_KEY"] == expected
    with config.snapshot():
        assert config.tavily_api_key == expected
    assert json.loads(config.config_file.read_text(encoding="utf-8"))["TAVILY_API_KEY"] == value


def test_tavily_environment_overrides_key_array(monkeypatch):
    config = Config()
    config.config_file.write_text(json.dumps({
        "TAVILY_API_KEY": [{"user": "file-user", "key": "file-key", "is_enable": True}],
    }), encoding="utf-8")
    monkeypatch.setenv("TAVILY_API_KEY", "env-key")

    assert config.tavily_api_key == "env-key"
    with config.snapshot():
        assert config.tavily_api_key == "env-key"


@pytest.mark.parametrize("entry", [
    123,
    "old-array-key",
    {"key": 123, "is_enable": True},
    {"key": "key", "is_enable": "true"},
    {"key": "key"},
])
def test_tavily_rejects_invalid_entries(entry):
    config = Config()
    config.config_file.write_text(json.dumps({"TAVILY_API_KEY": [entry]}), encoding="utf-8")

    with pytest.raises(ValueError, match="string key and boolean is_enable"):
        _ = config.tavily_api_key
    with pytest.raises(ValueError, match="string key and boolean is_enable"):
        with config.snapshot():
            pass
