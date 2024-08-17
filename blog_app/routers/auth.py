from datetime import timedelta, datetime, timezone
from io import BytesIO
from typing import Annotated, Optional
import logging
import re

from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, UploadFile, File
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse

from ..database import SessionLocal
from ..models import Users
from ..tasks.tasks import compress_img
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from dotenv import load_dotenv
import os

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

templates = Jinja2Templates(directory="./blog_app/templates")

logger = logging.getLogger(__name__)

class LoginForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    async def create_oauth_form(self):
        form = await self.request.form()
        self.username = form.get("email")
        self.password = form.get("password")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

def get_password_hash(password):
    return bcrypt_context.hash(password)


def verify_password(plain_password, hashed_password):
    return bcrypt_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str, db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user


def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id, 'role': role}
    expire = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expire})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def is_password_strong(password: str) -> bool:
    if len(password) < 12:
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"\d", password):  # Check for at least one digit
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):  # Check for at least one special character
        return False
    return True


async def get_current_user(request: Request):
    try:
        token = request.cookies.get("access_token")
        if token is None:
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: str = payload.get('id')
        if username is None or user_id is None:
            await logout(request)
            return None
        return {'username': username, 'id': user_id}
    except JWTError:
        await logout(request)
        return None

async def get_authenticated_user(request: Request, user: dict = Depends(get_current_user)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_302_FOUND, detail="Not authenticated", headers={"Location": "/auth"})
    return user

async def profile_picture_upload(request: Request, user, file: UploadFile = File(None), db: Session = Depends(get_db)):
    if file and file.filename != "":
        try:
            contents = await file.read()
            image = Image.open(BytesIO(contents))

            output = BytesIO()
            image.save(output, format="PNG")
            output.seek(0)

            image_dir = "./blog_app/static/images/avas/"
            if not os.path.exists(image_dir):
                os.makedirs(image_dir)

            file_path = os.path.join(image_dir, f"{user.id}.png")

            with open(file_path, "wb") as f:
                f.write(output.read())

            compress_img.delay(file_path)

            user.has_pp = True

            db.add(user)
            db.commit()

        except UnidentifiedImageError:
            msg = 'File is not a valid image'
            logger.error(f"File is not a valid image for user {user.id}")
            return templates.TemplateResponse("settings.html", {"request": request, "user": user, "msg": msg})
        except SQLAlchemyError as db_err:
            db.rollback()
            logger.error(f"Database error: {db_err}")
            msg = 'Database error occurred'
            return templates.TemplateResponse("settings.html", {"request": request, "user": user, "msg": msg})
        except (OSError, IOError) as file_err:
            logger.error(f"File error: {file_err}")
            msg = 'File system error occurred'
            return templates.TemplateResponse("settings.html", {"request": request, "user": user, "msg": msg})
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            msg = 'An unexpected error occurred'
            return templates.TemplateResponse("settings.html", {"request": request, "user": user, "msg": msg})

@router.post("/token")
async def login_for_access_token(response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        return False

    try:
        token = create_access_token(user.username, user.id, user.role, timedelta(hours=12))

        response.set_cookie(key="access_token", value=token, httponly=True)

        return True

    except Exception as e:
        logger.error(f"Error during token creation: {str(e)}")
        return False


@router.get("/", response_class=HTMLResponse)
async def auth_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/", response_class=HTMLResponse)
async def login(request: Request, db: db_dependency):
    try:
        form = LoginForm(request)
        await form.create_oauth_form()
        response = RedirectResponse(url="/tweets", status_code=status.HTTP_302_FOUND)

        validate_user_cookie = await login_for_access_token(response=response, form_data=form, db=db)

        if not validate_user_cookie:
            msg = 'Incorrect Username or Password'
            return templates.TemplateResponse('login.html', {'request': request, 'msg': msg})

        return response

    except HTTPException:
        msg = 'Unknown Error'
        return templates.TemplateResponse('login.html', {'request': request, 'msg': msg})


@router.get("/register", response_class=HTMLResponse)
async def auth_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register", response_class=HTMLResponse)
async def register(request: Request, email: str = Form(...), username: str = Form(...),
                   firstname: str = Form(...), lastname: str = Form(...),
                   password: str = Form(...), repeat_password: str = Form(...),
                   phonenumber: str = Form(...), db: Session = Depends(get_db),
                   file: UploadFile = File(None)):

    validation1 = db.query(Users).filter(Users.username == username).first()
    validation2 = db.query(Users).filter(Users.email == email).first()

    if password != repeat_password:
        msg = 'Invalid registration request: Passwords do not match'
        return templates.TemplateResponse("register.html", {'request': request, 'msg': msg})

    if validation1 is not None:
        msg = 'Invalid registration request: Username is already taken'
        return templates.TemplateResponse("register.html", {'request': request, 'msg': msg})

    if validation2 is not None:
        msg = 'Invalid registration request: Email is already taken'
        return templates.TemplateResponse("register.html", {'request': request, 'msg': msg})

    if not is_password_strong(password):
        msg = 'Password must be at least 12 characters long, with at least one lowercase letter, ' \
              'one uppercase letter, one number, and one special character.'
        return templates.TemplateResponse("register.html", {'request': request, 'msg': msg})

    user_model = Users()
    user_model.username = username
    user_model.email = email
    user_model.first_name = firstname
    user_model.last_name = lastname
    user_model.phone_number = phonenumber

    hash_password = get_password_hash(password)
    user_model.hashed_password = hash_password
    user_model.is_active = True
    user_model.role = None

    db.add(user_model)
    db.commit()

    user_data = db.query(Users).filter(Users.username == username).first()

    await profile_picture_upload(request, user_data, file, db)

    msg = 'User successfully created'
    return templates.TemplateResponse("login.html", {'request': request, 'msg': msg})


@router.get("/logout")
async def logout(request: Request):
    msg = 'Logout Successful'
    response = templates.TemplateResponse("login.html", {'request': request, 'msg': msg})
    response.delete_cookie(key="access_token")
    return response


