import operator
import time
from typing import Annotated, Any, List

from loguru import logger

from ai_prompter import Prompter
from langchain_core.output_parsers.pydantic import PydanticOutputParser
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from open_notebook.ai.provision import provision_langchain_model
from open_notebook.domain.notebook import vector_search
from open_notebook.exceptions import OpenNotebookError
from open_notebook.search.hybrid import hybrid_search
from open_notebook.utils import clean_thinking_content
from open_notebook.utils.error_classifier import classify_error
from open_notebook.utils.text_utils import extract_text_content

# Models that can act as a safe fallback when the primary model is
# temporarily unavailable (e.g. provider 503). Configured via env.
FALLBACK_MODEL_HINTS = (
    "gpt-5.4",
    "gpt-4",
    "deepseek",
    "nemotron",
    "free",
)

# ---------------------------------------------------------------------------
# Per-process model availability cache.
# When a model call fails (503 / auth / timeout) we remember it for a short
# window so later calls in the same process (e.g. the 3 ask-graph stages)
# skip straight to a working fallback instead of burning a timeout on a
# known-dead provider channel.
# ---------------------------------------------------------------------------
_MODEL_COOLDOWN: dict[str, float] = {}
_MODEL_COOLDOWN_SECONDS = 5 * 60  # 5 minutes
# Errors we consider "worth caching" - transient enough to retry after TTL.
_CACHEABLE_ERRORS = ("InternalServerError", "AuthenticationError", "TimeoutError", "ServiceUnavailable")


def _mark_model_unavailable(model_id: str, error: Exception) -> None:
    """Remember that a model call just failed (only for cacheable errors)."""
    name = type(error).__name__
    if any(k in name for k in _CACHEABLE_ERRORS):
        _MODEL_COOLDOWN[model_id] = time.monotonic()
        logger.warning(f"[fallback] cooldown {model_id} for {_MODEL_COOLDOWN_SECONDS}s ({name})")


def _is_model_available(model_id: str) -> bool:
    mark = _MODEL_COOLDOWN.get(model_id)
    if mark is None:
        return True
    if time.monotonic() - mark > _MODEL_COOLDOWN_SECONDS:
        _MODEL_COOLDOWN.pop(model_id, None)
        return True
    return False


async def _model_call_with_fallback(
    system_prompt: str,
    model_id: str | None,
    provider: str,
    max_tokens: int,
    call_fn,
) -> "Any":
    """Invoke `call_fn(model)` with the requested model; if the call fails
    (e.g. provider 503 on gpt-5.6-luna), retry once with an available
    fallback model from the same provider (e.g. gpt-5.4-mini)."""

    async def _invoke(mid: str | None):
        model = await provision_langchain_model(
            system_prompt, mid, provider, max_tokens=max_tokens
        )
        return await call_fn(model)

    # If the primary model is in cooldown (recently failed with 503/auth),
    # skip straight to the fallback chain - don't burn a timeout on it.
    if model_id and not _is_model_available(model_id):
        logger.warning(f"[fallback] primary {model_id} in cooldown, skipping to fallback chain")
        last_error: Exception | None = None
        for fallback in await _fallback_chain(model_id, FALLBACK_MODEL_HINTS):
            try:
                logger.warning(f"[fallback] trying cooldown-skipped fallback {fallback.id} ({fallback.name})")
                return await _invoke(fallback.id)
            except Exception as e:
                _mark_model_unavailable(fallback.id, e)
                last_error = e
        raise last_error or RuntimeError("no fallback models available")

    try:
        return await _invoke(model_id)
    except Exception as primary_error:
        _mark_model_unavailable(model_id or "", primary_error)
        logger.warning(f"[fallback] primary call failed: {type(primary_error).__name__}: {primary_error}")
        # Only fall back when we actually have a model id (explicit selection)
        if not model_id:
            raise
        try:
            # Fallback across providers (chain): same-provider hints first,
            # then same-provider, then any other provider's language model.
            last_error = primary_error
            for fallback in await _fallback_chain(model_id, FALLBACK_MODEL_HINTS):
                try:
                    logger.warning(
                        f"[fallback] Primary model {model_id} failed, trying {fallback.id} ({fallback.name})"
                    )
                    return await _invoke(fallback.id)
                except Exception as e:
                    _mark_model_unavailable(fallback.id, e)
                    last_error = e
                    logger.warning(f"[fallback] fallback {fallback.id} also failed: {type(e).__name__}")
            raise last_error
        except Exception as fallback_error:
            logger.warning(f"[fallback] fallback path failed: {type(fallback_error).__name__}: {fallback_error}")
            raise primary_error


async def _fallback_chain(
    failed_model_id: str, hint_substrings: list[str]
) -> "list[Any]":
    """Return an ordered chain of fallback language models for a failed call.

    Order (best effort, resilient to single-provider outages):
      1. Same-provider candidates matching fallback hints (e.g. a "mini" model)
      2. Same-provider candidates (any)
      3. Other providers' language models (cross-provider fallback)

    Returns an empty list if nothing is available.
    """
    try:
        from open_notebook.ai.models import Model, model_manager

        primary = await model_manager.get_model(failed_model_id)
        primary_provider = getattr(primary, "provider", "") if primary else ""
        primary_provider_norm = primary_provider.replace("_", "-").lower()
        models = await Model.get_models_by_type("language")

        def _norm(p: str | None) -> str:
            return (p or "").replace("_", "-").lower()

        same_provider = [
            m for m in models
            if _norm(getattr(m, "provider", None)) == primary_provider_norm
            and m.id != failed_model_id
        ]
        other_provider = [
            m for m in models
            if _norm(getattr(m, "provider", None)) != primary_provider_norm
            and m.id != failed_model_id
        ]

        def _hinted(models_list):
            """Sort by hint priority (earlier hint in the tuple = higher priority).
            Falls back to the model name for stable ordering.
            """

            def _score(m):
                name = m.name or ""
                for i, h in enumerate(hint_substrings):
                    if h in name:
                        return i
                return len(hint_substrings)

            return sorted(models_list, key=lambda m: (_score(m), m.name or ""))

        chain: list = []
        seen: set[str] = set()
        for bucket in (_hinted(same_provider), same_provider, _hinted(other_provider)):
            for m in bucket:
                if m.id in seen:
                    continue
                seen.add(m.id)
                # Skip models in cooldown (recently failed with 503/auth/etc).
                if not _is_model_available(m.id):
                    logger.debug(f"[fallback] skipping {m.id} (in cooldown)")
                    continue
                chain.append(m)
        return chain
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[fallback] _fallback_chain failed: {exc}")
        return []


async def _structured_call_with_fallback(
    system_prompt: str,
    model_id: str | None,
    provider: str,
    max_tokens: int,
) -> "Any":
    """Structured (JSON) model call with automatic fallback on provider error.

    Note: many OpenAI-compatible providers (e.g. xcode.best) do not support
    `response_format=json_object` and time out or 503. We therefore attempt
    structured first, then fall back to plain chat (prompt-guided JSON).
    """

    async def _invoke_plain(mid: str | None):
        model = await provision_langchain_model(
            system_prompt, mid, provider, max_tokens=max_tokens
        )
        return await model.ainvoke(system_prompt)

    async def _invoke(mid: str | None):
        try:
            model = await provision_langchain_model(
                system_prompt,
                mid,
                provider,
                max_tokens=max_tokens,
                structured=dict(type="json"),
            )
            return await model.ainvoke(system_prompt)
        except Exception as json_mode_error:
            logger.warning(
                f"[fallback] JSON mode failed for {mid}, retrying plain: {type(json_mode_error).__name__}"
            )
            return await _invoke_plain(mid)

    # Primary in cooldown (known 503/auth) -> skip straight to fallback chain.
    if model_id and not _is_model_available(model_id):
        logger.warning(f"[fallback] structured primary {model_id} in cooldown, skipping to fallback chain")
        last_error: Exception | None = None
        for fallback in await _fallback_chain(model_id, FALLBACK_MODEL_HINTS):
            try:
                logger.warning(f"[fallback] structured cooldown-skipped fallback {fallback.id} ({fallback.name})")
                return await _invoke(fallback.id)
            except Exception as e:
                _mark_model_unavailable(fallback.id, e)
                last_error = e
        raise last_error or RuntimeError("no fallback models available")

    try:
        return await _invoke(model_id)
    except Exception as primary_error:
        _mark_model_unavailable(model_id or "", primary_error)
        logger.warning(f"[fallback] structured call failed: {type(primary_error).__name__}: {primary_error}")
        if not model_id:
            raise
        last_error = primary_error
        # Try every candidate in order (same-provider hints -> same-provider ->
        # other providers) until one succeeds.
        for fallback in await _fallback_chain(model_id, FALLBACK_MODEL_HINTS):
            try:
                logger.warning(
                    f"[fallback] Structured primary {model_id} failed, trying {fallback.id} ({fallback.name})"
                )
                return await _invoke(fallback.id)
            except Exception as e:
                _mark_model_unavailable(fallback.id, e)
                last_error = e
                logger.warning(f"[fallback] structured fallback {fallback.id} also failed: {type(e).__name__}")
        raise last_error


class SubGraphState(TypedDict):
    question: str
    term: str
    instructions: str
    results: dict
    answer: str
    ids: list  # Added for provide_answer function


class Search(BaseModel):
    term: str
    instructions: str = Field(
        description="Tell the answeting LLM what information you need extracted from this search"
    )


class Strategy(BaseModel):
    reasoning: str
    searches: List[Search] = Field(
        default_factory=list,
        description="You can add up to five searches to this strategy",
    )


class ThreadState(TypedDict):
    question: str
    strategy: Strategy
    answers: Annotated[list, operator.add]
    final_answer: str


async def call_model_with_messages(state: ThreadState, config: RunnableConfig) -> dict:
    try:
        parser = PydanticOutputParser(pydantic_object=Strategy)
        system_prompt = Prompter(prompt_template="ask/entry", parser=parser).render(  # type: ignore[arg-type]
            data=state  # type: ignore[arg-type]
        )
        ai_message = await _structured_call_with_fallback(
            system_prompt,
            config.get("configurable", {}).get("strategy_model"),
            "tools",
            max_tokens=2000,
        )

        # Clean the thinking content from the response
        message_content = extract_text_content(ai_message.content)
        cleaned_content = clean_thinking_content(message_content)

        # Parse the cleaned JSON content
        strategy = parser.parse(cleaned_content)

        return {"strategy": strategy}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


async def trigger_queries(state: ThreadState, config: RunnableConfig):
    return [
        Send(
            "provide_answer",
            {
                "question": state["question"],
                "instructions": s.instructions,
                "term": s.term,
                # "type": s.type,
            },
        )
        for s in state["strategy"].searches
    ]


async def provide_answer(state: SubGraphState, config: RunnableConfig) -> dict:
    try:
        payload = state
        # Hybrid retrieval: vector + BM25 fused by RRF (rerank optional)
        hybrid = await hybrid_search(
            state["term"],
            limit=10,
            search_sources=True,
            search_notes=True,
            rerank=False,
        )
        if not hybrid:
            return {"answers": []}
        results = [
            {
                "id": r.id,
                "title": r.title,
                "content": r.content,
                "parent_id": r.parent_id,
            }
            for r in hybrid
        ]
        payload["results"] = results
        payload["ids"] = [r["id"] for r in results]
        system_prompt = Prompter(prompt_template="ask/query_process").render(data=payload)  # type: ignore[arg-type]
        ai_message = await _model_call_with_fallback(
            system_prompt,
            config.get("configurable", {}).get("answer_model"),
            "tools",
            max_tokens=2000,
            call_fn=lambda model: model.ainvoke(system_prompt),
        )
        ai_content = extract_text_content(ai_message.content)
        return {"answers": [clean_thinking_content(ai_content)]}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


async def write_final_answer(state: ThreadState, config: RunnableConfig) -> dict:
    try:
        system_prompt = Prompter(prompt_template="ask/final_answer").render(data=state)  # type: ignore[arg-type]
        ai_message = await _model_call_with_fallback(
            system_prompt,
            config.get("configurable", {}).get("final_answer_model"),
            "tools",
            max_tokens=2000,
            call_fn=lambda model: model.ainvoke(system_prompt),
        )
        final_content = extract_text_content(ai_message.content)
        return {"final_answer": clean_thinking_content(final_content)}
    except OpenNotebookError:
        raise
    except Exception as e:
        error_class, user_message = classify_error(e)
        raise error_class(user_message) from e


agent_state = StateGraph(ThreadState)
agent_state.add_node("agent", call_model_with_messages)
agent_state.add_node("provide_answer", provide_answer)
agent_state.add_node("write_final_answer", write_final_answer)
agent_state.add_edge(START, "agent")
agent_state.add_conditional_edges("agent", trigger_queries, ["provide_answer"])
agent_state.add_edge("provide_answer", "write_final_answer")
agent_state.add_edge("write_final_answer", END)

graph = agent_state.compile()
