from __future__ import annotations

import re
from collections.abc import Mapping

_OBVIOUS_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9_-]{7,}"),
    re.compile(r"-----BEGIN [A-Z ]+-----"),
)
_SECRET_KEY_PATTERN = re.compile(
    r"(?:^|[_-])(secret|token|password|passwd|passphrase|api[_-]?key|private[_-]?key|client[_-]?secret)(?:$|[_-])",
    re.IGNORECASE,
)
_DOTENV_SECRET_LINE_PATTERN = re.compile(
    r"(?m)^[A-Z0-9_]*(SECRET|TOKEN|PASSWORD|PASSWD|PASSPHRASE|API_KEY|PRIVATE_KEY|CLIENT_SECRET)[A-Z0-9_]*\s*=",
    re.IGNORECASE,
)


def _is_secret_key(key: object) -> bool:
    return isinstance(key, str) and bool(_SECRET_KEY_PATTERN.search(key))


def _redact_string(value: str, known_secrets: list[str]) -> str:
    redacted = value
    for secret in known_secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")

    if redacted != value:
        return redacted

    for pattern in _OBVIOUS_SECRET_PATTERNS:
        if pattern.search(value):
            return "[REDACTED]"

    if _DOTENV_SECRET_LINE_PATTERN.search(value):
        return "[REDACTED]"

    return value


def redact_secrets(value: object, known_secrets: list[str] | None = None) -> object:
    secrets = [secret for secret in (known_secrets or []) if secret]

    if isinstance(value, str):
        return _redact_string(value, secrets)
    if isinstance(value, Mapping):
        return {
            key: "[REDACTED]" if _is_secret_key(key) else redact_secrets(inner, secrets)
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item, secrets) for item in value)
    if isinstance(value, set):
        return {redact_secrets(item, secrets) for item in value}
    if isinstance(value, frozenset):
        return frozenset(redact_secrets(item, secrets) for item in value)

    return value
