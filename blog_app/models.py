from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from .database import Base

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True)
    username = Column(String, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    hashed_password = Column(String)
    has_pp = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default=None)
    phone_number = Column(String)

    tweets = relationship("Tweets", back_populates="user")


class Tweets(Base):
    __tablename__ = 'tweets'

    id = Column(Integer, primary_key=True, index=True)
    new_tweet = Column(String)
    liked = Column(Boolean, default=False)
    has_image = Column(Boolean, default=False)
    image_id = Column(Integer, nullable=True, default=None)
    owner_id = Column(Integer, ForeignKey("users.id"))
    retweeted = Column(Boolean, default=False)
    op_id = Column(Integer, nullable=True, default=None)
    op_username = Column(String, nullable=True, default=None)

    user = relationship("Users", back_populates="tweets")

    @hybrid_property
    def has_pp(self):
        return self.user.has_pp

    @hybrid_property
    def username(self):
        return self.user.username
