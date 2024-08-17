import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = 'postgresql://postgres:test1234!@db:5432/NewTwitterDatabase'

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def test_db_connection():
    try:
        db = SessionLocal()
        db.execute(text('SELECT 1'))
        logger.info("Database connection successfully established.")
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
    finally:
        db.close()

