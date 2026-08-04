import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from surreal_commands import get_command_status as surreal_get_command_status
from surreal_commands import submit_command as surreal_submit_command
from surrealdb import RecordID

from open_notebook.database.repository import repo_query


class CommandService:
    """Generic service layer for command operations"""

    @staticmethod
    async def submit_command_job(
        module_name: str,  # Actually app_name for surreal-commands
        command_name: str,
        command_args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit a generic command job for background processing"""
        try:
            # Lazily load command modules - only for podcast-related jobs.
            # This prevents source upload / transformation / etc. from being
            # blocked by missing optional dependencies like podcast_creator.
            if module_name == "podcast" or "podcast" in (command_name or "").lower():
                try:
                    import commands.podcast_commands  # noqa: F401
                except Exception as import_err:
                    logger.warning(
                        f"Podcast commands unavailable (optional): {import_err}"
                    )
            # Also try to ensure the source / transformation command modules
            # are registered with the local registry when present.
            try:
                import commands.source_commands  # noqa: F401
            except Exception as import_err:
                logger.warning(f"Source commands unavailable: {import_err}")
            try:
                import commands.embedding_commands  # noqa: F401
            except Exception as import_err:
                logger.warning(f"Embedding commands unavailable: {import_err}")

            # surreal-commands expects: submit_command(app_name, command_name, args)
            # `args` must be a plain dict; Pydantic models must be serialized.
            if hasattr(command_args, "model_dump"):
                args_payload = command_args.model_dump(mode="json")
            elif hasattr(command_args, "dict"):
                args_payload = command_args.dict()
            else:
                args_payload = command_args
            cmd_id = await asyncio.to_thread(
                surreal_submit_command,
                module_name,  # This is actually the app name (e.g., "open_notebook")
                command_name,  # Command name (e.g., "process_text")
                args_payload,  # Input data as a plain dict
                context,
            )
            # Convert RecordID to string if needed
            if not cmd_id:
                raise ValueError("Failed to get cmd_id from submit_command")
            cmd_id_str = str(cmd_id)
            logger.info(
                f"Submitted command job: {cmd_id_str} for {module_name}.{command_name}"
            )
            return cmd_id_str

        except Exception as e:
            logger.error(f"Failed to submit command job: {e}")
            raise

    @staticmethod
    async def get_command_status(job_id: str) -> Dict[str, Any]:
        """Get status of any command job"""
        try:
            status = await surreal_get_command_status(job_id)
            raw_status = getattr(status, "status", None)
            status_value = raw_status.value if hasattr(raw_status, "value") else str(raw_status) if raw_status is not None else "unknown"
            return {
                "job_id": job_id,
                "status": status_value,
                "result": status.result if status else None,
                "error_message": getattr(status, "error_message", None)
                if status
                else None,
                "created": str(status.created)
                if status and hasattr(status, "created") and status.created
                else None,
                "updated": str(status.updated)
                if status and hasattr(status, "updated") and status.updated
                else None,
                "progress": getattr(status, "progress", None) if status else None,
            }
        except Exception as e:
            logger.error(f"Failed to get command status: {e}")
            raise

    @staticmethod
    async def list_command_jobs(
        module_filter: Optional[str] = None,
        command_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List command jobs with optional filtering"""
        query = """
            SELECT
                id,
                app,
                name,
                args,
                context,
                status,
                result,
                error_message,
                created,
                updated
            FROM command
            """
        conditions: List[str] = []
        params: Dict[str, Any] = {}

        if module_filter:
            conditions.append("app = $app")
            params["app"] = module_filter
        if command_filter:
            conditions.append("name = $name")
            params["name"] = command_filter
        if status_filter:
            conditions.append("status = $status")
            params["status"] = status_filter

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created DESC LIMIT $limit"
        params["limit"] = max(1, min(limit, 500))

        try:
            rows = await repo_query(query, params)
            jobs: List[Dict[str, Any]] = []
            for row in rows:
                created = row.get("created")
                updated = row.get("updated")
                jobs.append(
                    {
                        "job_id": str(row.get("id")),
                        "app": row.get("app"),
                        "command": row.get("name"),
                        "status": row.get("status"),
                        "args": row.get("args"),
                        "context": row.get("context"),
                        "result": row.get("result"),
                        "error_message": row.get("error_message"),
                        "created": created.isoformat() if hasattr(created, "isoformat") else str(created) if created else None,
                        "updated": updated.isoformat() if hasattr(updated, "isoformat") else str(updated) if updated else None,
                    }
                )
            return jobs
        except Exception as e:
            logger.warning(f"Command job listing unavailable: {e}")
            return []

    @staticmethod
    async def cancel_command_job(job_id: str) -> bool:
        """Cancel a running command job"""
        try:
            logger.info(f"Attempting to cancel job: {job_id}")
            record_id = job_id if isinstance(job_id, RecordID) else RecordID.parse(job_id)
            rows = await repo_query(
                "SELECT id, status FROM command WHERE id = $id LIMIT 1",
                {"id": record_id},
            )
            if not rows:
                raise ValueError(f"Command job not found: {job_id}")

            current_status = str(rows[0].get("status", "")).lower()
            if current_status in {"completed", "failed", "canceled"}:
                return False

            # Only queued jobs can be canceled truthfully.
            # Once a worker marks the command running, this service cannot
            # safely interrupt execution mid-flight.
            if current_status != "new":
                logger.warning(
                    f"Refusing to fake-cancel running command job {job_id} "
                    f"(status={current_status})"
                )
                return False

            await repo_query(
                """
                UPDATE $id
                SET status = $status,
                    updated = time::now()
                """,
                {"id": record_id, "status": "canceled"},
            )
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to cancel command job: {e}")
            raise
