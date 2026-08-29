"""Run configuration models + backend/meter registries.

The runner is closed for modification: new backends/meters/datasets are added
here by registering a name, never by editing the runner loop.
"""

from __future__ import annotations

import os

import yaml
from pydantic import BaseModel, Field, field_validator

from harness.backends.api import APIBackend, OpenAICompatibleClient
from harness.backends.mock import MockBackend
from harness.meters import CostMeter, LatencyMeter, MockEnergyMeter, EstimatedEnergyMeter

# provider -> (default base_url, api-key env var)
_PROVIDERS = {
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY"),
    "vllm": ("http://localhost:8000/v1", "VLLM_API_KEY"),  # local vLLM OpenAI server (M3)
}

_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/llm-vuln-bench",
    "X-Title": "llm-vuln-detection-benchmark",
}


class ModelSpec(BaseModel):
    id: str
    backend: str
    params: dict = {}
    price: dict = {"in": 0.0, "out": 0.0}  # USD per 1M tokens


class DatasetCfg(BaseModel):
    source: str
    path: str
    n: int | None = None
    stratify_by: str | None = None
    # field mapping for `source: jsonl` (e.g. PrimeVul: func/target/idx)
    code_field: str = "code"
    label_field: str = "label"
    id_field: str = "id"
    cwe_field: str | None = None


class GenCfg(BaseModel):
    temperature: float = 0.0
    max_output_tokens: int = 128
    max_code_chars: int | None = None  # truncate long inputs to bound cost/context
    # Which prompt template to use; "v1" is the anchor used by the original runs.
    prompt_variant: str = "v1"

    @field_validator("prompt_variant")
    @classmethod
    def _known_variant(cls, v: str) -> str:
        from harness.tasks.vuln_detect import PROMPT_TEMPLATES

        if v not in PROMPT_TEMPLATES:
            raise ValueError(
                f"unknown prompt_variant {v!r}; known: {sorted(PROMPT_TEMPLATES)}"
            )
        return v


class RunConfig(BaseModel):
    run_name: str
    seed: int = 0
    dataset: DatasetCfg
    task: str = "vuln_detect_binary"
    models: list[ModelSpec]
    meters: list[str]
    reps: int = 1
    gen: GenCfg = Field(default_factory=GenCfg)
    concurrency: int = 1  # parallel in-flight requests (use 1 for latency-fidelity runs)
    output_dir: str = "harness/runs"


def load_config(path: str) -> RunConfig:
    """Load a run config. HARNESS_CONCURRENCY_OVERRIDE lets the concurrency sweep
    reuse one config across levels without writing four near-identical files."""
    with open(path, encoding="utf-8") as fh:
        cfg = RunConfig(**yaml.safe_load(fh))
    override = os.environ.get("HARNESS_CONCURRENCY_OVERRIDE")
    if override:
        cfg = cfg.model_copy(update={"concurrency": int(override)})
    return cfg


def make_backend(spec: ModelSpec, seed: int):
    if spec.backend == "mock":
        return MockBackend(behavior=spec.params.get("behavior", "balanced"), seed=seed)
    if spec.backend == "api":
        provider = spec.params.get("provider", "openrouter")
        if provider not in _PROVIDERS:
            raise ValueError(f"unknown provider: {provider!r}")
        default_base, key_env = _PROVIDERS[provider]
        base_url = spec.params.get("base_url", default_base)
        api_key = os.environ.get(key_env)
        headers = _OPENROUTER_HEADERS if provider == "openrouter" else None
        # Optional reasoning control, e.g. params.reasoning: {enabled: false} or {effort: low}
        extra_body = {"reasoning": spec.params["reasoning"]} if "reasoning" in spec.params else None
        client = OpenAICompatibleClient(
            api_key=api_key,
            base_url=base_url,
            extra_headers=headers,
            extra_body=extra_body,
            provider_order=spec.params.get("provider_order"),
        )
        return APIBackend(model=spec.params.get("model", spec.id), client=client)
    raise ValueError(f"unknown backend: {spec.backend!r}")


def make_meter(name: str, spec: ModelSpec):
    if name == "cost":
        return CostMeter(price_in=spec.price.get("in", 0.0), price_out=spec.price.get("out", 0.0))
    if name == "latency":
        return LatencyMeter()
    if name == "energy_mock":
        return MockEnergyMeter()
    if name == "energy_estimated":
        return EstimatedEnergyMeter(active_params_b=spec.params.get("active_params_b", 0.0))
    if name == "energy_measured":
        # GPU-only: constructs a live NVML reader (needs pynvml + a GPU).
        from harness.meters import ZeusEnergyMeter, NvmlEnergyReader

        reader = NvmlEnergyReader(gpu_index=spec.params.get("gpu_index", 0))
        return ZeusEnergyMeter(reader=reader, idle_power_w=spec.params.get("idle_power_w", 0.0))
    raise ValueError(f"unknown meter: {name!r}")
