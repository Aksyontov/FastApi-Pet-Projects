from typing import Annotated
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from sqlalchemy.orm import Session
from starlette import status
from fastapi.responses import JSONResponse, RedirectResponse

from ..models import *
from ..database import SessionLocal
from .auth import get_current_user

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def get_username_by_id(user_id, db: get_db()):
    user = db.query(Users).filter(Users.id == user_id).first()
    return user.username if user else "Unknown"


@router.get("/", response_class=HTMLResponse)
async def read_all(request: Request, db: db_dependency):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    tweets = db.query(Tweets).order_by(Tweets.id.desc()).all()

    for tweet in tweets:
        if tweet.retweeted:
            tweet.op_username = get_username_by_id(tweet.op_id, db)

    return templates.TemplateResponse("home.html", {"request": request, "tweets": tweets, 'user': user})

@router.get("/users/{user_id}", response_class=HTMLResponse)
async def read_all_by_user(request: Request, db: db_dependency, user_id: int):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    tweets = db.query(Tweets).filter(Tweets.owner_id == user_id).order_by(Tweets.id.desc()).all()
    for tweet in tweets:
        if tweet.retweeted:
            tweet.op_username = get_username_by_id(tweet.op_id, db)

    return templates.TemplateResponse("user_page.html", {"request": request, "tweets": tweets, 'user': user})


@router.get("/add_tweet", response_class=HTMLResponse)
async def add_new_tweet(request: Request):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("add_tweet.html", {"request": request, 'user': user})


@router.post("/add_tweet", response_class=HTMLResponse)
async def new_tweet(
    request: Request,
    db: db_dependency,
    new_tweet: str = Form(...),
    file: UploadFile = File(None)
):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    tweet_model = Tweets()
    tweet_model.new_tweet = new_tweet
    tweet_model.liked = False
    tweet_model.owner_id = user.get("id")

    db.add(tweet_model)
    db.commit()

    tweet = db.query(Tweets).filter(Tweets.new_tweet == new_tweet).first()

    if file and file.filename != "":
        try:
            contents = await file.read()
            image = Image.open(BytesIO(contents))

            output = BytesIO()
            image.save(output, format="PNG")
            output.seek(0)

            with open(f"./blog_app/static/images/tweets/{tweet.id}.png", "wb") as f:
                f.write(output.read())

            compress_img.delay(f"./blog_app/static/images/tweets/{tweet.id}.png")

            tweet.has_image = True
            tweet.image_id = tweet.id

            db.add(tweet)
            db.commit()

        except UnidentifiedImageError:
            return HTMLResponse("File is not a valid image", status_code=400)

    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)


@router.post("/retweet/{tweet_id}", response_class=HTMLResponse)
async def retweet(request: Request, tweet_id: int, db: db_dependency):
    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

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
async def edit_tweet(request: Request, tweet_id: int, db: db_dependency):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    tweet = db.query(Tweets).filter(Tweets.id == tweet_id).first()

    return templates.TemplateResponse("edit_tweet.html", {"request": request, "tweet": tweet, 'user': user})


@router.post("/edit_tweet/{tweet_id}", response_class=HTMLResponse)
async def edit_tweet_commit(request: Request, tweet_id: int, db: db_dependency, new_tweet: str = Form(...)):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    tweet_model = db.query(Tweets).filter(Users.id == user.get('id')).filter(Tweets.id == tweet_id).first()

    if tweet_model is None:
        return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)

    tweet_model.new_tweet = new_tweet

    db.add(tweet_model)
    db.commit()

    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)


@router.post("/delete/{tweet_id}", response_class=HTMLResponse)
async def delete_tweet(request: Request, tweet_id: int, db: db_dependency):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    tweet_model = db.query(Tweets).filter(Tweets.id == tweet_id).filter(Tweets.owner_id == user.get('id')).first()

    if tweet_model is None:
        return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)

    db.delete(tweet_model)
    db.commit()

    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)


@router.get("/like/{tweet_id}", response_class=HTMLResponse)
async def like_tweet(request: Request, tweet_id: int, db: db_dependency):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    tweet = db.query(Tweets).filter(Tweets.id == tweet_id).first()

    tweet.liked = not tweet.liked

    db.add(tweet)
    db.commit()

    return JSONResponse(content={"status": "success", "liked": tweet.liked})
