# Task 5 Report: Deterministic Guardrails

## Status

DONE. Commit `92c7022` (`feat(task-5): add deterministic guardrails`).

## RED Evidence

Command:

```bash
python -m pytest tests/test_guardrails.py -v
```

Observed result before implementation:

```text
ERROR collecting tests/test_guardrails.py
ModuleNotFoundError: No module named 'safeloop.security.guardrails'
```

This was the expected RED failure because `safeloop.security.guardrails` did not exist yet.

## GREEN Evidence

Focused command:

```bash
python -m pytest tests/test_guardrails.py -v
```

Observed result:

```text
6 passed in 0.16s
```

Full-suite command:

```bash
python -m pytest -v
```

Observed result:

```text
52 passed in 0.71s
```

## Files Changed

- `safeloop/security/guardrails.py`: added deterministic guardrail evaluation, workspace containment checks, and command/path deny logic.
- `tests/test_guardrails.py`: added RED-first coverage for workspace containment, blocked paths, blocked commands, approval-required commands, deny-over-approval precedence, and safe reads.
- `PLAN.md`: marked Task 5 steps complete and recorded the implementation commit hash.
- `AGENT_LOG.md`: appended the Task 5 process entry.

## Commit

`92c7022` (`feat(task-5): add deterministic guardrails`)

## Self-Review

- Scope stayed within Task 5: no command execution, dispatcher, file tools, LLM provider calls, or UI work.
- `GuardrailEngine.evaluate()` applies deny over approval and approval over allow.
- Default blocked path and command patterns are deterministic and path/command checks stay local.
