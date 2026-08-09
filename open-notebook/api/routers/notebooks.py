from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from loguru import logger

from api.models import (
    NotebookCreate,
    NotebookDeletePreview,
    NotebookDeleteResponse,
    NotebookResponse,
    NotebookUpdate,
)
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.domain.notebook import Notebook, Source
from open_notebook.exceptions import InvalidInputError
from open_notebook.utils.logger import Operation, Result, get_logger

router = APIRouter()


async def _get_notebook_counts(notebook_id: str) -> tuple[int, int]:
    """Get notebook source/note counts from the relationship tables."""
    source_result = await repo_query(
        "SELECT count() as count FROM reference WHERE out = $notebook_id GROUP ALL",
        {"notebook_id": ensure_record_id(notebook_id)},
    )
    note_result = await repo_query(
        "SELECT count() as count FROM artifact WHERE out = $notebook_id GROUP ALL",
        {"notebook_id": ensure_record_id(notebook_id)},
    )
    source_count = source_result[0]["count"] if source_result else 0
    note_count = note_result[0]["count"] if note_result else 0
    return source_count, note_count


@router.get("/notebooks", response_model=List[NotebookResponse])
async def get_notebooks(
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
    order_by: str = Query("updated desc", description="Order by field and direction"),
):
    """Get all notebooks with optional filtering and ordering."""
    log = get_logger("notebooks_api", Operation.READ, f"archived={archived} order_by={order_by}")
    log.debug("-> get_notebooks()")
    try:
        # Validate order_by against allowlist to prevent SurrealQL injection
        allowed_fields = {"name", "created", "updated"}
        allowed_directions = {"asc", "desc"}

        parts = order_by.strip().lower().split()
        if len(parts) == 1:
            if parts[0] not in allowed_fields:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid order_by field: '{order_by}'. Allowed fields: {', '.join(sorted(allowed_fields))}",
                )
            validated_order_by = parts[0]
        elif len(parts) == 2:
            if parts[0] not in allowed_fields or parts[1] not in allowed_directions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid order_by: '{order_by}'. Allowed fields: {', '.join(sorted(allowed_fields))}. Allowed directions: asc, desc",
                )
            validated_order_by = f"{parts[0]} {parts[1]}"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid order_by format: '{order_by}'. Expected 'field' or 'field direction'",
            )

        result = await repo_query(f"SELECT * FROM notebook ORDER BY {validated_order_by}")

        # Filter by archived status if specified
        if archived is not None:
            result = [nb for nb in result if nb.get("archived") == archived]

        log.bind(result=Result.SUCCESS).info(f"<- get_notebooks() count={len(result)}")
        counts_by_id = {}
        for nb in result:
            notebook_id = str(nb.get("id", ""))
            counts_by_id[notebook_id] = await _get_notebook_counts(notebook_id)

        return [
            NotebookResponse(
                id=str(nb.get("id", "")),
                name=nb.get("name", ""),
                description=nb.get("description", ""),
                archived=nb.get("archived", False),
                created=str(nb.get("created", "")),
                updated=str(nb.get("updated", "")),
                source_count=counts_by_id.get(str(nb.get("id", "")), (0, 0))[0],
                note_count=counts_by_id.get(str(nb.get("id", "")), (0, 0))[1],
            )
            for nb in result
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching notebooks: {str(e)}")
        get_logger("notebooks_api", Operation.READ, "-", Result.FAILURE).error(
            f"get_notebooks() failed: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching notebooks: {str(e)}"
        )


@router.post("/notebooks", response_model=NotebookResponse)
async def create_notebook(notebook: NotebookCreate):
    """Create a new notebook."""
    log = get_logger("notebooks_api", Operation.CREATE, f"name={notebook.name}")
    log.debug("-> create_notebook()")
    try:
        new_notebook = Notebook(
            name=notebook.name,
            description=notebook.description,
        )
        await new_notebook.save()

        log.bind(result=Result.SUCCESS).info(f"<- create_notebook() id={new_notebook.id}")
        return NotebookResponse(
            id=new_notebook.id or "",
            name=new_notebook.name,
            description=new_notebook.description,
            archived=new_notebook.archived or False,
            created=str(new_notebook.created),
            updated=str(new_notebook.updated),
            source_count=0,  # New notebook has no sources
            note_count=0,  # New notebook has no notes
        )
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating notebook: {str(e)}")
        get_logger("notebooks_api", Operation.CREATE, f"name={notebook.name}", Result.FAILURE).error(
            f"create_notebook() failed: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error creating notebook: {str(e)}"
        )


@router.get(
    "/notebooks/{notebook_id}/delete-preview", response_model=NotebookDeletePreview
)
async def get_notebook_delete_preview(notebook_id: str):
    """Get a preview of what will be deleted when this notebook is deleted."""
    log = get_logger("notebooks_api", Operation.READ, f"notebook_id={notebook_id}")
    log.debug("-> get_notebook_delete_preview()")
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        preview = await notebook.get_delete_preview()

        log.bind(result=Result.SUCCESS).info(
            f"<- get_notebook_delete_preview() notes={preview['note_count']}"
        )
        return NotebookDeletePreview(
            notebook_id=str(notebook.id),
            notebook_name=notebook.name,
            note_count=preview["note_count"],
            exclusive_source_count=preview["exclusive_source_count"],
            shared_source_count=preview["shared_source_count"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delete preview for notebook {notebook_id}: {e}")
        get_logger("notebooks_api", Operation.READ, f"notebook_id={notebook_id}", Result.FAILURE).error(
            f"get_notebook_delete_preview() failed: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching notebook deletion preview: {str(e)}",
        )


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(notebook_id: str):
    """Get a specific notebook by ID."""
    log = get_logger("notebooks_api", Operation.READ, f"notebook_id={notebook_id}")
    log.debug("-> get_notebook()")
    try:
        # Query with counts for single notebook
        result = await repo_query(
            "SELECT * FROM $notebook_id",
            {"notebook_id": ensure_record_id(notebook_id)},
        )

        if not result:
            raise HTTPException(status_code=404, detail="Notebook not found")

        nb = result[0]
        source_count, note_count = await _get_notebook_counts(notebook_id)
        log.bind(result=Result.SUCCESS).info(f"<- get_notebook() found")
        return NotebookResponse(
            id=str(nb.get("id", "")),
            name=nb.get("name", ""),
            description=nb.get("description", ""),
            archived=nb.get("archived", False),
            created=str(nb.get("created", "")),
            updated=str(nb.get("updated", "")),
            source_count=source_count,
            note_count=note_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching notebook {notebook_id}: {str(e)}")
        get_logger("notebooks_api", Operation.READ, f"notebook_id={notebook_id}", Result.FAILURE).error(
            f"get_notebook() failed: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error fetching notebook: {str(e)}"
        )


@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(notebook_id: str, notebook_update: NotebookUpdate):
    """Update a notebook."""
    log = get_logger("notebooks_api", Operation.UPDATE, f"notebook_id={notebook_id}")
    log.debug("-> update_notebook()")
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Update only provided fields
        if notebook_update.name is not None:
            notebook.name = notebook_update.name
        if notebook_update.description is not None:
            notebook.description = notebook_update.description
        if notebook_update.archived is not None:
            notebook.archived = notebook_update.archived

        await notebook.save()

        result = await repo_query(
            "SELECT * FROM $notebook_id",
            {"notebook_id": ensure_record_id(notebook_id)},
        )

        if result:
            nb = result[0]
            source_count, note_count = await _get_notebook_counts(notebook_id)
            return NotebookResponse(
                id=str(nb.get("id", "")),
                name=nb.get("name", ""),
                description=nb.get("description", ""),
                archived=nb.get("archived", False),
                created=str(nb.get("created", "")),
                updated=str(nb.get("updated", "")),
                source_count=source_count,
                note_count=note_count,
            )

        # Fallback if query fails
        log.bind(result=Result.SUCCESS).info(f"<- update_notebook() ok")
        return NotebookResponse(
            id=notebook.id or "",
            name=notebook.name,
            description=notebook.description,
            archived=notebook.archived or False,
            created=str(notebook.created),
            updated=str(notebook.updated),
            source_count=0,
            note_count=0,
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating notebook {notebook_id}: {str(e)}")
        get_logger("notebooks_api", Operation.UPDATE, f"notebook_id={notebook_id}", Result.FAILURE).error(
            f"update_notebook() failed: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error updating notebook: {str(e)}"
        )


@router.post("/notebooks/{notebook_id}/sources/{source_id}")
async def add_source_to_notebook(notebook_id: str, source_id: str):
    """Add an existing source to a notebook (create the reference)."""
    log = get_logger("notebooks_api", Operation.UPDATE, f"notebook_id={notebook_id} source_id={source_id}")
    log.debug("-> add_source_to_notebook()")
    try:
        # Check if notebook exists
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Check if source exists
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        # Check if reference already exists (idempotency)
        existing_ref = await repo_query(
            "SELECT * FROM reference WHERE out = $source_id AND in = $notebook_id",
            {
                "notebook_id": ensure_record_id(notebook_id),
                "source_id": ensure_record_id(source_id),
            },
        )

        # If reference doesn't exist, create it
        if not existing_ref:
            await repo_query(
                "RELATE $source_id->reference->$notebook_id",
                {
                    "notebook_id": ensure_record_id(notebook_id),
                    "source_id": ensure_record_id(source_id),
                },
            )

        return {"message": "Source linked to notebook successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error linking source {source_id} to notebook {notebook_id}: {str(e)}"
        )
        get_logger("notebooks_api", Operation.UPDATE, f"notebook_id={notebook_id} source_id={source_id}", Result.FAILURE).error(
            f"add_source_to_notebook() failed: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error linking source to notebook: {str(e)}"
        )


@router.delete("/notebooks/{notebook_id}/sources/{source_id}")
async def remove_source_from_notebook(notebook_id: str, source_id: str):
    """Remove a source from a notebook (delete the reference)."""
    log = get_logger("notebooks_api", Operation.DELETE, f"notebook_id={notebook_id} source_id={source_id}")
    log.debug("-> remove_source_from_notebook()")
    try:
        # Check if notebook exists
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        # Delete the reference record linking source to notebook
        await repo_query(
            "DELETE reference WHERE out = $source_id AND in = $notebook_id",
            {
                "notebook_id": ensure_record_id(notebook_id),
                "source_id": ensure_record_id(source_id),
            },
        )

        return {"message": "Source removed from notebook successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error removing source {source_id} from notebook {notebook_id}: {str(e)}"
        )
        get_logger("notebooks_api", Operation.DELETE, f"notebook_id={notebook_id} source_id={source_id}", Result.FAILURE).error(
            f"remove_source_from_notebook() failed: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error removing source from notebook: {str(e)}"
        )


@router.delete("/notebooks/{notebook_id}", response_model=NotebookDeleteResponse)
async def delete_notebook(
    notebook_id: str,
    delete_exclusive_sources: bool = Query(
        False,
        description="Whether to delete sources that belong only to this notebook",
    ),
):
    """
    Delete a notebook with cascade deletion.

    Always deletes all notes associated with the notebook.
    If delete_exclusive_sources is True, also deletes sources that belong only
    to this notebook (not linked to any other notebooks).
    """
    log = get_logger("notebooks_api", Operation.DELETE, f"notebook_id={notebook_id} delete_exclusive={delete_exclusive_sources}")
    log.debug("-> delete_notebook()")
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        result = await notebook.delete(delete_exclusive_sources=delete_exclusive_sources)

        log.bind(result=Result.SUCCESS).info(
            f"<- delete_notebook() notes={result['deleted_notes']} sources={result['deleted_sources']}"
        )
        return NotebookDeleteResponse(
            message="Notebook deleted successfully",
            deleted_notes=result["deleted_notes"],
            deleted_sources=result["deleted_sources"],
            unlinked_sources=result["unlinked_sources"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notebook {notebook_id}: {str(e)}")
        get_logger("notebooks_api", Operation.DELETE, f"notebook_id={notebook_id}", Result.FAILURE).error(
            f"delete_notebook() failed: {e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error deleting notebook: {str(e)}"
        )


@router.get("/notebooks/{notebook_id}/export", response_class=PlainTextResponse)
async def export_notebook(notebook_id: str):
    """Export a notebook as a self-contained Markdown document.

    Includes the notebook metadata, each source's title/content, notes, and
    source insights. The document is plain Markdown so it can be shared,
    archived, or re-imported manually.
    """
    log = get_logger("notebooks_api", Operation.READ, f"notebook_id={notebook_id} export")
    log.debug("-> export_notebook()")
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        sources = await notebook.get_sources(include_full_text=True)
        notes = await notebook.get_notes(include_content=True)

        lines: list[str] = []
        lines.append(f"# {notebook.name}")
        lines.append("")
        if notebook.description:
            lines.append(f"> {notebook.description}")
            lines.append("")

        lines.append(f"*Exported: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        lines.append("")

        # Sources
        lines.append("## Sources")
        lines.append("")
        if not sources:
            lines.append("_No sources in this notebook._")
            lines.append("")
        for i, src in enumerate(sources, 1):
            lines.append(f"### {i}. {getattr(src, 'title', 'Untitled')}")
            lines.append("")
            full_text = getattr(src, "full_text", "") or ""
            if full_text:
                # Keep it readable: first 8000 chars per source.
                content = full_text[:8000]
                if len(full_text) > 8000:
                    content += "\n\n_[content truncated]_"
                lines.append(content)
                lines.append("")
            else:
                lines.append("_No content available._")
                lines.append("")

        # Notes
        lines.append("## Notes")
        lines.append("")
        if not notes:
            lines.append("_No notes in this notebook._")
            lines.append("")
        for j, note in enumerate(notes, 1):
            lines.append(f"### {j}. {getattr(note, 'title', 'Note')}")
            lines.append("")
            content = getattr(note, "content", "") or ""
            if content:
                lines.append(content)
                lines.append("")

        # Insights (gather from all sources)
        lines.append("## Insights")
        lines.append("")
        insight_count = 0
        for src in sources:
            try:
                insights = await src.get_insights()
            except Exception:
                insights = []
            for insight in insights:
                insight_count += 1
                lines.append(f"### {insight_count}. {getattr(insight, 'insight_type', 'Insight')}")
                lines.append("")
                icontent = getattr(insight, "content", "") or ""
                lines.append(icontent)
                lines.append("")
        if insight_count == 0:
            lines.append("_No insights generated._")
            lines.append("")

        markdown = "\n".join(lines)
        log.bind(result=Result.SUCCESS).info(f"<- export_notebook() {len(sources)} sources, {len(notes)} notes")
        return markdown
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting notebook {notebook_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error exporting notebook: {str(e)}"
        )
