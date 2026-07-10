# Task 14 Report: Credential Manager and DeepSeek Client

## Status

DONE. Commit `68b0c96` (`feat(task-14): add credential manager and deepseek client`).

## RED Evidence

Command:

```bash
python -m pytest tests/test_credentials.py tests/test_deepseek_client.py -v
```

Observed result before implementation:

```text
ERROR collecting tests/test_credentials.py
ModuleNotFoundError: No module named 'safeloop.credentials'
ERROR collecting tests/test_deepseek_client.py
ModuleNotFoundError: No module named 'safeloop.llm.deepseek'
```

This was the expected RED failure because both task-owned modules were still missing.

## GREEN Evidence

Focused command:

```bash
python -m pytest tests/test_credentials.py tests/test_deepseek_client.py -v
```

Observed result:

```text
12 passed in 0.56s
```

Full-suite command:

```bash
python -m pytest -v
```

Observed result:

```text
65 passed in 1.70s
```

## Secret Scan Evidence

Command:

```powershell
Get-ChildItem -Recurse -File | Select-String -Pattern 'sk-'
```

Observed result:

```text
Matches were limited to dummy placeholders and existing test/redaction fixtures such as sk-test, sk-secret, sk-env, sk-dotenv, and sk-live-1234567890, plus generated .pyc cache entries containing the same dummy strings. No real API key appeared.
```

## Files Changed

- `safeloop/credentials.py`: added `CredentialManager`, `CredentialError`, provider/env mapping, keyring writes, and read-only env/dotenv reads.
- `safeloop/llm/deepseek.py`: added `DeepSeekClient` and `DeepSeekClientError` with injected `httpx.Client`, bearer auth, default model, and malformed/non-2xx handling.
- `safeloop/llm/__init__.py`: exported the new DeepSeek client symbols.
- `safeloop/cli.py`: replaced the `credentials` placeholder with `status`, `set`, and `clear` subcommands while leaving other placeholders intact.
- `tests/test_credentials.py`: added keyring/env/dotenv behavior coverage, read-only backend checks, empty-key rejection, and CLI no-secret-output coverage.
- `tests/test_deepseek_client.py`: added offline transport coverage for request shape, model override, non-2xx handling, and malformed responses.
- `tests/test_cli_bootstrap.py`: narrowed placeholder assertions to the still-unimplemented commands.
- `PLAN.md`: recorded Task 14 RED/GREEN/scan evidence and hash placeholder note.
- `AGENT_LOG.md`: appended the Task 14 trace entry.

## Self-Review

- Scope stayed inside the assigned Task 14 files.
- Tests remain offline and deterministic.
- `credentials status` prints only the status word and never key material.
- `set_key()` and `clear_key()` are intentionally limited to the `keyring` backend.

## Hash Traceability

The implementation commit was recorded in a follow-up process commit because the final hash of a feature commit cannot be written into files inside that same exact commit.

## Review-Fix Evidence

### RED

Command:

```bash
python -m pytest tests/test_credentials.py tests/test_deepseek_client.py -v
```

Observed failures:

```text
FAILED tests/test_credentials.py::test_keyring_backend_clear_propagates_unexpected_errors
FAILED tests/test_deepseek_client.py::test_deepseek_client_raises_clear_error_on_non_json_response
```

### GREEN

Focused command:

```bash
python -m pytest tests/test_credentials.py tests/test_deepseek_client.py -v
```

Observed result:

```text
14 passed in 0.57s
```

Full-suite command:

```bash
python -m pytest -v
```

Observed result:

```text
67 passed in 1.76s
```

### Review-Fix Commit

Pending until the review-fix commit is created.
