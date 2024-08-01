from PIL import Image, ImageOps

from blog_app.tasks.celery_app import celery_app as celery

@celery.task
def compress_img(image_path: str):
    if image_path.split('/')[-2] == 'tweets':
        image = Image.open(image_path)
        image = ImageOps.contain(image, (800, 800))
        image.save(image_path)
    else:
        image = Image.open(image_path)
        image.thumbnail((200, 200))
        image.save(image_path)