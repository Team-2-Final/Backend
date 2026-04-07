from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

DATABASE_URL = (
    f"oracle+oracledb://{settings.oracle_user}:{settings.oracle_password}@{settings.oracle_dsn}"
)

engine = create_engine(
    DATABASE_URL,
    echo=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_oracle_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()