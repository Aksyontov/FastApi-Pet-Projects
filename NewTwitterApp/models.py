from .database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey


class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True)
    username = Column(String, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String, default=None)
    phone_number = Column(String)


class Tweets(Base):
    __tablename__ = 'tweets'

    id = Column(Integer, primary_key=True, index=True)
    new_tweet = Column(String)
    liked = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = Column(String, ForeignKey("users.username"))