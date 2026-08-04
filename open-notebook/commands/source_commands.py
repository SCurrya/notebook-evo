import time
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.database.repository import ensure_record_id
from open_notebook.domain.notebook import Source
from open_notebook.domain.transformation import Transformation
from open_notebook.exceptions import ConfigurationError

try:
    from open_notebook.graphs.source import source_graph
    from open_notebook.graphs.transformation import graph as transform_graph
    _GRAPHS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Graphs not available, source processing will be limited: {e}")
    source_graph = None  # type: ignore[assignment]
    transform_graph = None  # type: ignore[assignment]
    _GRAPHS_AVAILABLE = False


def full_model_dump(model):
    if isinstance(model, BaseModel):
        return model.model_dump()
    elif isinstance(model, dict):
        return {k: full_model_dump(v) for k, v in model.items()}
    elif isinstance(model, list):
        return [full_model_dump(item) for item in model]
    else:
        return model


class SourceProcessingInput(CommandInput):
    source_id: str
    content_state: Dict[str, Any]
    notebook_ids: List[str]
    transformations: List[str]
    embed: bool


class SourceProcessingOutput(CommandOutput):
    success: bool
    source_id: str
    embedded_chunks: int = 0
    insights_created: int = 0
    processing_time: float
    error_message: Optional[str] = None


@command(
    "process_source",
    app="open_notebook",
    retry={
        "max_attempts": 15,  # Handle deep queues (workaround for SurrealDB v2 transaction conflicts)
        "wait_strategy": "exponential_jitter",
        "wait_min": 1,
        "wait_max": 120,  # Allow queue to drain
        "stop_on": [ValueError, ConfigurationError],  # Don't retry validation/config errors
        "retry_log_level": "debug",  # Avoid log noise during transaction conflicts
    },
)
async def process_source_command(
    input_data: SourceProcessingInput,
) -> SourceProcessingOutput:
    """
    Process source content using the source_graph workflow
    """
    start_time = time.time()
    _cmd_log_id = input_data.source_id

    try:
        logger.info(
            f"[PDF/PROCESS] ▸ START source={_cmd_log_id} "
            f"notebooks={len(input_data.notebook_ids)} "
            f"transforms={len(input_data.transformations)} embed={input_data.embed}"
        )
        logger.debug(
            f"[PDF/PROCESS]   input notebook_ids={input_data.notebook_ids} "
            f"transform_ids={input_data.transformations}"
        )
        logger.debug(
            f"[PDF/PROCESS]   content_state keys="
            f"{list(input_data.content_state.keys()) if input_data.content_state else None}"
        )

        # 1. Load transformation objects from IDs
        transformations = []
        for trans_id in input_data.transformations:
            logger.info(f"[PDF/PROCESS] ▸ loading transformation {trans_id}")
            transformation = await Transformation.get(trans_id)
            if not transformation:
                logger.error(f"[PDF/PROCESS] ✗ transformation {trans_id} not found")
                raise ValueError(f"Transformation '{trans_id}' not found")
            transformations.append(transformation)
            logger.info(f"[PDF/PROCESS] ✓ transformation {trans_id} loaded")

        logger.info(f"[PDF/PROCESS] ✓ {len(transformations)} transformations loaded")

        # 2. Get existing source record to update its command field
        source = await Source.get(input_data.source_id)
        if not source:
            logger.error(f"[PDF/PROCESS] ✗ source {input_data.source_id} not found")
            raise ValueError(f"Source '{input_data.source_id}' not found")
        logger.info(f"[PDF/PROCESS] ✓ source {source.id} title={source.title!r} loaded")

        # Update source with command reference
        source.command = (
            ensure_record_id(input_data.execution_context.command_id)
            if input_data.execution_context
            else None
        )
        await source.save()

        logger.info(
            f"[PDF/PROCESS] ✓ source {source.id} linked to command "
            f"{input_data.execution_context.command_id if input_data.execution_context else 'N/A'}"
        )

        # 3. Process source with all notebooks
        logger.info(
            f"[PDF/PROCESS] ▸ invoking source_graph with "
            f"{len(input_data.notebook_ids)} notebooks "
            f"transforms={len(transformations)} embed={input_data.embed}"
        )

        # Execute source_graph with all notebooks
        if source_graph is None:
            logger.error(
                f"[PDF/PROCESS] ✗ source_graph not available (graphs import failed)"
            )
            raise ValueError("source_graph is not available (graphs import failed)")
        graph_start = time.time()
        result = await source_graph.ainvoke(
            {  # type: ignore[arg-type]
                "content_state": input_data.content_state,
                "notebook_ids": input_data.notebook_ids,  # Use notebook_ids (plural) as expected by SourceState
                "apply_transformations": transformations,
                "embed": input_data.embed,
                "source_id": input_data.source_id,  # Add the source_id to the state
            }
        )
        graph_time = time.time() - graph_start
        logger.info(
            f"[PDF/PROCESS] ✓ source_graph completed in {graph_time:.2f}s "
            f"(result keys={list(result.keys()) if isinstance(result, dict) else 'N/A'})"
        )

        processed_source = result["source"]
        try:
            full_text_len = len(processed_source.full_text or "")
        except Exception as _e:
            full_text_len = -1
            logger.debug(f"[PDF/PROCESS]   could not read full_text: {_e}")
        logger.info(
            f"[PDF/PROCESS] ✓ processed_source={processed_source.id} "
            f"full_text_len={full_text_len}"
        )

        # 4. Gather processing results (notebook associations handled by source_graph)
        # Note: embedding is fire-and-forget (async job), so we can't query the
        # count here — it hasn't completed yet. The embed_source_command logs
        # the actual count when it finishes.
        insights_list = await processed_source.get_insights()
        insights_created = len(insights_list)

        processing_time = time.time() - start_time
        embed_status = "submitted" if input_data.embed else "skipped"
        logger.info(
            f"[PDF/PROCESS] ◂ END source={processed_source.id} "
            f"in {processing_time:.2f}s insights={insights_created} "
            f"full_text={full_text_len}ch embed={embed_status}"
        )

        return SourceProcessingOutput(
            success=True,
            source_id=str(processed_source.id),
            embedded_chunks=0,
            insights_created=insights_created,
            processing_time=processing_time,
        )

    except ValueError as e:
        # Validation errors are permanent failures - don't retry
        processing_time = time.time() - start_time
        logger.error(
            f"[PDF/PROCESS] ✗ VALIDATION ERROR source={_cmd_log_id} "
            f"in {processing_time:.2f}s: {e}"
        )
        return SourceProcessingOutput(
            success=False,
            source_id=input_data.source_id,
            processing_time=processing_time,
            error_message=str(e),
        )
    except Exception as e:
        # Transient failure - will be retried (surreal-commands logs final failure)
        logger.error(
            f"[PDF/PROCESS] ✗ TRANSIENT ERROR source={_cmd_log_id} "
            f"(will retry): {type(e).__name__}: {e}"
        )
        raise


# =============================================================================
# RUN TRANSFORMATION COMMAND
# =============================================================================


class RunTransformationInput(CommandInput):
    """Input for running a transformation on an existing source."""

    source_id: str
    transformation_id: str


class RunTransformationOutput(CommandOutput):
    """Output from transformation command."""

    success: bool
    source_id: str
    transformation_id: str
    processing_time: float
    error_message: Optional[str] = None


@command(
    "run_transformation",
    app="open_notebook",
    retry={
        "max_attempts": 5,
        "wait_strategy": "exponential_jitter",
        "wait_min": 1,
        "wait_max": 60,
        "stop_on": [ValueError, ConfigurationError],  # Don't retry validation/config errors
        "retry_log_level": "debug",
    },
)
async def run_transformation_command(
    input_data: RunTransformationInput,
) -> RunTransformationOutput:
    """
    Run a transformation on an existing source to generate an insight.

    This command runs the transformation graph which:
    1. Loads the source and transformation
    2. Calls the LLM to generate insight content
    3. Creates the insight via create_insight command (fire-and-forget)

    Use this command for UI-triggered insight generation to avoid blocking
    the HTTP request while the LLM processes.

    Retry Strategy:
    - Retries up to 5 times for transient failures (network, timeout, etc.)
    - Uses exponential-jitter backoff (1-60s)
    - Does NOT retry permanent failures (ValueError for validation errors)
    """
    start_time = time.time()

    try:
        logger.info(
            f"Running transformation {input_data.transformation_id} "
            f"on source {input_data.source_id}"
        )

        # Load source
        source = await Source.get(input_data.source_id)
        if not source:
            raise ValueError(f"Source '{input_data.source_id}' not found")

        # Load transformation
        transformation = await Transformation.get(input_data.transformation_id)
        if not transformation:
            raise ValueError(
                f"Transformation '{input_data.transformation_id}' not found"
            )

        # Run transformation graph (includes LLM call + insight creation)
        if transform_graph is None:
            raise ValueError("transform_graph is not available (graphs import failed)")
        await transform_graph.ainvoke(
            input=dict(source=source, transformation=transformation)
        )

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully ran transformation {input_data.transformation_id} "
            f"on source {input_data.source_id} in {processing_time:.2f}s"
        )

        return RunTransformationOutput(
            success=True,
            source_id=input_data.source_id,
            transformation_id=input_data.transformation_id,
            processing_time=processing_time,
        )

    except ValueError as e:
        # Validation errors are permanent failures - don't retry
        processing_time = time.time() - start_time
        logger.error(
            f"Failed to run transformation {input_data.transformation_id} "
            f"on source {input_data.source_id}: {e}"
        )
        return RunTransformationOutput(
            success=False,
            source_id=input_data.source_id,
            transformation_id=input_data.transformation_id,
            processing_time=processing_time,
            error_message=str(e),
        )
    except Exception as e:
        # Transient failure - will be retried (surreal-commands logs final failure)
        logger.debug(
            f"Transient error running transformation {input_data.transformation_id} "
            f"on source {input_data.source_id}: {e}"
        )
        raise
