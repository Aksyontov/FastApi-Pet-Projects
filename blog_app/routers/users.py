from io import BytesIO
from typing import Annotated

from PIL import UnidentifiedImageError, Image
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse
from ..models import *
from ..database import SessionLocal
from .auth import get_current_user, verify_password, get_password_hash, profile_picture_upload, is_password_strong, get_authenticated_user
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
authenticated_user_dependency = Annotated[dict, Depends(get_authenticated_user)]
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
templates = Jinja2Templates(directory="./blog_app/templates")


def change_password(request: Request, user_data, password, password2):
    if password2:
        if not password:
            return False, "You should enter your current password to change it"

        if not is_password_strong(password2):
            return False, ("Password must be at least 12 characters long, with at least one lowercase letter, "
                           "one uppercase letter, one number, and one special character.")

        if verify_password(password, user_data.hashed_password):
            user_data.hashed_password = get_password_hash(password2)
            return True, "Password successfully updated"
        else:
            return False, "Current password is incorrect"

    return False, None


@router.get("/settings", response_class=HTMLResponse)
async def settings_view(request: Request, user: authenticated_user_dependency):
    return templates.TemplateResponse("settings.html",
                                      {"request": request, "user": user})


@router.post("/settings", response_class=HTMLResponse)
async def settings_change(request: Request, db: db_dependency, user: authenticated_user_dependency,
                          email: str = Form(None),
                          firstname: str = Form(None), lastname: str = Form(None),
                          phonenumber: str = Form(None), file: UploadFile = File(None),
                          password: str = Form(None), new_password: str = Form(None)):

    user_data = db.query(Users).filter(Users.id == user.get('id')).first()

    changes_made = False
    msg = "No changes were made"

    validation = db.query(Users).filter(Users.email == email).first()

    if email and email != user_data.email and validation is None:
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

    password_changed, password_msg = change_password(request, user_data, password, new_password)

    if password_changed:
        changes_made = True
    elif password_msg:
        return templates.TemplateResponse("settings.html", {"request": request, "user": user, "msg": password_msg})

    profile_picture_response = await profile_picture_upload(request, user_data, file, db)
    if profile_picture_response is not None :
        return profile_picture_response

    if changes_made:
        db.add(user_data)
        db.commit()
        msg = "Information updated"

    return templates.TemplateResponse("settings.html", {"request": request, "user": user, "msg": msg})