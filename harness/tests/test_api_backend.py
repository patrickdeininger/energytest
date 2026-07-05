"""Tests for the API backend and OpenAI-compatible client.

No network: APIBackend takes an injected client, and OpenAICompatibleClient takes
an injected SDK object. This unit-tests the mapping logic (which is where bugs
hide) without spending money.
"""

from harness.schema import GenParams
from harness.backends.api import APIBackend, RawCompletion, OpenAICompatibleClient


class FakeClient:
    def __init__(self, raw):
        self.raw = raw
        self.calls = []

    def complete(self, model, prompt, params):
        self.calls.append((model, prompt, params))
        return self.raw


def test_api_backend_maps_raw_completion_to_response():
    fake = FakeClient(RawCompletion(text="YES vulnerable", input_tokens=120, output_tokens=8))
    backend = APIBackend(model="vendor/model-x", client=fake)
    r = backend.generate("prompt here", GenParams(max_output_tokens=64))
    assert r.text == "YES vulnerable"
    assert r.input_tokens == 120
    assert r.output_tokens == 8
    assert fake.calls[0][0] == "vendor/model-x"
    assert fake.calls[0][1] == "prompt here"


# --- Fake OpenAI SDK objects (shape of openai>=1.0 chat.completions.create) ---
class _Msg:
    def __init__(self, content, reasoning=None):
        self.content = content
        self.reasoning = reasoning


class _Choice:
    def __init__(self, content, reasoning=None):
        self.message = _Msg(content, reasoning)


class _Usage:
    def __init__(self, p, c):
        self.prompt_tokens = p
        self.completion_tokens = c


class _Resp:
    def __init__(self, content, p, c, reasoning=None):
        self.choices = [_Choice(content, reasoning)]
        self.usage = _Usage(p, c)


class _FakeCompletions:
    def __init__(self, resp):
        self._resp = resp
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self._resp


class _FakeChat:
    def __init__(self, resp):
        self.completions = _FakeCompletions(resp)


class _FakeSDK:
    def __init__(self, resp):
        self.chat = _FakeChat(resp)


def test_openai_compatible_client_maps_sdk_response_and_forwards_params():
    sdk = _FakeSDK(_Resp("NO, not vulnerable", 100, 5))
    client = OpenAICompatibleClient(api_key="x", sdk_client=sdk)
    raw = client.complete("m1", "the prompt", GenParams(temperature=0.0, max_output_tokens=32))
    assert raw.text == "NO, not vulnerable"
    assert raw.input_tokens == 100
    assert raw.output_tokens == 5
    kw = sdk.chat.completions.kwargs
    assert kw["model"] == "m1"
    assert kw["messages"] == [{"role": "user", "content": "the prompt"}]
    assert kw["temperature"] == 0.0
    assert kw["max_tokens"] == 32


def test_openai_compatible_client_handles_null_content():
    sdk = _FakeSDK(_Resp(None, 10, 0))
    client = OpenAICompatibleClient(api_key="x", sdk_client=sdk)
    raw = client.complete("m", "p", GenParams())
    assert raw.text == ""
    assert raw.output_tokens == 0


def test_client_falls_back_to_reasoning_when_content_empty():
    # Reasoning models leave content empty and put tokens in `reasoning`.
    sdk = _FakeSDK(_Resp("", 100, 60, reasoning="...analysis... therefore it is vulnerable. YES"))
    client = OpenAICompatibleClient(api_key="x", sdk_client=sdk)
    raw = client.complete("m", "p", GenParams())
    assert "YES" in raw.text  # recovered the verdict from the reasoning channel
    assert raw.output_tokens == 60


def test_client_forwards_extra_body_for_reasoning_control():
    sdk = _FakeSDK(_Resp("NO", 10, 5))
    client = OpenAICompatibleClient(api_key="x", sdk_client=sdk, extra_body={"reasoning": {"enabled": False}})
    client.complete("m", "p", GenParams())
    assert sdk.chat.completions.kwargs["extra_body"] == {"reasoning": {"enabled": False}}
