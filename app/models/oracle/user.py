from sqlalchemy import Column, Integer, String, Sequence, DateTime
from app.db.oracle import Base


class User(Base):
    __tablename__ = "users"

    id = Column("user_id", Integer, Sequence("users_seq"), primary_key=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    email = Column(String(100), nullable=False, unique=True)
    username = Column("name", String(50), nullable=False)
    hashed_password = Column("password", String(255), nullable=False)
    role = Column(String(20), nullable=False)