Status: DONE

Commit hashes:
- Pending until implementation commit is created.

RED evidence:
- `python -m pytest tests/test_demo.py tests/test_cli_bootstrap.py -v` -> `2 failed, 3 passed`; `demo` still returned `demo is not yet implemented`, and `run` rejected `--config`, `--task`, and `--mock-response`.
- `python -m pytest tests/test_demo.py::test_demo_command_exits_zero_and_prints_mechanism_events -v` -> failed because the visible demo output lacked `patch_file success=True` and `run_tests success=True`.

GREEN evidence:
- `python -m pytest tests/test_demo.py tests/test_cli_bootstrap.py -v` -> `6 passed in 4.21s`.
- `python -m safeloop demo` -> exit `0`; stdout contained `guardrail_blocked`, `feedback_added test_failure`, `patch_file success=True`, `run_tests success=True`, and `finished`.
- `python -m pytest -v` -> `134 passed in 9.89s`.
- Fresh pre-commit verification: `python -m pytest tests/test_demo.py tests/test_cli_bootstrap.py -v` -> `6 passed in 4.32s`; `python -m safeloop demo` -> exit `0`; `python -m pytest -v` -> `134 passed in 9.19s`.

Files changed:
- `safeloop/cli.py`
- `safeloop/demo.py`
- `tests/test_demo.py`
- `tests/test_cli_bootstrap.py`
- `samples/python_buggy_calculator/calculator.py`
- `samples/python_buggy_calculator/test_calculator.py`
- `samples/python_buggy_calculator/safeloop.yml`
- `Makefile`
- `PLAN.md`
- `AGENT_LOG.md`
- `.superpowers/sdd/task-12-report.md`

Concerns:
- The checked-in sample remains intentionally buggy; `python -m safeloop demo` copies it to a temporary workspace before applying the mock patch, so the repository sample is not mutated by the demo.
- `make demo` could not be executed in this Windows shell because `make` is not installed; the target command `python -m safeloop demo` was verified directly.
- WebUI remains a placeholder for Task 13.
