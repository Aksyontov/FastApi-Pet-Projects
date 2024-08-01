from datetime import timedelta, datetime, timezone
from io import BytesIO
from typing import Annotated, Optional

from PIL import Image, UnidentifiedImageError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, UploadFile, File
from pydantic import BaseModel
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

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

SECRET_KEY = '3373758923d0830fd22fa5e733537ad23f7b3e34e8f2c470d89ca6f69f52f28e'
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')

templates = Jinja2Templates(directory="./blog_app/templates")


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


@router.post("/token")
async def login_for_access_token(response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        return False

    token = create_access_token(user.username, user.id, user.role, timedelta(hours=12))

    response.set_cookie(key="access_token", value=token, httponly=True)

    return True


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
                   password: str = Form(...), password2: str = Form(...),
                   phonenumber: str = Form(...), db: Session = Depends(get_db),
                   file: UploadFile = File(None)):

    validation1 = db.query(Users).filter(Users.username == username).first()
    validation2 = db.query(Users).filter(Users.email == email).first()

    if password != password2 or validation1 is not None or validation2 is not None:
        msg = 'Invalid registration request'
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

    user = db.query(Users).filter(Users.username == username).first()

    if file and file.filename != "":
        try:
            contents = await file.read()
            image = Image.open(BytesIO(contents))

            output = BytesIO()
            image.save(output, format="PNG")
            output.seek(0)

            with open(f"./blog_app/static/images/avas/{user.id}.png", "wb") as f:
                f.write(output.read())

            compress_img.delay(f"./blog_app/static/images/avas/{user.get('id')}.png")

            user.has_pp = True

            db.add(user)
            db.commit()

        except UnidentifiedImageError:
            return HTMLResponse("File is not a valid image", status_code=400)

    msg = 'User successfully created'
    return templates.TemplateResponse("login.html", {'request': request, 'msg': msg})


@router.get("/logout")
async def logout(request: Request):
    msg = 'Logout Successful'
    response = templates.TemplateResponse("login.html", {'request': request, 'msg': msg})
    response.delete_cookie(key="access_token")
    return response


