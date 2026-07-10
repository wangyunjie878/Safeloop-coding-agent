from __future__ import annotations

from pathlib import Path
import os
from typing import Literal

import keyring
from keyring.errors import PasswordDeleteError
from dotenv import dotenv_values


class CredentialError(RuntimeError):
    pass


_SERVICE_NAME = "safeloop-agent"
_ENV_VAR_BY_PROVIDER = {"deepseek": "DEEPSEEK_API_KEY"}


class CredentialManager:
    def __init__(
        self,
        backend: Literal["keyring", "env", "dotenv"] = "keyring",
        dotenv_path: Path | str | None = None,
    ) -> None:
        self.backend = backend
        self.dotenv_path = Path(dotenv_path) if dotenv_path is not None else Path.cwd() / ".env"

    def status(self, provider: str) -> dict[str, str]:
        return {
            "provider": provider,
            "status": "configured" if self.get_key(provider) else "missing",
        }

    def set_key(self, provider: str, key: str) -> None:
        self._validate_key(key)
        if self.backend != "keyring":
            raise CredentialError(f"{self.backend} backend is read-only")
        keyring.set_password(_SERVICE_NAME, provider, key)

    def get_key(self, provider: str) -> str | None:
        if self.backend == "keyring":
            return keyring.get_password(_SERVICE_NAME, provider)

        env_var = self._env_var_name(provider)
        if self.backend == "env":
            return os.environ.get(env_var)
        if self.backend == "dotenv":
            value = dotenv_values(self.dotenv_path).get(env_var)
            return value if isinstance(value, str) else None
        raise CredentialError(f"Unsupported credential backend: {self.backend}")

    def clear_key(self, provider: str) -> None:
        if self.backend != "keyring":
            raise CredentialError(f"{self.backend} backend is read-only")
        try:
            keyring.delete_password(_SERVICE_NAME, provider)
        except PasswordDeleteError:
            return
        except Exception as exc:
            raise CredentialError(f"Failed to clear credential for {provider}") from exc

    def _env_var_name(self, provider: str) -> str:
        try:
            return _ENV_VAR_BY_PROVIDER[provider]
        except KeyError as exc:
            raise CredentialError(f"Unsupported provider: {provider}") from exc

    @staticmethod
    def _validate_key(key: str) -> None:
        if not key.strip():
            raise CredentialError("Empty keys are invalid")
