from sqlalchemy import select

from database.db import get_session
from database.models import PromptImage


async def get_prompt_image_file_id(image_name: str) -> str | None:
    session = get_session()
    try:
        result = await session.execute(
            select(PromptImage.file_id).where(PromptImage.image_name == image_name)
        )
        return result.scalar_one_or_none()
    finally:
        await session.close()


async def save_prompt_image_file_id(image_name: str, file_id: str) -> None:
    session = get_session()
    try:
        result = await session.execute(
            select(PromptImage).where(PromptImage.image_name == image_name)
        )
        prompt_image = result.scalar_one_or_none()
        if prompt_image is None:
            session.add(PromptImage(image_name=image_name, file_id=file_id))
        else:
            prompt_image.file_id = file_id
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
