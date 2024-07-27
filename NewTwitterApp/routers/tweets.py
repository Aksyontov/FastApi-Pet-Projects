from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Request, Form
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import RedirectResponse

from ..models import Tweets
from ..database import SessionLocal
from .auth import get_current_user

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="/tweets",
    tags=["tweets"]
)

templates = Jinja2Templates(directory="./NewTwitterApp/templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class TweetRequest(BaseModel):
    new_tweet: str = Field(min_length=1, max_length=280)


@router.get("/", response_class=HTMLResponse)
async def read_all(request: Request, db: db_dependency):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    tweets = db.query(Tweets).all()

    return templates.TemplateResponse("home.html", {"request": request, "tweets": tweets, 'user': user})


@router.get("/add_tweet", response_class=HTMLResponse)
async def add_new_tweet(request: Request):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("add_tweet.html", {"request": request, 'user': user})


@router.post("/add_tweet", response_class=HTMLResponse)
async def new_tweet(request: Request,  db: db_dependency, new_tweet: str = Form(...)):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    tweet_model = Tweets()
    tweet_model.new_tweet = new_tweet
    tweet_model.liked = False
    tweet_model.owner_id = user.get("id")
    tweet_model.owner = user.get("username")

    db.add(tweet_model)
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

    tweet_model = db.query(Tweets).filter(Tweets.id == tweet_id).first()
    tweet_model.new_tweet = new_tweet

    db.add(tweet_model)
    db.commit()

    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)


@router.get("/delete/{tweet_id}")
async def delete_tweet(request: Request, tweet_id: int, db: db_dependency):

    user = await get_current_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)

    tweet_model = db.query(Tweets).filter(Tweets.id == tweet_id).filter(Tweets.owner_id == user.get('id')).first()

    if tweet_model is None:
        return RedirectResponse(url='/todos', status_code=status.HTTP_302_FOUND)

    db.query(Tweets).filter(Tweets.id == tweet_id).delete()

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

    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)


@router.get("/", status_code=status.HTTP_200_OK)
async def read_all(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    return db.query(Tweets).filter(Tweets.owner_id == user.get('id')).all()


@router.get("/{tweet_id}", status_code=status.HTTP_200_OK)
async def read_tweet(user: user_dependency, db: db_dependency, tweet_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    todo_model = db.query(Tweets).filter(Tweets.id == tweet_id).filter(Tweets.owner_id == user.get('id')).first()
    if todo_model is not None:
        return todo_model
    raise HTTPException(status_code=404, detail="Tweet not found.")

@router.post("/new_tweet", status_code=status.HTTP_201_CREATED)
async def post_tweet(user: user_dependency, db: db_dependency, tweet_request: TweetRequest):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    tweet_model = Tweets(**tweet_request.dict(), owner_id=user.get('id'), owner=user.get('username'))

    db.add(tweet_model)
    db.commit()


@router.put("/{tweet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(user: user_dependency, db: db_dependency, tweet_request: TweetRequest, tweet_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    tweet_model = db.query(Tweets).filter(Tweets.id == tweet_id).filter(Tweets.owner_id == user.get('id')).first()
    if tweet_model is None:
        raise HTTPException(status_code=404, detail='Tweet not found.')

    tweet_model.new_tweet = tweet_request.new_tweet

    db.add(tweet_model)
    db.commit()


@router.delete("/{tweet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_dependency, db: db_dependency, tweet_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=401, detail='Authentication Failed')
    tweet_model = db.query(Tweets).filter(Tweets.id == tweet_id).filter(Tweets.owner_id == user.get('id')).first()
    if tweet_model is None:
        raise HTTPException(status_code=404, detail='Tweet not found.')
    db.query(Tweets).filter(Tweets.id == tweet_id).filter(Tweets.owner_id == user.get('id')).delete()

    db.commit()


