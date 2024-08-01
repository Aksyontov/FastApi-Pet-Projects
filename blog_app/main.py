from fastapi import FastAPI
from .models import Base
from .database import engine
from .routers import auth, tweets, users
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from starlette import status
import sentry_sdk

sentry_sdk.init(
    dsn="https://d9ff45bcc9fe05f99b11b169d4c0db71@o4507694747025408.ingest.us.sentry.io/4507694750957568",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="./blog_app/static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)

app.include_router(auth.router)
app.include_router(tweets.router)
app.include_router(users.router)
