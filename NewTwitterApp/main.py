from fastapi import FastAPI
from .models import Base
from .database import engine
from .routers import auth, tweets, admin, users
from starlette.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from starlette import status

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="./NewTwitterApp/static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url='/tweets', status_code=status.HTTP_302_FOUND)

app.include_router(auth.router)
app.include_router(tweets.router)
app.include_router(admin.router)
app.include_router(users.router)