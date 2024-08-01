from sqlalchemy import create_engine, StaticPool, text
from sqlalchemy.orm import sessionmaker
from ..database import Base
from ..main import app
from fastapi.testclient import TestClient
import pytest
from ..models import Tweets, Users
from ..routers.auth import bcrypt_context
from fastapi import Request


SQLALCHEMY_DATABASE_URL = 'postgresql://postgres:test1234!@localhost/test_blog_database'

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def override_get_current_user(request: Request):
    return {'username': 'testuser', 'id': '123'}


client = TestClient(app)


@pytest.fixture
def test_user():
    user = Users(
        email="test@example.com",
        username="testuser",
        first_name="Test",
        last_name="User",
        hashed_password=bcrypt_context.hash("testpassword"),
        has_pp=False,
        is_active=True,
        role="user",
        phone_number="1234567890"
    )

    db = TestingSessionLocal()
    db.add(user)
    db.commit()
    yield user
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM users;"))
        connection.commit()


@pytest.fixture
def test_tweet():
    tweet = Tweets(
        new_tweet="This is a test tweet",
        liked=False,
        has_image=False,
        image_id=None,
        owner_id=test_user.id,
        retweeted=False,
        op_id=None,
        op_username=None
    )

    db = TestingSessionLocal()
    db.add(tweet)
    db.commit()
    yield tweet
    with engine.connect() as connection:
        connection.execute(text("DELETE FROM todos;"))
        connection.commit()


