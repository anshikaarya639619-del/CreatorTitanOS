"""Adapter for providers that explicitly document OpenAI-compatible chat completions."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from router import ErrorKind, ProviderError


class OpenAICompatibleAdapter:
    def __init__(self, base_url, credential_env, *, extra_headers=None):
        self.base_url = base_url.rstrip("/")
        self.credential_env = credential_env
        self.extra_headers = extra_headers or {}

    def invoke(self, model, payload, *, idempotency_key, timeout_seconds):
        key = os.environ.get(self.credential_env, "")
        if not key:
            raise ProviderError(ErrorKind.AUTH, "Missing provider credential environment variable")
        body = {
            "model": model,
            "messages": payload.get("messages") or [
                {"role": "user", "content": str(payload.get("prompt", ""))}
            ],
        }
        for field in ("temperature", "max_tokens", "top_p", "response_format"):
            if field in payload:
                body[field] = payload[field]
        request = Request(
            self.base_url + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
                **self.extra_headers,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
                choices = result.get("choices") or []
                if choices:
                    return choices[0].get("message", {}).get("content", result)
                return result
        except HTTPError as exc:
            retry_after = exc.headers.get("Retry-After")
            try:
                retry_after = float(retry_after) if retry_after else None
            except ValueError:
                retry_after = None
            if exc.code == 429:
                raise ProviderError(ErrorKind.RATE_LIMITED, "Provider rate limit", retry_after)
            if exc.code in (401, 403):
                raise ProviderError(ErrorKind.AUTH, "Provider rejected credentials")
            if exc.code == 402:
                raise ProviderError(ErrorKind.BILLING, "Provider billing restriction")
            if exc.code in (400, 404, 422):
                raise ProviderError(ErrorKind.INVALID_REQUEST, "Provider rejected request")
            if exc.code >= 500:
                raise ProviderError(ErrorKind.TRANSIENT, "Provider server error")
            raise ProviderError(ErrorKind.UNKNOWN, "Provider HTTP error " + str(exc.code))
        except (URLError, TimeoutError, OSError):
            raise ProviderError(ErrorKind.TRANSIENT, "Provider network/timeout error")
