from fastapi import APIRouter
from sqlalchemy import select

from app.database import *
from app.bookings.models import *
from app.config import *

engine = create_async_engine(settings.DATABASE_URL)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
)


@router.get("")
async def get_bookings():
    pass
