#!/usr/bin/env bash
# Round-2 revision batch. Sequential: concurrent runs would collide on provider rate limits.
set -u
cd "$(dirname "$0")/../.."
echo "=== r2_anchor64 ==="; python -m harness.run --config harness/configs/r2_anchor64.yaml || echo "FAILED: r2_anchor64"
echo "=== r2_budget256 ==="; python -m harness.run --config harness/configs/r2_budget256.yaml || echo "FAILED: r2_budget256"
echo "=== r2_conf ==="; python -m harness.run --config harness/configs/r2_conf.yaml || echo "FAILED: r2_conf"
echo "=== r2_prompt_v2 ==="; python -m harness.run --config harness/configs/r2_prompt_v2.yaml || echo "FAILED: r2_prompt_v2"
echo "=== r2_prompt_v3 ==="; python -m harness.run --config harness/configs/r2_prompt_v3.yaml || echo "FAILED: r2_prompt_v3"
echo "=== r2_draw2 ==="; python -m harness.run --config harness/configs/r2_draw2.yaml || echo "FAILED: r2_draw2"
echo "=== r2_draw3 ==="; python -m harness.run --config harness/configs/r2_draw3.yaml || echo "FAILED: r2_draw3"
