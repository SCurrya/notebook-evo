"""
Studio 路由器 - 提供 Studio 模块的 API 端点。

包含四个功能模块：
1. 自定义模板引擎：模板 CRUD（POST/GET/PUT/DELETE /v1/studio/templates）
2. 报告生成器：POST /v1/studio/report/generate
3. FAQs 创建工具：POST /v1/studio/faq/generate
4. 时间线生成器：POST /v1/studio/timeline/generate

报告、FAQ、时间线生成均复用现有 Transformations 引擎。
"""

import json
from typing import List

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import (
    FAQGenerateRequest,
    FAQGenerateResponse,
    FAQItem,
    ReportGenerateRequest,
    ReportGenerateResponse,
    StudioTemplateCreate,
    StudioTemplateResponse,
    StudioTemplateUpdate,
    TimelineEvent,
    TimelineGenerateRequest,
    TimelineGenerateResponse,
)
from open_notebook.ai.models import DefaultModels
from open_notebook.domain.notebook import Notebook
from open_notebook.domain.studio import StudioTemplate
from open_notebook.domain.transformation import Transformation
from open_notebook.exceptions import InvalidInputError, OpenNotebookError
from open_notebook.graphs.transformation import graph as transformation_graph
from open_notebook.utils.logger import Operation, Result, get_logger

router = APIRouter()


# === 报告/FAQ/时间线生成所用的提示词模板 ===

# 报告类型对应的提示词
REPORT_PROMPTS = {
    "academic": (
        "你是一位学术研究助手。请根据以下笔记本内容生成一份学术报告。\n"
        "报告应包含：摘要、研究背景、主要发现、方法论、结论和参考文献要点。\n"
        "使用严谨的学术语言，保持客观中立。输出 Markdown 格式。"
    ),
    "business": (
        "你是一位商业分析顾问。请根据以下笔记本内容生成一份商业报告。\n"
        "报告应包含：执行摘要、市场洞察、关键数据、风险分析、建议和下一步行动。\n"
        "使用专业的商业语言，突出可操作的见解。输出 Markdown 格式。"
    ),
    "brief": (
        "你是一位信息摘要专家。请根据以下笔记本内容生成一份简短摘要报告。\n"
        "报告应包含：核心要点（3-5 条）、关键结论、注意事项。\n"
        "保持简洁明了，控制在 500 字以内。输出 Markdown 格式。"
    ),
}

# FAQ 生成提示词
FAQ_PROMPT_TEMPLATE = (
    "你是一位知识问答助手。请根据以下笔记本内容生成 {num} 个常见问题解答（FAQ）。\n"
    "要求：\n"
    "1. 问题应覆盖内容的关键知识点\n"
    "2. 回答应准确、简洁、基于提供的内容\n"
    "3. 严格输出 JSON 数组格式，每个元素包含 question 和 answer 字段\n"
    "输出格式示例：\n"
    '[{{"question": "问题1", "answer": "回答1"}}, {{"question": "问题2", "answer": "回答2"}}]'
)

# 时间线生成提示词
TIMELINE_PROMPT = (
    "你是一位时间线分析专家。请从以下笔记本内容中提取所有具有时间属性的事件，"
    "并按时间先后顺序排列。\n"
    "要求：\n"
    "1. 提取所有提及日期、时间节点的事件\n"
    "2. 日期尽量标准化为 YYYY-MM-DD 格式，无法确定具体日期的可使用年份或月份\n"
    "3. 事件描述应简洁明了\n"
    "4. 严格输出 JSON 数组格式，每个元素包含 date 和 event 字段\n"
    "输出格式示例：\n"
    '[{{"date": "2024-01-15", "event": "事件描述1"}}, {{"date": "2024-03-01", "event": "事件描述2"}}]'
)


async def _get_notebook_context(notebook_id: str) -> str:
    """获取笔记本的完整上下文内容，供 LLM 处理使用。"""
    log = get_logger("studio_api", Operation.READ, f"notebook_id={notebook_id}")
    log.debug("-> _get_notebook_context()")
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="笔记本不存在")
        context = await notebook.get_context()
        if not context.strip():
            raise HTTPException(
                status_code=400,
                detail="笔记本内容为空，无法生成结果。请先添加来源或笔记。",
            )
        log.bind(result=Result.SUCCESS).info("<- _get_notebook_context() 获取内容成功")
        return context
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取笔记本上下文失败 notebook_id={notebook_id}: {e}")
        get_logger(
            "studio_api", Operation.READ, f"notebook_id={notebook_id}", Result.FAILURE
        ).error(f"_get_notebook_context() 失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取笔记本内容失败: {e}"
        )


async def _run_transformation(prompt: str, input_text: str, title: str) -> str:
    """
    调用现有 Transformations 引擎执行转换。

    创建临时 Transformation 对象（不持久化），使用默认转换模型。
    """
    log = get_logger("studio_api", Operation.TRANSFORM, f"title={title}")
    log.debug("-> _run_transformation()")
    try:
        # 创建临时 Transformation 对象（不保存到数据库）
        transformation = Transformation(
            name=f"studio_{title}",
            title=title,
            description="Studio 临时转换",
            prompt=prompt,
            apply_default=False,
        )

        # 获取默认转换模型
        defaults = await DefaultModels.get_instance()
        model_id = defaults.default_transformation_model

        # 调用转换引擎
        result = await transformation_graph.ainvoke(
            dict(input_text=input_text, transformation=transformation),
            config=dict(configurable={"model_id": model_id} if model_id else {}),
        )

        output = result["output"]
        log.bind(result=Result.SUCCESS).info("<- _run_transformation() 生成成功")
        return output
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"转换引擎执行失败 title={title}: {e}")
        get_logger(
            "studio_api", Operation.TRANSFORM, f"title={title}", Result.FAILURE
        ).error(f"_run_transformation() 失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"转换引擎执行失败: {e}"
        )


def _parse_json_response(raw: str, fallback_field: str) -> list:
    """
    从 LLM 输出中解析 JSON 数组。

    LLM 可能输出包含 Markdown 代码块或额外文本的响应，
    此函数尝试提取并解析 JSON 数组。
    """
    text = raw.strip()

    # 尝试去除 Markdown 代码块包裹
    if text.startswith("```"):
        lines = text.split("\n")
        # 去除首行 ``` 和末行 ```
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # 尝试直接解析
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    # 尝试提取第一个 JSON 数组
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    logger.warning(f"无法解析 JSON 响应，{fallback_field} 解析失败，原始输出: {raw[:200]}")
    raise HTTPException(
        status_code=500,
        detail=f"无法解析 LLM 输出为 JSON 格式，请重试。",
    )


# =========================================================================
# 模块 1：自定义模板引擎 - 模板 CRUD
# =========================================================================


@router.get("/v1/studio/templates", response_model=List[StudioTemplateResponse])
async def list_templates():
    """获取所有 Studio 自定义模板。"""
    log = get_logger("studio_api", Operation.READ)
    log.debug("-> list_templates()")
    try:
        templates = await StudioTemplate.get_all(order_by="updated desc")
        log.bind(result=Result.SUCCESS).info(
            f"<- list_templates() count={len(templates)}"
        )
        return [
            StudioTemplateResponse(
                id=t.id or "",
                name=t.name,
                description=t.description,
                prompt=t.prompt,
                output_format=t.output_format,
                created_at=str(t.created) if t.created else "",
                updated_at=str(t.updated) if t.updated else "",
            )
            for t in templates
        ]
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        get_logger("studio_api", Operation.READ, "-", Result.FAILURE).error(
            f"list_templates() 失败: {e}"
        )
        raise HTTPException(status_code=500, detail=f"获取模板列表失败: {e}")


@router.post("/v1/studio/templates", response_model=StudioTemplateResponse)
async def create_template(template_data: StudioTemplateCreate):
    """创建新的 Studio 自定义模板。"""
    log = get_logger("studio_api", Operation.CREATE, f"name={template_data.name}")
    log.debug("-> create_template()")
    try:
        template = StudioTemplate(
            name=template_data.name,
            description=template_data.description,
            prompt=template_data.prompt,
            output_format=template_data.output_format,
        )
        await template.save()

        log.bind(result=Result.SUCCESS).info(
            f"<- create_template() id={template.id}"
        )
        return StudioTemplateResponse(
            id=template.id or "",
            name=template.name,
            description=template.description,
            prompt=template.prompt,
            output_format=template.output_format,
            created_at=str(template.created) if template.created else "",
            updated_at=str(template.updated) if template.updated else "",
        )
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建模板失败: {e}")
        get_logger(
            "studio_api", Operation.CREATE, f"name={template_data.name}", Result.FAILURE
        ).error(f"create_template() 失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建模板失败: {e}")


@router.get("/v1/studio/templates/{template_id}", response_model=StudioTemplateResponse)
async def get_template(template_id: str):
    """获取指定的 Studio 自定义模板。"""
    log = get_logger("studio_api", Operation.READ, f"template_id={template_id}")
    log.debug("-> get_template()")
    try:
        template = await StudioTemplate.get(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")

        log.bind(result=Result.SUCCESS).info("<- get_template() 找到模板")
        return StudioTemplateResponse(
            id=template.id or "",
            name=template.name,
            description=template.description,
            prompt=template.prompt,
            output_format=template.output_format,
            created_at=str(template.created) if template.created else "",
            updated_at=str(template.updated) if template.updated else "",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模板失败 template_id={template_id}: {e}")
        get_logger(
            "studio_api", Operation.READ, f"template_id={template_id}", Result.FAILURE
        ).error(f"get_template() 失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模板失败: {e}")


@router.put("/v1/studio/templates/{template_id}", response_model=StudioTemplateResponse)
async def update_template(template_id: str, template_update: StudioTemplateUpdate):
    """更新指定的 Studio 自定义模板。"""
    log = get_logger("studio_api", Operation.UPDATE, f"template_id={template_id}")
    log.debug("-> update_template()")
    try:
        template = await StudioTemplate.get(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")

        # 仅更新提供的字段
        if template_update.name is not None:
            template.name = template_update.name
        if template_update.description is not None:
            template.description = template_update.description
        if template_update.prompt is not None:
            template.prompt = template_update.prompt
        if template_update.output_format is not None:
            template.output_format = template_update.output_format

        await template.save()

        log.bind(result=Result.SUCCESS).info("<- update_template() 更新成功")
        return StudioTemplateResponse(
            id=template.id or "",
            name=template.name,
            description=template.description,
            prompt=template.prompt,
            output_format=template.output_format,
            created_at=str(template.created) if template.created else "",
            updated_at=str(template.updated) if template.updated else "",
        )
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新模板失败 template_id={template_id}: {e}")
        get_logger(
            "studio_api", Operation.UPDATE, f"template_id={template_id}", Result.FAILURE
        ).error(f"update_template() 失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新模板失败: {e}")


@router.delete("/v1/studio/templates/{template_id}")
async def delete_template(template_id: str):
    """删除指定的 Studio 自定义模板。"""
    log = get_logger("studio_api", Operation.DELETE, f"template_id={template_id}")
    log.debug("-> delete_template()")
    try:
        template = await StudioTemplate.get(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="模板不存在")

        await template.delete()

        log.bind(result=Result.SUCCESS).info("<- delete_template() 删除成功")
        return {"message": "模板删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除模板失败 template_id={template_id}: {e}")
        get_logger(
            "studio_api", Operation.DELETE, f"template_id={template_id}", Result.FAILURE
        ).error(f"delete_template() 失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除模板失败: {e}")


# =========================================================================
# 模块 2：报告生成器
# =========================================================================


@router.post("/v1/studio/report/generate", response_model=ReportGenerateResponse)
async def generate_report(request: ReportGenerateRequest):
    """根据笔记本内容生成报告（学术/商业/简短摘要）。"""
    log = get_logger(
        "studio_api", Operation.TRANSFORM,
        f"notebook_id={request.notebook_id} report_type={request.report_type}",
    )
    log.debug("-> generate_report()")
    try:
        # 获取笔记本上下文
        context = await _get_notebook_context(request.notebook_id)

        # 获取对应报告类型的提示词
        prompt = REPORT_PROMPTS.get(request.report_type, REPORT_PROMPTS["academic"])

        # 调用转换引擎生成报告
        report = await _run_transformation(
            prompt=prompt,
            input_text=context,
            title=f"report_{request.report_type}",
        )

        log.bind(result=Result.SUCCESS).info("<- generate_report() 报告生成成功")
        return ReportGenerateResponse(
            report=report,
            report_type=request.report_type,
            notebook_id=request.notebook_id,
        )
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"报告生成失败: {e}")
        get_logger(
            "studio_api", Operation.TRANSFORM,
            f"notebook_id={request.notebook_id}", Result.FAILURE,
        ).error(f"generate_report() 失败: {e}")
        raise HTTPException(status_code=500, detail=f"报告生成失败: {e}")


# =========================================================================
# 模块 3：FAQs 创建工具
# =========================================================================


@router.post("/v1/studio/faq/generate", response_model=FAQGenerateResponse)
async def generate_faq(request: FAQGenerateRequest):
    """根据笔记本内容生成 FAQ 问答列表。"""
    log = get_logger(
        "studio_api", Operation.TRANSFORM,
        f"notebook_id={request.notebook_id} num_questions={request.num_questions}",
    )
    log.debug("-> generate_faq()")
    try:
        # 获取笔记本上下文
        context = await _get_notebook_context(request.notebook_id)

        # 构建 FAQ 提示词
        prompt = FAQ_PROMPT_TEMPLATE.format(num=request.num_questions)

        # 调用转换引擎生成 FAQ
        raw_output = await _run_transformation(
            prompt=prompt,
            input_text=context,
            title="faq",
        )

        # 解析 JSON 响应
        faq_list = _parse_json_response(raw_output, "FAQ")

        # 转换为 FAQItem 列表
        faqs = []
        for item in faq_list:
            if isinstance(item, dict) and "question" in item and "answer" in item:
                faqs.append(
                    FAQItem(
                        question=str(item["question"]),
                        answer=str(item["answer"]),
                    )
                )

        if not faqs:
            logger.warning("FAQ 解析结果为空")
            raise HTTPException(
                status_code=500, detail="FAQ 生成结果为空，请重试。"
            )

        log.bind(result=Result.SUCCESS).info(
            f"<- generate_faq() 生成 {len(faqs)} 条 FAQ"
        )
        return FAQGenerateResponse(
            faqs=faqs,
            notebook_id=request.notebook_id,
        )
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"FAQ 生成失败: {e}")
        get_logger(
            "studio_api", Operation.TRANSFORM,
            f"notebook_id={request.notebook_id}", Result.FAILURE,
        ).error(f"generate_faq() 失败: {e}")
        raise HTTPException(status_code=500, detail=f"FAQ 生成失败: {e}")


# =========================================================================
# 模块 4：时间线生成器
# =========================================================================


@router.post("/v1/studio/timeline/generate", response_model=TimelineGenerateResponse)
async def generate_timeline(request: TimelineGenerateRequest):
    """根据笔记本内容提取事件并生成时间线。"""
    log = get_logger(
        "studio_api", Operation.TRANSFORM,
        f"notebook_id={request.notebook_id}",
    )
    log.debug("-> generate_timeline()")
    try:
        # 获取笔记本上下文
        context = await _get_notebook_context(request.notebook_id)

        # 调用转换引擎生成时间线
        raw_output = await _run_transformation(
            prompt=TIMELINE_PROMPT,
            input_text=context,
            title="timeline",
        )

        # 解析 JSON 响应
        event_list = _parse_json_response(raw_output, "时间线")

        # 转换为 TimelineEvent 列表
        events = []
        for item in event_list:
            if isinstance(item, dict) and "date" in item and "event" in item:
                events.append(
                    TimelineEvent(
                        date=str(item["date"]),
                        event=str(item["event"]),
                    )
                )

        if not events:
            logger.warning("时间线解析结果为空")
            raise HTTPException(
                status_code=500, detail="时间线生成结果为空，请重试。"
            )

        log.bind(result=Result.SUCCESS).info(
            f"<- generate_timeline() 生成 {len(events)} 个事件"
        )
        return TimelineGenerateResponse(
            events=events,
            notebook_id=request.notebook_id,
        )
    except HTTPException:
        raise
    except OpenNotebookError:
        raise
    except Exception as e:
        logger.error(f"时间线生成失败: {e}")
        get_logger(
            "studio_api", Operation.TRANSFORM,
            f"notebook_id={request.notebook_id}", Result.FAILURE,
        ).error(f"generate_timeline() 失败: {e}")
        raise HTTPException(status_code=500, detail=f"时间线生成失败: {e}")
