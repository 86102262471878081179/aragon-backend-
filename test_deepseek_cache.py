import pytest

from main import DeepSeekBooster


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("language", "en"),
        ("model", "model-b"),
        ("max_tokens", 2048),
        ("system_prompt", "Respond concisely."),
        ("response_format", {"type": "json_object"}),
        ("entropy", 0.7),
        ("apply_veto", True),
    ],
)
def test_result_parameters_are_in_cache_key(parameter, value):
    baseline = {
        "language": None,
        "model": None,
        "max_tokens": None,
        "system_prompt": None,
        "response_format": None,
        "entropy": None,
        "apply_veto": False,
    }
    changed = {**baseline, parameter: value}

    assert DeepSeekBooster._cache_key(
        "prompt", "context", 3, baseline
    ) != DeepSeekBooster._cache_key(
        "prompt", "context", 3, changed
    )


def test_prompt_context_and_depth_are_in_cache_key():
    key = DeepSeekBooster._cache_key("p", "c", 3, {})
    assert key != DeepSeekBooster._cache_key("p2", "c", 3, {})
    assert key != DeepSeekBooster._cache_key("p", "c2", 3, {})
    assert key != DeepSeekBooster._cache_key("p", "c", 4, {})


def test_cache_returns_independent_deep_copies():
    booster = DeepSeekBooster()

    first = booster.boost("prompt")
    first["reasoning_trace"][0]["note"] = "changed"
    first["parameters"]["response_format"] = {"changed": True}

    second = booster.boost("prompt")

    assert second["reasoning_trace"][0]["note"] != "changed"
    assert second["parameters"]["response_format"] is None


def test_cache_is_limited_to_512_entries():
    booster = DeepSeekBooster()

    for i in range(513):
        booster.boost(f"prompt-{i}")

    assert len(booster.cache) == 512
    assert not any('"prompt":"prompt-0"' in key for key in booster.cache)


def test_cache_uses_lru_eviction():
    booster = DeepSeekBooster()

    for i in range(512):
        booster.boost(f"prompt-{i}")

    # Prompt 0 wird zum zuletzt verwendeten Eintrag.
    booster.boost("prompt-0")
    booster.boost("new-prompt")

    assert len(booster.cache) == 512
    assert any('"prompt":"prompt-0"' in key for key in booster.cache)
    assert not any('"prompt":"prompt-1"' in key for key in booster.cache)


def test_non_json_response_format_is_rejected():
    booster = DeepSeekBooster()

    with pytest.raises(ValueError, match="JSON"):
        booster.boost("prompt", response_format=object())


@pytest.mark.parametrize("depth", [0, -1, 11, True])
def test_invalid_depth_is_rejected(depth):
    with pytest.raises(ValueError, match="depth"):
        DeepSeekBooster().boost("prompt", depth=depth)
