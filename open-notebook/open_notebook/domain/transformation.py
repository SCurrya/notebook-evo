from typing import ClassVar, Optional

from pydantic import Field

from open_notebook.domain.base import ObjectModel, RecordModel
from open_notebook.utils.logger import Operation, Result, get_logger


class Transformation(ObjectModel):
    table_name: ClassVar[str] = "transformation"
    name: str
    title: str
    description: str
    prompt: str
    apply_default: bool

    async def save(self) -> None:
        """Save transformation and log the state transition."""
        is_new = self.id is None
        get_logger(
            "transformation_domain",
            Operation.CREATE if is_new else Operation.UPDATE,
            f"name={self.name}",
        ).debug(f"{'Creating' if is_new else 'Updating'} transformation")
        await super().save()
        get_logger(
            "transformation_domain",
            Operation.CREATE if is_new else Operation.UPDATE,
            f"transformation_id={self.id} name={self.name}",
            Result.SUCCESS,
        ).info(f"Transformation {'created' if is_new else 'updated'}")

    async def delete(self) -> bool:
        """Delete transformation and log the state transition."""
        get_logger(
            "transformation_domain", Operation.DELETE, f"transformation_id={self.id} name={self.name}"
        ).debug("Deleting transformation")
        result = await super().delete()
        get_logger(
            "transformation_domain", Operation.DELETE,
            f"transformation_id={self.id}", Result.SUCCESS,
        ).info("Transformation deleted")
        return result


class DefaultPrompts(RecordModel):
    record_id: ClassVar[str] = "open_notebook:default_prompts"
    transformation_instructions: Optional[str] = Field(
        None, description="Instructions for executing a transformation"
    )
