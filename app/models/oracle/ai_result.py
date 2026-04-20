from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Float
from app.db.oracle import Base


class AIResult(Base):
    __tablename__ = "ai_result"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("growth_batch.id"))

    inference_id = Column(String(100), nullable=False)
    model_version = Column(String(50))

    result_type = Column(String(50), nullable=False)
    result_value = Column(String(100))

    confidence = Column(Float)
    severity = Column(Integer)

    is_alert_sent = Column(Integer, default=0)

    captured_at = Column(DateTime)
    inferred_at = Column(DateTime)

    # recorded_at = Column(DateTime)