#!/usr/bin/env python3
"""
Playbook engine: schema, validation, variable substitution, and execution.

Playbook format (YAML or JSON) example:

version: 1
name: "Restart Service"
category: "infrastructure"
description: "Restart a systemd service and verify status"
parameters:
  - name: service_name
    required: true
    description: "Systemd service name"
prerequisites:
  - type: "non_empty"
    param: "service_name"
steps:
  - id: check_status
    name: "Check service status"
    action: "shell"
    args:
      command: "systemctl is-active ${service_name} || true"
    outputs:
      - name: current_status
        from: stdout
  - id: restart_service
    name: "Restart service"
    action: "shell"
    args:
      command: "sudo systemctl restart ${service_name}"
    when:
      - type: "not_equals"
        left: "${current_status}"
        right: "active"
  - id: verify
    name: "Verify service status"
    action: "shell"
    args:
      command: "systemctl is-active ${service_name}"
    validations:
      - type: "equals"
        left: "${stdout}"
        right: "active"

NOTE: For safety, shell execution is disabled by default. Pass allow_unsafe_shell=True
to enable. Supported safe actions include: noop, wait, http_request.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from string import Template
from typing import Any, Dict, List, Optional, Tuple

import httpx


def _substitute(value: Any, variables: Dict[str, Any]) -> Any:
    """Recursively substitute ${var} placeholders using string.Template semantics."""
    if isinstance(value, str):
        try:
            return Template(value).safe_substitute(variables)
        except Exception:
            return value
    if isinstance(value, list):
        return [_substitute(v, variables) for v in value]
    if isinstance(value, dict):
        return {k: _substitute(v, variables) for k, v in value.items()}
    return value


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return False


@dataclass
class StepResult:
    step_id: str
    name: str
    started_at: float
    finished_at: float
    status: str  # "success" | "skipped" | "failed"
    outputs: Dict[str, Any]
    error: Optional[str] = None


class PlaybookValidationError(Exception):
    pass


class PlaybookExecutionError(Exception):
    pass


class PlaybookEngine:
    """Validates and executes playbooks deterministically with variable passing."""

    def __init__(self, allow_unsafe_shell: bool = False):
        self.allow_unsafe_shell = allow_unsafe_shell

    def validate(self, spec: Dict[str, Any]) -> None:
        # Basic schema checks
        if not isinstance(spec, dict):
            raise PlaybookValidationError("Playbook must be an object")
        if not spec.get("name"):
            raise PlaybookValidationError("Playbook 'name' is required")
        if not isinstance(spec.get("steps"), list) or not spec["steps"]:
            raise PlaybookValidationError("Playbook must include non-empty 'steps' list")

        # Validate parameters list
        params = spec.get("parameters", [])
        if params and not isinstance(params, list):
            raise PlaybookValidationError("'parameters' must be a list")
        for p in params:
            if not isinstance(p, dict) or not p.get("name"):
                raise PlaybookValidationError("Each parameter must be an object with 'name'")

        # Validate each step
        seen_ids: set[str] = set()
        for idx, step in enumerate(spec["steps"], 1):
            if not isinstance(step, dict):
                raise PlaybookValidationError(f"Step {idx} must be an object")
            step_id = step.get("id") or f"step_{idx}"
            if step_id in seen_ids:
                raise PlaybookValidationError(f"Duplicate step id: {step_id}")
            seen_ids.add(step_id)
            if not step.get("action"):
                raise PlaybookValidationError(f"Step {step_id} missing 'action'")
            if step["action"] == "shell" and not self.allow_unsafe_shell:
                # Permit definition but will require explicit flag at execution
                pass

    async def execute(self, spec: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[StepResult], Dict[str, Any]]:
        self.validate(spec)
        variables: Dict[str, Any] = {}
        parameters = parameters or {}

        # Check prerequisites
        for prereq in spec.get("prerequisites", []) or []:
            if prereq.get("type") == "non_empty":
                param = prereq.get("param")
                if not parameters.get(param):
                    raise PlaybookValidationError(f"Prerequisite failed: parameter '{param}' must be non-empty")

        results: List[StepResult] = []
        success = True

        for idx, raw_step in enumerate(spec["steps"], 1):
            step = json.loads(json.dumps(raw_step))  # deep copy
            step_id = step.get("id") or f"step_{idx}"
            name = step.get("name") or step_id
            started_at = time.time()

            # Build context for substitution
            context_vars = {**parameters, **variables}
            step = _substitute(step, context_vars)

            # Evaluate 'when' conditions
            when_conditions = step.get("when") or []
            should_run = True
            for cond in when_conditions:
                if not self._eval_condition(cond, context_vars):
                    should_run = False
                    break

            if not should_run:
                finished_at = time.time()
                results.append(StepResult(
                    step_id=step_id,
                    name=name,
                    started_at=started_at,
                    finished_at=finished_at,
                    status="skipped",
                    outputs={}
                ))
                continue

            # Execute action
            try:
                action = step.get("action")
                args = step.get("args") or {}
                outputs: Dict[str, Any] = {}

                if action == "noop":
                    await asyncio.sleep(float(args.get("delay", 0)))
                    outputs["message"] = args.get("message", "noop")

                elif action == "wait":
                    await asyncio.sleep(float(args.get("seconds", 1)))
                    outputs["slept"] = args.get("seconds", 1)

                elif action == "http_request":
                    method = str(args.get("method", "GET")).upper()
                    url = str(args.get("url"))
                    if not url:
                        raise PlaybookExecutionError("http_request requires 'url'")
                    timeout = float(args.get("timeout", 20))
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        resp = await client.request(method, url, headers=args.get("headers"), json=args.get("json"), data=args.get("data"))
                    outputs["status_code"] = resp.status_code
                    outputs["headers"] = dict(resp.headers)
                    # Try parse JSON, else text
                    try:
                        outputs["body_json"] = resp.json()
                    except Exception:
                        outputs["body"] = resp.text

                elif action == "shell":
                    if not self.allow_unsafe_shell:
                        raise PlaybookExecutionError("Shell action is disabled. Enable with allow_unsafe_shell=True.")
                    # Cautious shell execution with asyncio subprocess
                    cmd = args.get("command")
                    if not cmd:
                        raise PlaybookExecutionError("shell requires 'command'")
                    proc = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout_b, stderr_b = await proc.communicate()
                    outputs["returncode"] = proc.returncode
                    outputs["stdout"] = stdout_b.decode().strip()
                    outputs["stderr"] = stderr_b.decode().strip()
                    if proc.returncode != 0:
                        raise PlaybookExecutionError(f"Non-zero return code: {proc.returncode}")

                else:
                    raise PlaybookExecutionError(f"Unknown action: {action}")

                # Export outputs to variables
                for out in step.get("outputs") or []:
                    name_key = out.get("name")
                    if not name_key:
                        continue
                    source = out.get("from", "value")
                    if source == "value":
                        variables[name_key] = out.get("value")
                    elif source in ("stdout", "stderr", "returncode", "status_code", "body", "body_json"):
                        variables[name_key] = outputs.get(source)
                    else:
                        # Generic mapping
                        variables[name_key] = outputs.get(source)

                # Validations
                for val in step.get("validations") or []:
                    if not self._eval_condition(val, {**context_vars, **variables, **outputs}):
                        raise PlaybookExecutionError(f"Validation failed: {val}")

                finished_at = time.time()
                results.append(StepResult(
                    step_id=step_id,
                    name=name,
                    started_at=started_at,
                    finished_at=finished_at,
                    status="success",
                    outputs=outputs,
                ))

            except Exception as e:
                finished_at = time.time()
                success = False
                results.append(StepResult(
                    step_id=step_id,
                    name=name,
                    started_at=started_at,
                    finished_at=finished_at,
                    status="failed",
                    outputs=outputs if 'outputs' in locals() else {},
                    error=str(e),
                ))
                break  # stop on first failure for determinism

        return success, results, variables

    def _eval_condition(self, cond: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
        """Evaluate simple structured conditions using substituted values."""
        cond = _substitute(cond, ctx)
        ctype = cond.get("type")

        if ctype in {"equals", "eq"}:
            return str(cond.get("left")) == str(cond.get("right"))
        if ctype in {"not_equals", "ne"}:
            return str(cond.get("left")) != str(cond.get("right"))
        if ctype == "contains":
            left = cond.get("left")
            right = cond.get("right")
            try:
                return str(right) in str(left)
            except Exception:
                return False
        if ctype == "http_status" or ctype == "status_code":
            try:
                return int(cond.get("left")) == int(cond.get("right", 200))
            except Exception:
                return False
        if ctype == "truthy":
            return _coerce_bool(cond.get("value"))
        if ctype == "falsy":
            return not _coerce_bool(cond.get("value"))
        # Unknown condition type defaults to False for safety
        return False


def load_playbook_content(raw: str) -> Dict[str, Any]:
    """Load YAML or JSON string into a Python dict."""
    raw = raw.strip()
    if not raw:
        raise PlaybookValidationError("Empty playbook content")
    # Try JSON first
    try:
        return json.loads(raw)
    except Exception:
        pass
    # Then YAML (optional dependency)
    try:
        import yaml  # type: ignore
        return yaml.safe_load(raw)
    except Exception as e:
        raise PlaybookValidationError(f"Failed to parse playbook content: {e}")
