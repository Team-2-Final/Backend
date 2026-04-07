from sqlalchemy import Column, Integer, String, Sequence, DateTime
from app.db.oracle import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column("token_id", Integer, Sequence("refresh_tokens_seq"), primary_key=True)
    user_id = Column(Integer, nullable=False)
    refresh_token = Column(String(500), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    revoked = Column(Integer, nullable=False, default=0)