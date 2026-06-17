from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

db_url = get_settings().database_url
engine = create_engine(db_url, echo=get_settings().debug)


class Base(DeclarativeBase):
    pass


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionLocal = sessionmaker(engine, expire_on_commit=False)
