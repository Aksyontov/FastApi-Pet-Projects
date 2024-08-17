import logging
from PIL import Image, ImageOps
from pathlib import Path

from blog_app.tasks.celery_app import celery_app as celery

logger = logging.getLogger(__name__)

@celery.task
def compress_img(image_path: str):
    try:
        image_path = Path(image_path)

        if not image_path.is_absolute():
            logger.warning(f"Relative path provided, converting to absolute path: {image_path}")
            image_path = image_path.resolve()

        if image_path.parent.name == 'tweets':
            logger.info(f"Processing tweet image: {image_path}")
            image = Image.open(image_path)
            image = ImageOps.contain(image, (800, 800))
        else:
            logger.info(f"Processing profile picture image: {image_path}")
            image = Image.open(image_path)
            image.thumbnail((200, 200))

        image.save(image_path)
        logger.info(f"Image saved successfully: {image_path}")

    except Exception as e:
        logger.error(f"Failed to process image at {image_path}: {str(e)}")
