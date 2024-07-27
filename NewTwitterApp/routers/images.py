from fastapi import UploadFile, APIRouter
import shutil

router = APIRouter(
    prefix="/images",
    tags=["images"]
)

@router.post("/upload_images")
async def add_image(file: UploadFile):
    with open(f"./NewTwitterApp/static/images/{file.filename}", "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)