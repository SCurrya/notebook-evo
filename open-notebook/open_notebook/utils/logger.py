"""
Unified logging system for Open Notebook.

Provides structured logging with a consistent format:
    {timestamp} | {level} | {module} | {operation} | {params} | {result} | {message}

Features:
- loguru-based with structured fields bound via ``extra``
- Optional JSON output (set ``OPEN_NOTEBOOK_LOG_JSON=1``) for log aggregation
- Configurable log level via ``OPEN_NOTEBOOK_LOG_LEVEL`` (DEBUG/INFO/WARNING/ERROR)
- ``@log_operation(module, operation)`` decorator for automatic function-call logging
- Lazy parameter evaluation: params are only extracted when DEBUG is enabled

Usage::

    from open_notebook.utils.logger import (
        get_logger, log_operation, Operation, Result,
    )

    log = get_logger("notebooks_api", Operation.READ)
    log.info("fetched notebook", params="notebook_id=abc", result=Result.SUCCESS)

    @log_operation("notebook_service", Operation.CREATE)
    async def create_notebook(name: str, ...):
        ...
"""

import functools
import inspect
import os
import sys
from typing import Any, Callable, Dict, Optional, TypeVar

from loguru import logger as _loguru_logger

F = TypeVar("F", bound=Callable[..., Any])


class Operation:
    """Standard operation type tags for consistent log analysis."""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SEARCH = "SEARCH"
    TRANSFORM = "TRANSFORM"
    CHAT = "CHAT"


class Result:
    """Standard result status values."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


# Unified format: {timestamp} | {level} | {module} | {operation} | {params} | {result} | {message}
LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{extra[module]} | {extra[operation]} | {extra[params]} | {extra[result]} | {message}"
)

JSON_FORMAT = (
    '{{"timestamp":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
    '"level":"{level}",'
    '"module":"{extra[module]}",'
    '"operation":"{extra[operation]}",'
    '"params":"{extra[params]}",'
    '"result":"{extra[result]}",'
    '"message":"{message}"}}'
)

# Default extra values so unbound log calls still resolve the format placeholders.
_DEFAULT_EXTRA: Dict[str, str] = {
    "module": "-",
    "operation": "-",
    "params": "-",
    "result": "-",
}

_configured = False


def _get_log_level() -> str:
    return os.getenv("OPEN_NOTEBOOK_LOG_LEVEL", "INFO").upper()


def _is_json_enabled() -> bool:
    return os.getenv("OPEN_NOTEBOOK_LOG_JSON", "").lower() in ("1", "true", "yes")


def configure_logging() -> None:
    """
    Configure the global loguru logger with the unified structured format.

    - Sets default ``extra`` fields so the format works for unbound log calls.
    - Replaces the default stderr handler (id ``0``) with a structured one.
    - Preserves custom handlers (e.g. file handlers added by ``api/main.py``).

    Safe to call multiple times; only the first call has effect.
    """
    global _configured
    if _configured:
        return
    _configured = True

    _loguru_logger.configure(extra=dict(_DEFAULT_EXTRA))

    # Remove only the built-in default handler (id 0), keep custom handlers.
    try:
        _loguru_logger.remove(0)
    except ValueError:
        pass

    fmt = JSON_FORMAT if _is_json_enabled() else LOG_FORMAT
    _loguru_logger.add(
        sys.stderr,
        format=fmt,
        level=_get_log_level(),
        backtrace=False,
        diagnose=False,
    )


# Configure on import so every module benefits from the structured format.
configure_logging()


def _truncate(value: Any, max_len: int = 200) -> str:
    """Convert ``value`` to string and truncate if too long."""
    try:
        s = str(value)
    except Exception:
        s = "<unrepr>"
    if len(s) > max_len:
        return s[:max_len] + "...[truncated]"
    return s


def _format_params(**kwargs: Any) -> str:
    """Format keyword parameters into a compact ``k=v`` string."""
    if not kwargs:
        return "-"
    return " ".join(f"{k}={_truncate(v)}" for k, v in kwargs.items())


# Cache function signatures so we only introspect once per decorated function.
_sig_cache: Dict[Callable[..., Any], inspect.Signature] = {}


def _extract_params(func: Callable[..., Any], args: tuple, kwargs: dict) -> Dict[str, Any]:
    """Extract named parameters from ``args``/``kwargs`` based on the function signature.

    Skips ``self`` and ``cls``. Returns an empty dict on failure.
    """
    sig = _sig_cache.get(func)
    if sig is None:
        try:
            sig = inspect.signature(func)
        except (ValueError, TypeError):
            sig = None
        _sig_cache[func] = sig  # type: ignore[assignment]

    if sig is None:
        return {}

    try:
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        return {
            name: value
            for name, value in bound.arguments.items()
            if name not in ("self", "cls")
        }
    except TypeError:
        return {}


def _debug_enabled() -> bool:
    """Return True when DEBUG is the configured log level (cheap, cached check)."""
    return _get_log_level() == "DEBUG"


def get_logger(
    module: str = "-",
    operation: str = "-",
    params: str = "-",
    result: str = "-",
):
    """Return a loguru logger pre-bound with structured context fields."""
    return _loguru_logger.bind(
        module=module, operation=operation, params=params, result=result
    )


def log_operation(module: str, operation: str) -> Callable[[F], F]:
    """
    Decorator that logs function entry, success, and exceptions.

    Args:
        module: Module name (e.g. ``"notebook_service"``).
        operation: Operation type (use :class:`Operation` constants).

    Logs:
        - DEBUG on entry with parameters (params extracted lazily).
        - INFO on success.
        - ERROR on exception, then re-raises.

    Works with both sync and async functions.
    """

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                params_str = (
                    _format_params(**_extract_params(func, args, kwargs))
                    if _debug_enabled()
                    else "-"
                )
                log = get_logger(module, operation, params_str, "-")
                log.debug(f"-> {func.__name__}()")
                try:
                    result = await func(*args, **kwargs)
                    log.bind(result=Result.SUCCESS).info(f"<- {func.__name__}() ok")
                    return result
                except Exception as e:
                    log.bind(result=Result.FAILURE).error(
                        f"<- {func.__name__}() failed: {type(e).__name__}: {e}"
                    )
                    raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                params_str = (
                    _format_params(**_extract_params(func, args, kwargs))
                    if _debug_enabled()
                    else "-"
                )
                log = get_logger(module, operation, params_str, "-")
                log.debug(f"-> {func.__name__}()")
                try:
                    result = func(*args, **kwargs)
                    log.bind(result=Result.SUCCESS).info(f"<- {func.__name__}() ok")
                    return result
                except Exception as e:
                    log.bind(result=Result.FAILURE).error(
                        f"<- {func.__name__}() failed: {type(e).__name__}: {e}"
                    )
                    raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator


# Re-export the configured loguru logger for convenience.
logger = _loguru_logger


__all__ = [
    "logger",
    "log_operation",
    "get_logger",
    "configure_logging",
    "Operation",
    "Result",
    "LOG_FORMAT",
    "JSON_FORMAT",
]
