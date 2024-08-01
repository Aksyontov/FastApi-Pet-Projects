from io import BytesIO
from typing import Annotated

from PIL import UnidentifiedImageError, Image
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse
from ..models import *
from ..database import SessionLocal
from .auth import get_current_user, verify_password, get_password_hash
from ..tasks.tasks import compress_img
from passlib.context import CryptContext

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not Found"}}
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
templates = Jinja2Templates(directory="./blog_app/templates")


@router.get("/settings", response_class=HTMLResponse)
async def settings_view(request: Request):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("settings.html",
                                      {"request": request, "user": user})


@router.post("/settings", response_class=HTMLResponse)
async def settings_change(request: Request, db: db_dependency, email: str = Form(None),
                          firstname: str = Form(None), lastname: str = Form(None),
                          phonenumber: str = Form(None), file: UploadFile = File(None),
                          password: str = Form(None), password2: str = Form(None)):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    user_data = db.query(Users).filter(Users.id == user.get('id')).first()

    changes_made = False
    msg = "No changes were made"

    if email and email != user_data.email:
        user_data.email = email
        changes_made = True

    if firstname and firstname != user_data.first_name:
        user_data.first_name = firstname
        changes_made = True

    if lastname and lastname != user_data.last_name:
        user_data.last_name = lastname
        changes_made = True

    if phonenumber and phonenumber != user_data.phone_number:
        user_data.phone_number = phonenumber
        changes_made = True

    if file and file.filename != "":
        try:
            contents = await file.read()
            image = Image.open(BytesIO(contents))

            output = BytesIO()
            image.save(output, format="PNG")
            output.seek(0)

            with open(f"./blog_app/static/images/avas/{user.get('id')}.png", "wb") as f:
                f.write(output.read())


            compress_img.delay(f"./blog_app/static/images/avas/{user.get('id')}.png")

            user_data.has_pp = True
            changes_made = True

        except UnidentifiedImageError:
            return HTMLResponse("File is not a valid image", status_code=400)

    if password2:
        if not password:
            return templates.TemplateResponse("settings.html",
                                              {"request": request, "user": user,
                                               "msg": "You should enter your current password to change it"})

        if verify_password(password, user_data.hashed_password):
            user_data.hashed_password = get_password_hash(password2)
            changes_made = True
        else:
            return templates.TemplateResponse("settings.html", {"request": request, "user": user,
                                                                "msg": "Current password is incorrect"})

    if changes_made:
        db.add(user_data)
        db.commit()
        msg = "Information updated"

    return templates.TemplateResponse("settings.html", {"request": request, "user": user, "msg": msg})