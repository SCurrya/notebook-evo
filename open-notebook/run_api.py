#!/usr/bin/env python3
"""
Startup script for Open Notebook API server.

Starts both the FastAPI server AND an in-process surreal-commands worker so
that async source processing (PDF upload, podcast generation, ...) actually
runs instead of being stuck in 'new' state.
"""

import os
import sys
import threading
from pathlib import Path

import uvicorn

# Add the current directory to Python path so imports work
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def _start_surreal_commands_worker() -> None:
    """Spawn the async command worker in a background thread."""
    import logging

    logger = logging.getLogger("run_api.worker")

    def _worker_main():
        try:
            logger.info("Starting in-process surreal-commands worker...")
            import commands  # noqa: F401  # triggers commands/__init__.py
            try:
                import commands.podcast_commands  # noqa: F401
            except Exception as e:
                logger.warning(f"podcast commands unavailable: {e}")
            try:
                import commands.source_commands  # noqa: F401
            except Exception as e:
                logger.warning(f"source commands unavailable: {e}")

            from surreal_commands.core.worker import listen_for_commands
            from surreal_commands.core.registry import registry

            registered = registry.get_all_commands()
            logger.info(
                f"Surreal-commands worker registered: "
                f"{[f'{c.app_id}.{c.name}' for c in registered]}"
            )
            if not registered:
                logger.warning(
                    "No commands registered! Async processing will not work."
                )

            max_tasks = int(os.getenv("OPEN_NOTEBOOK_WORKER_MAX_TASKS", "5"))
            print(f"surreal-commands worker max_tasks={max_tasks}")

            loop = __import__("asyncio").new_event_loop()
            __import__("asyncio").set_event_loop(loop)
            try:
                loop.run_until_complete(listen_for_commands(max_tasks=max_tasks))
            finally:
                loop.close()
        except Exception:
            logger.exception("Surreal-commands worker crashed")

    t = threading.Thread(target=_worker_main, name="surreal-cmds-worker", daemon=True)
    t.start()
    print("surreal-commands worker thread spawned")


if __name__ == "__main__":
    # Default configuration
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "5055"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"

    print(f"Starting Open Notebook API server on {host}:{port}")
    print(f"Reload mode: {reload}")

    # Ensure async source processing works in API-only mode
    _start_surreal_commands_worker()

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[str(current_dir)] if reload else None,
    )
