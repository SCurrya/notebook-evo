"""
Studio 域模型定义。

包含自定义模板（StudioTemplate）的持久化模型，
用于支持 Studio 模块中的模板管理功能。
"""

from typing import ClassVar

from open_notebook.domain.base import ObjectModel
from open_notebook.utils.logger import Operation, Result, get_logger


class StudioTemplate(ObjectModel):
    """Studio 自定义模板域模型，持久化到 SurrealDB 的 studio_template 表。"""

    table_name: ClassVar[str] = "studio_template"
    name: str
    description: str = ""
    prompt: str
    output_format: str = "markdown"

    async def save(self) -> None:
        """保存模板并记录日志。"""
        is_new = self.id is None
        get_logger(
            "studio_domain",
            Operation.CREATE if is_new else Operation.UPDATE,
            f"name={self.name}",
        ).debug(f"{'创建' if is_new else '更新'} Studio 模板")
        await super().save()
        get_logger(
            "studio_domain",
            Operation.CREATE if is_new else Operation.UPDATE,
            f"template_id={self.id} name={self.name}",
            Result.SUCCESS,
        ).info(f"Studio 模板{'创建' if is_new else '更新'}成功")

    async def delete(self) -> bool:
        """删除模板并记录日志。"""
        get_logger(
            "studio_domain", Operation.DELETE, f"template_id={self.id} name={self.name}"
        ).debug("删除 Studio 模板")
        result = await super().delete()
        get_logger(
            "studio_domain", Operation.DELETE,
            f"template_id={self.id}", Result.SUCCESS,
        ).info("Studio 模板删除成功")
        return result
