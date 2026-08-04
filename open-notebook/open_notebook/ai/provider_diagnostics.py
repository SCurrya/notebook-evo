import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx
from loguru import logger


def redact_secret(value: Optional[str]) -> str:
    """Return a log-safe representation of a secret."""
    if not value:
        return "<missing>"
    if len(value) <= 8:
        return "<redacted>"
    return f"{value[:4]}...{value[-4:]}"


def response_snippet(response: Optional[httpx.Response], limit: int = 800) -> str:
    if response is None:
        return ""
    try:
        text = response.text
    except Exception:
        return "<unreadable response body>"
    return text[:limit]


@dataclass
class ProviderAttempt:
    provider: str
    model: str
    url: str
    retry_count: int
    started_at: float

    @classmethod
    def start(cls, provider: str, model: str, url: str, retry_count: int) -> "ProviderAttempt":
        return cls(
            provider=provider,
            model=model,
            url=url,
            retry_count=retry_count,
            started_at=time.perf_counter(),
        )

    @property
    def latency_ms(self) -> int:
        return int((time.perf_counter() - self.started_at) * 1000)


def log_provider_success(attempt: ProviderAttempt, status_code: Optional[int] = None) -> None:
    logger.info(
        "[AI/PROVIDER] success provider={} model={} url={} status={} latency_ms={} retry_count={}",
        attempt.provider,
        attempt.model,
        attempt.url,
        status_code or "n/a",
        attempt.latency_ms,
        attempt.retry_count,
    )


def log_provider_failure(attempt: ProviderAttempt, error: BaseException) -> None:
    status: Any = "n/a"
    body = ""

    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        body = response_snippet(error.response)
    elif isinstance(error, httpx.RequestError):
        body = str(error)[:800]
    else:
        body = str(error)[:800]

    logger.error(
        "[AI/PROVIDER] failure provider={} model={} url={} status={} latency_ms={} "
        "retry_count={} error_type={} response_body={}",
        attempt.provider,
        attempt.model,
        attempt.url,
        status,
        attempt.latency_ms,
        attempt.retry_count,
        type(error).__name__,
        body,
    )
