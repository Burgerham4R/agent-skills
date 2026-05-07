"""Data contracts for the TRTC eval toolchain.

All cross-script JSON payloads MUST be validated through these models.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Literal


class Constraints(BaseModel):
    """Code constraints for a single eval case. evaluator.py reads and executes grep."""

    must_include: list[str] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    must_include_in_files: dict[str, list[str]] = Field(default_factory=dict)
    file_count_min: int = 1


class Weights(BaseModel):
    """Scoring weights. Defined in cases.json, NEVER in skill prompts."""

    w_must_include: float = 0.6
    w_must_not: float = 0.4
    w_events: float = 0.7
    w_compile_bonus: float = 0.3
    w_static_in_final: float = 0.4
    w_dynamic_in_final: float = 0.6

    @field_validator("w_static_in_final", "w_dynamic_in_final")
    @classmethod
    def _check_final_sum(cls, v: float) -> float:
        return v


class Acceptance(BaseModel):
    """Pass thresholds. Either static or dynamic not meeting threshold => passed=False."""

    static_score_min: float = 0.7
    dynamic_score_min: float = 0.7
    must_compile: bool = True


class InjectionPoint(BaseModel):
    """A single ability's code injection point (pairs with template INJECTION.json, see §5.2)."""

    target_file: str
    replace_mode: Literal["overwrite", "append", "between_markers"] = "overwrite"
    marker_begin: str | None = None
    marker_end: str | None = None


class TraceStep(BaseModel):
    """A single line written to trace.jsonl by orchestrator."""

    step: Literal[
        "_meta", "run_ai", "evaluator", "demo_build",
        "log_stream_start", "demo_run", "log_stream_stop", "runtime_monitor"
    ]
    ts: str
    exit_code: int | None = None
    duration_sec: float | None = None
    status: Literal["ok", "fail", "skipped", "timeout"] | None = None
    reason: str | None = None
    stdout_tail: str | None = None
    stderr_tail: str | None = None
    nonce: str | None = None


class Case(BaseModel):
    """A single eval case from cases.json."""

    test_id: str
    ability: str
    product: Literal["chat", "call", "rtc-engine", "live", "room", "conference"]
    platform: Literal["ios", "android", "web", "flutter", "electron", "unity"]
    scenario: str | None = None
    user_prompt: str
    expected_slice_ids: list[str]
    constraints: Constraints
    expected_events: list[str]
    acceptance: Acceptance
    weights: Weights = Field(default_factory=Weights)
    demo_injection_map: dict[str, InjectionPoint] = Field(default_factory=dict)
    auto_run_flow: list[str] = Field(default_factory=list)
    tags: list[str]
    status: Literal["active", "draft"]


class StaticResult(BaseModel):
    """Output of evaluator.py."""

    test_id: str
    must_include_hit: float
    must_not_include_clean: float
    hits: list[str]
    misses: list[str]
    dirty: list[str]
    score: float


class DynamicResult(BaseModel):
    """Output of runtime_monitor.py."""

    test_id: str
    compile_ok: bool
    compile_exit_code: int
    events_captured: list[str]
    events_missing: list[str]
    events_hit_ratio: float
    nonce_seen: bool = False
    score: float


class CaseSummary(BaseModel):
    """Per-case summary written by orchestrator."""

    test_id: str
    ability: str
    platform: str
    static_result: StaticResult | None
    dynamic_result: DynamicResult | None
    final_score: float
    passed: bool
    failure_reason: str | None = None
    artifacts_dir: str
    duration_sec: float
