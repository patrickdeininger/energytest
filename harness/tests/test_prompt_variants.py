"""Tests for prompt variants, confidence elicitation, and provider pinning.

These back the round-2 revision runs: prompt-sensitivity (R2#6, R3#3), a
threshold-sweepable confidence score for PR curves / VD-Score (R2#8), and
deterministic provider routing so the configured price is the price actually
paid (R2#4, R3#3).
"""

import pytest

from harness.backends.api import OpenAICompatibleClient, RawCompletion
from harness.config import RunConfig, load_config, make_backend
from harness.schema import GenParams, Task
from harness.tasks.vuln_detect import (
    PROMPT_TEMPLATES,
    build_prompt,
    parse,
)


def _task(code="int f(){char b[8];gets(b);return 0;}"):
    return Task(id="t1", code=code, label=1, cwe="CWE-120", source="fixture")


# --- prompt variants -------------------------------------------------------

def test_default_variant_is_v1_and_is_byte_identical_to_the_anchor():
    """v1 must reproduce the July run's prompt exactly, or the anchor re-run is
    not an anchor and prompt_hash continuity across epochs is broken."""
    assert build_prompt(_task()) == build_prompt(_task(), variant="v1")
    p = build_prompt(_task(code="MARKER"))
    assert p.startswith("You are a security code reviewer.")
    assert p.rstrip().endswith("Is this code vulnerable?")


@pytest.mark.parametrize("variant", sorted(PROMPT_TEMPLATES))
def test_every_variant_embeds_the_code_and_asks_the_question(variant):
    p = build_prompt(_task(code="MARKER_CODE_123"), variant=variant)
    assert "MARKER_CODE_123" in p
    assert "vulnerab" in p.lower()


@pytest.mark.parametrize("variant", sorted(PROMPT_TEMPLATES))
def test_every_variant_truncates_long_code(variant):
    p = build_prompt(_task(code="A" * 5000), max_code_chars=100, variant=variant)
    assert "truncat" in p.lower()
    assert p.count("A") <= 120


def test_variants_are_actually_different_prompts():
    """A 'paraphrase' that collides with the anchor measures nothing."""
    rendered = {v: build_prompt(_task(), variant=v) for v in PROMPT_TEMPLATES}
    assert len(set(rendered.values())) == len(rendered)


def test_v3_flips_the_option_order_relative_to_v1():
    """v1 offers YES first, v3 offers NO first -- that asymmetry is the point of
    the variant, so assert it rather than trusting the prose."""
    v1, v3 = build_prompt(_task(), variant="v1"), build_prompt(_task(), variant="v3")
    assert v1.index('"YES"') < v1.index('"NO"')
    assert v3.index('"NO"') < v3.index('"YES"')


def test_unknown_variant_raises():
    with pytest.raises(KeyError):
        build_prompt(_task(), variant="nope")


# --- confidence parsing ----------------------------------------------------

def test_parses_labelled_verdict_and_confidence():
    p = parse("VERDICT: YES\nCONFIDENCE: 85\nBuffer overflow via gets().")
    assert p.label == 1 and p.parsed_ok
    assert p.confidence == pytest.approx(0.85)


def test_parses_labelled_negative_verdict():
    p = parse("VERDICT: NO\nCONFIDENCE: 12")
    assert p.label == 0 and p.parsed_ok
    assert p.confidence == pytest.approx(0.12)


def test_labelled_verdict_wins_over_body_text_mentioning_vulnerable():
    """The explanation almost always contains the word 'vulnerable'; the labelled
    verdict must not be overridden by it."""
    p = parse("VERDICT: NO\nCONFIDENCE: 5\nThis is not vulnerable; no exploitable path.")
    assert p.label == 0
    assert p.confidence == pytest.approx(0.05)


def test_confidence_is_clamped_and_tolerates_percent_and_decimals():
    assert parse("VERDICT: YES\nCONFIDENCE: 140").confidence == pytest.approx(1.0)
    assert parse("VERDICT: YES\nCONFIDENCE: -3").confidence == pytest.approx(0.0)
    assert parse("VERDICT: YES\nCONFIDENCE: 72%").confidence == pytest.approx(0.72)
    assert parse("VERDICT: YES\nCONFIDENCE: 0.9").confidence == pytest.approx(0.9)


def test_confidence_is_none_when_absent_and_legacy_parsing_is_unchanged():
    p = parse("YES\n\nThe function calls gets() on a fixed buffer.")
    assert p.label == 1 and p.parsed_ok and p.confidence is None


def test_verdict_label_without_confidence_still_parses():
    p = parse("VERDICT: YES")
    assert p.label == 1 and p.parsed_ok and p.confidence is None


def test_confidence_without_verdict_falls_back_to_leading_token():
    p = parse("YES\nCONFIDENCE: 60")
    assert p.label == 1 and p.confidence == pytest.approx(0.60)


# --- provider pinning ------------------------------------------------------

class _FakeSDK:
    def __init__(self):
        self.kwargs = None
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.kwargs = kwargs

        class _U:
            prompt_tokens, completion_tokens = 10, 3

        class _M:
            content, reasoning = "YES", None

        class _C:
            message = _M()

        class _R:
            choices, usage, provider = [_C()], _U(), "DeepInfra"

        return _R()


def test_provider_order_is_sent_and_fallbacks_disabled():
    sdk = _FakeSDK()
    c = OpenAICompatibleClient(sdk_client=sdk, provider_order=["DeepInfra"])
    c.complete("meta-llama/llama-3.3-70b-instruct", "p", GenParams())
    assert sdk.kwargs["extra_body"]["provider"] == {
        "order": ["DeepInfra"],
        "allow_fallbacks": False,
    }


def test_provider_order_coexists_with_reasoning_extra_body():
    sdk = _FakeSDK()
    c = OpenAICompatibleClient(
        sdk_client=sdk, extra_body={"reasoning": {"enabled": False}}, provider_order=["Novita"]
    )
    c.complete("m", "p", GenParams())
    eb = sdk.kwargs["extra_body"]
    assert eb["reasoning"] == {"enabled": False}
    assert eb["provider"]["order"] == ["Novita"]


def test_no_provider_key_when_unpinned():
    sdk = _FakeSDK()
    OpenAICompatibleClient(sdk_client=sdk).complete("m", "p", GenParams())
    assert "provider" not in (sdk.kwargs.get("extra_body") or {})


def test_routed_provider_is_captured_on_the_completion():
    """Which provider actually served the request is the difference between the
    configured price and the price paid -- it must be logged, not assumed."""
    sdk = _FakeSDK()
    raw = OpenAICompatibleClient(sdk_client=sdk).complete("m", "p", GenParams())
    assert isinstance(raw, RawCompletion)
    assert raw.provider == "DeepInfra"


def test_make_backend_threads_provider_order_from_config():
    spec = RunConfig(
        run_name="t",
        dataset={"source": "fixture", "path": "x"},
        models=[
            {
                "id": "llama",
                "backend": "api",
                "params": {"provider": "openrouter", "provider_order": ["DeepInfra"]},
            }
        ],
        meters=["cost"],
    ).models[0]
    backend = make_backend(spec, seed=0)
    assert backend.client._provider_order == ["DeepInfra"]


# --- config plumbing -------------------------------------------------------

def test_gen_config_defaults_to_v1_and_accepts_a_variant(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        "run_name: t\n"
        "dataset: {source: fixture, path: x}\n"
        "models: [{id: m, backend: mock}]\n"
        "meters: [cost]\n"
        "gen: {prompt_variant: v2}\n",
        encoding="utf-8",
    )
    assert load_config(str(cfg)).gen.prompt_variant == "v2"

    cfg2 = tmp_path / "c2.yaml"
    cfg2.write_text(
        "run_name: t\n"
        "dataset: {source: fixture, path: x}\n"
        "models: [{id: m, backend: mock}]\n"
        "meters: [cost]\n",
        encoding="utf-8",
    )
    assert load_config(str(cfg2)).gen.prompt_variant == "v1"


def test_unknown_prompt_variant_is_rejected_at_config_load(tmp_path):
    """Fail before spending, not after 12,000 API calls."""
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        "run_name: t\n"
        "dataset: {source: fixture, path: x}\n"
        "models: [{id: m, backend: mock}]\n"
        "meters: [cost]\n"
        "gen: {prompt_variant: typo}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_config(str(cfg))


def test_concurrency_override_from_env(tmp_path, monkeypatch):
    """The concurrency sweep reuses one config across levels via this override."""
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        "run_name: t\n"
        "dataset: {source: fixture, path: x}\n"
        "models: [{id: m, backend: mock}]\n"
        "meters: [cost]\n"
        "concurrency: 10\n",
        encoding="utf-8",
    )
    assert load_config(str(cfg)).concurrency == 10
    monkeypatch.setenv("HARNESS_CONCURRENCY_OVERRIDE", "32")
    assert load_config(str(cfg)).concurrency == 32
