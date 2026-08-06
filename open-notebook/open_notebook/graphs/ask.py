import operator
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
)


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

    try:
        return await _invoke(model_id)
    except Exception as primary_error:
        logger.warning(f"[fallback] primary call failed: {type(primary_error).__name__}: {primary_error}")
        # Only fall back when we actually have a model id (explicit selection)
        if not model_id:
            raise
        try:
            # Find a fallback model among available ones (same provider)
            from open_notebook.ai.models import Model, model_manager

            primary = await model_manager.get_model(model_id)
            primary_provider = getattr(primary, "provider", "") if primary else ""
            logger.warning(f"[fallback] primary provider: {primary_provider}")
            models = await Model.get_models_by_type("language")
            logger.warning(f"[fallback] found {len(models)} language models")
            # Provider names may be hyphenated (Esperanto) or underscored (DB);
            # normalize both sides before comparing.
            primary_provider_norm = primary_provider.replace("_", "-").lower()
            candidates = [
                m
                for m in models
                if (getattr(m, "provider", "") or "").replace("_", "-").lower()
                == primary_provider_norm
                and m.id != model_id
            ]
            logger.warning(f"[fallback] {len(candidates)} same-provider candidates")
            # Prefer model names matching our fallback hints
            candidates.sort(
                key=lambda m: (
                    0 if any(h in (m.name or "") for h in FALLBACK_MODEL_HINTS) else 1
                )
            )
            if not candidates:
                raise primary_error
            fallback = candidates[0]
            logger.warning(
                f"[fallback] Primary model {model_id} failed, retrying with fallback "
                f"{fallback.id} ({fallback.name}) among [{', '.join(m.name or '?' for m in candidates)}]"
            )
            return await _invoke(fallback.id)
        except Exception as fallback_error:
            logger.warning(f"[fallback] fallback path failed: {type(fallback_error).__name__}: {fallback_error}")
            raise primary_error


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

    try:
        return await _invoke(model_id)
    except Exception as primary_error:
        logger.warning(f"[fallback] structured call failed: {type(primary_error).__name__}: {primary_error}")
        if not model_id:
            raise
        try:
            from open_notebook.ai.models import Model, model_manager

            primary = await model_manager.get_model(model_id)
            primary_provider = getattr(primary, "provider", "") if primary else ""
            primary_provider_norm = primary_provider.replace("_", "-").lower()
            models = await Model.get_models_by_type("language")
            candidates = [
                m
                for m in models
                if (getattr(m, "provider", "") or "").replace("_", "-").lower()
                == primary_provider_norm
                and m.id != model_id
            ]
            candidates.sort(
                key=lambda m: (
                    0 if any(h in (m.name or "") for h in FALLBACK_MODEL_HINTS) else 1
                )
            )
            if not candidates:
                raise primary_error
            fallback = candidates[0]
            logger.warning(
                f"[fallback] Structured primary model {model_id} failed, using fallback {fallback.id}"
            )
            return await _invoke(fallback.id)
        except Exception as fallback_error:
            logger.warning(f"[fallback] structured fallback failed: {fallback_error}")
            raise primary_error


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
