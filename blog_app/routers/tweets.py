import os
import logging
from typing import Annotated
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette import status
from fastapi.responses import JSONResponse, RedirectResponse

from ..models import *
from ..database import SessionLocal
from .auth import get_current_user, get_authenticated_user

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from PIL import Image, UnidentifiedImageError
from io import BytesIO

from ..tasks.tasks import compress_img

router = APIRouter(
    prefix="/tweets",
    tags=["tweets"]
)

templates = Jinja2Templates(directory="./blog_app/templates")
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
authenticated_user_dependency = Annotated[dict, Depends(get_authenticated_user)]


def get_username_by_id(user_id, db: Session):
    user = db.query(Users).filter(Users.id == user_id).first()
    return user.username if user else "Unknown"


async def tweet_picture_upload(request: Request, tweet: Tweets, file: UploadFile = File(None), db: Session = Depends(get_db)):
    if file and file.filename != "":
        try:
            contents = await file.read()
            image = Image.open(BytesIO(contents))

            output = BytesIO()
            image.save(output, format="PNG")
            output.seek(0)

            image_dir = "./blog_app/static/images/tweets/"
            if not os.path.exists(image_dir):
                os.makedirs(image_dir)

            file_path = os.path.join(image_dir, f"{tweet.id}.png")

            with open(file_path, "wb") as f:
                f.write(output.read())

            compress_img.delay(file_path)

            tweet.has_image = True
            tweet.image_id = tweet.id

            db.add(tweet)
            db.commit()


        except UnidentifiedImageError:
            logger.error(f"File is not a valid image for tweet {tweet.id}")
            return RedirectResponse(
                url=f"/tweets/add_tweet?msg=Invalid image file&tweet_text={tweet.new_tweet}",
                status_code=status.HTTP_302_FOUND
            )

        except SQLAlchemyError as db_err:
            db.rollback()
            logger.error(f"Database error: {db_err}")
            return RedirectResponse(
                url=f"/tweets/add_tweet?msg=Database error occurred&tweet_text={tweet.new_tweet}",
                status_code=status.HTTP_302_FOUND
            )

        except (OSError, IOError) as file_err:
            logger.error(f"File error: {file_err}")
            return RedirectResponse(
                url=f"/tweets/add_tweet?msg=File system error occurred&tweet_text={tweet.new_tweet}",
                status_code=status.HTTP_302_FOUND
            )

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return RedirectResponse(
                url=f"/tweets/add_tweet?msg=Unexpected error occurred&tweet_text={tweet.new_tweet}",
                status_code=status.HTTP_302_FOUND
            )


@router.get("/", response_class=HTMLResponse)
async def read_all(request: Request, db: db_dependency, user: authenticated_user_dependency):

    tweets = db.query(Tweets).order_by(Tweets.id.desc()).all()

    for tweet in tweets:
        if tweet.retweeted:
            tweet.op_username = get_username_by_id(tweet.op_id, db)

    return templates.TemplateResponse("home.html", {"request": request, "tweets": tweets, 'user': user})

@router.get("/users/{user_id}", response_class=HTMLResponse)
async def read_all_by_user(request: Request, db: db_dependency, user_id: int, user: authenticated_user_dependency):

    tweets = db.query(Tweets).filter(Tweets.owner_id == user_id).order_by(Tweets.id.desc()).all()
    for tweet in tweets:
        if tweet.retweeted:
            tweet.op_username = get_username_by_id(tweet.op_id, db)

    return templates.TemplateResponse("user_page.html", {"request": request, "tweets": tweets, 'user': user})


@router.get("/add_tweet", response_class=HTMLResponse)
async def add_new_tweet(request: Request, user: authenticated_user_dependency):
    return templates.TemplateResponse("add_tweet.html", {"request": request, 'user': user})


@router.post("/add_tweet", response_class=HTMLResponse)
async def new_tweet(
    request: Request,
    db: db_dependency,
    user: authenticated_user_dependency,
    new_tweet: str = Form(None),
    file: UploadFile = File(None)
):
    if not new_tweet and (not file or file.filename == ""):
        msg = "You must provide either a tweet text or upload an image."
        return templates.TemplateResponse("add_tweet.html", {"request": request, "msg": msg})

    tweet_model = Tweets()
    tweet_model.new_tweet = new_tweet or ""
    tweet_model.liked = False
    tweet_model.owner_id = user.get("id")

    db.add(tweet_model)
    db.commit()

    tweet = db.query(Tweets).filter(Tweets.id == tweet_model.id).first()

    if file and file.filename != "":
        response = await tweet_picture_upload(request, tweet, file, db)
        if response:
            return response

    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)


@router.post("/retweet/{tweet_id}", response_class=HTMLResponse)
async def retweet(request: Request, tweet_id: int, db: db_dependency, user: authenticated_user_dependency):
    original_tweet = db.query(Tweets).filter(Tweets.id == tweet_id).first()
    if original_tweet is None:
        return RedirectResponse(url="/tweets", status_code=status.HTTP_404_NOT_FOUND)

    new_tweet = Tweets(
        new_tweet=original_tweet.new_tweet,
        liked=False,
        has_image=original_tweet.has_image,
        image_id=original_tweet.image_id,
        owner_id=user.get('id'),
        retweeted=True,
        op_id=original_tweet.owner_id
    )

    db.add(new_tweet)
    db.commit()

    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)


@router.get("/edit_tweet/{tweet_id}", response_class=HTMLResponse)
async def edit_tweet(request: Request, tweet_id: int, db: db_dependency, user: authenticated_user_dependency):
    tweet = db.query(Tweets).filter(Tweets.id == tweet_id).first()

    if tweet.owner_id != user.get('id'):
        return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("edit_tweet.html", {"request": request, "tweet": tweet, 'user': user})


@router.post("/edit_tweet/{tweet_id}", response_class=HTMLResponse)
async def edit_tweet_commit(request: Request, tweet_id: int, db: db_dependency, user: authenticated_user_dependency,
                            new_tweet: str = Form(...)):

    tweet_model = db.query(Tweets).filter(Users.id == user.get('id')).filter(Tweets.id == tweet_id).first()

    if tweet_model is None:
        return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)

    tweet_model.new_tweet = new_tweet

    db.add(tweet_model)
    db.commit()

    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)


@router.post("/delete/{tweet_id}", response_class=HTMLResponse)
async def delete_tweet(request: Request, tweet_id: int, db: db_dependency, user: authenticated_user_dependency):

    tweet_model = db.query(Tweets).filter(Tweets.id == tweet_id).filter(Tweets.owner_id == user.get('id')).first()

    if tweet_model is None:
        return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)

    db.delete(tweet_model)
    db.commit()

    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)


@router.get("/like/{tweet_id}", response_class=HTMLResponse)
async def like_tweet(request: Request, tweet_id: int, db: db_dependency, user: authenticated_user_dependency):
    tweet = db.query(Tweets).filter(Tweets.id == tweet_id).first()

    tweet.liked = not tweet.liked

    db.add(tweet)
    db.commit()

    return JSONResponse(content={"status": "success", "liked": tweet.liked})
