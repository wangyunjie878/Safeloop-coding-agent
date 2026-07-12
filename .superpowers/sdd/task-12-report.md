Status: DONE

Commit hashes:
- `5e11b3f` (`feat(task-12): add cli commands and mechanism demo`)

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

Review fix:
- Reviewer Rawls found one Important spec issue: the documented interface `python -m safeloop run --config safeloop.yml --task "..." --llm mock` failed unless an extra `--mock-response` flag was supplied.
- Commit `6111087` (`fix(task-12): allow default mock run`) adds a RED-first regression for the documented command and supplies a default mock `finish` response when no explicit mock script is passed.
- RED: `python -m pytest tests/test_demo.py tests/test_cli_bootstrap.py -v` failed with `test_run_command_uses_default_mock_finish_response` returning exit code `2`.
- GREEN: `python -m pytest tests/test_demo.py tests/test_cli_bootstrap.py -v` -> `7 passed`; `python -m safeloop run --config samples/python_buggy_calculator/safeloop.yml --task verify --llm mock` -> exit `0`, `final_status: finished`; `python -m pytest -v` -> `135 passed`.
